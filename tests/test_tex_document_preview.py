import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bib import BibliographyManager
from bib_gui_modern import (
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
            self.assertEqual(set(gui.document_file_menu.options["values"]), {"main.tex", "appendix.tex"})
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
            self.assertEqual(gui.document_file_menu.value, "No .tex files found")
            self.assertIn("No LaTeX", gui.document_info.options["text"])
            gui._select_batch_document_project(str(root / "two"))
            self.assertEqual(gui.document_file_menu.value, "Preview unavailable")
            self.assertIn("not found", gui.document_info.options["text"])
            gui._load_batch_documents([])
            self.assertFalse(gui.document_project_frame.visible)
            self.assertIn("No processed project copies", gui.document_info.options["text"])

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
