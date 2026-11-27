"""Discover and process independent LaTeX projects."""

import os
import re
import traceback
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Callable

from bib import (
    BibliographyManager, LARGE_BIB_PARSE_THRESHOLD, _embedded_bib_blocks,
    _manual_bibliography_entries, _parse_large_bibtex, _parse_standard_bibtex,
)


@dataclass(frozen=True)
class RootFileProject:
    root: Path
    files: tuple[Path, ...]
    discovery_snapshot: tuple[tuple[str, bytes], ...]

    @property
    def name(self) -> str:
        return ", ".join(repr(path.name) for path in self.files)

    def __str__(self) -> str:
        return f"{self.root} [{self.name}]"


Project = Path | RootFileProject


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


def _latex_code(text: str) -> str:
    """Mask comments and verbatim text while retaining ordinary LaTeX commands."""
    masked = list(text)
    position = 0
    while position < len(text):
        end = position
        if text[position] == "%":
            end = text.find("\n", position)
            end = len(text) if end < 0 else end
        elif text[position] == "\\":
            begin = re.match(r"\\begin\{(verbatim\*?|lstlisting|minted|filecontents\*?)\}", text[position:])
            if begin:
                marker = r"\end{" + begin.group(1) + "}"
                end = text.find(marker, position + begin.end())
                if end < 0:
                    raise ValueError(f"Unclosed {begin.group(1)} environment")
                end += len(marker)
            else:
                verb = re.match(r"\\verb\*?([^A-Za-z\s])", text[position:])
                if verb:
                    end = text.find(verb.group(1), position + verb.end())
                    if end < 0 or "\n" in text[position:end]:
                        raise ValueError("Unclosed verb command")
                    end += 1
                else:
                    position += 2
                    continue
        if end > position:
            for index in range(position, end):
                if text[index] not in "\r\n":
                    masked[index] = " "
            position = end
        else:
            position += 1
    return "".join(masked)


