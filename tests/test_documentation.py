"""
Tests for project documentation.

Validates that README.md exists, contains required sections,
and is consistent with the actual project structure.

These tests ensure documentation stays up-to-date with features:
- Cross-platform support (macOS, Windows, Linux)
- UI components (indicator, history panel)
- Environment variables
- Installation instructions
"""

import os
import re
from pathlib import Path

import pytest


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class TestReadmeExists:
    """Tests for README.md file existence and basic structure."""

    def test_readme_exists(self):
        """README.md file should exist in project root."""
        readme_path = PROJECT_ROOT / "README.md"
        assert readme_path.exists(), "README.md file not found in project root"

    def test_readme_not_empty(self):
        """README.md should not be empty."""
        readme_path = PROJECT_ROOT / "README.md"
        content = readme_path.read_text()
        assert len(content) > 100, "README.md appears to be too short"

    def test_readme_has_title(self):
        """README.md should start with a proper title."""
        readme_path = PROJECT_ROOT / "README.md"
        content = readme_path.read_text()
        # Should start with # Context-Aware Whisper
        assert content.strip().startswith("# Context-Aware Whisper"), "README should start with '# Context-Aware Whisper'"


class TestReadmeRequiredSections:
    """Tests for required sections in README.md."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_has_installation_section(self, readme_content):
        """README should have an Installation section."""
        assert "## Installation" in readme_content, "Missing Installation section"

    def test_has_usage_section(self, readme_content):
        """README should have a Usage section."""
        assert "## Usage" in readme_content, "Missing Usage section"

    def test_has_requirements_section(self, readme_content):
        """README should have a Requirements section."""
        assert "## Requirements" in readme_content, "Missing Requirements section"

    def test_has_permissions_section(self, readme_content):
        """README should have a Permissions Setup section."""
        assert "## Permissions Setup" in readme_content or "Permissions" in readme_content, \
            "Missing Permissions section"

    def test_has_troubleshooting_section(self, readme_content):
        """README should have a Troubleshooting section."""
        assert "## Troubleshooting" in readme_content, "Missing Troubleshooting section"


class TestReadmeInstallationContent:
    """Tests for installation instructions content."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_mentions_python_version(self, readme_content):
        """Installation should mention Python version requirement."""
        assert "Python 3.10" in readme_content or "python3" in readme_content.lower(), \
            "Should mention Python version requirement"

    def test_mentions_virtual_environment(self, readme_content):
        """Installation should mention virtual environment setup."""
        assert "venv" in readme_content, "Should mention virtual environment setup"

    def test_mentions_pip_install(self, readme_content):
        """Installation should mention pip install command."""
        assert "pip install" in readme_content, "Should mention pip install command"

    def test_mentions_env_file(self, readme_content):
        """Installation should mention .env file configuration."""
        assert ".env" in readme_content, "Should mention .env file"

    def test_mentions_groq_api_key(self, readme_content):
        """Installation should mention GROQ_API_KEY."""
        assert "GROQ_API_KEY" in readme_content, "Should mention GROQ_API_KEY"


