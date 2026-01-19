"""
Tests for the Menu Bar Component

Tests the menubar module including:
- MenuBarApp class initialization and state management
- create_menubar_app factory function
- Integration with CAWUI
- Thread safety of state updates
- Cleanup and resource management
"""

import sys
import threading
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from hypothesis import given, strategies as st, settings


# Test availability detection
class TestMenuBarAvailability:
    """Tests for menu bar availability detection."""

    def test_menubar_available_on_macos(self):
        """On macOS, MENUBAR_AVAILABLE should be True if PyObjC is installed."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MENUBAR_AVAILABLE, is_menubar_available

        # On macOS with PyObjC, should be available
        assert MENUBAR_AVAILABLE is True
        assert is_menubar_available() is True

    def test_menubar_not_available_on_other_platforms(self):
        """On non-macOS platforms, MENUBAR_AVAILABLE should be False."""
        if sys.platform == "darwin":
            pytest.skip("Non-macOS test")

        from context_aware_whisper.ui.menubar import MENUBAR_AVAILABLE, is_menubar_available

        assert MENUBAR_AVAILABLE is False
        assert is_menubar_available() is False


class TestCreateMenubarApp:
    """Tests for the create_menubar_app factory function."""

    def test_create_menubar_app_returns_none_on_non_macos(self):
        """create_menubar_app returns None on non-macOS platforms."""
        if sys.platform == "darwin":
            pytest.skip("Non-macOS test")

        from context_aware_whisper.ui.menubar import create_menubar_app

        result = create_menubar_app(on_quit=lambda: None)
        assert result is None

    def test_create_menubar_app_returns_instance_on_macos(self):
        """create_menubar_app returns MenuBarApp instance on macOS."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import create_menubar_app, MenuBarApp

        on_quit = MagicMock()
        on_history = MagicMock()

        result = create_menubar_app(
            on_quit=on_quit,
            on_history_toggle=on_history
        )

        assert result is not None
        assert isinstance(result, MenuBarApp)

    def test_create_menubar_app_handles_exceptions(self):
        """create_menubar_app returns None on exceptions."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import create_menubar_app

        with patch('context_aware_whisper.ui.menubar.MenuBarApp', side_effect=RuntimeError("Test")):
            result = create_menubar_app(on_quit=lambda: None)
            assert result is None


class TestMenuBarApp:
    """Tests for the MenuBarApp class."""

    @pytest.fixture
    def mock_appkit(self):
        """Mock AppKit and Foundation for testing without actual UI."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        # We don't actually mock these - we test with real PyObjC
        # but don't start the app (no run loop)
        yield

    def test_init_without_pyobjc_raises(self):
        """MenuBarApp raises RuntimeError if PyObjC not available."""
        with patch('context_aware_whisper.ui.menubar.MENUBAR_AVAILABLE', False):
            # Need to reimport to get the patched version
            from context_aware_whisper.ui import menubar
            original = menubar.MENUBAR_AVAILABLE
            menubar.MENUBAR_AVAILABLE = False

            try:
                with pytest.raises(RuntimeError, match="Menu bar not available"):
                    menubar.MenuBarApp(on_quit=lambda: None)
            finally:
                menubar.MENUBAR_AVAILABLE = original

    def test_init_stores_callbacks(self):
        """MenuBarApp stores callback functions."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        on_quit = MagicMock()
        on_history = MagicMock()

        app = MenuBarApp(on_quit=on_quit, on_history_toggle=on_history)

        assert app._on_quit is on_quit
        assert app._on_history_toggle is on_history

    def test_init_default_state(self):
        """MenuBarApp initializes with correct default state."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        app = MenuBarApp(on_quit=lambda: None)

        assert app._is_recording is False
        assert app._initialized is False
        assert app._status_item is None

    def test_set_recording_updates_state(self):
        """set_recording updates internal state."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        app = MenuBarApp(on_quit=lambda: None)

        # Test setting to recording
        app.set_recording(True)
        assert app._is_recording is True
        assert app.is_recording is True

        # Test setting back to idle
        app.set_recording(False)
        assert app._is_recording is False
        assert app.is_recording is False

    def test_set_recording_thread_safe(self):
        """set_recording is thread-safe."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        app = MenuBarApp(on_quit=lambda: None)
        errors = []

        def toggle_recording():
            try:
                for _ in range(100):
                    app.set_recording(True)
                    app.set_recording(False)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=toggle_recording) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    @pytest.mark.skip(reason="Requires macOS application context - crashes in pytest")
    def test_start_creates_status_item(self):
        """start() creates the NSStatusItem."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        app = MenuBarApp(on_quit=lambda: None)
        app.start()

        assert app._initialized is True
        assert app._status_item is not None
        assert app._menu is not None

        # Cleanup
        app.stop()

    @pytest.mark.skip(reason="Requires macOS application context - crashes in pytest")
    def test_start_idempotent(self):
        """start() is idempotent - multiple calls have no effect."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        app = MenuBarApp(on_quit=lambda: None)
        app.start()
        status_item = app._status_item

        # Second start should not create new item
        app.start()
        assert app._status_item is status_item

        # Cleanup
        app.stop()

    @pytest.mark.skip(reason="Requires macOS application context - crashes in pytest")
    def test_stop_removes_status_item(self):
        """stop() removes the status item."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        app = MenuBarApp(on_quit=lambda: None)
        app.start()
        assert app._status_item is not None

        app.stop()
        assert app._status_item is None
        assert app._initialized is False

    def test_stop_safe_without_start(self):
        """stop() is safe to call without start()."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        app = MenuBarApp(on_quit=lambda: None)
        # Should not raise
        app.stop()

    @pytest.mark.skip(reason="Requires macOS application context - crashes in pytest")
    def test_set_recording_updates_ui_when_started(self):
        """set_recording updates UI elements when app is started."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        app = MenuBarApp(on_quit=lambda: None)
        app.start()

        # Set to recording
        app.set_recording(True)
        assert app._status_item.title() == MenuBarApp.ICON_RECORDING
        assert app._status_menu_item.title() == "Status: Recording..."

        # Set back to idle
        app.set_recording(False)
        assert app._status_item.title() == MenuBarApp.ICON_IDLE
        assert app._status_menu_item.title() == "Status: Idle"

        # Cleanup
        app.stop()


class TestMenuBarDelegate:
    """Tests for the MenuBarDelegate class."""

    def test_delegate_calls_history_callback(self):
        """MenuBarDelegate calls history callback on showHistory_."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarDelegate

        history_callback = MagicMock()
        quit_callback = MagicMock()

        delegate = MenuBarDelegate.alloc().init()
        delegate.setHistoryCallback_(history_callback)
        delegate.setQuitCallback_(quit_callback)

        delegate.showHistory_(None)

        history_callback.assert_called_once()
        quit_callback.assert_not_called()

    def test_delegate_calls_quit_callback(self):
        """MenuBarDelegate calls quit callback on quitApp_."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarDelegate

        history_callback = MagicMock()
        quit_callback = MagicMock()

        delegate = MenuBarDelegate.alloc().init()
        delegate.setHistoryCallback_(history_callback)
        delegate.setQuitCallback_(quit_callback)

        delegate.quitApp_(None)

        quit_callback.assert_called_once()
        history_callback.assert_not_called()

    def test_delegate_handles_none_callbacks(self):
        """MenuBarDelegate handles None callbacks gracefully."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarDelegate

        delegate = MenuBarDelegate.alloc().init()
        # Don't set callbacks - they default to None

        # Should not raise
        delegate.showHistory_(None)
        delegate.quitApp_(None)


