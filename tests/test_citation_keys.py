import tempfile
import unittest
from pathlib import Path

from bib import BibliographyManager


class CitationKeyTests(unittest.TestCase):
    def setUp(self):
        self.manager = BibliographyManager()

    def test_keys_use_each_author_surname_initial(self):
        key = self.manager.generate_citation_key(
            {"author": "Smith, Jane and Doe, John", "year": "2024"},
            set(),
        )
        self.assertEqual(key, "SD2024")

    def test_duplicate_keys_use_alphabetical_suffixes(self):
        existing = set()
        generated = []
        for _ in range(4):
            key = self.manager.generate_citation_key(
                {"author": "Smith, Jane", "year": "2024"},
                existing,
            )
            generated.append(key)
            existing.add(key)
        self.assertEqual(generated, ["S2024", "S2024a", "S2024b", "S2024c"])

    def test_suffixes_continue_after_z(self):
        base_key = "S2024"
        existing = {base_key, *(f"{base_key}{chr(letter)}" for letter in range(ord("a"), ord("z") + 1))}
        key = self.manager.generate_citation_key(
            {"author": "Smith, Jane", "year": "2024"},
            existing,
        )
        self.assertEqual(key, "S2024aa")

    def test_different_years_do_not_need_suffixes(self):
        first = self.manager.generate_citation_key(
            {"author": "Smith, Jane", "year": "2023"},
            set(),
        )
        second = self.manager.generate_citation_key(
            {"author": "Smith, Jane", "year": "2024"},
            {first},
        )
        self.assertEqual((first, second), ("S2023", "S2024"))

    def test_missing_author_uses_reported_fallback(self):
        self.manager.all_entries = [{"ID": "no-author", "title": "Untitled", "year": "2024"}]
        self.manager.fix_citation_keys()
        self.assertEqual(self.manager.all_entries[0]["ID"], "X2024")
        self.assertEqual(
            self.manager.report_data["key_audit"][0]["Warning"],
            "No author surname; used X fallback",
        )

    def test_missing_year_uses_zero_year_and_reports_fallback(self):
        self.manager.all_entries = [{"ID": "no-year", "author": "Smith, Jane"}]
        self.manager.fix_citation_keys()
        self.assertEqual(self.manager.all_entries[0]["ID"], "S0000")
        self.assertIn("no four-digit year; used 0000", self.manager.report_data["key_audit"][0]["Warning"])

    def test_latex_accented_surname_uses_its_initial(self):
        key = self.manager.generate_citation_key(
            {"author": r'{\v{S}}imek, Jana', "year": "2024"},
            set(),
        )
        self.assertEqual(key, "S2024")

    def test_key_suffixes_follow_sorted_file_and_entry_order(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory)
            (source / "z.bib").write_text(
                "@article{z,\n author={Smith, Jane},\n title={Zebra Ecology},\n year={2022}\n}\n",
                encoding="utf-8",
            )
            (source / "a.bib").write_text(
                "@article{a1,\n author={Smith, Alex},\n title={Alpha Astronomy},\n year={2020}\n}\n"
                "@article{a2,\n author={Smith, Alex},\n title={Beta Botany},\n year={2021}\n}\n",
                encoding="utf-8",
            )
            manager = BibliographyManager(str(source))
            self.assertEqual(manager.crawl_and_collect(), (2, 3))
            manager.remove_duplicates()
            manager.fix_citation_keys()
            self.assertEqual(
                [entry["ID"] for entry in manager.all_entries],
                ["S2020", "S2021", "S2022"],
            )

    def test_duplicate_detection_runs_after_key_normalization_changes(self):
        self.manager.all_entries = [
            {
                "ID": "first",
                "ENTRYTYPE": "article",
                "author": "Smith, Jane",
                "title": "A Reliable Example of Duplicate Detection",
                "year": "2024",
            },
            {
                "ID": "second",
                "ENTRYTYPE": "article",
                "author": "Smith, Jane",
                "title": "A Reliable Example of Duplicate Detection",
                "year": "2024",
            },
        ]
        self.assertEqual(self.manager.find_duplicates(), 1)

    def test_processed_copy_updates_citations_without_changing_sources(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory)
            bib_text = (
                "@article{oldSmith,\n"
                "  author = {Smith, Jane},\n"
                "  title = {Unique Work on Graphs},\n"
                "  year = {2020}\n"
                "}\n"
                "@article{oldJones,\n"
                "  author = {Jones, Alex},\n"
                "  title = {Unique Work on Forests},\n"
                "  crossref = {oldSmith},\n"
                "  year = {2021}\n"
                "}\n"
            )
            tex_text = r"\cite{oldSmith,oldJones}" + "\n"
            bib_path = source / "references.bib"
            tex_path = source / "paper.tex"
            bib_path.write_text(bib_text, encoding="utf-8")
            tex_path.write_text(tex_text, encoding="utf-8")

            manager = BibliographyManager(str(source))
            self.assertEqual(manager.crawl_and_collect(), (1, 2))
            manager.remove_duplicates()
            manager.fix_citation_keys()
            processed = manager.create_processed_copy()

            self.assertEqual(bib_path.read_text(encoding="utf-8"), bib_text)
            self.assertEqual(tex_path.read_text(encoding="utf-8"), tex_text)
            self.assertIn("@article{S2020,", (processed / "references.bib").read_text(encoding="utf-8"))
            self.assertIn("@article{J2021,", (processed / "references.bib").read_text(encoding="utf-8"))
            self.assertIn("crossref = {S2020}", (processed / "references.bib").read_text(encoding="utf-8"))
            self.assertEqual(
                (processed / "paper.tex").read_text(encoding="utf-8"),
                r"\cite{S2020,J2021}" + "\n",
            )
            self.assertTrue((processed / "master.bib").is_file())

            rescanned = BibliographyManager(str(source))
            self.assertEqual(rescanned.crawl_and_collect(), (1, 2))


if __name__ == "__main__":
    unittest.main()
