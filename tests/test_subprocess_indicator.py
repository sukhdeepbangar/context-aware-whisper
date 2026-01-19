"""
Tests for Subprocess Indicator

Tests the subprocess-based recording indicator which runs in a separate
process to prevent focus stealing on macOS.
"""

import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest


# =============================================================================
# Tests for SubprocessIndicator Client
# =============================================================================


class TestSubprocessIndicatorClientStructure:
    """Tests for SubprocessIndicator client class structure."""

    def test_subprocess_indicator_client_exists(self):
        """Test that SubprocessIndicator class exists."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        assert SubprocessIndicator is not None

    def test_subprocess_indicator_has_required_methods(self):
        """Test that SubprocessIndicator has all required methods."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        required_methods = ['start', 'stop', 'set_state']
        for method in required_methods:
            assert hasattr(SubprocessIndicator, method), f"Missing method: {method}"
            assert callable(getattr(SubprocessIndicator, method)), f"{method} should be callable"

    def test_subprocess_indicator_has_properties(self):
        """Test that SubprocessIndicator has required properties."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        assert hasattr(indicator, 'is_running')
        assert hasattr(indicator, 'current_state')

    def test_subprocess_indicator_can_be_instantiated(self):
        """Test that SubprocessIndicator can be instantiated."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        assert indicator is not None
        assert indicator._started is False
        assert indicator._process is None

    def test_subprocess_indicator_initial_state_is_idle(self):
        """Test that initial state is idle."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        assert indicator.current_state == "idle"


class TestSubprocessIndicatorClientLifecycle:
    """Tests for SubprocessIndicator lifecycle management."""

    def test_start_returns_false_when_script_not_found(self):
        """Test that start returns False when script doesn't exist."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()

        with patch.object(Path, 'exists', return_value=False):
            result = indicator.start()

        assert result is False
        assert indicator._started is False

    def test_stop_when_not_started(self):
        """Test that stop doesn't crash when not started."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        # Should not raise exception
        indicator.stop()

    def test_set_state_when_not_started(self):
        """Test that set_state doesn't crash when not started."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        # Should not raise exception
        indicator.set_state("recording")

    def test_start_is_idempotent(self):
        """Test that calling start multiple times returns True after first success."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        indicator._started = True  # Simulate already started

        result = indicator.start()
        assert result is True

    def test_is_running_false_when_not_started(self):
        """Test that is_running is False when not started."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        assert indicator.is_running is False

    def test_context_manager_protocol(self):
        """Test that SubprocessIndicator supports context manager protocol."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        assert hasattr(indicator, '__enter__')
        assert hasattr(indicator, '__exit__')


class TestSubprocessIndicatorClientStateManagement:
    """Tests for SubprocessIndicator state management."""

    def test_valid_states(self):
        """Test that all valid states are accepted."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        valid_states = ["idle", "recording", "transcribing", "success", "error"]
        indicator = SubprocessIndicator()

        for state in valid_states:
            # Should not raise exception
            indicator.set_state(state)

    def test_invalid_state_ignored(self):
        """Test that invalid states are silently ignored."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        # Should not raise exception
        indicator.set_state("invalid_state")
        # State should remain idle
        assert indicator.current_state == "idle"

    @patch('context_aware_whisper.ui.subprocess_indicator_client.subprocess.Popen')
    def test_set_state_writes_to_stdin(self, mock_popen):
        """Test that set_state writes command to subprocess stdin."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline.return_value = "ready"
        mock_popen.return_value = mock_process

        indicator = SubprocessIndicator()
        indicator._started = True
        indicator._process = mock_process

        indicator.set_state("recording")

        mock_process.stdin.write.assert_called_with("recording\n")
        mock_process.stdin.flush.assert_called()

    def test_redundant_state_updates_skipped(self):
        """Test that redundant state updates are skipped for efficiency."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()

        indicator = SubprocessIndicator()
        indicator._started = True
        indicator._process = mock_process
        indicator._current_state = "recording"

        # Set same state again
        indicator.set_state("recording")

        # Should NOT write to stdin (redundant)
        mock_process.stdin.write.assert_not_called()

    def test_success_error_states_always_sent(self):
        """Test that success/error states are always sent even if repeated."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()

        indicator = SubprocessIndicator()
        indicator._started = True
        indicator._process = mock_process
        indicator._current_state = "success"

        # Set success again
        indicator.set_state("success")

        # Should write to stdin (not skipped for success/error)
        mock_process.stdin.write.assert_called_with("success\n")


