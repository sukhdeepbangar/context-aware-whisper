"""Tests for scripts/verify_feature.py verification tool."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, strategies as st, settings

# Add scripts directory to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from verify_feature import (
    Verifier,
    VerificationResult,
    MODULE_TEST_MAP,
    colorize,
)


class TestColorize:
    """Tests for colorize function."""

    def test_colorize_with_tty(self):
        """colorize applies color when stdout is TTY."""
        with patch("sys.stdout.isatty", return_value=True):
            result = colorize("test", "green")
            assert "\033[92m" in result
            assert "test" in result
            assert "\033[0m" in result

    def test_colorize_without_tty(self):
        """colorize returns plain text when stdout is not TTY."""
        with patch("sys.stdout.isatty", return_value=False):
            result = colorize("test", "green")
            assert result == "test"
            assert "\033[" not in result

    def test_colorize_invalid_color(self):
        """colorize handles invalid color gracefully."""
        with patch("sys.stdout.isatty", return_value=True):
            result = colorize("test", "invalid_color")
            assert "test" in result


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_creation(self):
        """VerificationResult can be created with all fields."""
        result = VerificationResult(
            name="Test",
            passed=True,
            message="All good",
            details="Some details",
        )
        assert result.name == "Test"
        assert result.passed is True
        assert result.message == "All good"
        assert result.details == "Some details"

    def test_default_details(self):
        """VerificationResult details defaults to empty string."""
        result = VerificationResult(
            name="Test",
            passed=False,
            message="Failed",
        )
        assert result.details == ""


class TestVerifier:
    """Tests for Verifier class."""

    @pytest.fixture
    def verifier(self, tmp_path):
        """Create a verifier with a temp project root."""
        return Verifier(project_root=tmp_path)

    @pytest.fixture
    def real_verifier(self):
        """Create a verifier with the real project root."""
        project_root = Path(__file__).parent.parent
        return Verifier(project_root=project_root)

    def test_init_default_project_root(self):
        """Verifier uses script parent as default project root."""
        v = Verifier()
        assert v.project_root.exists()

    def test_init_custom_project_root(self, tmp_path):
        """Verifier accepts custom project root."""
        v = Verifier(project_root=tmp_path)
        assert v.project_root == tmp_path

    def test_results_initially_empty(self, verifier):
        """Verifier starts with empty results list."""
        assert verifier.results == []


class TestModuleTestMapping:
    """Tests for file-to-test mapping."""

    @pytest.fixture
    def verifier(self):
        """Create a verifier with real project root."""
        project_root = Path(__file__).parent.parent
        return Verifier(project_root=project_root)

    def test_audio_recorder_mapping(self, verifier):
        """audio_recorder.py maps to its test files."""
        tests = verifier.map_files_to_tests(["src/context_aware_whisper/audio_recorder.py"])
        assert any("audio_recorder" in t for t in tests)

    def test_transcriber_mapping(self, verifier):
        """transcriber.py maps to its test files."""
        tests = verifier.map_files_to_tests(["src/context_aware_whisper/transcriber.py"])
        assert any("transcriber" in t for t in tests)

    def test_output_handler_mapping(self, verifier):
        """output_handler.py maps to its test files."""
        tests = verifier.map_files_to_tests(["src/context_aware_whisper/output_handler.py"])
        assert any("output_handler" in t for t in tests)

    def test_test_file_includes_itself(self, verifier):
        """Test files map to themselves."""
        tests = verifier.map_files_to_tests(["tests/test_audio_recorder.py"])
        assert "tests/test_audio_recorder.py" in tests

    def test_unrelated_file_returns_empty(self, verifier):
        """Unrelated files return empty set."""
        tests = verifier.map_files_to_tests(["README.md"])
        assert len(tests) == 0

    def test_multiple_files(self, verifier):
        """Multiple files map to multiple test sets."""
        tests = verifier.map_files_to_tests([
            "src/context_aware_whisper/audio_recorder.py",
            "src/context_aware_whisper/output_handler.py",
        ])
        has_audio = any("audio_recorder" in t for t in tests)
        has_output = any("output_handler" in t for t in tests)
        assert has_audio and has_output


class TestModuleTestMapCompleteness:
    """Property-based tests for MODULE_TEST_MAP."""

    @given(st.sampled_from(list(MODULE_TEST_MAP.keys())))
    @settings(max_examples=20)
    def test_all_modules_have_tests(self, module):
        """Every module in the map has at least one test."""
        tests = MODULE_TEST_MAP[module]
        assert len(tests) > 0

    @given(st.sampled_from(list(MODULE_TEST_MAP.keys())))
    @settings(max_examples=20)
    def test_all_test_paths_are_valid_format(self, module):
        """All test paths follow the expected format."""
        tests = MODULE_TEST_MAP[module]
        for test_path in tests:
            assert test_path.startswith("tests/")
            assert test_path.endswith(".py")
            assert "test_" in test_path


class TestGetChangedFiles:
    """Tests for get_changed_files method."""

    @pytest.fixture
    def verifier(self, tmp_path):
        """Create verifier with temp directory (not a git repo)."""
        return Verifier(project_root=tmp_path)

    def test_returns_list(self, verifier):
        """get_changed_files returns a list."""
        files = verifier.get_changed_files()
        assert isinstance(files, list)

    def test_non_git_directory_returns_empty(self, verifier):
        """Non-git directory returns empty list."""
        files = verifier.get_changed_files()
        assert files == []


class TestVerifierIntegration:
    """Integration tests for Verifier with real project."""

    @pytest.fixture
    def verifier(self):
        """Create verifier with real project root."""
        project_root = Path(__file__).parent.parent
        return Verifier(project_root=project_root)

    def test_run_pytest_returns_tuple(self, verifier):
        """run_pytest returns (returncode, output) tuple."""
        # Run a quick test that should pass
        returncode, output = verifier.run_pytest(
            test_paths=["tests/test_init.py"],
            extra_args=["--collect-only"],
        )
        assert isinstance(returncode, int)
        assert isinstance(output, str)

    def test_check_unit_tests_returns_result(self, verifier):
        """check_unit_tests returns a VerificationResult."""
        # Mock run_pytest to avoid actually running tests
        with patch.object(verifier, "run_pytest", return_value=(0, "All passed")):
            result = verifier.check_unit_tests()
            assert isinstance(result, VerificationResult)
            assert result.name == "Unit Tests"
            assert result.passed is True

    def test_check_unit_tests_failure(self, verifier):
        """check_unit_tests returns failed result on test failure."""
        with patch.object(verifier, "run_pytest", return_value=(1, "Test failed")):
            result = verifier.check_unit_tests()
            assert result.passed is False
            assert "failed" in result.message.lower()


class TestVerifierVerifyMethod:
    """Tests for the main verify method."""

    @pytest.fixture
    def verifier(self):
        """Create verifier with real project root."""
        project_root = Path(__file__).parent.parent
        return Verifier(project_root=project_root)

    def test_verify_unit_only(self, verifier):
        """verify with unit_only runs unit tests."""
        with patch.object(verifier, "check_unit_tests") as mock_check:
            mock_check.return_value = VerificationResult(
                name="Unit Tests",
                passed=True,
                message="All passed",
            )
            with patch("builtins.print"):  # Suppress output
                result = verifier.verify(unit_only=True)
            assert result is True
            mock_check.assert_called_once()

    def test_verify_integration_only(self, verifier):
        """verify with integration_only runs integration tests."""
        with patch.object(verifier, "check_integration_tests") as mock_check:
            mock_check.return_value = VerificationResult(
                name="Integration Tests",
                passed=True,
                message="All passed",
            )
            with patch("builtins.print"):
                result = verifier.verify(integration_only=True)
            assert result is True
            mock_check.assert_called_once()

    def test_verify_returns_false_on_failure(self, verifier):
        """verify returns False when tests fail."""
        with patch.object(verifier, "check_unit_tests") as mock_check:
            mock_check.return_value = VerificationResult(
                name="Unit Tests",
                passed=False,
                message="Tests failed",
            )
            with patch("builtins.print"):
                result = verifier.verify(unit_only=True)
            assert result is False

    def test_verify_all_runs_both(self, verifier):
        """verify with run_all runs both unit and integration tests."""
        with patch.object(verifier, "check_unit_tests") as mock_unit:
            with patch.object(verifier, "check_integration_tests") as mock_int:
                mock_unit.return_value = VerificationResult(
                    name="Unit Tests",
                    passed=True,
                    message="All passed",
                )
                mock_int.return_value = VerificationResult(
                    name="Integration Tests",
                    passed=True,
                    message="All passed",
                )
                with patch("builtins.print"):
                    result = verifier.verify(run_all=True)
                assert result is True
                mock_unit.assert_called_once()
                mock_int.assert_called_once()
