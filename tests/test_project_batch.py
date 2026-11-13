import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bibtexparser

from project_batch import discover_projects, process_projects, validate_project_roots


class ProjectBatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def make_project(self, name, author, year, key="same"):
        root = self.root / name
        root.mkdir(parents=True)
        (root / "main.tex").write_text(
            "\\documentclass{article}\n\\cite{" + key + "}\n", encoding="utf-8"
        )
        (root / "refs.bib").write_text(
            f"@book{{{key},author={{{author}}},year={{{year}}},title={{A unique {name}}}}}\n",
            encoding="utf-8",
        )
        return root

    def test_discovery_ignores_generated_folders_and_keeps_nested_roots_visible(self):
        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("group/second", "Jones", 2021)
        nested = self.make_project("first/nested", "Doe", 2022)
        ignored = first / "processed"
        ignored.mkdir()
        (ignored / "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
        (first / "refs").mkdir()
        (first / "refs" / "extra.bib").write_text("@book{x,title={X}}", encoding="utf-8")
        self.assertEqual(set(discover_projects(self.root)), {first, second, nested})
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_project_roots(self.root, [first, nested])
        self.assertEqual(validate_project_roots(self.root, [first, second]), [first, second])

    def test_projects_with_same_keys_are_reviewed_and_written_independently(self):
        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("second", "Jones", 2021)
        originals = {path: path.read_bytes() for path in (first / "main.tex", first / "refs.bib", second / "main.tex", second / "refs.bib")}
        reviews = []

        def review(path, manager):
            reviews.append((path, list(manager.report_data["keys_changed"])))
            return True

        results = process_projects([first, second], 85, True, review, lambda: False, lambda _: None)
        self.assertEqual([item["status"] for item in results], ["success", "success"])
        self.assertEqual(reviews, [(first, [("same", "S2020")]), (second, [("same", "J2021")])])
        for root, key in [(first, "S2020"), (second, "J2021")]:
            output = root / "processed"
            self.assertIn("\\cite{" + key + "}", (output / "main.tex").read_text(encoding="utf-8"))
            database = bibtexparser.loads((output / "master.bib").read_text(encoding="utf-8"))
            self.assertEqual([entry["ID"] for entry in database.entries], [key])
            self.assertTrue((output / "report.html").is_file())
        self.assertEqual(originals, {path: path.read_bytes() for path in originals})

    def test_failure_empty_project_and_cancellation_are_reported(self):
        bad = self.make_project("bad", "Smith", 2020)
        (bad / "main.tex").write_bytes(b"\xff")
        empty = self.root / "empty"
        empty.mkdir()
        good = self.make_project("good", "Jones", 2021)
        after = self.make_project("after", "Doe", 2022)
        stopped = False

        def review(_project, _manager):
            nonlocal stopped
            stopped = True
            return False

        results = process_projects([bad, empty, good, after], 85, False, review, lambda: stopped, lambda _: None)
        self.assertEqual([r["status"] for r in results], ["error", "skipped", "skipped", "skipped"])
        self.assertIn("LaTeX", results[0]["detail"])
        self.assertIn("No bibliography", results[1]["detail"])
        self.assertIn("Review cancelled", results[2]["detail"])
        self.assertIn("Batch cancelled", results[3]["detail"])
        self.assertFalse((good / "processed").exists())
        self.assertFalse((after / "processed").exists())

    def test_rejects_outside_duplicate_and_generated_roots(self):
        project = self.make_project("project", "Smith", 2020)
        for invalid in [[], [project, project], [self.root.parent]]:
            with self.assertRaises(ValueError):
                validate_project_roots(self.root, invalid)
        generated = project / "processed"
        generated.mkdir()
        with self.assertRaisesRegex(ValueError, "Generated"):
            validate_project_roots(self.root, [generated])

    def test_nested_generated_folders_are_not_scanned_or_copied(self):
        project = self.make_project("project", "Smith", 2020)
        generated = project / "chapter" / "processed"
        generated.mkdir(parents=True)
        (generated / "stale.bib").write_text("@book{stale,title={Stale}}", encoding="utf-8")
        results = process_projects([project], 85, False, lambda *_: True, lambda: False, lambda _: None)
        self.assertEqual(results[0]["status"], "success")
        self.assertEqual(results[0]["manager"].report_data["initial_entries"], 1)
        self.assertFalse((project / "processed" / "chapter" / "processed").exists())

    def test_later_failure_does_not_remove_earlier_output(self):
        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("second", "Jones", 2021)
        (second / "refs.bib").write_bytes(b"\xff")
        results = process_projects([first, second], 85, False, lambda *_: True, lambda: False, lambda _: None)
        self.assertEqual([result["status"] for result in results], ["success", "error"])
        self.assertTrue((first / "processed" / "master.bib").exists())
        self.assertFalse((second / "processed").exists())

    def test_project_with_only_master_bib_is_discovered_and_processed(self):
        project = self.root / "master-only"
        project.mkdir()
        source = project / "master.bib"
        source.write_text("@book{old,author={Smith},year={2020},title={Work}}", encoding="utf-8")
        self.assertEqual(discover_projects(self.root), [project])
        results = process_projects([project], 85, False, lambda *_: True, lambda: False, lambda _: None)
        self.assertEqual(results[0]["status"], "success")
        self.assertIn("@book{old,", source.read_text(encoding="utf-8"))
        self.assertIn("@book{S2020,", (project / "processed" / "master.bib").read_text(encoding="utf-8"))

    def test_desktop_batch_worker_requests_review_for_each_project(self):
        from bib_gui_modern import ModernBibGUI

        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("second", "Jones", 2021)
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.processing = True
        gui._key_review_event = None
        reviewed = []
        finished = []
        gui._log_message = lambda _message: None
        gui._ui_call = lambda function, *args, **kwargs: function(*args, **kwargs)

        def approve():
            reviewed.append((gui._batch_project, list(gui.manager.report_data["keys_changed"])))
            gui._key_review_approved = True
            gui._key_review_event.set()

        gui._show_key_review = approve
        gui._finish_batch = finished.extend
        gui._batch_worker([first, second], 85, False)
        self.assertEqual(reviewed, [(first, [("same", "S2020")]), (second, [("same", "J2021")])])
        self.assertEqual([result["status"] for result in finished], ["success", "success"])
        self.assertFalse(gui.processing)

    def test_desktop_starts_unambiguous_projects_without_folder_dialog(self):
        from bib_gui_modern import ModernBibGUI

        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("second", "Jones", 2021)
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.processing = False
        gui.root = object()
        started = []
        gui._start_batch = started.extend
        with patch("bib_gui_modern.filedialog.askdirectory", return_value=str(self.root)), \
             patch.object(gui, "_resolve_batch_project_folders") as resolve:
            gui._browse_batch_projects()
        self.assertEqual(started, [first, second])
        resolve.assert_not_called()

    def test_desktop_asks_to_resolve_overlapping_roots(self):
        from bib_gui_modern import ModernBibGUI

        first = self.make_project("first", "Smith", 2020)
        nested = self.make_project("first/nested", "Jones", 2021)
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.processing = False
        gui.root = object()
        with patch("bib_gui_modern.filedialog.askdirectory", return_value=str(self.root)), \
             patch.object(gui, "_resolve_batch_project_folders") as resolve, \
             patch.object(gui, "_start_batch") as start:
            gui._browse_batch_projects()
        start.assert_not_called()
        self.assertEqual(resolve.call_args.args[:2], (self.root, [first, nested]))
        self.assertIn("overlap", resolve.call_args.args[2])

    def test_desktop_reports_no_detected_projects(self):
        from bib_gui_modern import ModernBibGUI

        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.processing = False
        gui.root = object()
        with patch("bib_gui_modern.filedialog.askdirectory", return_value=str(self.root)), \
             patch("bib_gui_modern.messagebox.showinfo") as info, \
             patch.object(gui, "_start_batch") as start:
            gui._browse_batch_projects()
        start.assert_not_called()
        self.assertEqual(info.call_args.args[0], "No projects found")

    def test_batch_processes_manual_and_filecontents_bibliographies(self):
        manual = self.root / "manual"
        manual.mkdir()
        original = (
            "\\documentclass{article}\n\\cite{one}\n"
            "\\begin{thebibliography}{9}\n\\bibitem{one}A reference.\n"
            "\\end{thebibliography}\n"
        )
        (manual / "main.tex").write_text(original, encoding="utf-8")
        embedded = self.root / "embedded"
        embedded.mkdir()
        (embedded / "main.tex").write_text(
            "\\begin{filecontents*}{refs.bib}\n"
            "@book{old,author={Smith},year={2020},title={Work}}\n"
            "\\end{filecontents*}\n\\documentclass{article}\n\\cite{old}\n",
            encoding="utf-8",
        )
        self.assertEqual(set(discover_projects(self.root)), {manual, embedded})
        results = process_projects([manual, embedded], 85, False, lambda *_: True, lambda: False, lambda _: None)
        self.assertEqual([result["status"] for result in results], ["success", "success"])
        self.assertEqual((manual / "processed" / "main.tex").read_text(encoding="utf-8"), original)
        self.assertIn("\\cite{S2020}", (embedded / "processed" / "main.tex").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