class TestSubprocessIndicatorClientConstants:
    """Tests for SubprocessIndicator constants."""

    def test_ready_timeout_exists(self):
        """Test that READY_TIMEOUT constant exists."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        assert hasattr(SubprocessIndicator, 'READY_TIMEOUT')
        assert SubprocessIndicator.READY_TIMEOUT > 0

    def test_stop_timeout_exists(self):
        """Test that STOP_TIMEOUT constant exists."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        assert hasattr(SubprocessIndicator, 'STOP_TIMEOUT')
        assert SubprocessIndicator.STOP_TIMEOUT > 0


# =============================================================================
# Tests for Subprocess Indicator Script (Unit Tests)
# =============================================================================


class TestSubprocessIndicatorScriptStructure:
    """Tests for subprocess_indicator.py script structure."""

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_subprocess_indicator_script_exists(self):
        """Test that subprocess_indicator.py exists."""
        script_path = Path(__file__).parent.parent / "src" / "context-aware-whisper" / "ui" / "subprocess_indicator.py"
        assert script_path.exists(), f"Script not found at {script_path}"

    def test_subprocess_indicator_script_is_importable_with_mocks(self):
        """Test that subprocess_indicator.py can be parsed (not executed on non-macOS)."""
        import ast

        script_path = Path(__file__).parent.parent / "src" / "context-aware-whisper" / "ui" / "subprocess_indicator.py"
        if script_path.exists():
            with open(script_path) as f:
                code = f.read()
            # Should parse without syntax errors
            ast.parse(code)


class TestSubprocessIndicatorVisualDesign:
    """Tests for visual design constants in subprocess indicator."""

    def test_visual_constants_defined(self):
        """Test that visual design constants are defined in the script."""
        script_path = Path(__file__).parent.parent / "src" / "context-aware-whisper" / "ui" / "subprocess_indicator.py"
        if script_path.exists():
            with open(script_path) as f:
                code = f.read()

            # Check for key constants
            assert "INDICATOR_WIDTH" in code
            assert "INDICATOR_HEIGHT" in code
            assert "CORNER_RADIUS" in code
            assert "TOP_MARGIN" in code
            assert "BACKGROUND_COLOR" in code

    def test_color_constants_defined(self):
        """Test that color constants are defined in the script."""
        script_path = Path(__file__).parent.parent / "src" / "context-aware-whisper" / "ui" / "subprocess_indicator.py"
        if script_path.exists():
            with open(script_path) as f:
                code = f.read()

            # Check for color constants
            assert "COLOR_RED" in code
            assert "COLOR_ORANGE" in code
            assert "COLOR_GREEN" in code


# =============================================================================
# Tests for Integration with CAWUI
# =============================================================================


class TestCAWUISubprocessIntegration:
    """Tests for CAWUI integration with subprocess indicator."""

    def test_subprocess_indicator_available_flag_exists(self):
        """Test that SUBPROCESS_INDICATOR_AVAILABLE flag exists in app.py."""
        from context_aware_whisper.ui import app

        assert hasattr(app, 'SUBPROCESS_INDICATOR_AVAILABLE')

    def test_caw_ui_has_subprocess_indicator_attribute(self):
        """Test that CAWUI has _subprocess_indicator attribute."""
        from context_aware_whisper.ui.app import CAWUI

        ui = CAWUI()
        assert hasattr(ui, '_subprocess_indicator')

    def test_caw_ui_subprocess_indicator_initially_none(self):
        """Test that _subprocess_indicator is initially None."""
        from context_aware_whisper.ui.app import CAWUI

        ui = CAWUI()
        assert ui._subprocess_indicator is None

    @patch('context_aware_whisper.ui.app.SUBPROCESS_INDICATOR_AVAILABLE', False)
    def test_subprocess_indicator_not_started_when_unavailable(self):
        """Test that subprocess indicator is not started on non-macOS."""
        from context_aware_whisper.ui.app import CAWUI

        with patch('context_aware_whisper.ui.app.tk.Tk') as mock_tk:
            mock_root = MagicMock()
            mock_tk.return_value = mock_root

            ui = CAWUI()
            ui.start()

            assert ui._subprocess_indicator is None


