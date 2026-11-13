"""Discover and process independent LaTeX projects."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Callable

from bib import BibliographyManager


def _ignored_directory(name: str) -> bool:
    return name in {".git", "__MACOSX", "processed"} or name.startswith(("backup_", "processed_"))


def discover_projects(parent: Path) -> list[Path]:
    parent = parent.resolve()
    if not parent.is_dir():
        raise ValueError(f"Not a project directory: {parent}")
    document_roots = set()
    bib_directories = set()

    def scan_error(error: OSError) -> None:
        raise error

    for directory, names, files in os.walk(parent, followlinks=False, onerror=scan_error):
        names[:] = sorted(name for name in names if not _ignored_directory(name) and not (Path(directory) / name).is_symlink())
        root = Path(directory)
        if any(name.lower().endswith(".bib") for name in files):
            bib_directories.add(root)
        for name in files:
            if not name.lower().endswith(".tex"):
                continue
            tex = root / name
            content = tex.read_text(encoding="utf-8")
            content = re.sub(r"(?m)(?<!\\)%.*$", "", content)
            if re.search(r"\\documentclass\b|\\begin\s*\{(?:thebibliography|filecontents\*?)\}", content):
                document_roots.add(root)

    candidates = set(document_roots)
    for directory in bib_directories:
        if not any(root == directory or root in directory.parents for root in document_roots):
            candidates.add(directory)
    return sorted(candidates, key=lambda path: str(path.relative_to(parent)).casefold())


def validate_project_roots(parent: Path, projects: list[Path]) -> list[Path]:
    parent = parent.resolve()
    roots = [project.resolve() for project in projects]
    if not roots:
        raise ValueError("Select at least one project.")
    if len(set(roots)) != len(roots):
        raise ValueError("The same project was selected more than once.")
    for root in roots:
        if not root.is_dir() or not (root == parent or parent in root.parents):
            raise ValueError(f"Project must be a folder inside {parent}: {root}")
        if any(_ignored_directory(part) for part in root.relative_to(parent).parts):
            raise ValueError(f"Generated and backup folders cannot be selected: {root}")
        for other in roots:
            if root != other and root in other.parents:
                raise ValueError(f"Project folders overlap: {root} and {other}. Remove one or choose different roots.")
    return roots


def process_projects(
    projects: list[Path],
    threshold: float,
    generate_report: bool,
    review: Callable[[Path, BibliographyManager], bool],
    cancelled: Callable[[], bool],
    log: Callable[[str], None],
) -> list[dict]:
    results = []
    for project in projects:
        if cancelled():
            results.append({"project": project, "status": "skipped", "detail": "Batch cancelled"})
            continue
        manager = BibliographyManager(str(project))
        manager.strict_source_errors = True
        manager.include_source_master = True
        output = None
        try:
            log(f"Analyzing project: {project}")
            manager.report_data["start_time"] = datetime.now()
            manager.report_data["push_back"] = True
            manager.report_data["generate_report"] = generate_report
            _, count = manager.crawl_and_collect()
            for warning in manager.report_data["parse_warnings"]:
                log(f"Warning ({project}): {warning}")
            if not count:
                results.append({"project": project, "status": "skipped", "detail": "No bibliography entries found"})
                continue
            if cancelled():
                results.append({"project": project, "status": "skipped", "detail": "Batch cancelled"})
                continue
            manager.find_duplicates(threshold=threshold)
            manager.remove_duplicates()
            manager.fix_citation_keys()
            if cancelled() or not review(project, manager):
                results.append({"project": project, "status": "skipped", "detail": "Review cancelled"})
                continue
            if cancelled():
                results.append({"project": project, "status": "skipped", "detail": "Batch cancelled"})
                continue
            output = manager.create_processed_copy()
            manager.report_data["end_time"] = datetime.now()
            if generate_report:
                manager.generate_html_report(str(output / "report.html"))
            results.append({"project": project, "status": "success", "detail": str(output), "output": output, "manager": manager})
            log(f"Completed {project}: {output}")
        except Exception as error:
            detail = f"{type(error).__name__}: {error}"
            if output is not None:
                detail += f" (processed copy exists at {output})"
            result = {"project": project, "status": "error", "detail": detail}
            if output is not None:
                result.update({"output": output, "manager": manager})
            results.append(result)
            log(f"Error ({project}): {detail}")
    return results
