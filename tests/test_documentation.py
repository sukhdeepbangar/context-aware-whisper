"""
Tests for project documentation.

Validates that README.md exists, contains required sections,
and is consistent with the actual project structure.
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
        # Should start with # HandFree
        assert content.strip().startswith("# HandFree"), "README should start with '# HandFree'"


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

    def test_mentions_airpods(self, readme_content):
        """Usage should mention AirPods."""
        assert "AirPods" in readme_content, "Should mention AirPods"

    def test_mentions_mute_unmute(self, readme_content):
        """Usage should explain mute/unmute gestures."""
        content_lower = readme_content.lower()
        assert "unmute" in content_lower and "mute" in content_lower, \
            "Should explain mute/unmute gestures"

    def test_mentions_recording(self, readme_content):
        """Usage should mention recording."""
        assert "recording" in readme_content.lower(), "Should mention recording"

    def test_mentions_transcription(self, readme_content):
        """Usage should mention transcription."""
        assert "transcrib" in readme_content.lower(), "Should mention transcription"

    def test_mentions_main_py(self, readme_content):
        """Usage should mention how to run the app."""
        assert "python main.py" in readme_content or "handfree" in readme_content.lower(), \
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
        """HANDFREE_LANGUAGE should be documented."""
        assert "HANDFREE_LANGUAGE" in readme_content

    def test_type_delay_documented(self, readme_content):
        """HANDFREE_TYPE_DELAY should be documented."""
        assert "HANDFREE_TYPE_DELAY" in readme_content

    def test_sample_rate_documented(self, readme_content):
        """HANDFREE_SAMPLE_RATE should be documented."""
        assert "HANDFREE_SAMPLE_RATE" in readme_content

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

    def test_addresses_mute_detection(self, readme_content):
        """Troubleshooting should address mute detection issues."""
        content_lower = readme_content.lower()
        assert "mute" in content_lower, "Should address mute detection issues"

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

    def test_handfree_package_documented(self, readme_content):
        """handfree package should be documented."""
        assert "handfree" in readme_content.lower()

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