class TestReadmeUsageContent:
    """Tests for usage instructions content."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_mentions_fn_key(self, readme_content):
        """Usage should mention Fn/Globe key."""
        assert "Fn" in readme_content or "Globe" in readme_content, "Should mention Fn/Globe key"

    def test_mentions_hold_release(self, readme_content):
        """Usage should explain hold/release gestures."""
        content_lower = readme_content.lower()
        assert "hold" in content_lower and "release" in content_lower, \
            "Should explain hold/release gestures"

    def test_mentions_recording(self, readme_content):
        """Usage should mention recording."""
        assert "recording" in readme_content.lower(), "Should mention recording"

    def test_mentions_transcription(self, readme_content):
        """Usage should mention transcription."""
        assert "transcrib" in readme_content.lower(), "Should mention transcription"

    def test_mentions_main_py(self, readme_content):
        """Usage should mention how to run the app."""
        assert "python main.py" in readme_content or "context-aware-whisper" in readme_content.lower(), \
            "Should mention how to run the application"


class TestReadmeEnvironmentVariables:
    """Tests that documented environment variables match actual usage."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    @pytest.fixture
    def main_py_content(self):
        """Load main.py content."""
        main_path = PROJECT_ROOT / "main.py"
        return main_path.read_text()

    def test_groq_api_key_documented(self, readme_content):
        """GROQ_API_KEY should be documented."""
        assert "GROQ_API_KEY" in readme_content

    def test_language_env_documented(self, readme_content):
        """CAW_LANGUAGE should be documented."""
        assert "CAW_LANGUAGE" in readme_content

    def test_type_delay_documented(self, readme_content):
        """CAW_TYPE_DELAY should be documented."""
        assert "CAW_TYPE_DELAY" in readme_content

    def test_sample_rate_documented(self, readme_content):
        """CAW_SAMPLE_RATE should be documented."""
        assert "CAW_SAMPLE_RATE" in readme_content

    def test_env_vars_used_in_code(self, main_py_content, readme_content):
        """Environment variables used in code should be documented."""
        # Find env vars used in main.py
        env_pattern = r'os\.environ\.get\(["\'](\w+)["\']'
        used_vars = re.findall(env_pattern, main_py_content)

        for var in used_vars:
            assert var in readme_content, f"Environment variable {var} used in code but not documented"


class TestReadmeTroubleshootingContent:
    """Tests for troubleshooting section content."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_addresses_api_key_error(self, readme_content):
        """Troubleshooting should address missing API key."""
        content_lower = readme_content.lower()
        assert "api key" in content_lower or "groq_api_key" in content_lower, \
            "Should address API key issues"

    def test_addresses_hotkey_or_permissions(self, readme_content):
        """Troubleshooting should address hotkey or permission issues."""
        content_lower = readme_content.lower()
        # App uses hotkey detection (Fn key or Ctrl+Shift+Space)
        has_hotkey_content = "fn" in content_lower or "hotkey" in content_lower or "key" in content_lower
        has_permission_content = "permission" in content_lower or "accessibility" in content_lower
        assert has_hotkey_content or has_permission_content, \
            "Should address hotkey or permission issues"

    def test_addresses_typing_issues(self, readme_content):
        """Troubleshooting should address typing issues."""
        content_lower = readme_content.lower()
        assert "typing" in content_lower or "type" in content_lower, \
            "Should address typing issues"

    def test_addresses_accessibility(self, readme_content):
        """Troubleshooting should address accessibility permissions."""
        assert "Accessibility" in readme_content, "Should address Accessibility permissions"


class TestReadmeProjectStructure:
    """Tests that documented project structure matches reality."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_main_py_documented_and_exists(self, readme_content):
        """main.py should be documented and exist."""
        assert "main.py" in readme_content
        assert (PROJECT_ROOT / "main.py").exists()

    def test_caw_package_documented(self, readme_content):
        """context-aware-whisper package should be documented."""
        assert "context-aware-whisper" in readme_content.lower()

    def test_tests_directory_documented(self, readme_content):
        """tests directory should be documented."""
        assert "tests/" in readme_content or "tests" in readme_content.lower()
        assert (PROJECT_ROOT / "tests").is_dir()

    def test_requirements_txt_documented(self, readme_content):
        """requirements.txt should be documented."""
        assert "requirements.txt" in readme_content
        assert (PROJECT_ROOT / "requirements.txt").exists()


class TestReadmeCodeBlocks:
    """Tests for code block formatting in README."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_has_bash_code_blocks(self, readme_content):
        """README should have bash code blocks for commands."""
        assert "```bash" in readme_content, "Should have bash code blocks"

    def test_code_blocks_closed(self, readme_content):
        """All code blocks should be properly closed."""
        open_blocks = readme_content.count("```")
        assert open_blocks % 2 == 0, "Code blocks not properly closed"

    def test_has_shell_commands(self, readme_content):
        """README should have shell commands for installation."""
        # Should have common commands like pip, python, git
        assert "pip" in readme_content or "python" in readme_content, \
            "Should have shell commands"


class TestReadmePermissionsSection:
    """Tests for permissions documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_mentions_microphone_permission(self, readme_content):
        """Should mention microphone permission."""
        content_lower = readme_content.lower()
        assert "microphone" in content_lower, "Should mention microphone permission"

    def test_mentions_accessibility_permission(self, readme_content):
        """Should mention accessibility permission."""
        assert "Accessibility" in readme_content, "Should mention accessibility permission"

    def test_mentions_system_settings(self, readme_content):
        """Should mention System Settings/Preferences."""
        assert "System Settings" in readme_content or "System Preferences" in readme_content, \
            "Should mention how to access system settings"

    def test_mentions_privacy_security(self, readme_content):
        """Should mention Privacy & Security."""
        assert "Privacy" in readme_content, "Should mention Privacy settings"


