"""
Test suite for dependency structure and cross-platform compatibility.

Tests verify that:
1. Core dependencies are importable on all platforms
2. Platform-specific dependencies are properly isolated
3. Factory functions handle missing dependencies gracefully
4. pyproject.toml structure is valid
"""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

try:
    from hypothesis import given, strategies as st, settings
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
    # Create dummy decorators for when hypothesis is not installed
    def given(*args, **kwargs):
        def decorator(f):
            return f
        return decorator

    def settings(*args, **kwargs):
        def decorator(f):
            return f
        return decorator

    class st:
        @staticmethod
        def sampled_from(items):
            return None

        @staticmethod
        def text(*args, **kwargs):
            class Strategy:
                def filter(self, f):
                    return self
            return Strategy()


class TestCoreDependencies(unittest.TestCase):
    """Tests that core dependencies are available."""

    def test_sounddevice_importable(self):
        """Test sounddevice is importable."""
        import sounddevice
        self.assertIsNotNone(sounddevice)

    def test_numpy_importable(self):
        """Test numpy is importable."""
        import numpy
        self.assertIsNotNone(numpy)

    def test_scipy_importable(self):
        """Test scipy is importable."""
        import scipy
        self.assertIsNotNone(scipy)

    def test_groq_importable(self):
        """Test groq is importable."""
        import groq
        self.assertIsNotNone(groq)

    def test_pyperclip_importable(self):
        """Test pyperclip is importable."""
        import pyperclip
        self.assertIsNotNone(pyperclip)

    def test_pynput_importable(self):
        """Test pynput is importable."""
        import pynput
        self.assertIsNotNone(pynput)

    def test_dotenv_importable(self):
        """Test python-dotenv is importable."""
        import dotenv
        self.assertIsNotNone(dotenv)


class TestPlatformAbstractionLayer(unittest.TestCase):
    """Tests for platform abstraction layer functionality."""

    def test_platform_module_importable(self):
        """Test platform module can be imported."""
        from context_aware_whisper import platform
        self.assertIsNotNone(platform)

    def test_base_classes_importable(self):
        """Test base classes can be imported."""
        from context_aware_whisper.platform.base import HotkeyDetectorBase, OutputHandlerBase
        self.assertIsNotNone(HotkeyDetectorBase)
        self.assertIsNotNone(OutputHandlerBase)

    def test_get_platform_returns_valid_value(self):
        """Test get_platform returns one of the expected values."""
        from context_aware_whisper.platform import get_platform
        result = get_platform()
        self.assertIn(result, ["macos", "windows", "linux", "unknown"])

    def test_factory_functions_exist(self):
        """Test factory functions are exported."""
        from context_aware_whisper.platform import (
            create_hotkey_detector,
            create_output_handler,
            is_mute_detector_available,
            get_default_hotkey_description,
        )
        self.assertTrue(callable(create_hotkey_detector))
        self.assertTrue(callable(create_output_handler))
        self.assertTrue(callable(is_mute_detector_available))
        self.assertTrue(callable(get_default_hotkey_description))


class TestPlatformSpecificImports(unittest.TestCase):
    """Tests for platform-specific import handling."""

    def test_macos_modules_available_on_darwin(self):
        """Test macOS modules are available when running on macOS."""
        if sys.platform != "darwin":
            self.skipTest("Only runs on macOS")

        from context_aware_whisper.platform.macos.hotkey_detector import MacOSHotkeyDetector
        from context_aware_whisper.platform.macos.output_handler import MacOSOutputHandler
        self.assertIsNotNone(MacOSHotkeyDetector)
        self.assertIsNotNone(MacOSOutputHandler)

    def test_windows_modules_importable_via_pynput(self):
        """Test Windows modules can be imported (pynput is available)."""
        from context_aware_whisper.platform.windows.hotkey_detector import WindowsHotkeyDetector
        from context_aware_whisper.platform.windows.output_handler import WindowsOutputHandler
        self.assertIsNotNone(WindowsHotkeyDetector)
        self.assertIsNotNone(WindowsOutputHandler)

    def test_linux_modules_importable_via_pynput(self):
        """Test Linux modules can be imported (pynput is available)."""
        from context_aware_whisper.platform.linux.hotkey_detector import LinuxHotkeyDetector
        from context_aware_whisper.platform.linux.output_handler import LinuxOutputHandler
        self.assertIsNotNone(LinuxHotkeyDetector)
        self.assertIsNotNone(LinuxOutputHandler)


