#!/usr/bin/env python3
"""Browser interface for the BibTeX Bibliography Manager."""

from datetime import datetime
from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from bibtexparser.bwriter import BibTexWriter

from bib import BibliographyManager


st.set_page_config(
    page_title="BibTeX Bibliography Manager",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-header { font-size: 2.7rem; font-weight: 700; padding: 0.4rem 0; }
    .muted { color: #667085; }
    </style>
    """,
    unsafe_allow_html=True,
)

RULE_FORMATS = {
    "author-year-title": "{author}-{year}-{title}",
    "author-year-titleword": "{author}-{year}-{titleword}",
    "author-title": "{author}-{title}",
    "professor-style": "{authorstem}{year}",
    "professor-strict": "{authorstrict}{year}",
    "author-et-al-year": "{authoretal}{year}",
    "lastname-only-year": "{lastname}{year}",
    "firstauthor-year-titleword": "{author}{year}{titleword}",
    "compact-initials": "{authorinitials}{year}",
    "numeric": "ref{numeric}",
}


def init_state():
    defaults = {
        "manager": None,
        "processed": False,
        "master_bytes": None,
        "report_bytes": None,
        "report_name": "bibliography_report.html",
        "source_name": "",
        "notes": {},
        "tags": {},
        "favorites": set(),
        "issue_text": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def citation_format(rule: str, custom: str) -> str:
    if rule == "custom" and custom.strip():
        return custom.strip()
    return RULE_FORMATS.get(rule, RULE_FORMATS["author-year-titleword"])


def build_outputs(manager: BibliographyManager):
    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = ("ID",)
    master_bytes = writer.write(manager.master_db).encode("utf-8")

    report_bytes = None
    report_name = "bibliography_report.html"
    report_path = manager.generate_html_report()
    if report_path and Path(report_path).exists():
        report_bytes = Path(report_path).read_bytes()
        report_name = Path(report_path).name
    return master_bytes, report_bytes, report_name


def process_directory(directory: str, threshold: int, push_back: bool, generate_report: bool, key_format: str):
    manager = BibliographyManager(directory)
    manager.report_data["start_time"] = datetime.now()
    _num_files, num_entries = manager.crawl_and_collect()
    if num_entries == 0:
        raise ValueError("No BibTeX entries were found.")
    manager.find_duplicates(threshold=float(threshold))
    manager.remove_duplicates()
    manager.fix_citation_keys(key_format)
    master_path = manager.create_master_bibliography()
    if push_back:
        manager.push_to_folders(master_path)
    manager.report_data["end_time"] = datetime.now()
    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = ("ID",)
    master_bytes = writer.write(manager.master_db).encode("utf-8")
    if not generate_report:
        return manager, master_bytes, None, None
    _generated_master_bytes, report_bytes, report_name = build_outputs(manager)
    return manager, master_bytes, report_bytes, report_name


def process_uploads(uploaded_files, threshold: int, key_format: str, generate_report: bool):
    with tempfile.TemporaryDirectory() as temp_dir:
        for uploaded_file in uploaded_files:
            file_path = Path(temp_dir) / Path(uploaded_file.name).name
            file_path.write_bytes(uploaded_file.getbuffer())
        return process_directory(temp_dir, threshold, False, generate_report, key_format)


def entry_frame(manager: BibliographyManager) -> pd.DataFrame:
    rows = []
    duplicate_keys = {
        str(entry.get("ID", "")).strip()
        for group in manager.report_data.get("duplicate_groups", [])
        for entry in group.get("entries", [])
    }
    for entry in manager.all_entries:
        key = str(entry.get("ID", "")).strip()
        rows.append(
            {
                "Favorite": "★" if key in st.session_state.favorites else "",
                "Duplicate": "Yes" if key in duplicate_keys else "",
                "Key": key,
                "Authors": str(entry.get("author", "")),
                "Year": str(entry.get("year", "")),
                "Title": str(entry.get("title", "")),
                "Source": str(entry.get("journal") or entry.get("booktitle") or entry.get("_source_file_display") or ""),
                "DOI": str(entry.get("doi", "")),
            }
        )
    return pd.DataFrame(rows)


def render_library(manager: BibliographyManager):
    st.subheader("📚 Library")
    frame = entry_frame(manager)
    query = st.text_input("Search title, author, year, DOI, or key", key="library_query")
    filters = st.multiselect("Filters", ["Duplicates", "Has DOI", "Missing year", "Favorites"])
    if query:
        mask = frame.astype(str).apply(lambda column: column.str.contains(query, case=False, na=False)).any(axis=1)
        frame = frame[mask]
    if "Duplicates" in filters:
        frame = frame[frame["Duplicate"] == "Yes"]
    if "Has DOI" in filters:
        frame = frame[frame["DOI"].str.strip() != ""]
    if "Missing year" in filters:
        frame = frame[frame["Year"].str.strip() == ""]
    if "Favorites" in filters:
        frame = frame[frame["Favorite"] == "★"]

    st.caption(f"Showing {len(frame)} of {len(manager.all_entries)} references")
    st.dataframe(frame, use_container_width=True, height=390, hide_index=True)

    keys = frame["Key"].tolist() if not frame.empty else []
    selected_key = st.selectbox("Reference details", ["Select a reference"] + keys)
    if selected_key != "Select a reference":
        selected = next((entry for entry in manager.all_entries if str(entry.get("ID", "")) == selected_key), None)
        if selected:
            left, right = st.columns(2)
            with left:
                st.markdown(f"**{selected.get('title', 'Untitled')}**")
                st.write(f"Authors: {selected.get('author', '')}")
                st.write(f"Year: {selected.get('year', '')}")
                st.write(f"Key: `{selected.get('ID', '')}`")
                st.write(f"DOI: {selected.get('doi', '') or 'Not provided'}")
            with right:
                st.session_state.notes[selected_key] = st.text_area(
                    "Notes", value=st.session_state.notes.get(selected_key, ""), key=f"note_{selected_key}"
                )
                st.session_state.tags[selected_key] = st.text_input(
                    "Tags", value=st.session_state.tags.get(selected_key, ""), key=f"tag_{selected_key}"
                )
                if st.button("Toggle favorite", key=f"favorite_{selected_key}"):
                    if selected_key in st.session_state.favorites:
                        st.session_state.favorites.remove(selected_key)
                    else:
                        st.session_state.favorites.add(selected_key)
                    st.rerun()


def render_duplicates(manager: BibliographyManager):
    st.subheader("🔍 Duplicate Review")
    groups = manager.report_data.get("duplicate_groups", [])
    if not groups:
        st.success("No duplicate groups found.")
        return
    labels = [f"Group {index}: {group.get('similarity', 'N/A')}% similarity" for index, group in enumerate(groups, 1)]
    selected_index = st.selectbox("Duplicate group", range(len(labels)), format_func=lambda index: labels[index])
    group = groups[selected_index]
    st.write(f"Entries in group: {len(group.get('entries', []))}")
    rows = []
    for entry in group.get("entries", []):
        rows.append(
            {
                "Status": "KEPT" if entry.get("_status") == "kept" else "REMOVED",
                "Key": entry.get("ID", ""),
                "Authors": entry.get("author", ""),
                "Year": entry.get("year", ""),
                "Title": entry.get("title", ""),
                "Source": entry.get("_source_file_display", entry.get("_source_file", "")),
                "Fields": entry.get("_merge_field_count", ""),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with st.expander("Show entry details"):
        for entry in group.get("entries", []):
            st.markdown(f"**{entry.get('_status', 'unknown').upper()}**: `{entry.get('ID', '')}`")
            st.code(entry.get("_entry_text", "No original entry text available."), language="bibtex")


def render_fixes(manager: BibliographyManager):
    st.subheader("🛠 Fixes and Changes")
    changes = manager.report_data.get("keys_changed", [])
    if changes:
        st.dataframe(pd.DataFrame(changes, columns=["Old key", "New key"]), use_container_width=True, hide_index=True)
    else:
        st.info("No citation keys changed during this run.")
    st.markdown("#### Output files")
    st.write("The cleaned bibliography and HTML report can be downloaded from the sidebar.")


init_state()
st.markdown('<div class="main-header">📚 BibTeX Bibliography Manager</div>', unsafe_allow_html=True)
st.caption("Final Year Project | Browser-based testing interface")

with st.sidebar:
    st.header("⚙️ Project setup")
    input_method = st.radio("Input method", ["Upload .bib files", "Use server directory"])
    uploaded_files = []
    directory = ""
    if input_method == "Upload .bib files":
        uploaded_files = st.file_uploader("Select one or more BibTeX files", type=["bib"], accept_multiple_files=True)
    else:
        directory = st.text_input("Server directory path", placeholder="C:/path/to/bibliography")
    threshold = st.slider("Duplicate similarity threshold", 0, 100, 85)
    push_back = st.checkbox("Push master.bib to source folders", value=True, disabled=input_method != "Use server directory")
    generate_report = st.checkbox("Generate HTML report", value=True)

    st.subheader("Citation key policy")
    rule = st.selectbox("Naming rule", list(RULE_FORMATS) + ["custom"], index=1)
    custom = st.text_input("Custom pattern", "{author}-{year}-{titleword}", disabled=rule != "custom")
    st.caption(f"Format: `{citation_format(rule, custom)}`")
    run_button = st.button("🚀 Run pipeline", type="primary", use_container_width=True)

    if st.session_state.master_bytes:
        st.download_button("💾 Download master.bib", st.session_state.master_bytes, "master.bib", "application/x-bibtex", use_container_width=True)
    if st.session_state.report_bytes:
        st.download_button("📊 Download HTML report", st.session_state.report_bytes, st.session_state.report_name, "text/html", use_container_width=True)

if run_button:
    try:
        key_format = citation_format(rule, custom)
        with st.spinner("Processing bibliography..."):
            if input_method == "Upload .bib files":
                if not uploaded_files:
                    st.warning("Please upload at least one .bib file.")
                    st.stop()
                manager, master_bytes, report_bytes, report_name = process_uploads(uploaded_files, threshold, key_format, generate_report)
                source_name = ", ".join(file.name for file in uploaded_files)
            else:
                if not directory or not Path(directory).is_dir():
                    st.error("Please enter a valid server directory.")
                    st.stop()
                manager, master_bytes, report_bytes, report_name = process_directory(directory, threshold, push_back, generate_report, key_format)
                source_name = directory
        st.session_state.manager = manager
        st.session_state.master_bytes = master_bytes
        st.session_state.report_bytes = report_bytes
        st.session_state.report_name = report_name or "bibliography_report.html"
        st.session_state.source_name = source_name
        st.session_state.processed = True
        st.session_state.favorites = set()
        st.success("Pipeline completed successfully.")
    except Exception as error:
        st.error(f"Pipeline failed: {error}")

if st.session_state.processed and st.session_state.manager:
    manager = st.session_state.manager
    data = manager.report_data
    st.divider()
    st.subheader("📊 Processing dashboard")
    metrics = st.columns(6)
    metrics[0].metric("Files", data.get("files_found", 0))
    metrics[1].metric("Initial entries", data.get("initial_entries", 0))
    metrics[2].metric("Duplicate groups", len(data.get("duplicate_groups", [])))
    metrics[3].metric("Removed", data.get("duplicates_removed", 0))
    metrics[4].metric("Final entries", data.get("final_entries", 0))
    metrics[5].metric("Keys changed", len(data.get("keys_changed", [])))

    tabs = st.tabs(["📈 Dashboard", "📚 Library", "🔍 Duplicates", "🛠 Fixes", "📄 Summary", "🐞 Report issue"])
    with tabs[0]:
        kept = data.get("final_entries", 0)
        removed = data.get("duplicates_removed", 0)
        fig = go.Figure(data=[go.Pie(labels=["Kept", "Removed"], values=[kept, removed], hole=0.35)])
        fig.update_layout(height=360)
        st.plotly_chart(fig, use_container_width=True)
        groups = data.get("duplicate_groups", [])
        if groups:
            sizes = [len(group.get("entries", [])) for group in groups]
            st.plotly_chart(px.bar(x=list(range(1, len(sizes) + 1)), y=sizes, labels={"x": "Group", "y": "Entries"}), use_container_width=True)
    with tabs[1]:
        render_library(manager)
    with tabs[2]:
        render_duplicates(manager)
    with tabs[3]:
        render_fixes(manager)
    with tabs[4]:
        start = data.get("start_time")
        end = data.get("end_time")
        duration = f"{(end - start).total_seconds():.1f}s" if start and end else "N/A"
        st.markdown(f"""
        **Source:** {st.session_state.source_name}

        **Duration:** {duration}

        **Similarity threshold:** {threshold}%

        **Outputs:** cleaned `master.bib`, normalized citation keys, duplicate analysis, and backups for directory processing.
        """)
    with tabs[5]:
        st.subheader("Report an issue")
        st.caption("Describe the problem and download the report to send with your feedback.")
        issue = st.text_area("Issue description", value=st.session_state.issue_text, height=180)
        st.session_state.issue_text = issue
        if st.button("Prepare issue report"):
            issue_report = f"BibTeX Bibliography Manager issue report\nGenerated: {datetime.now():%Y-%m-%d %H:%M}\nSource: {st.session_state.source_name}\n\n{issue}\n"
            st.download_button("Download issue report", issue_report, "bibliography_issue_report.txt", "text/plain")

st.divider()
st.caption("📚 BibTeX Bibliography Manager | Streamlit | Final Year Project 2026")
