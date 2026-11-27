import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from bib_gui_modern import ModernBibGUI


class FakeVariable:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeWidget:
    def __init__(self):
        self.config = {}
        self.value = None

    def configure(self, **kwargs):
        self.config.update(kwargs)

    def set(self, value):
        self.value = value

    def get(self):
        return self.value

    def grid(self):
        pass

    def grid_remove(self):
        pass


class FakeTree:
    def __init__(self):
        self.rows = []
        self.config = {}

    def configure(self, **kwargs):
        self.config.update(kwargs)

    def delete(self, *_items):
        self.rows.clear()

    def get_children(self):
        return list(range(len(self.rows)))

    def insert(self, _parent, _index, values):
        self.rows.append(values)


class KeyReviewTests(unittest.TestCase):
    def make_gui(self, mappings):
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.manager = SimpleNamespace(report_data={"keys_changed": mappings})
        gui._key_review_items = []
        gui._key_review_push_back = True
        gui._batch_project = None
        gui._batch_progress = None
        gui._review_source = None
        gui.key_review_search_var = FakeVariable()
        gui.key_review_tree = FakeTree()
        gui.key_review_count_label = FakeWidget()
        gui.key_review_status_label = FakeWidget()
        gui.key_review_project_label = FakeWidget()
        gui.key_review_path_label = FakeWidget()
        gui.key_review_confirm_btn = FakeWidget()
        gui.key_review_cancel_btn = FakeWidget()
        gui.key_review_mark_btn = FakeWidget()
        gui.key_review_project_menu = FakeWidget()
        gui.key_review_progress = FakeWidget()
        gui.key_review_single_btn = FakeWidget()
        gui.tabview = FakeWidget()
        gui._apply_pipeline_snapshot = lambda: None
        gui._set_status = lambda *args: None
        return gui

    def test_review_uses_real_changed_keys_and_search_filters_both_columns(self):
        gui = self.make_gui([
            ("legacySmith2024", "S2024"),
            ("alreadyNormalized", "alreadyNormalized"),
            ("oldDoe2023", "D2023"),
        ])

        gui._show_key_review()

        self.assertEqual(gui._key_review_items, [
            ("legacySmith2024", "S2024"),
            ("oldDoe2023", "D2023"),
        ])
        self.assertEqual(len(gui.key_review_tree.rows), 2)
        self.assertEqual(gui.key_review_confirm_btn.config["state"], "normal")
        self.assertEqual(gui.tabview.value, "🔑 Key Review")

        gui.key_review_search_var.set("d2023")
        gui._filter_key_review()

        self.assertEqual(gui.key_review_tree.rows, [("", "oldDoe2023", "D2023")])
        self.assertEqual(gui.key_review_count_label.config["text"], "1 of 2 changes")

    def test_approval_releases_pipeline_worker(self):
        gui = self.make_gui([])
        gui._key_review_event = threading.Event()

        gui._approve_key_review()

        self.assertTrue(gui._key_review_approved)
        self.assertTrue(gui._key_review_event.is_set())
        self.assertEqual(gui.key_review_confirm_btn.config["state"], "disabled")
        self.assertEqual(gui.key_review_status_label.config["text"], "Creating the output from the reviewed mappings...")

    def test_batch_review_shows_project_name_progress_and_full_path(self):
        gui = self.make_gui([("old", "new")])
        gui._batch_project = Path("workspace") / "First Paper"
        gui._batch_progress = (2, 4)
        gui._show_key_review()
        self.assertEqual(gui.key_review_project_label.config["text"], "Reviewing: First Paper  (project 2 of 4)")
        self.assertEqual(gui.key_review_path_label.config["text"], f"Location: {gui._batch_project}")
        gui._batch_project = Path("workspace") / "Other Paper"
        gui._batch_progress = (4, 4)
        gui._show_key_review()
        self.assertEqual(gui.key_review_project_label.config["text"], "Reviewing: Other Paper  (project 4 of 4)")
        self.assertEqual(gui.key_review_path_label.config["text"], f"Location: {gui._batch_project}")

    def test_batch_review_is_per_project_and_requires_each_ready_project(self):
        gui = self.make_gui([])
        first = Path("workspace") / "First Paper"
        second = Path("workspace") / "Failed Paper"
        third = Path("workspace") / "Third Paper"
        manager = SimpleNamespace(root_files_only=False, report_data={
            "key_audit": [
                {"Original Raw Key": "old", "Normalized Key": "S2024"},
                {"Original Raw Key": "same", "Normalized Key": "same"},
            ],
            "duplicate_groups": [{"entries": [
                {"ID": "old", "_status": "kept"},
                {"ID": "duplicate", "_status": "removed"},
            ]}],
        })
        gui._show_batch_key_review([
            {"project": first, "status": "ready", "manager": manager},
            {"project": second, "status": "error", "detail": "Could not read source"},
            {"project": third, "status": "ready", "manager": manager},
        ])
        self.assertEqual(gui.key_review_tree.rows, [
            (str(first), "old", "S2024"),
            (str(first), "same", "same"),
            (str(first), "duplicate", "Merged duplicate (not in master)"),
        ])
        self.assertEqual(gui.key_review_confirm_btn.config["state"], "disabled")
        gui._select_batch_key_review(str(second))
        self.assertEqual(gui.key_review_tree.rows, [(str(second), "ERROR", "Could not read source")])
        gui.key_review_project_menu.set(str(first))
        gui._mark_batch_project_reviewed()
        self.assertEqual(gui.key_review_project_menu.get(), str(third))
        self.assertEqual(gui.key_review_confirm_btn.config["state"], "disabled")
        gui._mark_batch_project_reviewed()
        self.assertEqual(gui.key_review_confirm_btn.config["state"], "normal")
        gui._batch_review_waiting = False
        gui._batch_review_results[0].update(status="success", detail="output")
        gui._select_batch_key_review(str(first))
        self.assertEqual(gui.key_review_tree.rows[0], (str(first), "old", "S2024"))
        self.assertEqual(gui.key_review_confirm_btn.config["state"], "disabled")

    def test_key_review_paginates_large_projects(self):
        gui = self.make_gui([(f"old{i}", f"new{i}") for i in range(1200)])
        gui._show_key_review()
        self.assertEqual(len(gui.key_review_tree.rows), 500)
        gui._change_key_review_page(1)
        self.assertEqual(gui.key_review_tree.rows[0], ("", "old500", "new500"))
        gui._change_key_review_page(1)
        self.assertEqual(len(gui.key_review_tree.rows), 200)

    def test_project_inventory_is_shown_before_analysis(self):
        gui = self.make_gui([])
        gui.dir_entry = FakeVariable("workspace")
        projects = [Path("workspace") / "one", Path("workspace") / "two"]
        gui._show_discovered_projects(projects)
        self.assertEqual(gui.key_review_project_label.config["text"], "2 projects found")
        self.assertEqual([row[0] for row in gui.key_review_tree.rows], list(map(str, projects)))
        self.assertEqual(gui.key_review_confirm_btn.config["text"], "Analyze projects")
        started = []
        gui._start_batch = started.extend
        gui._approve_key_review()
        self.assertEqual(started, projects)

    def test_single_file_review_uses_original_source_name(self):
        gui = self.make_gui([])
        gui._review_source = Path("workspace") / "submitted.zip"
        gui._show_key_review()
        self.assertEqual(gui.key_review_project_label.config["text"], "Reviewing: submitted.zip")
        self.assertEqual(gui.key_review_path_label.config["text"], f"Location: {gui._review_source}")

    def test_cancelling_review_releases_worker_without_approval(self):
        gui = self.make_gui([])
        gui.processing = True
        gui._key_review_event = threading.Event()
        gui._log_message = lambda _message: None
        gui._set_status = lambda *args: None

        gui._cancel_key_review()

        self.assertFalse(gui.processing)
        self.assertFalse(gui._key_review_approved)
        self.assertTrue(gui._key_review_event.is_set())
        self.assertEqual(gui.key_review_confirm_btn.config["state"], "disabled")


if __name__ == "__main__":
    unittest.main()