class TestReadmeMarkdownFormatting:
    """Tests for proper Markdown formatting."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_has_proper_headings(self, readme_content):
        """README should use proper heading hierarchy."""
        # Should have level 1 and level 2 headings
        assert readme_content.count("\n# ") >= 0  # Main title might be at start
        assert readme_content.count("\n## ") >= 4  # Should have multiple sections

    def test_has_bullet_lists(self, readme_content):
        """README should use bullet lists for features/steps."""
        assert "\n- " in readme_content or "\n* " in readme_content, \
            "Should use bullet lists"

    def test_has_tables_for_env_vars(self, readme_content):
        """Environment variables should be in a table."""
        # Tables in markdown use | characters
        assert "|" in readme_content, "Should use tables for structured data"

    def test_no_broken_links_syntax(self, readme_content):
        """Links should have proper markdown syntax."""
        # Check for common broken link patterns
        # Valid: [text](url)
        # Invalid: [text] (url) or [text](url or [text]url)
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', readme_content)
        # If we found links, the syntax is valid
        # Also check there are no malformed links with space before (
        malformed = re.findall(r'\[[^\]]+\]\s+\(', readme_content)
        assert len(malformed) == 0, "Found malformed markdown links"


class TestEnvExampleConsistency:
    """Tests that .env.example is consistent with README."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    @pytest.fixture
    def env_example_content(self):
        """Load .env.example content."""
        env_path = PROJECT_ROOT / ".env.example"
        if env_path.exists():
            return env_path.read_text()
        return ""

    def test_env_example_exists(self):
        """.env.example file should exist."""
        assert (PROJECT_ROOT / ".env.example").exists()

    def test_env_example_variables_documented(self, readme_content, env_example_content):
        """Variables in .env.example should be documented in README."""
        if not env_example_content:
            pytest.skip(".env.example not found")

        # Extract variable names from .env.example
        var_pattern = r'^([A-Z_]+)='
        for line in env_example_content.split('\n'):
            if line.strip() and not line.startswith('#'):
                match = re.match(var_pattern, line)
                if match:
                    var_name = match.group(1)
                    assert var_name in readme_content, \
                        f"{var_name} from .env.example should be documented in README"


