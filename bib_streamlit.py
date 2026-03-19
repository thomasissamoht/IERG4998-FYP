#!/usr/bin/env python3
"""
BibTeX Bibliography Manager - Streamlit Web App
A modern web interface for managing bibliography files
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import pandas as pd
from bib import BibliographyManager

# Page configuration
st.set_page_config(
    page_title="BibTeX Manager",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 20px 0;
    }
    .stat-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        color: #667eea;
    }
    .stat-label {
        color: #666;
        font-size: 0.9rem;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'manager' not in st.session_state:
    st.session_state.manager = None
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'report_path' not in st.session_state:
    st.session_state.report_path = None

# Header
st.markdown('<h1 class="main-header">📚 BibTeX Bibliography Manager</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Modern web-based tool for managing BibTeX files</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # File upload or directory input
    upload_method = st.radio("Input Method", ["Upload Files", "Use Directory"])
    
    uploaded_files = []
    directory = ""
    
    if upload_method == "Upload Files":
        uploaded_files = st.file_uploader(
            "Upload .bib files",
            type=['bib'],
            accept_multiple_files=True,
            help="Select one or more BibTeX files to process"
        )
    else:
        directory = st.text_input(
            "Directory Path",
            help="Enter path to directory containing .bib files",
            placeholder="C:/path/to/bib/files"
        )
    
    st.divider()
    
    # Similarity threshold
    threshold = st.slider(
        "Similarity Threshold",
        min_value=0,
        max_value=100,
        value=85,
        help="Minimum similarity percentage to consider entries as duplicates"
    )
    
    st.caption(f"Current: **{threshold}%**")
    
    st.divider()
    
    # Options
    st.subheader("Options")
    push_back = st.checkbox("Push master.bib to folders", value=True)
    generate_report = st.checkbox("Generate HTML report", value=True)
    
    st.divider()
    
    # Run button
    run_button = st.button(
        "🚀 Run Pipeline",
        type="primary",
        use_container_width=True
    )
    
    st.divider()
    
    # Info
    with st.expander("ℹ️ About"):
        st.markdown("""
        **BibTeX Bibliography Manager**
        
        Features:
        - Intelligent duplicate detection
        - Fuzzy string matching
        - Citation key normalization
        - Automated backups
        - HTML report generation
        
        Created with ❤️ using Streamlit
        """)

# Main content
if run_button:
    if upload_method == "Upload Files" and uploaded_files:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded files
            for uploaded_file in uploaded_files:
                file_path = Path(temp_dir) / uploaded_file.name
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
            
            # Process
            with st.spinner("🔄 Processing bibliography files..."):
                try:
                    # Initialize manager
                    manager = BibliographyManager(temp_dir)
                    manager.report_data['start_time'] = datetime.now()
                    
                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Step 1: Crawl
                    status_text.text("📁 Crawling for .bib files...")
                    num_files, num_entries = manager.crawl_and_collect()
                    progress_bar.progress(25)
                    
                    if num_entries == 0:
                        st.error("No entries found in uploaded files!")
                        st.stop()
                    
                    # Step 2: Find duplicates
                    status_text.text(f"🔍 Finding duplicates (threshold: {threshold}%)...")
                    num_groups = manager.find_duplicates(threshold=float(threshold))
                    progress_bar.progress(50)
                    
                    # Step 3: Remove duplicates
                    status_text.text("🗑️ Removing duplicates...")
                    manager.remove_duplicates()
                    progress_bar.progress(75)
                    
                    # Step 4: Fix keys
                    status_text.text("🔑 Normalizing citation keys...")
                    manager.fix_citation_keys()
                    
                    # Create master
                    master_path = manager.create_master_bibliography()
                    
                    # Generate report
                    manager.report_data['end_time'] = datetime.now()
                    if generate_report:
                        report_path = manager.generate_html_report()
                        st.session_state.report_path = report_path
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Processing complete!")
                    
                    # Store results
                    st.session_state.manager = manager
                    st.session_state.processed = True
                    
                    st.success("✨ Pipeline completed successfully!")
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.stop()
    
    elif upload_method == "Use Directory" and directory:
        if not Path(directory).exists():
            st.error("❌ Directory does not exist!")
            st.stop()
        
        with st.spinner("🔄 Processing bibliography files..."):
            try:
                # Initialize manager
                manager = BibliographyManager(directory)
                manager.report_data['start_time'] = datetime.now()
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Crawl
                status_text.text("📁 Crawling for .bib files...")
                num_files, num_entries = manager.crawl_and_collect()
                progress_bar.progress(25)
                
                if num_entries == 0:
                    st.error("No entries found!")
                    st.stop()
                
                # Step 2: Find duplicates
                status_text.text(f"🔍 Finding duplicates (threshold: {threshold}%)...")
                num_groups = manager.find_duplicates(threshold=float(threshold))
                progress_bar.progress(50)
                
                # Step 3: Remove duplicates
                status_text.text("🗑️ Removing duplicates...")
                manager.remove_duplicates()
                progress_bar.progress(75)
                
                # Step 4: Fix keys
                status_text.text("🔑 Normalizing citation keys...")
                manager.fix_citation_keys()
                
                # Create master
                master_path = manager.create_master_bibliography()
                
                # Push back if requested
                if push_back:
                    manager.push_to_folders(master_path)
                
                # Generate report
                manager.report_data['end_time'] = datetime.now()
                if generate_report:
                    report_path = manager.generate_html_report()
                    st.session_state.report_path = report_path
                
                progress_bar.progress(100)
                status_text.text("✅ Processing complete!")
                
                # Store results
                st.session_state.manager = manager
                st.session_state.processed = True
                
                st.success("✨ Pipeline completed successfully!")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.stop()
    else:
        st.warning("⚠️ Please upload files or specify a directory!")

# Display results if processed
if st.session_state.processed and st.session_state.manager:
    manager = st.session_state.manager
    data = manager.report_data
    
    st.divider()
    
    # Statistics
    st.header("📊 Processing Statistics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📁 Files", data['files_found'])
    with col2:
        st.metric("📝 Initial Entries", data['initial_entries'])
    with col3:
        st.metric("🔄 Duplicate Groups", len(data['duplicate_groups']))
    with col4:
        st.metric("🗑️ Removed", data['duplicates_removed'])
    with col5:
        st.metric("✅ Final Entries", data['final_entries'])
    
    # Reduction rate
    if data['initial_entries'] > 0:
        reduction_rate = (data['duplicates_removed'] / data['initial_entries']) * 100
        st.metric("🎯 Reduction Rate", f"{reduction_rate:.1f}%")
    
    st.divider()
    
    # Tabs for detailed views
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Visualization", "🔍 Duplicates", "🔑 Key Changes", "📄 Summary"])
    
    with tab1:
        st.subheader("Entry Distribution")
        
        # Pie chart
        fig = go.Figure(data=[go.Pie(
            labels=['Kept', 'Removed'],
            values=[data['final_entries'], data['duplicates_removed']],
            hole=.3,
            marker=dict(colors=['#28a745', '#dc3545'])
        )])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Bar chart of duplicate groups
        if data['duplicate_groups']:
            group_sizes = [len(g['entries']) for g in data['duplicate_groups']]
            fig2 = px.bar(
                x=[f"Group {i+1}" for i in range(len(group_sizes))],
                y=group_sizes,
                labels={'x': 'Duplicate Group', 'y': 'Number of Entries'},
                title="Entries per Duplicate Group"
            )
            fig2.update_traces(marker_color='#667eea')
            st.plotly_chart(fig2, use_container_width=True)
    
    with tab2:
        st.subheader("Duplicate Groups Found")
        
        if not data['duplicate_groups']:
            st.info("✨ No duplicates found!")
        else:
            for idx, group_data in enumerate(data['duplicate_groups'], 1):
                with st.expander(f"🔗 Duplicate Group {idx} - Similarity: {group_data.get('similarity', 'N/A')}%"):
                    entries = group_data['entries']
                    
                    for entry_idx, entry in enumerate(entries):
                        status = "✅ KEPT" if entry_idx == 0 else "❌ REMOVED"
                        col1, col2 = st.columns([1, 4])
                        
                        with col1:
                            if entry_idx == 0:
                                st.success(status)
                            else:
                                st.error(status)
                        
                        with col2:
                            title = entry.get('title', 'No title').replace('{', '').replace('}', '')[:100]
                            author = entry.get('author', 'Unknown')[:50]
                            year = entry.get('year', 'N/A')
                            key = entry.get('ID', 'unknown')
                            
                            st.markdown(f"**[{key}]** {title}")
                            st.caption(f"👤 {author} | 📅 {year}")
                        
                        st.divider()
    
    with tab3:
        st.subheader("Citation Key Changes")
        
        if not data['keys_changed']:
            st.info("No keys were changed")
        else:
            # Create dataframe
            df = pd.DataFrame(data['keys_changed'], columns=['Old Key', 'New Key'])
            st.dataframe(df, use_container_width=True, height=400)
            
            st.caption(f"Total keys normalized: **{len(data['keys_changed'])}**")
    
    with tab4:
        st.subheader("Processing Summary")
        
        duration = "N/A"
        if data['start_time'] and data['end_time']:
            duration = f"{(data['end_time'] - data['start_time']).total_seconds():.1f}s"
        
        summary_md = f"""
        ### 📋 Complete Report
        
        **Processing Details:**
        - ⏱️ Duration: {duration}
        - 📁 Files Processed: {data['files_found']}
        - 📝 Initial Entries: {data['initial_entries']}
        - 🔍 Duplicate Groups: {len(data['duplicate_groups'])}
        - 🗑️ Duplicates Removed: {data['duplicates_removed']}
        - ✅ Final Unique Entries: {data['final_entries']}
        - 🔑 Keys Normalized: {len(data['keys_changed'])}
        
        **Results:**
        - ✓ All original files backed up with timestamps
        - ✓ Master bibliography created
        - ✓ No data loss - backups available for restore
        - ✓ Citation keys normalized to consistent format
        
        **Quality Metrics:**
        - Duplicate reduction: {(data['duplicates_removed'] / max(data['initial_entries'], 1)) * 100:.1f}%
        - Similarity threshold used: {threshold}%
        """
        
        st.markdown(summary_md)
        
        # Download button for master.bib
        if hasattr(manager, 'master_db') and manager.master_db.entries:
            from bibtexparser.bwriter import BibTexWriter
            writer = BibTexWriter()
            bib_content = writer.write(manager.master_db)
            
            st.download_button(
                label="💾 Download master.bib",
                data=bib_content,
                file_name="master.bib",
                mime="text/plain"
            )
    
    # View report button
    if st.session_state.report_path:
        st.divider()
        if st.button("📊 Open HTML Report in Browser"):
            import webbrowser
            webbrowser.open(f"file:///{st.session_state.report_path}")
            st.success("Report opened in browser!")

# Footer
st.divider()
st.markdown("""
<p style="text-align: center; color: #666; font-size: 0.9em;">
    📚 BibTeX Bibliography Manager | Created with Streamlit | Final Year Project 2026
</p>
""", unsafe_allow_html=True)
