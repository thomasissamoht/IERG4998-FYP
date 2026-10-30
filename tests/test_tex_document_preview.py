import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
