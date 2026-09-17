#!/usr/bin/env python3
"""Multi-project Streamlit bibliography workspace."""

from datetime import datetime
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import zipfile

import pandas as pd
import streamlit as st
from bibtexparser.bwriter import BibTexWriter
from bib import BibliographyManager

st.set_page_config(page_title="Bib Workspace", page_icon="B", layout="wide")

APP_DIR = Path(__file__).resolve().parent / "app"
# Streamlit serves files from the project-level ./static directory at /app/static/.
STATIC_DIR = Path(__file__).resolve().parent / "static"
WORKSPACE_DIR = APP_DIR / "workspaces"
USERS_FILE = APP_DIR / "users.json"
PUBLIC_BASE_URL = os.getenv("BIB_PUBLIC_BASE_URL", "").rstrip("/")
USERNAME = os.getenv("BIB_APP_USERNAME", "admin")
PASSWORD = os.getenv("BIB_APP_PASSWORD", "bibliography")


def initialize_state():
    defaults = {"authenticated": False, "username": "", "active_project": "", "projects": {}}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def load_users() -> dict:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_users(users: dict):
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = USERS_FILE.with_suffix(".tmp")
    temporary_file.write_text(json.dumps(users, indent=2), encoding="utf-8")
    temporary_file.replace(USERS_FILE)


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 300_000).hex()
    return f"pbkdf2_sha256$300000${salt}${digest}"


def password_matches(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)).hex()
        return secrets.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def valid_username(username: str) -> bool:
    return 3 <= len(username) <= 32 and all(character.isalnum() or character in "_-" for character in username)


def authenticate(username: str, password: str) -> bool:
    if username == USERNAME and password == PASSWORD:
        return True
    user = load_users().get(username)
    return bool(user and password_matches(password, user.get("password_hash", "")))


def project_root(project_name: str) -> Path:
    safe_name = "".join(character for character in project_name if character.isalnum() or character in "-_ ").strip().replace(" ", "_")
    if not safe_name:
        raise ValueError("Project names must contain letters or numbers.")
    return WORKSPACE_DIR / st.session_state.username / safe_name


def save_uploads(project_name: str, uploaded_files) -> Path:
    target = project_root(project_name)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for uploaded_file in uploaded_files:
        filename = Path(uploaded_file.name).name
        if filename.lower().endswith(".zip"):
            with zipfile.ZipFile(BytesIO(uploaded_file.getvalue())) as archive:
                target_path = target.resolve()
                for member in archive.infolist():
                    destination = (target / member.filename).resolve()
                    if not str(destination).startswith(str(target_path)):
                        raise ValueError("The ZIP contains an unsafe path.")
                archive.extractall(target)
        elif filename.lower().endswith(".bib"):
            (target / filename).write_bytes(uploaded_file.getvalue())
    return target


def add_uploads(project_name: str, uploaded_files) -> Path:
    """Add new source files to an existing project without deleting its workspace."""
    target = project_root(project_name)
    if not target.is_dir():
        raise ValueError("The selected project workspace does not exist.")
    for uploaded_file in uploaded_files:
        filename = Path(uploaded_file.name).name
        if filename.lower().endswith(".zip"):
            with zipfile.ZipFile(BytesIO(uploaded_file.getvalue())) as archive:
                target_path = target.resolve()
                for member in archive.infolist():
                    destination = (target / member.filename).resolve()
                    if not str(destination).startswith(str(target_path)):
                        raise ValueError("The ZIP contains an unsafe path.")
                archive.extractall(target)
        elif filename.lower().endswith(".bib"):
            (target / filename).write_bytes(uploaded_file.getvalue())
    return target


def write_master(manager: BibliographyManager, project_name: str) -> tuple[bytes, Path]:
    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = ("ID",)
    master_bytes = writer.write(manager.master_db).encode("utf-8")
    export_path = STATIC_DIR / f"{project_name}.bib"
    export_path.write_bytes(master_bytes)
    return master_bytes, export_path


def process_workspace(project_name: str, workspace: Path):
    manager = BibliographyManager(str(workspace))
    manager.report_data["start_time"] = datetime.now()
    _file_count, entry_count = manager.crawl_and_collect()
    if entry_count == 0:
        raise ValueError("No BibTeX entries were found in the upload.")
    manager.find_duplicates(threshold=85.0)
    manager.remove_duplicates()
    manager.fix_citation_keys("{author}-{year}-{title_part}")
    manager.create_master_bibliography()
    manager.report_data["end_time"] = datetime.now()
    master_bytes, export_path = write_master(manager, project_name)
    st.session_state.projects[project_name] = {"manager": manager, "master_bytes": master_bytes, "export_path": str(export_path), "updated": datetime.now().isoformat(timespec="seconds")}
    st.session_state.active_project = project_name


