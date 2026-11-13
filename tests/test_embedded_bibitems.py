import tempfile
import unittest
from pathlib import Path

import bibtexparser

from bib import BibliographyManager


EXAMPLE = r"""\documentclass{article}
\begin{document}
Here is a citation \cite{einstein1905,knuth1984}.
\begin{thebibliography}{9}
\bibitem[Ein05]{einstein1905}
Albert Einstein,
\textit{Zur Elektrodynamik bewegter Körper},
Annalen der Physik, 1905.
\bibitem{knuth1984}
Donald E. Knuth,
\textit{The \TeX book},
Addison-Wesley, 1984.
\end{thebibliography}
\end{document}
"""


class EmbeddedBibitemTests(unittest.TestCase):
    def test_self_contained_document_preserves_text_and_exports_notes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paper = root / "paper.tex"
            paper.write_text(EXAMPLE, encoding="utf-8")
            manager = BibliographyManager(str(root))
            self.assertEqual(manager.crawl_and_collect(), (1, 2))
            self.assertEqual([entry["ID"] for entry in manager.all_entries],
                             ["einstein1905", "knuth1984"])
            manager.find_duplicates()
            manager.remove_duplicates()
            manager.fix_citation_keys()
            processed = manager.create_processed_copy()
            self.assertEqual(paper.read_text(encoding="utf-8"), EXAMPLE)
            self.assertEqual((processed / "paper.tex").read_text(encoding="utf-8"), EXAMPLE)
            data = bibtexparser.loads((processed / "master.bib").read_text(encoding="utf-8"))
            self.assertEqual({entry["ID"] for entry in data.entries}, {"einstein1905", "knuth1984"})
            self.assertTrue(all(entry["ENTRYTYPE"] == "misc" and entry["note"] for entry in data.entries))

    def test_conflicting_manual_and_bibtex_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "paper.tex").write_text(EXAMPLE, encoding="utf-8")
            (root / "refs.bib").write_text("@book{knuth1984,title={Another}}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "knuth1984"):
                BibliographyManager(str(root)).crawl_and_collect()

    def test_bibtex_keys_do_not_collide_with_preserved_manual_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "paper.tex").write_text(
                r"\begin{thebibliography}{9}" "\n" r"\bibitem{S2020}Manual" "\n"
                r"\end{thebibliography}", encoding="utf-8")
            (root / "refs.bib").write_text(
                "@book{old,author={Smith, Jane},year={2020},title={Work}}", encoding="utf-8")
            manager = BibliographyManager(str(root))
            manager.crawl_and_collect()
            manager.fix_citation_keys()
            self.assertEqual([entry["ID"] for entry in manager.all_entries], ["S2020a", "S2020"])
            processed = manager.create_processed_copy()
            self.assertEqual((processed / "paper.tex").read_text(encoding="utf-8"),
                             (root / "paper.tex").read_text(encoding="utf-8"))

    def test_external_keys_change_but_manual_label_and_text_remain_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paper = root / "paper.tex"
            original = (
                r"\cite{old,manual}" "\n"
                r"\begin{thebibliography}{9}" "\n"
                r"\bibitem[Label]{manual}Text with \textit{nested text}." "\n"
                r"\end{thebibliography}" "\n"
            )
            paper.write_text(original, encoding="utf-8")
            (root / "refs.bib").write_text(
                "@book{old,author={Smith, Jane},year={2020},title={Work}}", encoding="utf-8")
            manager = BibliographyManager(str(root))
            manager.crawl_and_collect()
            manager.find_duplicates()
            manager.remove_duplicates()
            manager.fix_citation_keys()
            output = manager.create_processed_copy()
            self.assertEqual(paper.read_text(encoding="utf-8"), original)
            self.assertEqual((output / "paper.tex").read_text(encoding="utf-8"),
                             original.replace(r"\cite{old,manual}", r"\cite{S2020,manual}"))

    def test_ignores_comments_and_verbatim_and_reports_unclosed_blocks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tex = root / "paper.tex"
            tex.write_text(
                "% \\begin{thebibliography}{9}\n"
                "\\begin{verbatim}\n\\begin{thebibliography}{9}\n"
                "\\bibitem{fake}Not real\n\\end{thebibliography}\n\\end{verbatim}\n"
                "\\begin{thebibliography}{9}\n% \\bibitem{fake}Comment\n"
                "\\bibitem[{A {nested} label}]{real} Real reference.\n"
                "\\end{thebibliography}\n", encoding="utf-8")
            manager = BibliographyManager(str(root))
            self.assertEqual(manager.crawl_and_collect(), (1, 1))
            self.assertEqual(manager.all_entries[0]["ID"], "real")
            tex.write_text("\\begin{thebibliography}{9}\n\\bibitem{a}Text\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unclosed"):
                BibliographyManager(str(root)).crawl_and_collect()

    def test_comments_escaping_and_verbatim_text_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "paper.tex").write_text(
                "% \\begin{verbatim}\n"
                "\\begin{thebibliography}{9}\n"
                "\\bibitem{real}Text \\% value and \\verb|literal| % comment\n"
                "continued.\n\\end{thebibliography}\n",
                encoding="utf-8")
            manager = BibliographyManager(str(root))
            self.assertEqual(manager.crawl_and_collect(), (1, 1))
            note = manager.all_entries[0]["note"]
            self.assertIn(r"\% value and \verb|literal|", note)
            self.assertNotIn("% comment", note)
            self.assertIn("continued.", note)

    def test_macro_only_bibliography_and_duplicate_manual_key_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tex = root / "paper.tex"
            tex.write_text(
                "\\begin{thebibliography}{9}\n\\myreferences\n\\end{thebibliography}",
                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "macro-generated"):
                BibliographyManager(str(root)).crawl_and_collect()
            tex.write_text(
                "\\begin{thebibliography}{9}\n\\bibitem{x}First\n"
                "\\bibitem{x}Second\n\\end{thebibliography}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "key 'x'"):
                BibliographyManager(str(root)).crawl_and_collect()


if __name__ == "__main__":
    unittest.main()
