import unittest

from bib_gui_modern import ModernBibGUI


class FakeVariable:
    def set(self, value):
        self.value = value


class FakeMenu:
    def configure(self, **kwargs):
        self.config = kwargs


class CollectionMenuTests(unittest.TestCase):
    def make_gui(self, names, selected=None, active=None):
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui._custom_collections = {name: set() for name in names}
        gui._selected_action_collection = selected
        gui._active_collection_name = active
        gui._selected_library_entry = None
        gui.library_action_collection_var = FakeVariable()
        gui.library_action_collection_menu = FakeMenu()
        gui._update_library_selection_actions = lambda entry: None
        return gui

    def test_empty_collections_clear_selection(self):
        gui = self.make_gui([], selected="old")
        gui._refresh_action_collection_menu()
        self.assertIsNone(gui._selected_action_collection)
        self.assertEqual(gui.library_action_collection_var.value, "Create a collection first")
        self.assertEqual(gui.library_action_collection_menu.config["state"], "disabled")

    def test_existing_selection_is_kept(self):
        gui = self.make_gui(["Alpha", "Beta"], selected="Beta", active="Alpha")
        gui._refresh_action_collection_menu()
        self.assertEqual(gui.library_action_collection_var.value, "Beta")
        self.assertEqual(gui._selected_action_collection, "Beta")

    def test_invalid_selection_uses_active_or_first_collection(self):
        gui = self.make_gui(["Alpha", "Beta"], selected="old", active="Beta")
        gui._refresh_action_collection_menu()
        self.assertEqual(gui.library_action_collection_var.value, "Beta")
        gui._selected_action_collection = None
        gui._active_collection_name = None
        gui._refresh_action_collection_menu()
        self.assertEqual(gui.library_action_collection_var.value, "Alpha")


if __name__ == "__main__":
    unittest.main()