class TestCrossPlatformDocumentation:
    """Tests for cross-platform support documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_mentions_cross_platform(self, readme_content):
        """README should mention cross-platform support."""
        content_lower = readme_content.lower()
        assert "cross-platform" in content_lower or (
            "macos" in content_lower and
            "windows" in content_lower and
            "linux" in content_lower
        ), "Should mention cross-platform support"

    def test_mentions_macos(self, readme_content):
        """README should mention macOS support."""
        assert "macOS" in readme_content, "Should mention macOS"

    def test_mentions_windows(self, readme_content):
        """README should mention Windows support."""
        assert "Windows" in readme_content, "Should mention Windows"

    def test_mentions_linux(self, readme_content):
        """README should mention Linux support."""
        assert "Linux" in readme_content, "Should mention Linux"

    def test_has_macos_installation(self, readme_content):
        """README should have macOS installation section."""
        assert "### macOS" in readme_content, "Should have macOS installation section"

    def test_has_windows_installation(self, readme_content):
        """README should have Windows installation section."""
        assert "### Windows" in readme_content, "Should have Windows installation section"

    def test_has_linux_installation(self, readme_content):
        """README should have Linux installation section."""
        assert "### Linux" in readme_content, "Should have Linux installation section"

    def test_mentions_ctrl_shift_space(self, readme_content):
        """README should mention Ctrl+Shift+Space hotkey for Windows/Linux."""
        assert "Ctrl+Shift+Space" in readme_content, \
            "Should mention Ctrl+Shift+Space hotkey for Windows/Linux"

    def test_mentions_wayland(self, readme_content):
        """README should mention Wayland for Linux users."""
        assert "Wayland" in readme_content or "wayland" in readme_content, \
            "Should mention Wayland for Linux"

    def test_mentions_x11(self, readme_content):
        """README should mention X11 for Linux users."""
        assert "X11" in readme_content or "x11" in readme_content, \
            "Should mention X11 for Linux"

    def test_mentions_wtype(self, readme_content):
        """README should mention wtype for Wayland."""
        assert "wtype" in readme_content, "Should mention wtype for Wayland"

    def test_mentions_xdotool(self, readme_content):
        """README should mention xdotool for X11."""
        assert "xdotool" in readme_content, "Should mention xdotool for X11"


class TestUIDocumentation:
    """Tests for UI components documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_mentions_visual_indicator(self, readme_content):
        """README should mention the visual indicator."""
        content_lower = readme_content.lower()
        assert "indicator" in content_lower, "Should mention visual indicator"

    def test_mentions_history_panel(self, readme_content):
        """README should mention the history panel."""
        content_lower = readme_content.lower()
        assert "history" in content_lower, "Should mention history panel"

    def test_describes_indicator_states(self, readme_content):
        """README should describe indicator states."""
        # Should mention recording, transcribing states
        content_lower = readme_content.lower()
        assert "rec" in content_lower or "recording" in content_lower, \
            "Should describe recording state"

    def test_mentions_indicator_colors(self, readme_content):
        """README should mention indicator colors."""
        content_lower = readme_content.lower()
        assert "red" in content_lower or "green" in content_lower or "orange" in content_lower, \
            "Should mention indicator colors"

    def test_mentions_history_toggle_hotkey(self, readme_content):
        """README should mention how to toggle history panel."""
        assert "Cmd+H" in readme_content or "Ctrl+H" in readme_content, \
            "Should mention history toggle hotkey"

    def test_mentions_copy_functionality(self, readme_content):
        """README should mention copy functionality in history."""
        content_lower = readme_content.lower()
        assert "copy" in content_lower, "Should mention copy functionality"


class TestUIEnvironmentVariables:
    """Tests for UI-related environment variables documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_ui_enabled_documented(self, readme_content):
        """CAW_UI_ENABLED should be documented."""
        assert "CAW_UI_ENABLED" in readme_content

    def test_ui_position_documented(self, readme_content):
        """CAW_UI_POSITION should be documented."""
        assert "CAW_UI_POSITION" in readme_content

    def test_history_enabled_documented(self, readme_content):
        """CAW_HISTORY_ENABLED should be documented."""
        assert "CAW_HISTORY_ENABLED" in readme_content

    def test_history_max_documented(self, readme_content):
        """CAW_HISTORY_MAX should be documented."""
        assert "CAW_HISTORY_MAX" in readme_content

    def test_hotkey_documented(self, readme_content):
        """CAW_HOTKEY should be documented."""
        assert "CAW_HOTKEY" in readme_content

    def test_debug_documented(self, readme_content):
        """CAW_DEBUG should be documented."""
        assert "CAW_DEBUG" in readme_content


class TestPlatformDirectoryDocumentation:
    """Tests for platform directory structure documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_mentions_platform_module(self, readme_content):
        """README should mention platform module."""
        assert "platform/" in readme_content, "Should mention platform directory"

    def test_mentions_macos_directory(self, readme_content):
        """README should mention macOS platform directory."""
        assert "macos/" in readme_content, "Should mention macos directory"

    def test_mentions_windows_directory(self, readme_content):
        """README should mention Windows platform directory."""
        assert "windows/" in readme_content, "Should mention windows directory"

    def test_mentions_linux_directory(self, readme_content):
        """README should mention Linux platform directory."""
        assert "linux/" in readme_content, "Should mention linux directory"

    def test_mentions_ui_module(self, readme_content):
        """README should mention UI module."""
        assert "ui/" in readme_content, "Should mention ui directory"

    def test_mentions_storage_module(self, readme_content):
        """README should mention storage module."""
        assert "storage/" in readme_content, "Should mention storage directory"


