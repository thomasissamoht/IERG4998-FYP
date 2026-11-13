import tempfile
import unittest
from pathlib import Path

from bib import BibliographyManager, _rewrite_bib_keys


class EmbeddedFileContentsTests(unittest.TestCase):
    def test_embedded_bib_is_processed_without_changing_original(self):
        source_text = (
            "\\begin{filecontents*}{references.bib}\n"
            "@article{oldKey,\n"
            "  author = {Smith, Jane},\n"
            "  title = {An Example},\n"
            "  year = {2020}\n"
            "}\n"
            "\\end{filecontents*}\n"
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\cite{oldKey}\n"
            "\\bibliography{references}\n"
            "\\end{document}\n"
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "paper.tex"
            source.write_text(source_text, encoding="utf-8")
            manager = BibliographyManager(str(root))
            self.assertEqual(manager.crawl_and_collect(), (1, 1))
            self.assertEqual(manager.all_entries[0]["ID"], "oldKey")
            manager.find_duplicates()
            manager.remove_duplicates()
            manager.fix_citation_keys()
            output = manager.create_processed_copy()
            self.assertEqual(source.read_text(encoding="utf-8"), source_text)
            processed = (output / "paper.tex").read_text(encoding="utf-8")
            self.assertIn("@article{S2020,", processed)
            self.assertIn("\\cite{S2020}", processed)
            self.assertIn("\\bibliography{references}", processed)
            self.assertIn("@article{S2020,", (output / "master.bib").read_text(encoding="utf-8"))

    def test_conflicting_external_file_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "references.bib").write_text("@book{external,title={External}}", encoding="utf-8")
            (root / "paper.tex").write_text(
                "\\begin{filecontents*}{references.bib}\n"
                "@book{embedded,title={Embedded}}\n"
                "\\end{filecontents*}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "references.bib"):
                BibliographyManager(str(root)).crawl_and_collect()

    def test_comment_and_non_bib_filecontents_are_not_collected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "paper.tex").write_text(
                "% \\begin{filecontents*}{ignored.bib}\n"
                "\\begin{filecontents*}{data.txt}\n"
                "@book{notbib,title={Not a bibliography}}\n"
                "\\end{filecontents*}\n",
                encoding="utf-8",
            )
            self.assertEqual(BibliographyManager(str(root)).crawl_and_collect(), (0, 0))

    def test_multiple_blocks_and_crossrefs_are_updated(self):
        source_text = (
            "\\begin{filecontents}[overwrite]{first.bib}\n"
            "@book{oldParent,\n"
            " author={Smith, Jane}, title={Parent}, year={2020}\n"
            "}\n"
            "@inbook{oldChild,\n"
            " author={Jones, Alex}, title={Child}, year={2021}, crossref={oldParent}\n"
            "}\n"
            "\\end{filecontents}\n"
            "\\begin{filecontents*}{second.bib}\n"
            "@book{oldOther,\n"
            " author={Doe, Jane}, title={Other}, year={2022}\n"
            "}\n"
            "\\end{filecontents*}\n"
            "\\cite{oldParent,oldChild,oldOther}\n"
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "paper.tex").write_text(source_text, encoding="utf-8")
            manager = BibliographyManager(str(root))
            self.assertEqual(manager.crawl_and_collect(), (1, 3))
            manager.fix_citation_keys()
            processed = manager.create_processed_copy()
            output = (processed / "paper.tex").read_text(encoding="utf-8")
            self.assertIn("crossref={S2020}", output)
            self.assertIn("\\cite{S2020,J2021,D2022}", output)
            self.assertIn("\\begin{filecontents}[overwrite]{first.bib}", output)
            self.assertIn("\\begin{filecontents*}{second.bib}", output)

    def test_reserved_master_filename_and_unclosed_block_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tex = root / "paper.tex"
            tex.write_text(
                "\\begin{filecontents*}{master.bib}\n"
                "@book{one,title={Example}}\n"
                "\\end{filecontents*}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "master.bib"):
                BibliographyManager(str(root)).crawl_and_collect()
            tex.write_text("\\begin{filecontents*}{references.bib}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unclosed"):
                BibliographyManager(str(root)).crawl_and_collect()

    def test_key_rewrite_does_not_change_fields_inside_text(self):
        source = (
            "@book(old,\n"
            " title = {Example, crossref={old}},\n"
            " crossref = {old}\n"
            ")\n"
        )
        updated = _rewrite_bib_keys(source, {"old": "new"})
        self.assertIn("@book(new,", updated)
        self.assertIn("title = {Example, crossref={old}}", updated)
        self.assertIn(" crossref = {new}", updated)


if __name__ == "__main__":
    unittest.main()
