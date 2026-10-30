import unittest

from bib_gui_modern import ModernBibGUI, _resolve_appearance_mode


class ThemeAppearanceTests(unittest.TestCase):
    def test_system_appearance_resolves_to_detected_mode(self):
        self.assertEqual(_resolve_appearance_mode("System", "Dark"), "dark")
        self.assertEqual(_resolve_appearance_mode("System", "Light"), "light")

    def test_explicit_appearance_mode_overrides_system_mode(self):
        self.assertEqual(_resolve_appearance_mode("Dark", "Light"), "dark")
        self.assertEqual(_resolve_appearance_mode("Light", "Dark"), "light")

    def test_light_and_dark_palettes_have_readable_distinct_surfaces(self):
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


if __name__ == "__main__":
    unittest.main()