def _root_file_projects(parent: Path) -> list[RootFileProject]:
    snapshot = _snapshot_sources(parent, root_files_only=True)
    files = sorted((parent / name for name in snapshot), key=lambda path: path.name.casefold())
    if len(files) == 1:
        return [RootFileProject(parent, (files[0],), tuple(sorted(snapshot.items())))]
    parents = list(range(len(files)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def join(first: int, second: int) -> None:
        parents[find(second)] = find(first)

    bib_keys: dict[str, list[int]] = {}
    tex_citations: dict[int, set[str]] = {}
    file_indexes = {path: index for index, path in enumerate(files)}
    for index, path in enumerate(files):
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".bib":
            locations = BibliographyManager(str(parent))._extract_entry_locations(text)
            if path.stat().st_size >= LARGE_BIB_PARSE_THRESHOLD:
                entries, warnings = _parse_large_bibtex(text)
                if warnings:
                    raise ValueError(f"Could not reliably discover keys in {path}: {warnings[0]}")
            else:
                entries = _parse_standard_bibtex(text, locations)
            for entry in entries:
                bib_keys.setdefault(str(entry.get("ID", "")).strip(), []).append(index)
            continue

        code = _latex_code(text)
        tex_citations[index] = {
            key.strip()
            for match in re.finditer(r"(?<!\\)\\[A-Za-z]*cite[A-Za-z]*\*?(?:\s*\[[^\]]*\])*\s*\{([^{}]*)\}", code, re.IGNORECASE)
            for key in match.group(1).split(",")
            if key.strip() and key.strip() != "*"
        }
        for key, *_ in _manual_bibliography_entries(text):
            bib_keys.setdefault(key, []).append(index)
        for _, start, end in _embedded_bib_blocks(text):
            block = text[start:end]
            locations = BibliographyManager(str(parent))._extract_entry_locations(block)
            for entry in _parse_standard_bibtex(block, locations):
                bib_keys.setdefault(str(entry.get("ID", "")).strip(), []).append(index)
        for match in re.finditer(r"(?<!\\)\\(input|include|bibliography|addbibresource)\*?(?:\s*\[[^\]]*\])*\s*\{([^{}]+)\}", code):
            command = match.group(1)
            for name in match.group(2).split(","):
                name = name.strip()
                target = (parent / name).resolve()
                if not target.suffix:
                    target = target.with_suffix(".bib" if command in {"bibliography", "addbibresource"} else ".tex")
                if target in file_indexes:
                    join(index, file_indexes[target])
    for index, keys in tex_citations.items():
        for key in keys:
            for owner in bib_keys.get(key, []):
                join(index, owner)
    if _snapshot_sources(parent, root_files_only=True) != snapshot:
        raise ValueError("Root-level sources changed during project discovery. Try again.")
    groups: dict[int, list[Path]] = {}
    for index, path in enumerate(files):
        groups.setdefault(find(index), []).append(path)
    frozen_snapshot = tuple(sorted(snapshot.items()))
    return [RootFileProject(parent, tuple(group), frozen_snapshot) for group in groups.values()]


def discover_batch_projects(parent: Path) -> list[Project]:
    parent = parent.resolve()
    projects = discover_projects(parent)
    if projects != [parent]:
        return [project for project in projects]
    children = []
    for path in sorted(parent.iterdir(), key=lambda item: item.name.casefold()):
        if path.is_dir() and not path.is_symlink() and not _ignored_directory(path.name):
            children.extend(discover_projects(path))
    root_projects = _root_file_projects(parent)
    if children or len(root_projects) > 1:
        return [*root_projects, *children]
    return [project for project in projects]


def validate_project_roots(
    parent: Path, projects: list[Project], *, allow_parent_with_children: bool = False
) -> list[Project]:
    parent = parent.resolve()
    roots = [project.root.resolve() if isinstance(project, RootFileProject) else project.resolve() for project in projects]
    if not roots:
        raise ValueError("Select at least one project.")
    if len(set(projects)) != len(projects):
        raise ValueError("The same project was selected more than once.")
    root_files: set[Path] = set()
    for project, root in zip(projects, roots):
        if isinstance(project, RootFileProject):
            if (root != parent or not project.files
                    or any(path.parent != parent or path.suffix.lower() not in {".tex", ".bib"}
                           or not path.is_file() for path in project.files)):
                raise ValueError(f"Invalid root-level project: {project}")
            if root_files.intersection(project.files):
                raise ValueError("Root-level project files overlap.")
            root_files.update(project.files)
        elif root == parent and any(isinstance(item, RootFileProject) for item in projects):
            raise ValueError("A whole-folder project cannot overlap root-level file groups.")
        if not root.is_dir() or not (root == parent or parent in root.parents):
            raise ValueError(f"Project must be a folder inside {parent}: {root}")
        if any(_ignored_directory(part) for part in root.relative_to(parent).parts):
            raise ValueError(f"Generated and backup folders cannot be selected: {root}")
        for other in roots:
            if root != other and root in other.parents and not (allow_parent_with_children and root == parent):
                raise ValueError(f"Project folders overlap: {root} and {other}. Remove one or choose different roots.")
    return [project if isinstance(project, RootFileProject) else root for project, root in zip(projects, roots)]


def _snapshot_sources(project: Path, root_files_only: bool = False) -> dict[str, bytes]:
    root = project.resolve()
    paths = sorted(
        path for pattern in ("*.bib", "*.tex")
        for path in (root.glob(pattern) if root_files_only else root.rglob(pattern))
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
    projects: list[Project],
    threshold: float,
    generate_report: bool,
    review: Callable[[list[dict]], bool],
    cancelled: Callable[[], bool],
    log: Callable[[str], None],
    progress: Callable[[str, int, int, Project, dict | None], None] | None = None,
) -> list[dict]:
    results = []
    total = len(projects)

    def notify(stage: str, index: int, project: Project, result: dict | None = None) -> None:
        if progress is not None:
            progress(stage, index, total, project, result.copy() if result is not None else None)

    for index, project in enumerate(projects, 1):
        if cancelled():
            results.append({"project": project, "status": "skipped", "detail": "Batch cancelled"})
            continue
        try:
            notify("Reading sources", index, project)
            root = project.root if isinstance(project, RootFileProject) else project
            manager = BibliographyManager(str(root))
            manager.strict_source_errors = True
            manager.include_source_master = True
            manager.root_files_only = isinstance(project, RootFileProject) or any(
                isinstance(other, Path) and root in other.parents for other in projects
            )
            if isinstance(project, RootFileProject):
                manager.selected_root_files = {path.name for path in project.files}
                safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", project.files[0].stem).strip("_") or "root"
                manager.output_name = f"processed_{safe_name}"
            snapshot = _snapshot_sources(root, manager.root_files_only)
            if isinstance(project, RootFileProject) and snapshot != dict(project.discovery_snapshot):
                raise ValueError("Root-level sources changed after discovery. Discover the projects again.")
            log(f"Analyzing project: {project}")
            manager.report_data["start_time"] = datetime.now()
            manager.report_data["push_back"] = True
            manager.report_data["generate_report"] = generate_report
            _, count = manager.crawl_and_collect()
            for warning in manager.report_data["parse_warnings"]:
                log(f"Warning ({project}): {warning}")
            if not count:
                results.append({"project": project, "status": "skipped", "detail": "No bibliography entries found"})
                notify("Analysis skipped", index, project)
                continue
            if cancelled():
                results.append({"project": project, "status": "skipped", "detail": "Batch cancelled"})
                continue
            notify("Finding duplicates", index, project)
            manager.find_duplicates(threshold=threshold)
            notify("Removing duplicates", index, project)
            manager.remove_duplicates()
            notify("Normalizing citation keys", index, project)
            manager.fix_citation_keys()
            if _snapshot_sources(root, manager.root_files_only) != snapshot:
                raise ValueError("Project sources changed during analysis. Analyze the project again.")
            if cancelled():
                results.append({"project": project, "status": "skipped", "detail": "Batch cancelled"})
                continue
            results.append({
                "project": project, "status": "ready", "detail": "Ready for review",
                "manager": manager, "snapshot": snapshot,
            })
            notify("Analysis complete", index, project)
        except Exception as error:
            detail = f"{type(error).__name__}: {error}"
            results.append({"project": project, "status": "error", "detail": detail, "traceback": traceback.format_exc()})
            log(f"Error ({project}): {detail}")
            notify("Analysis failed", index, project)

    ready = [result for result in results if result["status"] == "ready"]
    approved = bool(ready) and not cancelled() and review(results)
    for result in ready:
        project = result["project"]
        index = projects.index(project) + 1
        manager = result["manager"]
        root = project.root if isinstance(project, RootFileProject) else project
        snapshot = result.pop("snapshot")
        if not approved or cancelled():
            result.update(status="skipped", detail="Batch cancelled" if cancelled() else "Review cancelled")
            continue
        output = None
        try:
            notify("Creating processed copy", index, project)
            if _snapshot_sources(root, manager.root_files_only) != snapshot:
                raise ValueError("Project sources changed after review. Analyze the project again.")
            output = manager.create_processed_copy()
            manager.report_data["end_time"] = datetime.now()
            if generate_report:
                result["report_path"] = manager.generate_html_report(str(output / "report.html"))
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
        notify("Project finished", index, project, result)
    return results