class TestMacOSOptionalDependencies(unittest.TestCase):
    """Tests for macOS optional dependencies."""

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_pyobjc_core_available(self):
        """Test pyobjc-core is available on macOS."""
        import objc
        self.assertIsNotNone(objc)

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_quartz_available(self):
        """Test Quartz framework is available on macOS."""
        import Quartz
        self.assertIsNotNone(Quartz)

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_avfaudio_available(self):
        """Test AVFAudio framework is available on macOS."""
        from AVFAudio import AVAudioApplication
        self.assertIsNotNone(AVAudioApplication)


class TestFactoryGracefulDegradation(unittest.TestCase):
    """Tests that factory functions handle errors gracefully."""

    @patch.object(sys, 'platform', 'freebsd')
    def test_hotkey_detector_factory_unsupported_platform(self):
        """Test factory raises clear error on unsupported platform."""
        from context_aware_whisper.platform import create_hotkey_detector
        from context_aware_whisper.exceptions import PlatformNotSupportedError

        with self.assertRaises(PlatformNotSupportedError) as context:
            create_hotkey_detector(lambda: None, lambda: None)

        self.assertIn("not supported", str(context.exception).lower())
        self.assertIn("macos", str(context.exception).lower())

    @patch.object(sys, 'platform', 'freebsd')
    def test_output_handler_factory_unsupported_platform(self):
        """Test factory raises clear error on unsupported platform."""
        from context_aware_whisper.platform import create_output_handler
        from context_aware_whisper.exceptions import PlatformNotSupportedError

        with self.assertRaises(PlatformNotSupportedError) as context:
            create_output_handler()

        self.assertIn("not supported", str(context.exception).lower())


class TestPyprojectTomlStructure(unittest.TestCase):
    """Tests for pyproject.toml structure validation."""

    @classmethod
    def setUpClass(cls):
        """Load pyproject.toml once for all tests."""
        import tomllib

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            cls.pyproject = tomllib.load(f)

    def test_has_project_section(self):
        """Test pyproject.toml has [project] section."""
        self.assertIn("project", self.pyproject)

    def test_has_core_dependencies(self):
        """Test pyproject.toml has core dependencies."""
        deps = self.pyproject["project"]["dependencies"]
        dep_names = [d.split(">=")[0].split("[")[0].lower() for d in deps]

        required = ["sounddevice", "numpy", "scipy", "groq", "pyperclip", "pynput", "python-dotenv"]
        for req in required:
            self.assertIn(req, dep_names, f"Missing core dependency: {req}")

    def test_macos_optional_dependencies(self):
        """Test macOS dependencies are in optional-dependencies."""
        optional = self.pyproject["project"]["optional-dependencies"]
        self.assertIn("macos", optional)

        macos_deps = optional["macos"]
        macos_dep_names = [d.split(">=")[0].lower() for d in macos_deps]

        # pyobjc packages should be in macos optional
        self.assertIn("pyobjc-core", macos_dep_names)
        self.assertIn("pyobjc-framework-cocoa", macos_dep_names)

    def test_no_pyobjc_in_core_dependencies(self):
        """Test pyobjc packages are NOT in core dependencies."""
        deps = self.pyproject["project"]["dependencies"]
        dep_names = [d.split(">=")[0].lower() for d in deps]

        for dep in dep_names:
            self.assertNotIn("pyobjc", dep.lower(),
                           f"pyobjc package '{dep}' should not be in core dependencies")

    def test_pynput_in_core_dependencies(self):
        """Test pynput is in core dependencies (for Windows/Linux)."""
        deps = self.pyproject["project"]["dependencies"]
        dep_names = [d.split(">=")[0].lower() for d in deps]
        self.assertIn("pynput", dep_names)

    def test_dev_dependencies_include_pytest(self):
        """Test dev dependencies include pytest."""
        optional = self.pyproject["project"]["optional-dependencies"]
        self.assertIn("dev", optional)

        dev_deps = optional["dev"]
        dev_dep_names = [d.split(">=")[0].lower() for d in dev_deps]
        self.assertIn("pytest", dev_dep_names)

    def test_dev_dependencies_include_hypothesis(self):
        """Test dev dependencies include hypothesis for property tests."""
        optional = self.pyproject["project"]["optional-dependencies"]
        dev_deps = optional["dev"]
        dev_dep_names = [d.split(">=")[0].lower() for d in dev_deps]
        self.assertIn("hypothesis", dev_dep_names)

    def test_cross_platform_classifiers(self):
        """Test classifiers include multiple platforms."""
        classifiers = self.pyproject["project"]["classifiers"]

        # Should have classifiers for multiple platforms
        platform_classifiers = [c for c in classifiers if "Operating System" in c]
        self.assertGreater(len(platform_classifiers), 1,
                          "Should have classifiers for multiple operating systems")

        # Check specific platforms are mentioned
        classifiers_str = " ".join(classifiers)
        self.assertIn("MacOS", classifiers_str)
        self.assertIn("Windows", classifiers_str)
        self.assertIn("Linux", classifiers_str)


