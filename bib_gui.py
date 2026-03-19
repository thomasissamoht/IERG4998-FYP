#!/usr/bin/env python3
"""
BibTeX Bibliography Manager - GUI Version
Provides an intuitive graphical interface for bibliography management
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Import the bibliography manager
from bib import BibliographyManager


class BibliographyManagerGUI:
    """GUI application for bibliography management"""
    
    def __init__(self, root):
        """Initialize the GUI"""
        self.root = root
        self.root.title("BibTeX Bibliography Manager")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # Set style
        style = ttk.Style()
        style.theme_use('clam')
        
        self.manager: Optional[BibliographyManager] = None
        self.root_directory: Optional[str] = None
        self.is_processing: bool = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # ===== HEADER =====
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        
        ttk.Label(header_frame, text="📚 Bibliography Manager", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=5)
        
        ttk.Button(header_frame, text="📁 Select Folder", command=self.select_folder).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        self.folder_label = ttk.Label(header_frame, text="No folder selected", foreground="gray")
        self.folder_label.grid(row=0, column=2, sticky=tk.W, padx=10)
        
        # ===== NOTEBOOK (TABS) =====
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, sticky="nsew", pady=10)
        main_frame.rowconfigure(1, weight=1)
        
        # Tab 1: Pipeline
        self.pipeline_frame = ttk.Frame(notebook)
        notebook.add(self.pipeline_frame, text="Pipeline")
        self.setup_pipeline_tab()
        
        # Tab 2: Results
        self.results_frame = ttk.Frame(notebook)
        notebook.add(self.results_frame, text="Results")
        self.setup_results_tab()
        
        # Tab 3: Duplicates
        self.duplicates_frame = ttk.Frame(notebook)
        notebook.add(self.duplicates_frame, text="Duplicates Found")
        self.setup_duplicates_tab()
        
        # Tab 4: Settings
        self.settings_frame = ttk.Frame(notebook)
        notebook.add(self.settings_frame, text="Settings")
        self.setup_settings_tab()
        
    def setup_pipeline_tab(self):
        """Setup the pipeline/execution tab"""
        self.pipeline_frame.columnconfigure(0, weight=1)
        self.pipeline_frame.rowconfigure(1, weight=1)
        
        # Control panel
        control_frame = ttk.LabelFrame(self.pipeline_frame, text="Execution", padding="10")
        control_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        control_frame.columnconfigure(1, weight=1)
        
        ttk.Button(control_frame, text="▶ Run Full Pipeline", command=self.run_full_pipeline, 
                  width=20).grid(row=0, column=0, padx=5)
        
        ttk.Button(control_frame, text="⏹ Cancel", command=self.cancel_pipeline, 
                  width=20).grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(control_frame, text="Threshold:", foreground="gray").grid(row=0, column=2, padx=5)
        self.threshold_var = tk.DoubleVar(value=85.0)
        ttk.Scale(control_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                 variable=self.threshold_var).grid(row=0, column=3, sticky="ew", padx=5)
        self.threshold_label = ttk.Label(control_frame, text="85%")
        self.threshold_label.grid(row=0, column=4, padx=5)
        self.threshold_var.trace_add('write', self.update_threshold_label)
        
        self.push_back_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Push back to folders", 
                       variable=self.push_back_var).grid(row=0, column=5, padx=5)
        
        # Progress display
        progress_frame = ttk.LabelFrame(self.pipeline_frame, text="Progress", padding="10")
        progress_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=20, width=100, 
                                                   font=("Courier", 10), state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # Configure text tags for colors
        self.log_text.tag_configure("header", foreground="#0066cc", font=("Courier", 10, "bold"))
        self.log_text.tag_configure("success", foreground="#00aa00")
        self.log_text.tag_configure("warning", foreground="#ff6600")
        self.log_text.tag_configure("error", foreground="#dd0000")
        self.log_text.tag_configure("step", foreground="#0066cc", font=("Courier", 10, "bold"))
        
    def setup_results_tab(self):
        """Setup the results display tab"""
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        
        results_container = ttk.Frame(self.results_frame)
        results_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        results_container.columnconfigure(0, weight=1)
        results_container.rowconfigure(0, weight=1)
        
        # Create a frame for statistics
        stats_frame = ttk.LabelFrame(results_container, text="Summary Statistics", padding="15")
        stats_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        stats_frame.columnconfigure(1, weight=1)
        
        # Statistics display
        self.stats_display = {
            'files_found': tk.StringVar(value="0"),
            'total_entries': tk.StringVar(value="0"),
            'duplicates_found': tk.StringVar(value="0"),
            'entries_removed': tk.StringVar(value="0"),
            'final_entries': tk.StringVar(value="0"),
            'master_path': tk.StringVar(value=""),
        }
        
        stats = [
            ("🗂️  Files Found:", 'files_found'),
            ("📝 Total Entries:", 'total_entries'),
            ("🔄 Duplicate Groups:", 'duplicates_found'),
            ("🗑️  Entries Removed:", 'entries_removed'),
            ("✅ Final Entries:", 'final_entries'),
            ("📄 Master File:", 'master_path'),
        ]
        
        for i, (label, key) in enumerate(stats):
            ttk.Label(stats_frame, text=label, font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            value_label = ttk.Label(stats_frame, textvariable=self.stats_display[key], 
                                   font=("Arial", 10, "bold"), foreground="#0066cc")
            value_label.grid(row=i, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Results text area
        results_text_frame = ttk.LabelFrame(results_container, text="Details", padding="10")
        results_text_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        results_text_frame.columnconfigure(0, weight=1)
        results_text_frame.rowconfigure(0, weight=1)
        
        self.results_text = scrolledtext.ScrolledText(results_text_frame, height=15, width=100, 
                                                      font=("Courier", 9), state=tk.DISABLED)
        self.results_text.grid(row=0, column=0, sticky="nsew")
        
    def setup_duplicates_tab(self):
        """Setup the duplicates display tab"""
        self.duplicates_frame.columnconfigure(0, weight=1)
        self.duplicates_frame.rowconfigure(0, weight=1)
        
        duplicates_container = ttk.Frame(self.duplicates_frame)
        duplicates_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        duplicates_container.columnconfigure(0, weight=1)
        duplicates_container.rowconfigure(0, weight=1)
        
        self.duplicates_text = scrolledtext.ScrolledText(duplicates_container, height=30, width=120, 
                                                         font=("Courier", 9), state=tk.DISABLED)
        self.duplicates_text.grid(row=0, column=0, sticky="nsew")
        
        # Configure tags for duplicate display
        self.duplicates_text.tag_configure("group_header", foreground="#dd0000", font=("Courier", 9, "bold"))
        self.duplicates_text.tag_configure("entry", foreground="#000000")
        self.duplicates_text.tag_configure("field", foreground="#666666", font=("Courier", 8))
        
    def setup_settings_tab(self):
        """Setup the settings tab"""
        settings_frame = ttk.LabelFrame(self.settings_frame, text="Configuration", padding="15")
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        info_text = """
BibTeX Bibliography Manager - Settings