def process_project(project_name: str, uploaded_files):
    workspace = save_uploads(project_name, uploaded_files)
    process_workspace(project_name, workspace)


def update_project(project_name: str, uploaded_files):
    workspace = add_uploads(project_name, uploaded_files)
    process_workspace(project_name, workspace)


def load_project(project_name: str):
    """Rebuild in-memory state for a project discovered on disk."""
    project = st.session_state.projects.get(project_name)
    if project:
        return
    workspace = project_root(project_name)
    if not workspace.is_dir():
        return
    process_workspace(project_name, workspace)


def login_page():
    st.markdown("# Bib Workspace")
    st.caption("Secure bibliography workspaces for research teams")
    mode = st.radio("Account", ["Sign in", "Register"], horizontal=True)
    if mode == "Sign in":
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if submitted:
            if authenticate(username.strip(), password):
                st.session_state.authenticated = True
                st.session_state.username = username.strip()
                st.switch_page(DASHBOARD_PAGE)
            else:
                st.error("Invalid username or password.")
        return

    with st.form("register"):
        username = st.text_input("Choose a username", help="Use 3-32 letters, numbers, underscores, or hyphens.")
        password = st.text_input("Choose a password", type="password")
        confirmation = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
    if submitted:
        username = username.strip()
        users = load_users()
        if not valid_username(username):
            st.error("Username must be 3-32 characters and use only letters, numbers, underscores, or hyphens.")
        elif username == USERNAME or username in users:
            st.error("That username is already registered.")
        elif len(password) < 8:
            st.error("Password must be at least 8 characters long.")
        elif password != confirmation:
            st.error("Passwords do not match.")
        else:
            users[username] = {"password_hash": password_hash(password)}
            save_users(users)
            st.success("Account created. Choose Sign in to continue.")


def render_audit(manager: BibliographyManager):
    report = manager.report_data
    audit_tabs = st.tabs(["Key transformation", "Merged duplicates", "Metadata fixes"])
    with audit_tabs[0]:
        key_audit = report.get("key_audit", [])
        if key_audit:
            st.dataframe(pd.DataFrame(key_audit), use_container_width=True, hide_index=True)
        else:
            st.dataframe(pd.DataFrame(report.get("keys_changed", []), columns=["Original Raw Key", "Normalized Key"]), use_container_width=True, hide_index=True)
    with audit_tabs[1]:
        render_duplicate_evidence(manager)
    with audit_tabs[2]:
        st.dataframe(pd.DataFrame(report.get("metadata_fixes", [])), use_container_width=True, hide_index=True)


def _entry_location(entry: dict) -> str:
    source = entry.get("_source_file_display") or Path(entry.get("_source_file", "")).name or "Unknown file"
    start = entry.get("_entry_start_line") or entry.get("_line_number") or "?"
    end = entry.get("_entry_end_line") or start
    return f"{source} | lines {start}-{end}"


def _entry_text(entry: dict) -> str:
    raw_text = entry.get("_entry_text") or ""
    if raw_text.strip():
        return raw_text.strip()
    fields = [f"  {key} = {{{value}}}" for key, value in entry.items() if not key.startswith("_") and key != "ID"]
    entry_type = entry.get("ENTRYTYPE", "article")
    return "@" + str(entry_type) + "{" + str(entry.get("ID", "unknown")) + ",\n" + ",\n".join(fields) + "\n}"


def _source_context(manager: BibliographyManager, entry: dict, context_lines: int = 3) -> str:
    source_path = entry.get("_source_file")
    start = entry.get("_entry_start_line") or entry.get("_line_number")
    end = entry.get("_entry_end_line") or start
    if not source_path or not isinstance(start, int):
        return "Source context is unavailable for this entry."
    source_info = manager.report_data.get("source_files", {}).get(source_path, {})
    source_text = source_info.get("text")
    if source_text is None:
        try:
            source_text = Path(source_path).read_text(encoding="utf-8")
        except OSError:
            return "Source context is unavailable for this entry."
    lines = source_text.splitlines()
    first = max(start - context_lines - 1, 0)
    last = min((end if isinstance(end, int) else start) + context_lines, len(lines))
    return "\n".join(f"{line_number:4d} | {lines[line_number - 1]}" for line_number in range(first + 1, last + 1))