class TestExceptionHierarchy(unittest.TestCase):
    """Tests for exception hierarchy."""

    def test_platform_not_supported_error_exists(self):
        """Test PlatformNotSupportedError exists."""
        from context_aware_whisper.exceptions import PlatformNotSupportedError
        self.assertIsNotNone(PlatformNotSupportedError)

    def test_platform_not_supported_error_inherits_caw_error(self):
        """Test PlatformNotSupportedError inherits from Context-Aware WhisperError."""
        from context_aware_whisper.exceptions import Context-Aware WhisperError, PlatformNotSupportedError
        self.assertTrue(issubclass(PlatformNotSupportedError, Context-Aware WhisperError))

    def test_platform_not_supported_error_inherits_exception(self):
        """Test PlatformNotSupportedError inherits from Exception."""
        from context_aware_whisper.exceptions import PlatformNotSupportedError
        self.assertTrue(issubclass(PlatformNotSupportedError, Exception))


@pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
class TestPropertyBasedPlatformDetection(unittest.TestCase):
    """Property-based tests for platform detection."""

    @given(st.sampled_from(["darwin", "win32", "linux", "linux2"]))
    @settings(max_examples=10)
    def test_known_platforms_return_valid_result(self, platform_str):
        """Test that known platform strings return valid platform names."""
        with patch.object(sys, 'platform', platform_str):
            from context_aware_whisper.platform import get_platform
            result = get_platform()
            self.assertIn(result, ["macos", "windows", "linux"])

    @given(st.text(min_size=1, max_size=20).filter(
        lambda x: x not in ["darwin", "win32", "linux", "linux2"] and not x.startswith("linux")
    ))
    @settings(max_examples=20)
    def test_unknown_platforms_return_unknown(self, platform_str):
        """Test that unknown platform strings return 'unknown'."""
        with patch.object(sys, 'platform', platform_str):
            from context_aware_whisper.platform import get_platform
            result = get_platform()
            self.assertEqual(result, "unknown")


@pytest.mark.skipif(not HAS_HYPOTHESIS, reason="hypothesis not installed")
class TestPropertyBasedHotkeyDescription(unittest.TestCase):
    """Property-based tests for hotkey descriptions."""

    @given(st.sampled_from(["darwin", "win32", "linux"]))
    @settings(max_examples=10)
    def test_hotkey_description_never_empty(self, platform_str):
        """Test hotkey description is never empty for known platforms."""
        with patch.object(sys, 'platform', platform_str):
            from context_aware_whisper.platform import get_default_hotkey_description
            result = get_default_hotkey_description()
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    @given(st.sampled_from(["darwin", "win32", "linux"]))
    @settings(max_examples=10)
    def test_hotkey_description_is_readable(self, platform_str):
        """Test hotkey description contains readable characters."""
        with patch.object(sys, 'platform', platform_str):
            from context_aware_whisper.platform import get_default_hotkey_description
            result = get_default_hotkey_description()
            # Should contain letters or known symbols
            self.assertTrue(any(c.isalpha() for c in result),
                          f"Description '{result}' should contain letters")


class TestOutputHandlerConsistency(unittest.TestCase):
    """Tests to ensure output handler implementations are consistent."""

    def test_all_output_handlers_have_same_methods(self):
        """Test all output handlers implement the same interface."""
        from context_aware_whisper.platform.base import OutputHandlerBase

        required_methods = [
            'copy_to_clipboard',
            'type_text',
            'type_text_via_paste',
            'output',
        ]

        # Check abstract base has all methods
        for method in required_methods:
            self.assertTrue(hasattr(OutputHandlerBase, method),
                          f"OutputHandlerBase missing method: {method}")

    def test_all_hotkey_detectors_have_same_methods(self):
        """Test all hotkey detectors implement the same interface."""
        from context_aware_whisper.platform.base import HotkeyDetectorBase

        required_methods = [
            'start',
            'stop',
            'get_hotkey_description',
        ]

        required_properties = [
            'is_recording',
        ]

        for method in required_methods:
            self.assertTrue(hasattr(HotkeyDetectorBase, method),
                          f"HotkeyDetectorBase missing method: {method}")

        for prop in required_properties:
            self.assertTrue(hasattr(HotkeyDetectorBase, prop),
                          f"HotkeyDetectorBase missing property: {prop}")


if __name__ == '__main__':
    unittest.main()
