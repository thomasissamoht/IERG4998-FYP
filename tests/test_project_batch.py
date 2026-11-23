import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_discovery_ignores_generated_folders_and_keeps_outermost_roots(self):
        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("group/second", "Jones", 2021)
        nested = self.make_project("first/nested", "Doe", 2022)
        ignored = first / "processed"
        ignored.mkdir()
        (ignored / "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
        (first / "refs").mkdir()
        (first / "refs" / "extra.bib").write_text("@book{x,title={X}}", encoding="utf-8")
        self.assertEqual(set(discover_projects(self.root)), {first, second})
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_project_roots(self.root, [first, nested])
        self.assertEqual(validate_project_roots(self.root, [first, second]), [first, second])

    def test_projects_with_same_keys_are_reviewed_and_written_independently(self):
        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("second", "Jones", 2021)
        originals = {path: path.read_bytes() for path in (first / "main.tex", first / "refs.bib", second / "main.tex", second / "refs.bib")}
        reviews = []

        def review(items):
            reviews.extend((item["project"], list(item["manager"].report_data["keys_changed"])) for item in items)
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

    def test_batch_previews_all_projects_before_creating_any_output(self):
        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("second", "Jones", 2021)
        reviews = []

        def review(results):
            self.assertFalse((first / "processed").exists())
            self.assertFalse((second / "processed").exists())
            reviews.append([(item["project"], item["status"]) for item in results])
            return True

        results = process_projects([first, second], 85, False, review, lambda: False, lambda _: None)
        self.assertEqual(reviews, [[(first, "ready"), (second, "ready")]])
        self.assertEqual([item["status"] for item in results], ["success", "success"])

    def test_large_duplicate_report_includes_all_entries_and_key_changes(self):
        from bib import BibliographyManager

        manager = BibliographyManager(str(self.root))
        entries = [
            {"ID": f"key{i}", "title": f"Title {i}", "author": "Smith", "year": "2020"}
            for i in range(3000)
        ]
        manager.report_data.update({
            "initial_entries": len(entries),
            "final_entries": 1,
            "duplicates_removed": len(entries) - 1,
            "duplicate_groups": [{"entries": entries, "similarity": 100}],
            "keys_changed": [("key0", "S2020")],
        })
        report = Path(manager.generate_html_report(str(self.root / "report.html"))).read_text(encoding="utf-8")
        self.assertEqual(report.count('class="entry-key"'), len(entries))
        self.assertIn(">key0<", report)
        self.assertIn(">key2999<", report)
        self.assertIn(">S2020<", report)

    def test_failure_empty_project_and_cancellation_are_reported(self):
        bad = self.make_project("bad", "Smith", 2020)
        (bad / "main.tex").write_bytes(b"\xff")
        empty = self.root / "empty"
        empty.mkdir()
        good = self.make_project("good", "Jones", 2021)
        after = self.make_project("after", "Doe", 2022)
        stopped = False

        def review(_results):
            nonlocal stopped
            stopped = True
            return False

        results = process_projects([bad, empty, good, after], 85, False, review, lambda: stopped, lambda _: None)
        self.assertEqual([r["status"] for r in results], ["error", "skipped", "skipped", "skipped"])
        self.assertIn("LaTeX", results[0]["detail"])
        self.assertIn("No bibliography", results[1]["detail"])
        self.assertIn("Batch cancelled", results[2]["detail"])
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
        seen = []
        def review(items):
            seen.extend((item["project"], item["status"]) for item in items)
            self.assertFalse((first / "processed").exists())
            return True
        results = process_projects([first, second], 85, False, review, lambda: False, lambda _: None)
        self.assertEqual(seen, [(first, "ready"), (second, "error")])
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

    def test_desktop_batch_worker_requests_one_review_before_any_output(self):
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

        def approve(results):
            self.assertFalse((first / "processed").exists())
            self.assertFalse((second / "processed").exists())
            reviewed.append([(result["project"], list(result["manager"].report_data["keys_changed"])) for result in results])
            gui._key_review_approved = True
            gui._key_review_event.set()

        gui._show_batch_key_review = approve
        gui._finish_batch = finished.extend
        gui._batch_worker([first, second], 85, False)
        self.assertEqual(reviewed, [[(first, [("same", "S2020")]), (second, [("same", "J2021")])]])
        self.assertEqual([result["status"] for result in finished], ["success", "success"])
        self.assertFalse(gui.processing)

    def test_rejecting_combined_review_writes_no_outputs(self):
        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("second", "Jones", 2021)
        results = process_projects([first, second], 85, False, lambda _items: False, lambda: False, lambda _: None)
        self.assertEqual([item["status"] for item in results], ["skipped", "skipped"])
        self.assertTrue(all(item["detail"] == "Review cancelled" for item in results))
        self.assertFalse((first / "processed").exists())
        self.assertFalse((second / "processed").exists())

    def test_batch_with_no_analyzable_projects_does_not_request_review(self):
        project = self.make_project("broken", "Smith", 2020)
        (project / "refs.bib").write_bytes(b"\xff")
        review = MagicMock()
        results = process_projects([project], 85, False, review, lambda: False, lambda _: None)
        review.assert_not_called()
        self.assertEqual(results[0]["status"], "error")
        self.assertFalse((project / "processed").exists())

    def test_review_render_failure_does_not_leave_batch_waiting(self):
        from bib_gui_modern import ModernBibGUI

        project = self.make_project("project", "Smith", 2020)
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.processing = True
        gui.root = object()
        gui._log_message = MagicMock()
        gui._show_batch_key_review = MagicMock(side_effect=RuntimeError("review failed"))
        gui._ui_call = lambda function, *args, **kwargs: function(*args, **kwargs)
        gui._finish_batch = MagicMock()
        with patch("bib_gui_modern._save_diagnostic", return_value="diagnostic location"), \
             patch("bib_gui_modern.messagebox.showerror") as error:
            gui._batch_worker([project], 85, False)
        self.assertIn("review failed", error.call_args.args[1])
        self.assertFalse(gui.processing)
        self.assertEqual(gui._finish_batch.call_args.args[0][0]["status"], "skipped")
        self.assertFalse((project / "processed").exists())

    def test_changed_sources_are_not_processed_with_stale_review(self):
        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("second", "Jones", 2021)
        def review(_items):
            with (first / "refs.bib").open("a", encoding="utf-8") as source:
                source.write("\n% edited after preview\n")
            return True
        results = process_projects([first, second], 85, False, review, lambda: False, lambda _: None)
        self.assertEqual([item["status"] for item in results], ["error", "success"])
        self.assertIn("changed after review", results[0]["detail"])
        self.assertFalse((first / "processed").exists())
        self.assertTrue((second / "processed" / "master.bib").exists())

    def test_source_change_during_analysis_is_reported_before_review(self):
        from bib import BibliographyManager

        project = self.make_project("project", "Smith", 2020)
        original_fix = BibliographyManager.fix_citation_keys
        def mutate_source(manager):
            original_fix(manager)
            (project / "new.tex").write_text("New source", encoding="utf-8")
        review = MagicMock()
        with patch.object(BibliographyManager, "fix_citation_keys", mutate_source):
            results = process_projects([project], 85, False, review, lambda: False, lambda _: None)
        review.assert_not_called()
        self.assertEqual(results[0]["status"], "error")
        self.assertIn("changed during analysis", results[0]["detail"])
        self.assertFalse((project / "processed").exists())

    def test_desktop_runs_multiple_projects_from_the_selected_folder(self):
        from bib_gui_modern import ModernBibGUI

        first = self.make_project("first", "Smith", 2020)
        second = self.make_project("second", "Jones", 2021)
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.processing = False
        gui.root = object()
        gui.dir_entry = type("Entry", (), {"get": lambda self: str(self.root)})()
        gui.dir_entry.root = self.root
        gui.push_var = type("Option", (), {"get": lambda self: True})()
        started = []
        gui._start_batch = started.extend
        gui._run_pipeline()
        self.assertEqual(started, [first, second])

    def test_desktop_runs_one_discovered_project_with_single_pipeline(self):
        from bib_gui_modern import ModernBibGUI

        project = self.make_project("group/paper", "Smith", 2020)
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.processing = False
        gui.root = object()
        gui.dir_entry = MagicMock()
        gui.dir_entry.get.return_value = str(self.root)
        gui.push_var = MagicMock()
        gui.push_var.get.return_value = True
        gui.threshold_var = MagicMock()
        gui.threshold_var.get.return_value = 85
        gui.report_var = MagicMock()
        gui.report_var.get.return_value = False
        for name in (
            "_reset_tex_document_view", "_log_message", "_set_status", "key_review_project_label",
            "key_review_path_label", "key_review_confirm_btn", "key_review_cancel_btn",
            "key_review_status_label", "key_review_tree", "key_review_count_label", "log_text",
            "results_text", "view_report_btn", "run_btn", "cancel_btn",
        ):
            setattr(gui, name, MagicMock())
        gui._ui_call = lambda function, *args, **kwargs: function(*args, **kwargs)
        gui._log_lock = threading.Lock()
        gui._deferred_logs = []
        with patch("bib_gui_modern._save_last_source"), \
             patch("bib_gui_modern.threading.Thread") as thread, \
             patch.object(gui, "_start_batch") as batch:
            gui._run_pipeline()
        batch.assert_not_called()
        self.assertEqual(thread.call_args.kwargs["args"][0]["directory"], str(project))
        thread.return_value.start.assert_called_once()

    def test_batch_requires_processed_copy_option(self):
        from bib_gui_modern import ModernBibGUI

        self.make_project("one", "Smith", 2020)
        self.make_project("two", "Jones", 2021)
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.processing = False
        gui.root = object()
        gui.dir_entry = MagicMock()
        gui.dir_entry.get.return_value = str(self.root)
        gui.push_var = MagicMock()
        gui.push_var.get.return_value = False
        with patch("bib_gui_modern.messagebox.showwarning") as warning, \
             patch.object(gui, "_start_batch") as batch:
            gui._run_pipeline()
        batch.assert_not_called()
        self.assertIn("Create processed copy", warning.call_args.args[1])

    def test_desktop_uses_outer_project_for_nested_roots(self):
        from bib_gui_modern import ModernBibGUI

        first = self.make_project("first", "Smith", 2020)
        self.make_project("first/nested", "Jones", 2021)
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.processing = False
        gui.root = object()
        self.assertEqual(discover_projects(self.root), [first])

    def test_selected_folder_with_bibliography_owns_nested_projects(self):
        project = self.make_project("parent", "Smith", 2020)
        nested = project / "nested"
        nested.mkdir()
        (nested / "main.tex").write_bytes(b"\xff")
        self.assertEqual(discover_projects(project), [project])

    def test_fragment_tex_at_project_root_keeps_nested_bibliography_in_project(self):
        project = self.root / "paper"
        project.mkdir()
        (project / "chapter.tex").write_text(r"\cite{old}", encoding="utf-8")
        refs = project / "references"
        refs.mkdir()
        (refs / "refs.bib").write_text("@book{old,title={Work}}", encoding="utf-8")
        self.assertEqual(discover_projects(self.root), [project])

    def test_desktop_reports_no_detected_projects(self):
        from bib_gui_modern import ModernBibGUI

        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.processing = False
        gui.root = object()
        gui.dir_entry = type("Entry", (), {"get": lambda self: str(self.root)})()
        gui.dir_entry.root = self.root
        with patch("bib_gui_modern.messagebox.showinfo") as info, \
             patch.object(gui, "_start_batch") as start:
            gui._run_pipeline()
        start.assert_not_called()
        self.assertEqual(info.call_args.args[0], "No projects found")

    def test_single_pipeline_shows_empty_exception_and_saves_traceback(self):
        from bib_gui_modern import ModernBibGUI

        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.root = object()
        gui.step_cards = {}
        gui._key_review_approved = False
        gui._ui_call = lambda function, *args, **kwargs: function(*args, **kwargs)
        gui._apply_pipeline_snapshot = MagicMock()
        gui._log_message = MagicMock()
        gui._set_status = MagicMock()
        gui._flush_deferred_logs = MagicMock()
        gui.key_review_status_label = MagicMock()
        gui.run_btn = MagicMock()
        gui.cancel_btn = MagicMock()
        gui._status_text = MagicMock()
        settings = self.root / "settings.json"
        with patch("bib_gui_modern._settings_file_path", return_value=settings), \
             patch("bib_gui_modern.BibliographyManager", side_effect=RuntimeError()), \
             patch("bib_gui_modern.messagebox.showerror") as showerror:
            gui._pipeline_worker({
                "directory": str(self.root), "threshold": 85,
                "push_back": True, "generate_report": False,
            })
        self.assertIn("RuntimeError", showerror.call_args.args[1])
        self.assertIn("Traceback", (self.root / "app.log").read_text(encoding="utf-8"))
        self.assertIn("RuntimeError", (self.root / "app.log").read_text(encoding="utf-8"))

    def test_diagnostic_log_failure_is_reported(self):
        from bib_gui_modern import _save_diagnostic

        with patch("bib_gui_modern._settings_file_path", return_value=self.root / "settings.json"), \
             patch("bib_gui_modern._DiagnosticHandler", side_effect=PermissionError("denied")):
            self.assertIn("PermissionError: denied", _save_diagnostic("traceback"))

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