def _field_diff(kept_entry: dict, removed_entry: dict) -> pd.DataFrame:
    ignored_fields = {"ENTRYTYPE"}
    fields = sorted(
        {
            key
            for key in set(kept_entry) | set(removed_entry)
            if not key.startswith("_") and key not in ignored_fields
        }
    )
    rows = []
    for field in fields:
        kept_value = str(kept_entry.get(field, "")).strip()
        removed_value = str(removed_entry.get(field, "")).strip()
        if kept_value == removed_value:
            status = "MATCH"
        elif not removed_value:
            status = "ONLY KEPT"
        elif not kept_value:
            status = "ONLY REMOVED"
        else:
            status = "CONFLICT"
        rows.append({"Field": field, "Status": status, "Kept record": kept_value, "Removed record": removed_value})
    return pd.DataFrame(rows)


def render_duplicate_evidence(manager: BibliographyManager):
    groups = manager.report_data.get("duplicate_groups", [])
    if not groups:
        st.success("No duplicate groups were found. Every imported entry was retained.")
        return

    labels = [
        f"Group {number}: {group.get('similarity', 'N/A')}% similarity, {len(group.get('entries', []))} entries"
        for number, group in enumerate(groups, 1)
    ]
    selected_group = st.selectbox("Duplicate group", range(len(groups)), format_func=lambda index: labels[index])
    group = groups[selected_group]
    entries = group.get("entries", [])
    kept_entries = [entry for entry in entries if entry.get("_status") == "kept"]
    removed_entries = [entry for entry in entries if entry.get("_status") != "kept"]

    summary = st.columns(4)
    summary[0].metric("Similarity", f"{group.get('similarity', 'N/A')}%")
    summary[1].metric("Kept", len(kept_entries))
    summary[2].metric("Removed", len(removed_entries))
    summary[3].metric("Reason", group.get("reason", "Duplicate match"))

    overview_rows = []
    for entry in entries:
        overview_rows.append({
            "Status": "KEPT" if entry.get("_status") == "kept" else "REMOVED",
            "Key": entry.get("ID", ""),
            "Location": _entry_location(entry),
            "Author": entry.get("author", ""),
            "Year": entry.get("year", ""),
            "Title": entry.get("title", ""),
            "Fields": entry.get("_merge_field_count", ""),
            "Confidence": f"{entry.get('_match_confidence', group.get('similarity', 'N/A'))}%",
            "Match criterion": entry.get("_match_reason", group.get("reason", "Duplicate match")),
        })
    st.dataframe(pd.DataFrame(overview_rows), use_container_width=True, hide_index=True)

    if not kept_entries or not removed_entries:
        return

    removed_index = st.selectbox(
        "Removed entry to compare",
        range(len(removed_entries)),
        format_func=lambda index: f"{removed_entries[index].get('ID', 'unknown')} | {_entry_location(removed_entries[index])}",
    )
    kept_entry = kept_entries[0]
    removed_entry = removed_entries[removed_index]
    confidence = removed_entry.get("_match_confidence", group.get("similarity", "N/A"))
    criterion = removed_entry.get("_match_reason", group.get("reason", "Duplicate match"))
    if str(criterion).startswith("Exact DOI"):
        st.success(f"Match confidence: {confidence}% | Criterion: {criterion}")
    elif str(criterion).startswith("Exact normalized title"):
        st.info(f"Match confidence: {confidence}% | Criterion: {criterion}")
    else:
        st.warning(f"Match confidence: {confidence}% | Criterion: {criterion}")

    st.markdown("#### Field-level comparison")
    st.dataframe(_field_diff(kept_entry, removed_entry), use_container_width=True, hide_index=True)
    before, after = st.columns(2)
    with before:
        st.markdown("#### Before: removed source entry")
        st.caption(_entry_location(removed_entry))
        st.code(_entry_text(removed_entry), language="bibtex")
    with after:
        st.markdown("#### After: canonical kept entry")
        st.caption(_entry_location(kept_entry))
        st.code(_entry_text(kept_entry), language="bibtex")

    merged_fields = removed_entry.get("_merged_into_master_fields", [])
    if merged_fields:
        st.info("Fields contributed to the canonical record: " + ", ".join(merged_fields))
    else:
        st.caption("No missing fields were contributed by this removed copy.")

    with st.expander("Show source context with line numbers"):
        context_before, context_after = st.columns(2)
        with context_before:
            st.markdown("**Removed entry location**")
            st.code(_source_context(manager, removed_entry), language="text")
        with context_after:
            st.markdown("**Kept entry location**")
            st.code(_source_context(manager, kept_entry), language="text")


