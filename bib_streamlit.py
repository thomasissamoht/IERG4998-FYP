#!/usr/bin/env python3
"""Multi-project Streamlit bibliography workspace."""

from datetime import datetime
from io import BytesIO
import os
from pathlib import Path
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
PUBLIC_BASE_URL = os.getenv("BIB_PUBLIC_BASE_URL", "").rstrip("/")
USERNAME = os.getenv("BIB_APP_USERNAME", "admin")
PASSWORD = os.getenv("BIB_APP_PASSWORD", "bibliography")


def initialize_state():
    defaults = {"authenticated": False, "username": "", "active_project": "", "projects": {}}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


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
    manager.fix_citation_keys("{author}-{year}-{titleword}")
    manager.create_master_bibliography()
    manager.report_data["end_time"] = datetime.now()
    master_bytes, export_path = write_master(manager, project_name)
    st.session_state.projects[project_name] = {"manager": manager, "master_bytes": master_bytes, "export_path": str(export_path), "updated": datetime.now().isoformat(timespec="seconds")}
    st.session_state.active_project = project_name


def process_project(project_name: str, uploaded_files):
    workspace = save_uploads(project_name, uploaded_files)
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
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
    if submitted:
        if username == USERNAME and password == PASSWORD:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.switch_page(DASHBOARD_PAGE)
        else:
            st.error("Invalid username or password.")


def render_audit(manager: BibliographyManager):
    report = manager.report_data
    audit_tabs = st.tabs(["Key transformation", "Merged duplicates", "Metadata fixes"])
    with audit_tabs[0]:
        st.dataframe(pd.DataFrame(report.get("keys_changed", []), columns=["Original Raw Key", "Normalized Key"]), use_container_width=True, hide_index=True)
    with audit_tabs[1]:
        rows = []
        for group_number, group in enumerate(report.get("duplicate_groups", []), 1):
            kept = next((item.get("ID", "") for item in group.get("entries", []) if item.get("_status") == "kept"), "")
            for item in group.get("entries", []):
                if item.get("_status") == "removed":
                    rows.append({"Group": group_number, "Removed key": item.get("ID", ""), "Kept key": kept, "Reason": group.get("reason", "Duplicate match")})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with audit_tabs[2]:
        st.dataframe(pd.DataFrame(report.get("metadata_fixes", [])), use_container_width=True, hide_index=True)


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
    metrics = st.columns(5)
    metrics[0].metric("Source files", report.get("files_found", 0))
    metrics[1].metric("References", report.get("initial_entries", 0))
    metrics[2].metric("Duplicates removed", report.get("duplicates_removed", 0))
    metrics[3].metric("Final references", report.get("final_entries", 0))
    metrics[4].metric("Keys normalized", len(report.get("keys_changed", [])))
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