import unittest
from unittest.mock import patch, MagicMock
import sys

from keyviz.input_handler import (
    KeyboardSignaller,
    InputHandler,
    verify_cli_consent
)

class TestInputHandler(unittest.TestCase):
    
    @patch("keyboard.hook")
    def test_start_hook(self, mock_hook):
        """Verifies hook is registered on start_hook."""
        signaller = KeyboardSignaller()
        handler = InputHandler({}, signaller)
        handler.start_hook()
        
        self.assertTrue(handler.is_hooked)
        mock_hook.assert_called_once_with(handler.on_key_event)

    @patch("keyboard.unhook_all")
    @patch("keyboard.hook")
    def test_stop_hook(self, mock_hook, mock_unhook):
        """Verifies unhook is requested on stop_hook."""
        signaller = KeyboardSignaller()
        handler = InputHandler({}, signaller)
        handler.start_hook()
        handler.stop_hook()
        
        self.assertFalse(handler.is_hooked)
        mock_unhook.assert_called_once()

    def test_on_key_event_down(self):
        """Asserts key press is propagated to Qt signaller correctly."""
        signaller = KeyboardSignaller()
        handler = InputHandler({}, signaller)
        
        # Capture signal
        received = []
        def on_press(sc, name):
            received.append((sc, name))
        signaller.press_sig.connect(on_press)
        
        # Mock key event
        mock_event = MagicMock()
        mock_event.scan_code = 57
        mock_event.name = "space"
        mock_event.event_type = "down"
        
        handler.on_key_event(mock_event)
        self.assertEqual(received, [(57, "space")])

    def test_on_key_event_up(self):
        """Asserts key release is propagated to Qt signaller correctly."""
        signaller = KeyboardSignaller()
        handler = InputHandler({}, signaller)
        
        # Capture signal
        received = []
        def on_release(sc, name):
            received.append((sc, name))
        signaller.release_sig.connect(on_release)
        
        # Mock key event
        mock_event = MagicMock()
        mock_event.scan_code = 57
        mock_event.name = "space"
        mock_event.event_type = "up"
        
        handler.on_key_event(mock_event)
        self.assertEqual(received, [(57, "space")])

    @patch("builtins.input", return_value="y")
    def test_verify_cli_consent_granted(self, mock_input):
        """Asserts y/yes input grants consent, sets flag, and calls save callback."""
        config_data = {"consent_granted": False}
        mock_save = MagicMock()
        
        res = verify_cli_consent(config_data, mock_save)
        
        self.assertTrue(res)
        self.assertTrue(config_data["consent_granted"])
        mock_save.assert_called_once_with(config_data)

    @patch("builtins.input", return_value="n")
    @patch("sys.exit")
    def test_verify_cli_consent_denied(self, mock_exit, mock_input):
        """Asserts denial triggers sys.exit."""
        config_data = {"consent_granted": False}
        mock_save = MagicMock()
        
        verify_cli_consent(config_data, mock_save)
        
        mock_exit.assert_called_once_with(0)
        self.assertFalse(config_data["consent_granted"])
        mock_save.assert_not_called()

if __name__ == "__main__":
    unittest.main()