class TestHotkeyReferenceTable:
    """Tests for hotkey reference table in documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_has_hotkey_reference_section(self, readme_content):
        """README should have a hotkey reference section."""
        assert "Hotkey Reference" in readme_content or "hotkey" in readme_content.lower(), \
            "Should have hotkey reference section"

    def test_documents_macos_fn_key(self, readme_content):
        """README should document Fn/Globe key for macOS."""
        assert "Fn" in readme_content and "Globe" in readme_content, \
            "Should document Fn/Globe key for macOS"

    def test_documents_platform_specific_hotkeys(self, readme_content):
        """README should document platform-specific hotkeys."""
        # Check for table structure with platforms and hotkeys
        assert "| Platform |" in readme_content or "| macOS |" in readme_content, \
            "Should have platform hotkey table"


class TestLinuxSpecificDocumentation:
    """Tests for Linux-specific documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_mentions_apt_install(self, readme_content):
        """README should mention apt install for Debian/Ubuntu."""
        assert "apt install" in readme_content or "apt-get install" in readme_content, \
            "Should mention apt install for Debian/Ubuntu"

    def test_mentions_dnf_install(self, readme_content):
        """README should mention dnf install for Fedora."""
        assert "dnf install" in readme_content, "Should mention dnf install for Fedora"

    def test_mentions_input_group(self, readme_content):
        """README should mention input group for Linux permissions."""
        assert "input" in readme_content.lower(), "Should mention input group"

    def test_mentions_audio_group(self, readme_content):
        """README should mention audio group for Linux permissions."""
        content_lower = readme_content.lower()
        assert "audio" in content_lower, "Should mention audio group"

    def test_mentions_wl_clipboard(self, readme_content):
        """README should mention wl-clipboard for Wayland."""
        assert "wl-clipboard" in readme_content or "wl-copy" in readme_content, \
            "Should mention wl-clipboard for Wayland"


class TestWindowsSpecificDocumentation:
    """Tests for Windows-specific documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_mentions_windows_10(self, readme_content):
        """README should mention Windows 10 support."""
        assert "Windows 10" in readme_content, "Should mention Windows 10"

    def test_mentions_administrator(self, readme_content):
        """README should mention running as Administrator."""
        assert "administrator" in readme_content.lower() or "Administrator" in readme_content, \
            "Should mention Administrator mode"

    def test_mentions_windows_venv_activation(self, readme_content):
        """README should mention Windows venv activation syntax."""
        assert "venv\\Scripts\\activate" in readme_content or \
               r"venv\Scripts\activate" in readme_content, \
            "Should mention Windows venv activation"


class TestTkinterDocumentation:
    """Tests for tkinter/UI framework documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_mentions_tkinter(self, readme_content):
        """README should mention tkinter for UI issues."""
        assert "tkinter" in readme_content or "tk" in readme_content.lower(), \
            "Should mention tkinter"

    def test_mentions_python3_tk_package(self, readme_content):
        """README should mention python3-tk package for Linux."""
        assert "python3-tk" in readme_content, "Should mention python3-tk package"


