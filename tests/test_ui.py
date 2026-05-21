import unittest
from unittest.mock import MagicMock, patch
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint

from keyviz.ui import ZoomEffect, KeyButton, ConsentDialog, KeyboardOverlay

# Initialize a global QApplication instance for headless unit testing
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

class TestUI(unittest.TestCase):
    
    def setUp(self):
        # Build mock config manager
        self.mock_cm = MagicMock()
        self.mock_cm.CONFIG_DIR = "dummy_dir"
        self.mock_cm.get_config_path.return_value = "dummy_config.json"
        
        self.mock_cm.load_config.return_value = {
            "version": 1,
            "pos": [150, 150],
            "recorded_keys": {},
            "mode": "normal",
            "color": "default",
            "custom_pos": {},
            "no_mouse": False,
            "consent_granted": True
        }
        
        # Side effect for static package loading
        def mock_load_json(filename):
            if filename == "key.json":
                return {"esc": 1, "w": 17, "a": 30, "s": 31, "d": 32}
            elif filename == "layout.json":
                return [
                    {"sc_key": "esc", "x": 10, "y": 10, "w": 50, "h": 50, "label": "ESC"},
                    {"sc_key": "w", "x": 70, "y": 10, "w": 50, "h": 50, "label": "W"}
                ]
            return {}
            
        self.mock_cm.load_packaged_json.side_effect = mock_load_json
        
        # Build mock input handler
        self.mock_ih = MagicMock()
        self.mock_ih.signaller = MagicMock()

    def test_zoom_effect_lifecycle(self):
        """Verifies ZoomEffect updates scale and decays life values correctly."""
        effect = ZoomEffect(None, "X", None, None)
        self.assertEqual(effect.life, 1.0)
        self.assertEqual(effect.scale, 1.0)
        
        still_alive = effect.update()
        
        self.assertTrue(still_alive)
        self.assertLess(effect.life, 1.0)
        self.assertGreater(effect.scale, 1.0)

    def test_key_button_activation(self):
        """Verifies KeyButton registers label text and responds to activation state changes."""
        btn = KeyButton("w", [17], "W", 60, 60)
        self.assertEqual(btn.label.text(), "W")
        self.assertFalse(btn.is_active)
        
        btn.set_active(True)
        self.assertTrue(btn.is_active)
        
        btn.set_active(False)
        self.assertFalse(btn.is_active)

    def test_consent_dialog_creation(self):
        """Verifies ConsentDialog layout and title properties initialize properly."""
        dialog = ConsentDialog()
        self.assertEqual(dialog.windowTitle(), "KeyViz - Security Consent")
        self.assertIsNotNone(dialog.layout())

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_keyboard_overlay_layout_rebuild(self, mock_single_shot):
        """Asserts KeyboardOverlay instantiates button structures mapped from configs."""
        overlay = KeyboardOverlay(
            config_manager=self.mock_cm,
            input_handler=self.mock_ih,
            mode="normal"
        )
        
        # Check that we built 2 buttons based on the layout mock
        self.assertEqual(len(overlay.buttons), 2)
        
        # Check scan code registration maps to target buttons
        self.assertIn(1, overlay.keys_map)   # esc -> 1
        self.assertIn(17, overlay.keys_map)  # w -> 17
        
        # Assert we configured the startup single shot keyboard hook
        mock_single_shot.assert_called_once()

if __name__ == "__main__":
    unittest.main()
