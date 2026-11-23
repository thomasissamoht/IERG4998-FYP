import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bib import LARGE_BIB_PARSE_THRESHOLD
from bib_gui_modern import (
    ModernBibGUI,
    _large_preview_source,
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

    def test_large_preview_skips_generated_folders_and_uses_total_source_size(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            generated = root / "processed"
            generated.mkdir()
            with (generated / "large.bib").open("wb") as file:
                file.truncate(LARGE_BIB_PARSE_THRESHOLD)
            self.assertFalse(_large_preview_source(root))
            with (root / "source.bib").open("wb") as file:
                file.truncate(LARGE_BIB_PARSE_THRESHOLD - 1)
            (root / "source.tex").write_text("x", encoding="utf-8")
            self.assertTrue(_large_preview_source(root))

    def test_preview_starts_in_worker_thread(self):
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui._preview_generation = 3
        gui.run_btn = MagicMock()
        gui._set_status = MagicMock()
        gui._load_library_entries = MagicMock()
        with patch("bib_gui_modern.threading.Thread") as thread:
            gui._load_library_preview_from_source("source")
        self.assertEqual(thread.call_args.kwargs["args"], ("source", 3))
        thread.return_value.start.assert_called_once()
        gui.run_btn.configure.assert_called_once_with(state="disabled")

    def test_large_preview_does_not_parse_and_stale_result_is_ignored(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with (root / "large.bib").open("wb") as file:
                file.truncate(LARGE_BIB_PARSE_THRESHOLD)
            gui = ModernBibGUI.__new__(ModernBibGUI)
            gui._preview_generation = 2
            gui.processing = False
            gui.run_btn = MagicMock()
            gui.manager = MagicMock()
            gui._load_library_entries = MagicMock()
            gui._set_status = MagicMock()
            gui._log_message = MagicMock()
            gui._ui_call = lambda function, *args: function(*args)
            with patch("bib_gui_modern.BibliographyManager.crawl_and_collect") as crawl:
                gui._library_preview_worker(str(root), 1)
                crawl.assert_not_called()
            gui.run_btn.configure.assert_not_called()
            self.assertIsNotNone(gui.manager)
            gui._library_preview_worker(str(root), 2)
            self.assertIsNone(gui.manager)
            gui.run_btn.configure.assert_called_once_with(state="normal")
            gui._load_library_entries.assert_called_once()
            self.assertIn("Large source", gui._set_status.call_args.args[0])

    def test_preview_error_reenables_analyze_and_shows_details(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            gui = ModernBibGUI.__new__(ModernBibGUI)
            gui._preview_generation = 1
            gui.processing = False
            gui.root = object()
            gui.run_btn = MagicMock()
            gui._set_status = MagicMock()
            gui._log_message = MagicMock()
            gui._ui_call = lambda function, *args: function(*args)
            with patch("bib_gui_modern.BibliographyManager.crawl_and_collect", side_effect=ValueError("bad data")), \
                 patch("bib_gui_modern._save_diagnostic", return_value="diagnostic location"), \
                 patch("bib_gui_modern.messagebox.showerror") as error:
                gui._library_preview_worker(temporary_directory, 1)
            gui.run_btn.configure.assert_called_once_with(state="normal")
            self.assertIn("ValueError: bad data", error.call_args.args[1])
            self.assertIn("diagnostic location", error.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
