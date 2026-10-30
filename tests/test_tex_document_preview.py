import tempfile
import unittest
from pathlib import Path

from bib import BibliographyManager
from bib_gui_modern import _collect_tex_documents


class TexDocumentPreviewTests(unittest.TestCase):
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