class TestSubprocessIndicatorIPCProtocol:
    """Tests for IPC protocol between client and subprocess."""

    def test_valid_commands(self):
        """Test that all valid IPC commands are documented."""
        valid_commands = ['recording', 'transcribing', 'success', 'error', 'idle', 'exit']

        script_path = Path(__file__).parent.parent / "src" / "context-aware-whisper" / "ui" / "subprocess_indicator.py"
        if script_path.exists():
            with open(script_path) as f:
                code = f.read()

            for cmd in valid_commands:
                assert f'"{cmd}"' in code or f"'{cmd}'" in code, f"Command {cmd} should be handled"

    def test_ready_signal_sent_on_startup(self):
        """Test that subprocess sends 'ready' signal on startup."""
        script_path = Path(__file__).parent.parent / "src" / "context-aware-whisper" / "ui" / "subprocess_indicator.py"
        if script_path.exists():
            with open(script_path) as f:
                code = f.read()

            assert 'print("ready"' in code or "print('ready'" in code


class TestSubprocessIndicatorErrorHandling:
    """Tests for error handling in subprocess indicator."""

    def test_client_handles_process_death(self):
        """Test that client handles subprocess death gracefully."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process exited

        indicator = SubprocessIndicator()
        indicator._started = True
        indicator._process = mock_process

        # Mock _try_restart to prevent actual subprocess spawning
        with patch.object(indicator, '_try_restart'):
            # Should not raise exception
            indicator.set_state("recording")

    def test_client_handles_broken_pipe(self):
        """Test that client handles broken pipe gracefully."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin.write.side_effect = BrokenPipeError()

        indicator = SubprocessIndicator()
        indicator._started = True
        indicator._process = mock_process

        # Mock _try_restart to prevent actual subprocess spawning
        with patch.object(indicator, '_try_restart'):
            # Should not raise exception
            indicator.set_state("recording")
            assert indicator._started is False  # Should mark as not started


class TestSubprocessIndicatorCleanup:
    """Tests for subprocess indicator cleanup."""

    def test_stop_sends_exit_command(self):
        """Test that stop sends exit command to subprocess."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()

        indicator = SubprocessIndicator()
        indicator._started = True
        indicator._process = mock_process

        indicator.stop()

        mock_process.stdin.write.assert_called_with("exit\n")

    def test_stop_waits_for_process(self):
        """Test that stop waits for process to terminate."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        mock_process = MagicMock()
        mock_process.poll.return_value = None

        indicator = SubprocessIndicator()
        indicator._started = True
        indicator._process = mock_process

        indicator.stop()

        mock_process.wait.assert_called()

    def test_del_calls_stop(self):
        """Test that __del__ calls stop for cleanup."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        indicator._started = True
        indicator._process = MagicMock()

        # __del__ should call stop
        del indicator


# =============================================================================
# Tests for Thread Safety
# =============================================================================


class TestSubprocessIndicatorThreadSafety:
    """Tests for thread safety in subprocess indicator."""

    def test_client_has_lock(self):
        """Test that SubprocessIndicator has a threading lock."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator

        indicator = SubprocessIndicator()
        assert hasattr(indicator, '_lock')

    def test_set_state_uses_lock(self):
        """Test that set_state uses lock for thread safety."""
        from context_aware_whisper.ui.subprocess_indicator_client import SubprocessIndicator
        import threading

        indicator = SubprocessIndicator()
        indicator._started = True

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        indicator._process = mock_process

        # Replace lock with a mock to verify it's used
        original_lock = indicator._lock
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)
        indicator._lock = mock_lock

        indicator.set_state("recording")

        # Lock should have been acquired
        mock_lock.__enter__.assert_called()
        mock_lock.__exit__.assert_called()
