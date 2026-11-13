import json
import tempfile
import unittest
from pathlib import Path

from bib_gui_modern import (
    ModernBibGUI,
    _load_last_source,
    _resolve_appearance_mode,
    _save_last_source,
)


class GuiSettingsTests(unittest.TestCase):
    def test_system_appearance_uses_detected_mode(self):
        self.assertEqual(_resolve_appearance_mode("System", "Dark"), "dark")
        self.assertEqual(_resolve_appearance_mode("System", "Light"), "light")

    def test_explicit_appearance_mode_overrides_system_mode(self):
        self.assertEqual(_resolve_appearance_mode("Dark", "Light"), "dark")
        self.assertEqual(_resolve_appearance_mode("Light", "Dark"), "light")

    def test_appearance_palette_has_readable_light_and_dark_surfaces(self):
        gui = ModernBibGUI.__new__(ModernBibGUI)
        light = gui._theme_palette("light")
        dark = gui._theme_palette("dark")

        self.assertEqual(light["root"], "#e9eef6")
        self.assertEqual(light["text"], "#162133")
        self.assertEqual(dark["root"], "#0b1020")
        self.assertEqual(dark["text"], "#e5edf9")
        self.assertNotEqual(dark["card"], dark["surface"])

    def test_unsupported_appearance_mode_is_reported(self):
        with self.assertRaises(ValueError):
            _resolve_appearance_mode("sepia", "Light")

    def test_load_missing_settings_returns_empty_path(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            settings_file = Path(temporary_directory) / "settings.json"
            self.assertEqual(_load_last_source(settings_file), "")

    def test_save_and_load_last_source(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            settings_file = Path(temporary_directory) / "config" / "settings.json"
            source_path = str(Path(temporary_directory) / "project")
            _save_last_source(source_path, settings_file)
            self.assertEqual(_load_last_source(settings_file), source_path)

    def test_invalid_saved_source_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            settings_file = Path(temporary_directory) / "settings.json"
            settings_file.write_text(json.dumps({"last_source_path": 5}), encoding="utf-8")
            with self.assertRaises(ValueError):
                _load_last_source(settings_file)


if __name__ == "__main__":
    unittest.main()