class TestLocalTranscriptionDocumentation:
    """Tests for local transcription (whisper.cpp) documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_has_local_transcription_section(self, readme_content):
        """README should have a Local Transcription section."""
        assert "## Local Transcription" in readme_content or \
               "Local Transcription (whisper.cpp)" in readme_content, \
            "Missing Local Transcription section"

    def test_mentions_whisper_cpp(self, readme_content):
        """README should mention whisper.cpp."""
        assert "whisper.cpp" in readme_content, "Should mention whisper.cpp"

    def test_mentions_pywhispercpp(self, readme_content):
        """README should mention pywhispercpp package."""
        assert "pywhispercpp" in readme_content, "Should mention pywhispercpp"

    def test_mentions_model_download_command(self, readme_content):
        """README should mention how to download models."""
        assert "model_manager" in readme_content, "Should mention model_manager command"
        assert "download" in readme_content, "Should mention download command"

    def test_documents_available_models(self, readme_content):
        """README should document available model options."""
        assert "tiny.en" in readme_content, "Should mention tiny.en model"
        assert "base.en" in readme_content, "Should mention base.en model"
        assert "small.en" in readme_content, "Should mention small.en model"

    def test_documents_model_sizes(self, readme_content):
        """README should document model sizes."""
        assert "75 MB" in readme_content or "75MB" in readme_content, \
            "Should mention tiny model size"
        assert "142 MB" in readme_content or "142MB" in readme_content, \
            "Should mention base model size"

    def test_documents_transcriber_env_var(self, readme_content):
        """README should document CAW_TRANSCRIBER env var."""
        assert "CAW_TRANSCRIBER" in readme_content, \
            "Should document CAW_TRANSCRIBER"

    def test_documents_whisper_model_env_var(self, readme_content):
        """README should document CAW_WHISPER_MODEL env var."""
        assert "CAW_WHISPER_MODEL" in readme_content, \
            "Should document CAW_WHISPER_MODEL"

    def test_documents_models_dir_env_var(self, readme_content):
        """README should document CAW_MODELS_DIR env var."""
        assert "CAW_MODELS_DIR" in readme_content, \
            "Should document CAW_MODELS_DIR"

    def test_mentions_offline_capability(self, readme_content):
        """README should mention offline capability."""
        content_lower = readme_content.lower()
        assert "offline" in content_lower, "Should mention offline capability"

    def test_mentions_privacy_benefit(self, readme_content):
        """README should mention privacy benefits."""
        content_lower = readme_content.lower()
        assert "private" in content_lower or "privacy" in content_lower, \
            "Should mention privacy benefits"

    def test_has_model_comparison_table(self, readme_content):
        """README should have a model comparison table."""
        assert "| Model |" in readme_content or "| `tiny.en` |" in readme_content, \
            "Should have model comparison table"

    def test_mentions_local_vs_cloud_comparison(self, readme_content):
        """README should compare local vs cloud transcription."""
        assert "Cloud" in readme_content and "Local" in readme_content, \
            "Should compare cloud and local options"


class TestLocalTranscriptionTroubleshooting:
    """Tests for local transcription troubleshooting documentation."""

    @pytest.fixture
    def readme_content(self):
        """Load README content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text()

    def test_troubleshooting_model_not_found(self, readme_content):
        """README should address model not found error."""
        content_lower = readme_content.lower()
        assert "model not found" in content_lower or "failed to load" in content_lower, \
            "Should address model not found error"

    def test_troubleshooting_slow_transcription(self, readme_content):
        """README should address slow transcription."""
        content_lower = readme_content.lower()
        assert "slow" in content_lower, "Should address slow transcription"

    def test_troubleshooting_memory_usage(self, readme_content):
        """README should address memory usage issues."""
        content_lower = readme_content.lower()
        assert "memory" in content_lower or "ram" in content_lower, \
            "Should address memory usage"

    def test_troubleshooting_quality_issues(self, readme_content):
        """README should address transcription quality issues."""
        content_lower = readme_content.lower()
        assert "quality" in content_lower, "Should address quality issues"


class TestLocalTranscriberFileExists:
    """Tests that local_transcriber.py exists and is documented."""

    def test_local_transcriber_exists(self):
        """local_transcriber.py should exist."""
        local_transcriber_path = PROJECT_ROOT / "src" / "context-aware-whisper" / "local_transcriber.py"
        assert local_transcriber_path.exists(), "local_transcriber.py not found"

    def test_model_manager_exists(self):
        """model_manager.py should exist."""
        model_manager_path = PROJECT_ROOT / "src" / "context-aware-whisper" / "model_manager.py"
        assert model_manager_path.exists(), "model_manager.py not found"

    def test_local_transcriber_documented_in_readme(self):
        """local_transcriber.py should be mentioned in README."""
        readme_path = PROJECT_ROOT / "README.md"
        readme_content = readme_path.read_text()
        assert "local_transcriber" in readme_content, \
            "local_transcriber.py should be documented in README"

    def test_model_manager_documented_in_readme(self):
        """model_manager.py should be mentioned in README."""
        readme_path = PROJECT_ROOT / "README.md"
        readme_content = readme_path.read_text()
        assert "model_manager" in readme_content, \
            "model_manager.py should be documented in README"
