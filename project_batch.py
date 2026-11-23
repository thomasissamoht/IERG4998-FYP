"""Discover and process independent LaTeX projects."""

import os
import traceback
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Callable

from bib import BibliographyManager


def _ignored_directory(name: str) -> bool:
    return name in {".git", "__MACOSX", "processed"} or name.startswith(("backup_", "processed_"))


def discover_projects(parent: Path) -> list[Path]:
    parent = parent.resolve()
    if not parent.is_dir():
        raise ValueError(f"Not a project directory: {parent}")
    projects = []

    def scan_error(error: OSError) -> None:
        raise error

    for directory, names, files in os.walk(parent, followlinks=False, onerror=scan_error):
        names[:] = sorted(name for name in names if not _ignored_directory(name) and not (Path(directory) / name).is_symlink())
        root = Path(directory)
        if any(name.lower().endswith((".bib", ".tex")) for name in files):
            projects.append(root)
            names.clear()
    return sorted(projects, key=lambda path: str(path.relative_to(parent)).casefold())


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


def _snapshot_sources(project: Path) -> dict[str, bytes]:
    root = project.resolve()
    paths = sorted(
        path for pattern in ("*.bib", "*.tex") for path in root.rglob(pattern)
        if path.is_file() and not BibliographyManager._is_generated_workspace_path(path, root)
    )
    snapshots = {}
    for path in paths:
        digest = sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        snapshots[str(path.relative_to(root))] = digest.digest()
    return snapshots


def process_projects(
    projects: list[Path],
    threshold: float,
    generate_report: bool,
    review: Callable[[list[dict]], bool],
    cancelled: Callable[[], bool],
    log: Callable[[str], None],
) -> list[dict]:
    results = []
    for project in projects:
        if cancelled():
            results.append({"project": project, "status": "skipped", "detail": "Batch cancelled"})
            continue
        try:
            manager = BibliographyManager(str(project))
            manager.strict_source_errors = True
            manager.include_source_master = True
            snapshot = _snapshot_sources(project)
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
            if _snapshot_sources(project) != snapshot:
                raise ValueError("Project sources changed during analysis. Analyze the project again.")
            if cancelled():
                results.append({"project": project, "status": "skipped", "detail": "Batch cancelled"})
                continue
            results.append({
                "project": project, "status": "ready", "detail": "Ready for review",
                "manager": manager, "snapshot": snapshot,
            })
        except Exception as error:
            detail = f"{type(error).__name__}: {error}"
            results.append({"project": project, "status": "error", "detail": detail, "traceback": traceback.format_exc()})
            log(f"Error ({project}): {detail}")

    ready = [result for result in results if result["status"] == "ready"]
    approved = bool(ready) and not cancelled() and review(results)
    for result in ready:
        project = result["project"]
        manager = result["manager"]
        snapshot = result.pop("snapshot")
        if not approved or cancelled():
            result.update(status="skipped", detail="Batch cancelled" if cancelled() else "Review cancelled")
            continue
        output = None
        try:
            if _snapshot_sources(project) != snapshot:
                raise ValueError("Project sources changed after review. Analyze the project again.")
            output = manager.create_processed_copy()
            manager.report_data["end_time"] = datetime.now()
            if generate_report:
                manager.generate_html_report(str(output / "report.html"))
            result.update(status="success", detail=str(output), output=output)
            log(f"Completed {project}: {output}")
        except Exception as error:
            detail = f"{type(error).__name__}: {error}"
            if output is not None:
                detail += f" (processed copy exists at {output})"
            result.update(status="error", detail=detail, traceback=traceback.format_exc())
            if output is not None:
                result["output"] = output
            log(f"Error ({project}): {detail}")
    return results
