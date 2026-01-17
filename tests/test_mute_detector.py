"""
Unit tests for MuteDetector module.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from mute_detector import MuteDetector


class TestMuteDetector(unittest.TestCase):
    """Test cases for MuteDetector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.on_mute_callback = Mock()
        self.on_unmute_callback = Mock()
        self.detector = MuteDetector(
            on_mute=self.on_mute_callback,
            on_unmute=self.on_unmute_callback
        )

    def test_init(self):
        """Test MuteDetector initialization."""
        self.assertIsNotNone(self.detector)
        self.assertEqual(self.detector.on_mute, self.on_mute_callback)
        self.assertEqual(self.detector.on_unmute, self.on_unmute_callback)
        self.assertIsNone(self.detector._observer)
        self.assertIsNone(self.detector._session)
        self.assertIsNone(self.detector._last_mute_state)

    @patch('mute_detector.AVAudioApplication')
    @patch('mute_detector.AVAudioSession')
    @patch('mute_detector.NSNotificationCenter')
    def test_start(self, mock_notification_center, mock_audio_session, mock_audio_app):
        """Test starting the mute detector."""
        # Set up mocks
        mock_session_instance = MagicMock()
        mock_session_instance.setCategory_mode_options_error_.return_value = (True, None)
        mock_session_instance.setActive_error_.return_value = (True, None)
        mock_audio_session.sharedInstance.return_value = mock_session_instance

        mock_app_instance = MagicMock()
        mock_app_instance.isInputMuted.return_value = False
        mock_audio_app.sharedInstance.return_value = mock_app_instance

        mock_center = MagicMock()
        mock_notification_center.defaultCenter.return_value = mock_center

        # Start detector
        self.detector.start()

        # Verify audio session was configured
        mock_session_instance.setCategory_mode_options_error_.assert_called_once()
        mock_session_instance.setActive_error_.assert_called_once_with(True, None)

        # Verify notification observer was registered
        mock_center.addObserverForName_object_queue_usingBlock_.assert_called_once()

        # Verify initial state was set
        self.assertEqual(self.detector._last_mute_state, False)

    @patch('mute_detector.AVAudioApplication')
    def test_handle_notification_mute(self, mock_audio_app):
        """Test handling mute notification."""
        # Set up initial state as unmuted
        self.detector._last_mute_state = False

        # Mock the app to return muted state
        mock_app_instance = MagicMock()
        mock_app_instance.isInputMuted.return_value = True
        mock_audio_app.sharedInstance.return_value = mock_app_instance

        # Simulate notification
        self.detector._handle_notification(None)

        # Verify mute callback was called
        self.on_mute_callback.assert_called_once()
        self.on_unmute_callback.assert_not_called()
        self.assertEqual(self.detector._last_mute_state, True)

    @patch('mute_detector.AVAudioApplication')
    def test_handle_notification_unmute(self, mock_audio_app):
        """Test handling unmute notification."""
        # Set up initial state as muted
        self.detector._last_mute_state = True

        # Mock the app to return unmuted state
        mock_app_instance = MagicMock()
        mock_app_instance.isInputMuted.return_value = False
        mock_audio_app.sharedInstance.return_value = mock_app_instance

        # Simulate notification
        self.detector._handle_notification(None)

        # Verify unmute callback was called
        self.on_unmute_callback.assert_called_once()
        self.on_mute_callback.assert_not_called()
        self.assertEqual(self.detector._last_mute_state, False)

    @patch('mute_detector.AVAudioApplication')
    def test_handle_notification_no_state_change(self, mock_audio_app):
        """Test handling notification when state hasn't changed."""
        # Set up initial state as muted
        self.detector._last_mute_state = True

        # Mock the app to return same muted state
        mock_app_instance = MagicMock()
        mock_app_instance.isInputMuted.return_value = True
        mock_audio_app.sharedInstance.return_value = mock_app_instance

        # Simulate notification
        self.detector._handle_notification(None)

        # Verify no callbacks were called
        self.on_mute_callback.assert_not_called()
        self.on_unmute_callback.assert_not_called()

    @patch('mute_detector.NSNotificationCenter')
    def test_stop(self, mock_notification_center):
        """Test stopping the mute detector."""
        # Set up mock observer and session
        mock_center = MagicMock()
        mock_notification_center.defaultCenter.return_value = mock_center

        mock_session = MagicMock()
        self.detector._observer = "mock_observer"
        self.detector._session = mock_session

        # Stop detector
        self.detector.stop()

        # Verify observer was removed
        mock_center.removeObserver_.assert_called_once_with("mock_observer")

        # Verify session was deactivated
        mock_session.setActive_error_.assert_called_once_with(False, None)

        # Verify cleanup
        self.assertIsNone(self.detector._observer)
        self.assertIsNone(self.detector._session)

    @patch('mute_detector.AVAudioApplication')
    def test_is_muted_property(self, mock_audio_app):
        """Test is_muted property."""
        # Mock the app to return muted state
        mock_app_instance = MagicMock()
        mock_app_instance.isInputMuted.return_value = True
        mock_audio_app.sharedInstance.return_value = mock_app_instance

        # Check property
        self.assertTrue(self.detector.is_muted)

        # Mock the app to return unmuted state
        mock_app_instance.isInputMuted.return_value = False
        self.assertFalse(self.detector.is_muted)

    @patch('mute_detector.AVAudioApplication')
    @patch('mute_detector.AVAudioSession')
    @patch('mute_detector.NSNotificationCenter')
    def test_start_audio_session_error(self, mock_notification_center, mock_audio_session, mock_audio_app):
        """Test handling audio session configuration error."""
        # Set up mocks with error
        mock_session_instance = MagicMock()
        mock_session_instance.setCategory_mode_options_error_.return_value = (False, "Test Error")
        mock_audio_session.sharedInstance.return_value = mock_session_instance

        # Verify RuntimeError is raised
        with self.assertRaises(RuntimeError) as context:
            self.detector.start()

        self.assertIn("Failed to set audio session category", str(context.exception))


if __name__ == '__main__':
    unittest.main()
