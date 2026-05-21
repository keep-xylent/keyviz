import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import json
import tempfile
import shutil

from keyviz.config_manager import (
    DEFAULT_CONFIG,
    validate_and_migrate,
    update_button_pos,
    get_config_path,
    load_config,
    save_config,
    load_packaged_json
)

class TestConfigManager(unittest.TestCase):
    
    def test_validate_and_migrate_empty(self):
        """Verifies empty config returns a clean defaults dictionary with version 1."""
        res = validate_and_migrate({})
        self.assertEqual(res["version"], 1)
        self.assertEqual(res["pos"], DEFAULT_CONFIG["pos"])
        self.assertEqual(res["recorded_keys"], DEFAULT_CONFIG["recorded_keys"])
        self.assertFalse(res["consent_granted"])

    def test_validate_and_migrate_valid(self):
        """Verifies valid parameters pass and persist types correctly."""
        raw = {
            "version": 0,
            "pos": [200, 300],
            "recorded_keys": {"gaming": ["w", "a"]},
            "mode": "gaming",
            "color": "rgb",
            "custom_pos": {"gaming": {"w": [50, 60]}},
            "no_mouse": True,
            "consent_granted": True
        }
        res = validate_and_migrate(raw)
        self.assertEqual(res["version"], 1)
        self.assertEqual(res["pos"], [200, 300])
        self.assertEqual(res["recorded_keys"], {"gaming": ["w", "a"]})
        self.assertEqual(res["mode"], "gaming")
        self.assertEqual(res["color"], "rgb")
        self.assertEqual(res["custom_pos"], {"gaming": {"w": [50, 60]}})
        self.assertTrue(res["no_mouse"])
        self.assertTrue(res["consent_granted"])

    def test_validate_and_migrate_invalid_types_fallback(self):
        """Verifies invalid property types fall back to defaults without throwing errors."""
        raw = {
            "pos": "invalid_pos_type",
            "recorded_keys": "not_a_dict",
            "mode": 12345,  # not a string
            "color": None,
            "no_mouse": "yes",  # parses to bool
            "consent_granted": 0  # parses to bool
        }
        res = validate_and_migrate(raw)
        self.assertEqual(res["pos"], DEFAULT_CONFIG["pos"])
        self.assertEqual(res["recorded_keys"], DEFAULT_CONFIG["recorded_keys"])
        self.assertEqual(res["mode"], DEFAULT_CONFIG["mode"])
        self.assertEqual(res["color"], DEFAULT_CONFIG["color"])
        self.assertTrue(res["no_mouse"])
        self.assertFalse(res["consent_granted"])

    def test_validate_and_migrate_legacy_single_layer_custom_pos(self):
        """Verifies legacy custom_pos layout maps correctly."""
        raw = {
            "custom_pos": {
                "w": [10, 20],
                "a": [30, 40]
            }
        }
        res = validate_and_migrate(raw)
        self.assertEqual(res["custom_pos"]["w"], [10, 20])
        self.assertEqual(res["custom_pos"]["a"], [30, 40])

    def test_update_button_pos(self):
        """Asserts updating button position modifies custom_pos nested directories."""
        cfg = {"custom_pos": {}}
        updated = update_button_pos(cfg, "normal", "space", 150, 200)
        self.assertEqual(updated["custom_pos"]["normal"]["space"], [150, 200])

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"pos": [99, 99]}')
    def test_load_config_existing_valid(self, mock_file, mock_exists):
        """Asserts loading an existing valid file returns the parsed and migrated config."""
        mock_exists.return_value = True
        cfg = load_config()
        self.assertEqual(cfg["pos"], [99, 99])
        self.assertEqual(cfg["version"], 1)

    @patch("os.path.exists")
    @patch("shutil.copy2")
    @patch("builtins.open", new_callable=mock_open, read_data="malformed { json")
    def test_load_config_corrupted_fallback(self, mock_file, mock_copy, mock_exists):
        """Asserts loading a corrupted file triggers recovery and backup logic, returning defaults."""
        mock_exists.return_value = True
        
        # We also mock write to config inside exception handler
        with patch("keyviz.config_manager.save_config") as mock_save:
            cfg = load_config()
            self.assertEqual(cfg["pos"], DEFAULT_CONFIG["pos"])
            mock_copy.assert_called_once()
            mock_save.assert_called_once_with(DEFAULT_CONFIG)

if __name__ == "__main__":
    unittest.main()
