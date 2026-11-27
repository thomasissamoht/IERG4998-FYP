import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bib import BibliographyManager
from bib_gui_modern import (
    _collect_project_documents,
    _collect_tex_documents,
    _find_tex_citation_spans,
    _next_tex_citation_index,
    ModernBibGUI,
)
from project_batch import process_projects


class FakeWidget:
    def __init__(self):
        self.options = {}
        self.value = ""
        self.visible = False

    def configure(self, **kwargs):
        self.options.update(kwargs)

    def set(self, value):
        self.value = value

    def grid(self):
        self.visible = True

    def grid_remove(self):
        self.visible = False

    def delete(self, *_args):
        self.value = ""

    def insert(self, _index, value):
        self.value = value


class TexDocumentPreviewTests(unittest.TestCase):
    def test_selected_report_opens_as_file_uri_and_reports_browser_failure(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            report = Path(temporary_directory) / "report with spaces.html"
            report.write_text("<html></html>", encoding="utf-8")
            gui = ModernBibGUI.__new__(ModernBibGUI)
            gui.report_path = str(report)
            gui.root = MagicMock()
            gui._log_message = MagicMock()
            with patch("bib_gui_modern.webbrowser.open", return_value=True) as open_browser:
                gui._view_report()
                open_browser.assert_called_once_with(report.resolve().as_uri())
            with patch("bib_gui_modern.webbrowser.open", return_value=False), \
                 patch("bib_gui_modern.messagebox.showerror") as show_error:
                gui._view_report()
                show_error.assert_called_once()

    def make_viewer(self):
        gui = ModernBibGUI.__new__(ModernBibGUI)
        gui.manager = None
        gui._tex_documents = {}
        gui._document_report_data = {}
        gui._batch_document_projects = {}
        for name in (
            "document_project_frame", "document_project_menu", "document_file_menu", "document_text", "document_info",
            "document_previous_button", "document_next_button", "document_citation_count",
        ):
            setattr(gui, name, FakeWidget())
        gui._highlight_tex_citations = lambda content: None
        gui._log_message = lambda message: None
        return gui

    def test_batch_previews_switch_projects_and_files_without_using_last_manager(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            projects = []
            for name, author in [("First", "Smith"), ("Second", "Jones")]:
                project = root / name
                project.mkdir()
                (project / "references.bib").write_text(
                    f"@article{{old,author={{{author}}},title={{A Test}},year={{2024}}}}\n",
                    encoding="utf-8",
                )
                (project / "main.tex").write_text(r"\cite{old}", encoding="utf-8")
                (project / "appendix.tex").write_text("Appendix", encoding="utf-8")
                projects.append(project)
            results = process_projects(projects, 85, False, lambda *_: True, lambda: False, lambda _: None)
            gui = self.make_viewer()
            gui._load_batch_documents(results)
            self.assertTrue(gui.document_project_frame.visible)
            self.assertEqual(gui.document_project_menu.options["values"], [str(path) for path in projects])
            self.assertEqual(set(gui.document_file_menu.options["values"]),
                             {"main.tex", "appendix.tex", "references.bib", "master.bib"})
            gui._show_tex_document("main.tex")
            self.assertEqual(gui.document_text.value, r"\cite{S2024}")
            gui._select_batch_document_project(str(projects[1]))
            gui._show_tex_document("main.tex")
            self.assertEqual(gui.document_text.value, r"\cite{J2024}")
            self.assertIn("processed copy", gui.document_info.options["text"])
            self.assertEqual((projects[1] / "main.tex").read_text(encoding="utf-8"), r"\cite{old}")

    def test_batch_preview_reports_empty_and_unavailable_projects(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            empty = root / "empty"
            empty.mkdir()
            missing = root / "missing"
            report = {"processed_copy_path": str(empty)}
            results = [
                {"project": root / "one", "output": empty, "manager": SimpleNamespace(report_data=report)},
                {"project": root / "two", "output": missing, "manager": SimpleNamespace(report_data=report)},
                {"project": root / "skipped", "status": "skipped"},
            ]
            gui = self.make_viewer()
            gui._load_batch_documents(results)
            self.assertEqual(gui.document_file_menu.value, "No supported text files found")
            self.assertIn("No supported", gui.document_info.options["text"])
            gui._select_batch_document_project(str(root / "two"))
            self.assertEqual(gui.document_file_menu.value, "Preview unavailable")
            self.assertIn("not found", gui.document_info.options["text"])
            gui._load_batch_documents([])
            self.assertFalse(gui.document_project_frame.visible)
            self.assertIn("No processed project copies", gui.document_info.options["text"])

    def test_completed_project_is_added_without_interrupting_current_preview(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            gui = self.make_viewer()
            results = []
            for name in ("first", "second"):
                output = root / name
                output.mkdir()
                (output / "main.tex").write_text(name, encoding="utf-8")
                results.append({"project": root / (name + "-source"), "output": output,
                                "manager": SimpleNamespace(report_data={"processed_copy_path": str(output)})})
            gui._add_batch_document(results[0])
            self.assertEqual(gui.document_text.value, "first")
            gui._add_batch_document(results[1])
            self.assertEqual(gui.document_text.value, "first")
            self.assertEqual(len(gui.document_project_menu.options["values"]), 2)
            gui._select_batch_document_project(str(results[1]["project"]))
            self.assertEqual(gui.document_text.value, "second")

    def test_finds_common_citation_commands_for_document_navigation(self):
        content = (
            r"Intro \cite{key1} and \citep[see][p. 2]{key2}."
            "\n"
            r"\textcite*{key3}; \nocite{key4}."
        )

        citations = [
            content[start:end]
            for start, end in _find_tex_citation_spans(content)
        ]

        self.assertEqual(
            citations,
            [
                r"\cite{key1}",
                r"\citep[see][p. 2]{key2}",
                r"\textcite*{key3}",
            ],
        )

    def test_citation_navigation_wraps_in_both_directions(self):
        self.assertEqual(_next_tex_citation_index(2, 1, 3), 0)
        self.assertEqual(_next_tex_citation_index(0, -1, 3), 2)
        self.assertEqual(_next_tex_citation_index(-1, 1, 0), -1)

    def test_collects_nested_tex_files_by_relative_path(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "paper.tex").write_text(r"\cite{SD2024}" + "\n", encoding="utf-8")
            nested = root / "chapters"
            nested.mkdir()
            (nested / "methods.tex").write_text(r"\cite{AB2023a}" + "\n", encoding="utf-8")
            (root / "references.bib").write_text("@article{SD2024}\n", encoding="utf-8")

            self.assertEqual(
                _collect_tex_documents(root),
                {
                    str(Path("chapters") / "methods.tex"): r"\cite{AB2023a}" + "\n",
                    "paper.tex": r"\cite{SD2024}" + "\n",
                },
            )

    def test_project_text_files_are_selected_lazily_and_binary_files_excluded(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "paper.tex").write_text(r"\cite{key}", encoding="utf-8")
            (root / "notes.md").write_text("Notes", encoding="utf-8")
            (root / "bad.txt").write_bytes(b"\xff")
            (root / "figure.png").write_bytes(b"\x89PNG")
            (root / "processed").mkdir()
            (root / "processed" / "old.tex").write_text("Old", encoding="utf-8")
            (root / "nested").mkdir()
            documents = _collect_project_documents(root / "nested" / "..")
            self.assertEqual(set(documents), {"paper.tex", "notes.md", "bad.txt"})
            gui = self.make_viewer()
            gui._load_tex_documents({"project_documents": documents, "processed_copy_path": str(root)})
            self.assertEqual(gui.document_file_menu.value, "paper.tex")
            gui._show_tex_document("notes.md")
            self.assertEqual(gui.document_text.value, "Notes")
            self.assertIn("citation navigation is available for .tex", gui.document_info.options["text"])
            gui._show_tex_document("bad.txt")
            self.assertEqual(gui.document_text.value, "")
            self.assertIn("Could not read bad.txt", gui.document_info.options["text"])
            gui._show_tex_document("paper.tex")
            self.assertEqual(gui.document_text.value, r"\cite{key}")

    def test_archive_document_snapshots_survive_source_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            file = root / "notes.txt"
            file.write_text("Archive notes", encoding="utf-8")
            documents = _collect_project_documents(root, snapshot=True)
            file.unlink()
            gui = self.make_viewer()
            gui._load_tex_documents({"project_documents": documents})
            self.assertEqual(gui.document_text.value, "Archive notes")

    def test_dashboard_explains_preserved_manual_keys_when_no_files_change(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "paper.tex").write_text(
                "\\begin{thebibliography}{9}\n\\bibitem{manual}Reference.\n\\end{thebibliography}\n",
                encoding="utf-8",
            )
            result = process_projects([root], 85, False, lambda *_: True, lambda: False, lambda _: None)[0]
            gui = ModernBibGUI.__new__(ModernBibGUI)
            gui.manager = result["manager"]
            gui.stat_labels = {name: MagicMock() for name in
                               ("files", "folders", "initial", "groups", "removed", "final", "keys", "time")}
            for name in ("reduction_bar", "reduction_text", "keys_bar", "keys_text", "results_text",
                         "results_files_box", "results_folders_box"):
                setattr(gui, name, MagicMock())
            gui._update_results()
            summary = gui.results_text.insert.call_args.args[1]
            self.assertIn("Preserved 1 manual \\bibitem key(s)", summary)
            self.assertIn("No changes were recorded", summary)

    def test_pipeline_surfaces_tex_read_errors(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "references.bib").write_text(
                "@article{oldKey,\n"
                "  author = {Smith, Jane},\n"
                "  title = {A Test Article},\n"
                "  year = {2024}\n"
                "}\n",
                encoding="utf-8",
            )
            (root / "paper.tex").write_bytes(b"\\cite{oldKey}\n\xff")

            manager = BibliographyManager(str(root))
            self.assertEqual(manager.crawl_and_collect(), (1, 1))
            manager.remove_duplicates()
            manager.fix_citation_keys()
            master_path = manager.create_master_bibliography()

            with self.assertRaises(UnicodeDecodeError):
                manager.push_to_folders(master_path)

    def test_preview_reads_normalized_citations_after_project_update(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "references.bib").write_text(
                "@article{oldKey,\n"
                "  author = {Smith, Jane},\n"
                "  title = {A Test Article},\n"
                "  year = {2024}\n"
                "}\n",
                encoding="utf-8",
            )
            (root / "paper.tex").write_text(r"\cite{oldKey}" + "\n", encoding="utf-8")

            manager = BibliographyManager(str(root))
            self.assertEqual(manager.crawl_and_collect(), (1, 1))
            manager.remove_duplicates()
            manager.fix_citation_keys()
            master_path = manager.create_master_bibliography()
            updated_root = manager.push_to_folders(master_path) or root

            documents = _collect_tex_documents(updated_root)
            self.assertEqual(documents["paper.tex"], r"\cite{S2024}" + "\n")
            self.assertEqual(manager.report_data["tex_citation_updates"], 1)
            self.assertEqual(manager.report_data["tex_files_updated"], 1)

    def test_only_actually_rewritten_citations_are_recorded(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "references.bib").write_text(
                "@article{old,author={Smith},year={2024},title={Test}}", encoding="utf-8"
            )
            (root / "paper.tex").write_text(
                "\\cite{old} \\cite{S2024}\n% \\cite{old}\n\\citep[see]{old,other}\n",
                encoding="utf-8",
            )
            manager = BibliographyManager(str(root))
            manager.crawl_and_collect()
            manager.remove_duplicates()
            manager.fix_citation_keys()
            output = manager.create_processed_copy()
            text = (output / "paper.tex").read_text(encoding="utf-8")
            spans = manager.report_data["tex_citation_spans"]["paper.tex"]
            self.assertEqual([text[start:end] for start, end in spans],
                             [r"\cite{S2024}", r"\citep[see]{S2024,other}"])
            self.assertIn("% \\cite{old}", text)
            self.assertEqual(manager.report_data["tex_citation_updates"], 2)
            gui = self.make_viewer()
            gui._highlight_tex_citations = ModernBibGUI._highlight_tex_citations.__get__(gui)
            widget = MagicMock()
            gui._get_text_widget = lambda _: widget
            gui._document_report_data = manager.report_data
            gui._tex_documents = {"paper.tex": text}
            gui._show_tex_document("paper.tex")
            self.assertEqual(gui._tex_citation_spans, spans)
            self.assertEqual(gui._current_tex_citation_idx, 0)
            widget.see.assert_called_once()
            gui._tex_documents["paper.tex"] = text + "edited"
            gui._show_tex_document("paper.tex")
            self.assertEqual(gui._tex_citation_spans, [])
            self.assertIn("changed after processing", gui.document_info.options["text"])

    def test_fix_view_reads_changed_files_and_rejects_stale_sources(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "refs.bib"
            source.write_text("@book{old,author={Smith},year={2024},title={Work}}", encoding="utf-8")
            manager = BibliographyManager(str(root))
            manager.crawl_and_collect()
            manager.remove_duplicates()
            manager.fix_citation_keys()
            manager.create_processed_copy()
            gui = ModernBibGUI.__new__(ModernBibGUI)
            gui.manager = manager
            gui.fix_file_menu = MagicMock()
            gui.fixes_diff_text = MagicMock()
            gui.changed_info = MagicMock()
            gui.prev_change_btn = MagicMock()
            gui.next_change_btn = MagicMock()
            gui._show_unchanged_var = FakeWidget()
            gui._show_unchanged_var.get = lambda: True
            gui._diff_context_lines = 2
            gui._get_text_widget = lambda _: None
            gui._scroll_to_changed_line = MagicMock()
            gui._log_message = MagicMock()
            gui._show_file_fix("refs.bib")
            diff = gui.fixes_diff_text.insert.call_args.args[1]
            self.assertIn("@book{old", diff)
            self.assertIn("@book{S2024", diff)
            source.write_text("changed by user", encoding="utf-8")
            gui._show_file_fix("refs.bib")
            self.assertIn("Source changed after processing", gui.fixes_diff_text.insert.call_args.args[1])

    def test_existing_processed_subfolders_do_not_hide_source_key_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "references.bib").write_text(
                "@article{oldKey,\n"
                "  author = {Smith, Jane},\n"
                "  title = {A Test Article},\n"
                "  year = {2024}\n"
                "}\n",
                encoding="utf-8",
            )
            (root / "paper.tex").write_text(r"\cite{oldKey}" + "\n", encoding="utf-8")

            old_processed = root / "processed"
            old_processed.mkdir()
            (old_processed / "references.bib").write_text(
                "@article{S2024,\n"
                "  author = {Smith, Jane},\n"
                "  title = {A Test Article},\n"
                "  year = {2024}\n"
                "}\n",
                encoding="utf-8",
            )
            (old_processed / "paper.tex").write_text(r"\cite{S2024}" + "\n", encoding="utf-8")

            manager = BibliographyManager(str(root))
            self.assertEqual(manager.crawl_and_collect(), (1, 1))
            manager.remove_duplicates()
            manager.fix_citation_keys()
            master_path = manager.create_master_bibliography()
            processed = manager.push_to_folders(master_path)
            result_root = processed or root

            self.assertEqual(
                _collect_tex_documents(result_root)["paper.tex"],
                r"\cite{S2024}" + "\n",
            )
            self.assertEqual(manager.report_data["tex_citation_updates"], 1)
            self.assertEqual(manager.report_data["tex_files_updated"], 1)


if __name__ == "__main__":
    unittest.main()