def dashboard_page():
    if not st.session_state.authenticated:
        st.switch_page(LOGIN_PAGE)
    user_dir = WORKSPACE_DIR / st.session_state.username
    user_dir.mkdir(parents=True, exist_ok=True)
    project_names = sorted(set(path.name for path in user_dir.iterdir() if path.is_dir()) | set(st.session_state.projects))
    with st.sidebar:
        st.markdown("## Projects")
        selected = st.selectbox("Active project", project_names or ["No projects yet"])
        if project_names and selected != "No projects yet":
            st.session_state.active_project = selected
        with st.expander("Create new project"):
            new_name = st.text_input("Project name", placeholder="ML_Journal_2026")
            uploads = st.file_uploader("BibTeX or ZIP files", type=["bib", "zip"], accept_multiple_files=True)
            create = st.button("Process project", type="primary", use_container_width=True)
        with st.expander("Update active project"):
            update_uploads = st.file_uploader(
                "Add new BibTeX or ZIP files",
                type=["bib", "zip"],
                accept_multiple_files=True,
                key="update_project_uploads",
            )
            update = st.button("Update bibliography", use_container_width=True)
        if st.button("Sign out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.switch_page(LOGIN_PAGE)
    st.markdown("# Bibliography workspace")
    st.caption(f"Signed in as {st.session_state.username}")
    if create:
        if not new_name.strip() or not uploads:
            st.warning("Enter a project name and upload at least one .bib or .zip file.")
        else:
            try:
                with st.spinner("Processing and publishing bibliography..."):
                    process_project(new_name.strip(), uploads)
                st.success(f"{new_name.strip()} is ready.")
            except Exception as error:
                st.error(f"Processing failed: {error}")
    if update:
        active_project = st.session_state.active_project
        if not active_project or active_project == "No projects yet":
            st.warning("Select an existing project before adding references.")
        elif not update_uploads:
            st.warning("Upload at least one .bib or .zip file to update the project.")
        else:
            try:
                with st.spinner(f"Updating {active_project} and publishing the refreshed bibliography..."):
                    update_project(active_project, update_uploads)
                st.success(f"{active_project} updated. The existing Overleaf URL now serves the new master bibliography.")
            except Exception as error:
                st.error(f"Update failed: {error}")
    if st.session_state.active_project and st.session_state.active_project not in st.session_state.projects:
        with st.spinner("Loading project..."):
            load_project(st.session_state.active_project)
    project = st.session_state.projects.get(st.session_state.active_project)
    if not project:
        st.info("Create a project to begin.")
        return
    manager = project["manager"]
    report = manager.report_data
    st.subheader(st.session_state.active_project)
    metrics = st.columns(7)
    metrics[0].metric("Source files", report.get("files_found", 0))
    metrics[1].metric("References", report.get("initial_entries", 0))
    metrics[2].metric("Duplicate groups", len(report.get("duplicate_groups", [])))
    metrics[3].metric("Duplicates merged", report.get("duplicates_removed", 0))
    metrics[4].metric("Final references", report.get("final_entries", 0))
    metrics[5].metric("Keys normalized", len(report.get("keys_changed", [])))
    metrics[6].metric("Reduction", f"{(report.get('duplicates_removed', 0) / max(report.get('initial_entries', 0), 1) * 100):.1f}%")
    if PUBLIC_BASE_URL:
        export_url = f"{PUBLIC_BASE_URL}/{st.session_state.active_project}.bib"
        st.success(f"Live Overleaf URL: {export_url}")
    else:
        export_url = f"http://localhost:8501/app/static/{st.session_state.active_project}.bib"
        st.warning("A public URL is not configured. Start a Cloudflare tunnel and set BIB_PUBLIC_BASE_URL before processing uploads.")
    st.code(export_url, language="text")
    st.download_button("Download .bib", project["master_bytes"], f"{st.session_state.active_project}.bib", "application/x-bibtex")
    st.caption(f"Published: {project['updated']}")
    st.divider()
    st.subheader("Processing report")
    render_audit(manager)


initialize_state()
LOGIN_PAGE = st.Page(login_page, title="Login", icon="🔐", default=True)
DASHBOARD_PAGE = st.Page(dashboard_page, title="Dashboard", icon="📚")
navigation = st.navigation([LOGIN_PAGE, DASHBOARD_PAGE])
navigation.run()