SIMILARITY THRESHOLD:
- Controls how similar entries must be to be considered duplicates
- Range: 0-100 (%)
- Default: 85%
- Lower values = more aggressive duplicate detection
- Higher values = only very similar entries are merged

DUPLICATE DETECTION CRITERIA:
1. DOI Match (100% match if present)
2. Title Similarity (60% weight)
3. Author Similarity (30% weight)
4. Year Match (bonus +10%)

CITATION KEY GENERATION:
Format: firstname-year-firstword
- firstname: First author's last name
- year: Publication year
- firstword: First 3+ letter word from title

If duplicate keys exist, appends: -a, -b, -c, etc.

BACKUP STRATEGY:
- Original .bib files are backed up before being replaced
- Backups stored in: folder/backup_YYYYMMDD_HHMMSS/
- Backups are timestamped to prevent accidental overwriting

RECOMMENDATIONS:
- Start with 85% threshold
- Adjust lower if missing duplicates
- Always review duplicates before finalizing
- Test on small dataset first
        """
        
        ttk.Label(settings_frame, text=info_text, justify=tk.LEFT, 
                 font=("Courier", 9)).pack(fill=tk.BOTH, expand=True)
        
    def update_threshold_label(self, *args):
        """Update threshold display label"""
        self.threshold_label.config(text=f"{int(self.threshold_var.get())}%")
        
    def select_folder(self):
        """Select root directory"""
        folder = filedialog.askdirectory(title="Select root directory to search for .bib files")
        if folder:
            self.root_directory = folder
            self.manager = BibliographyManager(folder)
            self.folder_label.config(text=folder, foreground="black")
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"✓ Folder selected: {folder}\n", "success")
            self.log_text.config(state=tk.DISABLED)
            
    def log_message(self, message, tag=""):
        """Add message to log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()
        
    def run_full_pipeline(self):
        """Run the pipeline in a separate thread"""
        if not self.manager:
            messagebox.showwarning("Warning", "Please select a folder first!")
            return
        
        if self.is_processing:
            messagebox.showwarning("Warning", "Pipeline is already running!")
            return
        
        # Run in separate thread to prevent UI freezing
        thread = threading.Thread(target=self._pipeline_worker)
        thread.daemon = True
        thread.start()
        
    def _pipeline_worker(self):
        """Worker thread for pipeline execution"""
        self.is_processing = True
        
        if self.manager is None:
            self.log_message("❌ Error: No folder selected", "error")
            self.is_processing = False
            return
        
        try:
            threshold = self.threshold_var.get()
            push_back = self.push_back_var.get()
            
            self.log_message("\n" + "="*60, "header")
            self.log_message(" BibTeX Bibliography Manager - Full Pipeline", "header")
            self.log_message("="*60 + "\n", "header")
            
            # Step 1: Crawl
            self.log_message("\n" + "="*60, "step")
            self.log_message("STEP 1: Crawling folders for .bib files...", "step")
            self.log_message("="*60 + "\n", "step")
            
            num_files, num_entries = self.manager.crawl_and_collect()
            
            if num_entries == 0:
                self.log_message("⚠️  No entries found. Exiting.", "warning")
                self.is_processing = False
                return
            
            # Step 2: Find duplicates
            self.log_message("\n" + "="*60, "step")
            self.log_message("STEP 2: Identifying duplicates...", "step")
            self.log_message("="*60 + "\n", "step")
            
            num_duplicates = self.manager.find_duplicates(threshold=threshold)
            
            # Display duplicates in separate tab
            self._display_duplicates()
            
            # Step 3: Remove duplicates
            self.manager.remove_duplicates()
            
            # Step 4: Fix keys
            self.log_message("\n" + "="*60, "step")
            self.log_message("STEP 3: Fixing citation keys (labels)...", "step")
            self.log_message("="*60 + "\n", "step")
            
            self.manager.fix_citation_keys()
            
            # Step 5: Create master
            self.log_message("\n" + "="*60, "step")
            self.log_message("STEP 4: Creating master bibliography...", "step")
            self.log_message("="*60 + "\n", "step")
            
            master_path = self.manager.create_master_bibliography()
            
            # Step 6: Push back
            if push_back:
                self.log_message("\nPushing master.bib to original folders...", "step")
                self.manager.push_to_folders(master_path, create_backup=True)
            
            # Final summary
            self.log_message("\n" + "="*60, "header")
            self.log_message(" ✓ Pipeline completed successfully!", "header")
            self.log_message("="*60, "header")
            
            # Update statistics
            self._update_statistics(num_files, num_entries, num_duplicates, master_path)
            
        except Exception as e:
            self.log_message(f"\n❌ Error: {str(e)}", "error")
            messagebox.showerror("Error", f"Pipeline failed: {str(e)}")
        finally:
            self.is_processing = False
            
    def _display_duplicates(self):
        """Display duplicate groups in duplicates tab"""
        self.duplicates_text.config(state=tk.NORMAL)
        self.duplicates_text.delete(1.0, tk.END)
        
        if self.manager is None:
            self.duplicates_text.insert(tk.END, "No manager initialized.\n")
            self.duplicates_text.config(state=tk.DISABLED)
            return
        
        if not self.manager.duplicate_groups:
            self.duplicates_text.insert(tk.END, "No duplicates found.\n")
        else:
            for group_num, group in enumerate(self.manager.duplicate_groups, 1):
                self.duplicates_text.insert(tk.END, 
                    f"\n🔄 DUPLICATE GROUP {group_num} ({len(group)} entries)\n" + 
                    "─" * 80 + "\n", "group_header")
                
                for entry_num, idx in enumerate(group, 1):
                    entry = self.manager.all_entries[idx]
                    title = entry.get('title', 'NO TITLE')
                    key = entry.get('ID', 'NO_KEY')
                    author = entry.get('author', 'NO AUTHOR')
                    year = entry.get('year', 'N/A')
                    doi = entry.get('doi', 'N/A')
                    
                    self.duplicates_text.insert(tk.END, 
                        f"  Entry {entry_num}:\n" +
                        f"    Key: {key}\n" +
                        f"    Author: {author}\n" +
                        f"    Title: {title}\n" +
                        f"    Year: {year}\n" +
                        f"    DOI: {doi}\n\n", "entry")
        
        self.duplicates_text.config(state=tk.DISABLED)
        
    def _update_statistics(self, num_files, num_entries, num_duplicates, master_path):
        """Update results statistics"""
        if self.manager is None:
            return
        
        entries_removed = num_entries - len(self.manager.all_entries)
        
        self.stats_display['files_found'].set(str(num_files))
        self.stats_display['total_entries'].set(str(num_entries))
        self.stats_display['duplicates_found'].set(str(num_duplicates))
        self.stats_display['entries_removed'].set(str(entries_removed))
        self.stats_display['final_entries'].set(str(len(self.manager.all_entries)))
        self.stats_display['master_path'].set(master_path)
        
        # Update results text
        results = f"""
PIPELINE EXECUTION SUMMARY
{'='*60}

Input:
  - Folders searched: {num_files}
  - Total entries found: {num_entries}
  - Duplicate groups identified: {num_duplicates}

Processing:
  - Duplicate entries removed: {entries_removed}
  - Partial duplicates merged: {num_duplicates}

Output:
  - Final unique entries: {len(self.manager.all_entries)}
  - Master bibliography: {master_path}
  - Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Reduction:
  - Duplicates eliminated: {(entries_removed / num_entries * 100):.1f}% of original entries
  - Cleanup efficiency: {(entries_removed)}/{num_entries} duplicates removed
        """
        
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, results)
        self.results_text.config(state=tk.DISABLED)
        
    def cancel_pipeline(self):
        """Cancel the pipeline"""
        if self.is_processing:
            self.log_message("\n⏹ Pipeline cancelled by user", "warning")
            self.is_processing = False
        else:
            messagebox.showinfo("Info", "No pipeline is currently running.")


def main():
    """Launch the GUI application"""
    root = tk.Tk()
    app = BibliographyManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
