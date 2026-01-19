"""
Subprocess Indicator Client

Client wrapper for the subprocess-based recording indicator.
Manages subprocess lifecycle and provides a simple interface for state updates.
"""

import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional


class SubprocessIndicator:
    """
    Client for the subprocess-based recording indicator.

    This class manages the lifecycle of the indicator subprocess and provides
    a simple interface for updating the indicator state. The subprocess
    approach ensures the indicator can NEVER steal focus from other applications.

    Usage:
        indicator = SubprocessIndicator()
        if indicator.start():
            indicator.set_state("recording")
            # ... do work ...
            indicator.set_state("idle")
            indicator.stop()
    """

    # Timeout for subprocess ready signal
    READY_TIMEOUT = 5.0

    # Timeout for subprocess termination
    STOP_TIMEOUT = 2.0

    def __init__(self):
        """Initialize the subprocess indicator client."""
        self._process: Optional[subprocess.Popen] = None
        self._started = False
        self._lock = threading.Lock()
        self._current_state = "idle"

    def start(self) -> bool:
        """
        Launch the indicator subprocess.

        Returns:
            True if subprocess started successfully and is ready,
            False otherwise.
        """
        if self._started:
            return True

        with self._lock:
            if self._started:
                return True

            try:
                # Get the path to the subprocess script
                script_path = Path(__file__).parent / "subprocess_indicator.py"

                if not script_path.exists():
                    print(f"[Warning] Subprocess indicator script not found: {script_path}", file=sys.stderr)
                    return False

                # Launch subprocess
                self._process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # Line buffered
                )

                # Wait for "ready" signal
                start_time = time.time()
                while time.time() - start_time < self.READY_TIMEOUT:
                    if self._process.poll() is not None:
                        # Process exited prematurely
                        stderr_output = self._process.stderr.read() if self._process.stderr else ""
                        print(f"[Warning] Subprocess exited prematurely: {stderr_output}", file=sys.stderr)
                        self._process = None
                        return False

                    # Check if stdout has data
                    try:
                        # Non-blocking read attempt
                        line = self._process.stdout.readline()
                        if line.strip() == "ready":
                            self._started = True
                            return True
                    except Exception:
                        pass

                    time.sleep(0.01)

                # Timeout waiting for ready
                print("[Warning] Timeout waiting for subprocess indicator to be ready", file=sys.stderr)
                self._kill_process()
                return False

            except Exception as e:
                print(f"[Warning] Failed to start subprocess indicator: {e}", file=sys.stderr)
                self._process = None
                return False

    def set_state(self, state: str) -> None:
        """
        Set the indicator state.

        Args:
            state: One of "idle", "recording", "transcribing", "success", "error"
        """
        if not self._started or not self._process:
            return

        valid_states = ("idle", "recording", "transcribing", "success", "error")
        if state not in valid_states:
            return

        # Don't send redundant state updates (except for success/error which auto-hide)
        if state == self._current_state and state not in ("success", "error"):
            return

        with self._lock:
            if not self._process or self._process.poll() is not None:
                # Process died
                self._started = False
                self._try_restart()
                return

            try:
                self._process.stdin.write(f"{state}\n")
                self._process.stdin.flush()
                self._current_state = state
            except (BrokenPipeError, OSError) as e:
                # Process died or pipe broken
                print(f"[Warning] Failed to send state to subprocess: {e}", file=sys.stderr)
                self._started = False
                self._try_restart()

    def stop(self) -> None:
        """
        Terminate the subprocess cleanly.
        """
        if not self._started and not self._process:
            return

        with self._lock:
            self._started = False
            self._current_state = "idle"

            if self._process:
                try:
                    # Send exit command
                    if self._process.poll() is None:
                        try:
                            self._process.stdin.write("exit\n")
                            self._process.stdin.flush()
                        except (BrokenPipeError, OSError):
                            pass

                        # Wait for clean exit
                        try:
                            self._process.wait(timeout=self.STOP_TIMEOUT)
                        except subprocess.TimeoutExpired:
                            # Force kill if it doesn't exit cleanly
                            self._kill_process()
                finally:
                    self._process = None

    def _kill_process(self) -> None:
        """Force kill the subprocess."""
        if self._process:
            try:
                self._process.kill()
                self._process.wait(timeout=1.0)
            except Exception:
                pass
            self._process = None

    def _try_restart(self) -> None:
        """
        Attempt to restart the subprocess if it died unexpectedly.
        """
        self._kill_process()

        # Try to restart once
        try:
            if self.start():
                # Restore previous state if not idle
                if self._current_state != "idle":
                    state_to_restore = self._current_state
                    self._current_state = "idle"  # Reset to allow set_state
                    self.set_state(state_to_restore)
        except Exception:
            pass

    @property
    def is_running(self) -> bool:
        """Whether the subprocess is currently running."""
        return self._started and self._process is not None and self._process.poll() is None

    @property
    def current_state(self) -> str:
        """Current indicator state."""
        return self._current_state

    def __del__(self):
        """Cleanup on garbage collection."""
        try:
            self.stop()
        except Exception:
            pass

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
