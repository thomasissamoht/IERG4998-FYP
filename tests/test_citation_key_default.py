import unittest

from bib import BibliographyManager


class DefaultCitationKeyPolicyTests(unittest.TestCase):
    def setUp(self):
        self.manager = BibliographyManager()

    def test_default_key_uses_every_author_surname_initial_and_year(self):
        key = self.manager.generate_citation_key(
            {"author": "Smith, Jane and Doe, John and Brown, Alex and Jones, Lee", "year": "2024"},
            set(),
        )
        self.assertEqual(key, "SDBJ2024")

    def test_default_duplicate_keys_use_letter_suffix_without_separator(self):
        self.manager.all_entries = [
            {"ID": "first", "author": "Smith, Jane", "year": "2024"},
            {"ID": "second", "author": "Smith, Jane", "year": "2024"},
            {"ID": "third", "author": "Smith, Jane", "year": "2024"},
            {"ID": "fourth", "author": "Smith, Jane", "year": "2024"},
        ]

        self.manager.fix_citation_keys()

        self.assertEqual(
            [entry["ID"] for entry in self.manager.all_entries],
            ["S2024", "S2024a", "S2024b", "S2024c"],
        )


if __name__ == "__main__":
    unittest.main()