class TestMenuBarIntegration:
    """Integration tests for menu bar with CAWUI."""

    def test_cawui_creates_menubar(self):
        """CAWUI creates menubar when enabled."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.app import CAWUI

        ui = CAWUI(
            history_enabled=False,
            menubar_enabled=True,
            on_quit=lambda: None
        )

        # Note: start() must be called on main thread, so we just check config
        assert ui._menubar_enabled is True

    def test_cawui_menubar_disabled(self):
        """CAWUI respects menubar_enabled=False."""
        from context_aware_whisper.ui.app import CAWUI

        ui = CAWUI(
            history_enabled=False,
            menubar_enabled=False
        )

        assert ui._menubar_enabled is False


# Property-based tests
class TestMenuBarPropertyBased:
    """Property-based tests for menu bar."""

    @given(st.booleans())
    @settings(max_examples=50)
    def test_set_recording_maintains_consistency(self, is_recording):
        """set_recording always maintains consistent state."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        app = MenuBarApp(on_quit=lambda: None)
        app.set_recording(is_recording)

        assert app.is_recording == is_recording

    @given(st.lists(st.booleans(), min_size=1, max_size=20))
    @settings(max_examples=30)
    def test_rapid_state_changes(self, states):
        """Rapid state changes don't cause errors."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        app = MenuBarApp(on_quit=lambda: None)

        for state in states:
            app.set_recording(state)

        # Final state should match last value
        assert app.is_recording == states[-1]


class TestMenuBarIcons:
    """Tests for menu bar icon constants."""

    def test_icon_constants_defined(self):
        """Icon constants are defined correctly."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        assert hasattr(MenuBarApp, 'ICON_IDLE')
        assert hasattr(MenuBarApp, 'ICON_RECORDING')
        assert MenuBarApp.ICON_IDLE != MenuBarApp.ICON_RECORDING

    def test_icon_idle_is_microphone(self):
        """Idle icon is a microphone emoji."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        assert MenuBarApp.ICON_IDLE == "🎙️"

    def test_icon_recording_is_red_circle(self):
        """Recording icon is a red circle emoji."""
        if sys.platform != "darwin":
            pytest.skip("macOS-only test")

        from context_aware_whisper.ui.menubar import MenuBarApp

        assert MenuBarApp.ICON_RECORDING == "🔴"
