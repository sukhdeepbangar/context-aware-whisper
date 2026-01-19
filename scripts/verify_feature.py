#!/usr/bin/env python3
"""
Verification Tool for HandFree.

Run targeted tests based on changed files and perform verification checks
after feature implementations or bug fixes.

Usage:
    python scripts/verify_feature.py              # Auto-detect changes
    python scripts/verify_feature.py --all        # Run all tests
    python scripts/verify_feature.py --unit       # Unit tests only
    python scripts/verify_feature.py --integration # Integration tests only
    python scripts/verify_feature.py --file audio_recorder.py  # Tests for specific file
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Module-to-test mappings
MODULE_TEST_MAP: dict[str, list[str]] = {
    "audio_recorder": [
        "tests/test_audio_recorder.py",
        "tests/integration/test_audio_recorder_integration.py",
    ],
    "transcriber": [
        "tests/test_transcriber.py",
        "tests/test_transcriber_integration.py",
    ],
    "local_transcriber": [
        "tests/test_local_transcriber.py",
        "tests/integration/test_local_transcriber_integration.py",
    ],
    "output_handler": [
        "tests/test_output_handler.py",
        "tests/integration/test_output_handler_integration.py",
    ],
    "mute_detector": ["tests/test_mute_detector.py"],
    "history": ["tests/test_history_store.py"],
    "ui": [
        "tests/test_ui.py",
        "tests/test_animated_indicator.py",
        "tests/test_subprocess_indicator.py",
    ],
    "hotkey": [
        "tests/test_macos_hotkey_detector.py",
        "tests/test_linux_hotkey_detector.py",
        "tests/test_windows_hotkey_detector.py",
    ],
    "config": ["tests/test_config.py"],
    "main": ["tests/test_z_main.py", "tests/test_e2e.py"],
    "model_manager": ["tests/test_model_manager.py"],
    "platform": ["tests/test_platform.py"],
}

# ANSI color codes
COLORS = {
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "cyan": "\033[96m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def colorize(text: str, color: str) -> str:
    """Apply ANSI color to text if stdout is a TTY."""
    if not sys.stdout.isatty():
        return text
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


@dataclass
class VerificationResult:
    """Result of a verification step."""

    name: str
    passed: bool
    message: str
    details: str = ""


class Verifier:
    """Runs verification checks for HandFree."""

    def __init__(self, project_root: Path | None = None):
        """Initialize verifier with project root."""
        self.project_root = project_root or Path(__file__).parent.parent
        self.results: list[VerificationResult] = []

    def get_changed_files(self, base_ref: str = "HEAD~1") -> list[str]:
        """Get list of changed files from git."""
        try:
            # Try to get changes from HEAD~1
            result = subprocess.run(
                ["git", "diff", "--name-only", base_ref],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            if result.returncode == 0 and result.stdout.strip():
                return [f for f in result.stdout.strip().split("\n") if f]

            # If no changes from HEAD~1, try staged changes
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            if result.returncode == 0 and result.stdout.strip():
                return [f for f in result.stdout.strip().split("\n") if f]

            # Try unstaged changes
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            if result.returncode == 0 and result.stdout.strip():
                return [f for f in result.stdout.strip().split("\n") if f]

            return []
        except Exception:
            return []

    def map_files_to_tests(self, files: list[str]) -> set[str]:
        """Map changed files to relevant test files."""
        tests: set[str] = set()

        for filepath in files:
            filename = Path(filepath).stem
            # Direct module match
            for module, module_tests in MODULE_TEST_MAP.items():
                if module in filename:
                    for test in module_tests:
                        test_path = self.project_root / test
                        if test_path.exists():
                            tests.add(test)

            # If it's a test file itself, include it
            if filepath.startswith("tests/") and filepath.endswith(".py"):
                test_path = self.project_root / filepath
                if test_path.exists():
                    tests.add(filepath)

            # If it's a source file, find its test
            if filepath.startswith("src/context_aware_whisper/") and filepath.endswith(".py"):
                module_name = Path(filepath).stem
                test_file = f"tests/test_{module_name}.py"
                test_path = self.project_root / test_file
                if test_path.exists():
                    tests.add(test_file)

        return tests

    def run_pytest(
        self,
        test_paths: list[str] | None = None,
        markers: str | None = None,
        extra_args: list[str] | None = None,
    ) -> tuple[int, str]:
        """Run pytest with given arguments."""
        cmd = [sys.executable, "-m", "pytest", "-v"]

        if markers:
            cmd.extend(["-m", markers])

        if test_paths:
            cmd.extend(test_paths)

        if extra_args:
            cmd.extend(extra_args)

        print(colorize(f"\nRunning: {' '.join(cmd)}", "cyan"))

        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        return result.returncode, result.stdout + result.stderr

    def check_unit_tests(self) -> VerificationResult:
        """Run all unit tests."""
        returncode, output = self.run_pytest(markers="not integration")
        return VerificationResult(
            name="Unit Tests",
            passed=returncode == 0,
            message="All unit tests passed" if returncode == 0 else "Unit tests failed",
            details=output if returncode != 0 else "",
        )

    def check_integration_tests(self) -> VerificationResult:
        """Run integration tests (skips hardware-dependent ones)."""
        returncode, output = self.run_pytest(
            test_paths=["tests/integration/"],
            markers="integration and not requires_microphone",
        )
        return VerificationResult(
            name="Integration Tests",
            passed=returncode == 0,
            message="Integration tests passed" if returncode == 0 else "Integration tests failed",
            details=output if returncode != 0 else "",
        )

    def check_targeted_tests(self, changed_files: list[str]) -> VerificationResult:
        """Run tests targeted at changed files."""
        tests = self.map_files_to_tests(changed_files)
        if not tests:
            return VerificationResult(
                name="Targeted Tests",
                passed=True,
                message="No targeted tests found for changed files",
            )

        returncode, output = self.run_pytest(test_paths=list(tests))
        return VerificationResult(
            name="Targeted Tests",
            passed=returncode == 0,
            message=f"Targeted tests ({len(tests)} files) passed" if returncode == 0 else "Targeted tests failed",
            details=output if returncode != 0 else "",
        )

    def verify(
        self,
        run_all: bool = False,
        unit_only: bool = False,
        integration_only: bool = False,
        specific_file: str | None = None,
    ) -> bool:
        """Run verification checks and return overall success."""
        print(colorize("\n=== HandFree Verification ===\n", "bold"))

        if specific_file:
            # Run tests for specific file
            tests = self.map_files_to_tests([specific_file])
            if tests:
                print(f"Running tests for: {specific_file}")
                returncode, output = self.run_pytest(test_paths=list(tests))
                result = VerificationResult(
                    name=f"Tests for {specific_file}",
                    passed=returncode == 0,
                    message="Tests passed" if returncode == 0 else "Tests failed",
                    details=output if returncode != 0 else "",
                )
                self.results.append(result)
            else:
                print(colorize(f"No tests found for {specific_file}", "yellow"))
                return True

        elif run_all:
            # Run all tests
            print("Running all tests...")
            self.results.append(self.check_unit_tests())
            self.results.append(self.check_integration_tests())

        elif unit_only:
            print("Running unit tests only...")
            self.results.append(self.check_unit_tests())

        elif integration_only:
            print("Running integration tests only...")
            self.results.append(self.check_integration_tests())

        else:
            # Auto-detect changes and run targeted tests
            changed_files = self.get_changed_files()
            if changed_files:
                print(f"Detected {len(changed_files)} changed files:")
                for f in changed_files[:10]:  # Show first 10
                    print(f"  - {f}")
                if len(changed_files) > 10:
                    print(f"  ... and {len(changed_files) - 10} more")
                print()
                self.results.append(self.check_targeted_tests(changed_files))
            else:
                print("No changed files detected, running unit tests...")
                self.results.append(self.check_unit_tests())

        return self._print_summary()

    def _print_summary(self) -> bool:
        """Print verification summary and return overall success."""
        print(colorize("\n=== Verification Summary ===\n", "bold"))

        all_passed = True
        for result in self.results:
            status = colorize("PASS", "green") if result.passed else colorize("FAIL", "red")
            print(f"[{status}] {result.name}: {result.message}")
            if result.details and not result.passed:
                # Print first few lines of failure details
                lines = result.details.split("\n")
                for line in lines[-20:]:  # Last 20 lines
                    print(f"       {line}")
            if not result.passed:
                all_passed = False

        print()
        if all_passed:
            print(colorize("All verification checks passed!", "green"))
        else:
            print(colorize("Some verification checks failed.", "red"))

        return all_passed


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify HandFree feature implementations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Auto-detect changes and run targeted tests
  %(prog)s --all              Run all tests (unit + integration)
  %(prog)s --unit             Run only unit tests
  %(prog)s --integration      Run only integration tests
  %(prog)s --file audio_recorder.py  Run tests for specific file
        """,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests",
    )
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests",
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Run tests for a specific file",
    )

    args = parser.parse_args()

    verifier = Verifier()
    success = verifier.verify(
        run_all=args.all,
        unit_only=args.unit,
        integration_only=args.integration,
        specific_file=args.file,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
