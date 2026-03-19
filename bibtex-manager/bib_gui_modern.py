#!/usr/bin/env python3
"""
Modern BibTeX Bibliography Manager GUI
Using CustomTkinter for a beautiful, modern interface
"""

import customtkinter as ctk
import threading
import webbrowser
from pathlib import Path
from typing import Optional
from bib import BibliographyManager

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"


class ModernBibGUI:
    """Modern GUI for Bibliography Manager using CustomTkinter"""
    
    def __init__(self):
        """Initialize the modern GUI"""
        self.root = ctk.CTk()
        self.root.title("📚 BibTeX Bibliography Manager")
        self.root.geometry("1400x900")
        
        # Manager instance
        self.manager: Optional[BibliographyManager] = None
        self.processing = False
        self.report_path = None
        
        # Build UI
        self._build_ui()
        
    def _build_ui(self):
        """Build the user interface"""
        # Configure grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Left sidebar for controls
        self._build_sidebar()
        
        # Main content area with tabs
        self._build_main_content()
        
    def _build_sidebar(self):
        """Build left sidebar with controls"""
        sidebar = ctk.CTkFrame(self.root, width=300, corner_radius=0)
        sidebar.grid(row=0, column=0, rowspan=4, sticky="nsew")
        sidebar.grid_rowconfigure(6, weight=1)
        
        # Logo/Title
        logo_label = ctk.CTkLabel(
            sidebar, 
            text="📚 BibTeX Manager",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        subtitle = ctk.CTkLabel(
            sidebar,
            text="Modern Bibliography Tool",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Directory selection
        dir_label = ctk.CTkLabel(sidebar, text="Select Directory", font=ctk.CTkFont(size=14, weight="bold"))
        dir_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.dir_entry = ctk.CTkEntry(sidebar, placeholder_text="Choose directory with .bib files...")
        self.dir_entry.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        self.browse_btn = ctk.CTkButton(
            sidebar,
            text="📁 Browse",
            command=self._browse_directory,
            fg_color="gray25",
            hover_color="gray30"
        )
        self.browse_btn.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        # Similarity threshold slider
        threshold_label = ctk.CTkLabel(
            sidebar, 
            text="Similarity Threshold",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        threshold_label.grid(row=5, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.threshold_var = ctk.IntVar(value=85)
        self.threshold_label = ctk.CTkLabel(sidebar, text="85%", text_color="#3b8ed0")
        self.threshold_label.grid(row=6, column=0, padx=20, pady=0)
        
        self.threshold_slider = ctk.CTkSlider(
            sidebar,
            from_=0,
            to=100,
            variable=self.threshold_var,
            command=self._update_threshold_label
        )
        self.threshold_slider.grid(row=7, column=0, padx=20, pady=(5, 20), sticky="ew")
        
        # Options
        self.push_var = ctk.BooleanVar(value=True)
        self.push_check = ctk.CTkCheckBox(
            sidebar,
            text="Push master.bib to folders",
            variable=self.push_var,
            font=ctk.CTkFont(size=13)
        )
        self.push_check.grid(row=8, column=0, padx=20, pady=5, sticky="w")
        
        self.report_var = ctk.BooleanVar(value=True)
        self.report_check = ctk.CTkCheckBox(
            sidebar,
            text="Generate HTML report",
            variable=self.report_var,
            font=ctk.CTkFont(size=13)
        )
        self.report_check.grid(row=9, column=0, padx=20, pady=5, sticky="w")
        
        # Action buttons
        self.run_btn = ctk.CTkButton(
            sidebar,
            text="▶ Run Pipeline",
            command=self._run_pipeline,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#1f538d",
            hover_color="#14375e"
        )
        self.run_btn.grid(row=10, column=0, padx=20, pady=(30, 10), sticky="ew")
        
        self.cancel_btn = ctk.CTkButton(
            sidebar,
            text="⏹ Cancel",
            command=self._cancel_pipeline,
            height=35,
            fg_color="gray25",
            hover_color="gray30",
            state="disabled"
        )
        self.cancel_btn.grid(row=11, column=0, padx=20, pady=5, sticky="ew")
        
        self.view_report_btn = ctk.CTkButton(
            sidebar,
            text="📊 View Report",
            command=self._view_report,
            height=35,
            fg_color="gray25",
            hover_color="gray30",
            state="disabled"
        )
        self.view_report_btn.grid(row=12, column=0, padx=20, pady=5, sticky="ew")
        
        # Appearance mode switch
        appearance_label = ctk.CTkLabel(sidebar, text="Appearance Mode", font=ctk.CTkFont(size=12))
        appearance_label.grid(row=13, column=0, padx=20, pady=(30, 5))
        
        self.appearance_menu = ctk.CTkOptionMenu(
            sidebar,
            values=["System", "Light", "Dark"],
            command=self._change_appearance,
            fg_color="gray25",
            button_color="gray30"
        )
        self.appearance_menu.grid(row=14, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.appearance_menu.set("Dark")
        
    def _build_main_content(self):
        """Build main content area with tabs"""
        # Main frame
        main_frame = ctk.CTkFrame(self.root)
        main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Tab view
        self.tabview = ctk.CTkTabview(main_frame, corner_radius=10)
        self.tabview.grid(row=0, column=0, sticky="nsew")
        
        # Create tabs
        self.tabview.add("📋 Pipeline")
        self.tabview.add("📊 Results")
        self.tabview.add("🔍 Duplicates")
        self.tabview.add("ℹ️ About")
        
        self._build_pipeline_tab()
        self._build_results_tab()
        self._build_duplicates_tab()
        self._build_about_tab()
        
    def _build_pipeline_tab(self):
        """Build pipeline execution tab"""
        tab = self.tabview.tab("📋 Pipeline")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        
        # Progress textbox
        self.log_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word"
        )
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(tab)
        self.progress.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.progress.set(0)
        
    def _build_results_tab(self):
        """Build results summary tab"""
        tab = self.tabview.tab("📊 Results")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        
        # Stats frame
        stats_frame = ctk.CTkFrame(tab, fg_color="transparent")
        stats_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Create stat cards in grid
        stats = [
            ("📁 Files", "files"),
            ("📝 Initial", "initial"),
            ("🔄 Groups", "groups"),
            ("🗑️ Removed", "removed"),
            ("✅ Final", "final"),
            ("⚡ Time", "time")
        ]
        
        self.stat_labels = {}
        for idx, (label, key) in enumerate(stats):
            row = idx // 3
            col = idx % 3
            
            card = ctk.CTkFrame(stats_frame)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            stats_frame.grid_columnconfigure(col, weight=1)
            
            title = ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12), text_color="gray")
            title.pack(pady=(10, 5))
            
            value = ctk.CTkLabel(card, text="—", font=ctk.CTkFont(size=32, weight="bold"))
            value.pack(pady=(0, 10))
            
            self.stat_labels[key] = value
        
        # Details textbox
        self.results_text = ctk.CTkTextbox(tab, font=ctk.CTkFont(size=12))
        self.results_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
    def _build_duplicates_tab(self):
        """Build duplicates visualization tab"""
        tab = self.tabview.tab("🔍 Duplicates")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        
        self.duplicates_text = ctk.CTkTextbox(tab, font=ctk.CTkFont(size=12))
        self.duplicates_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
    def _build_about_tab(self):
        """Build about/help tab"""
        tab = self.tabview.tab("ℹ️ About")
        
        # Scrollable frame
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        about_text = """
        BibTeX Bibliography Manager
        ══════════════════════════════════════════
        
        A modern tool for managing BibTeX bibliography files.
        
        Features:
        • Crawl folders recursively for .bib files
        • Intelligent duplicate detection (fuzzy + exact matching)
        • Automatic citation key normalization
        • Backup system with timestamps
        • HTML report generation
        • Modern, beautiful interface
        
        How to Use:
        1. Select a directory containing .bib files
        2. Adjust similarity threshold (85% recommended)
        3. Click "Run Pipeline"
        4. View results in tabs
        5. Check HTML report for detailed analysis
        
        Duplicate Detection:
        • DOI matching for perfect duplicates
        • Fuzzy title matching (60% weight)
        • Author name matching (30% weight)
        • Year bonus (+10%)
        
        Citation Key Format:
        firstname-year-keyword
        (e.g., smith-2023-advances)
        
        ══════════════════════════════════════════
        Final Year Project 2026
        Created with ❤️ using Python & CustomTkinter
        """
        
        about_label = ctk.CTkLabel(
            scroll,
            text=about_text,
            font=ctk.CTkFont(family="Consolas", size=12),
            justify="left"
        )
        about_label.pack(padx=20, pady=20)
        
    def _update_threshold_label(self, value):
        """Update threshold label when slider moves"""
        self.threshold_label.configure(text=f"{int(value)}%")
        
    def _browse_directory(self):
        """Open directory browser"""
        directory = ctk.filedialog.askdirectory(title="Select Directory with .bib files")
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)
            
    def _change_appearance(self, mode: str):
        """Change appearance mode"""
        ctk.set_appearance_mode(mode.lower())
        
    def _log_message(self, message: str, color: str = "white"):
        """Add message to log"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()
        
    def _run_pipeline(self):
        """Run the bibliography management pipeline"""
        directory = self.dir_entry.get().strip()
        
        if not directory:
            self._log_message("❌ Please select a directory first!", "red")
            return
        
        if not Path(directory).exists():
            self._log_message("❌ Directory does not exist!", "red")
            return
        
        # Clear previous results
        self.log_text.delete("1.0", "end")
        self.results_text.delete("1.0", "end")
        self.duplicates_text.delete("1.0", "end")
        self.progress.set(0)
        
        # Disable run button
        self.run_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.processing = True
        
        # Run in thread
        thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        thread.start()
        
    def _pipeline_worker(self):
        """Worker thread for pipeline execution"""
        try:
            directory = self.dir_entry.get().strip()
            threshold = self.threshold_var.get()
            push_back = self.push_var.get()
            generate_report = self.report_var.get()
            
            self._log_message("="*60)
            self._log_message("🚀 Starting Bibliography Processing Pipeline")
            self._log_message("="*60)
            
            # Initialize manager
            self.manager = BibliographyManager(directory)
            self.progress.set(0.1)
            
            # Step 1: Crawl
            self._log_message("\n📁 Step 1/4: Crawling for .bib files...")
            num_files, num_entries = self.manager.crawl_and_collect()
            self._log_message(f"✓ Found {num_files} files with {num_entries} entries")
            self.progress.set(0.3)
            
            if num_entries == 0:
                self._log_message("\n⚠️ No entries found!")
                return
            
            # Step 2: Find duplicates
            self._log_message(f"\n🔍 Step 2/4: Finding duplicates (threshold: {threshold}%)...")
            num_groups = self.manager.find_duplicates(threshold=float(threshold))
            self._log_message(f"✓ Found {num_groups} duplicate groups")
            self.progress.set(0.5)
            
            # Step 3: Remove duplicates
            self._log_message("\n🗑️ Step 3/4: Removing duplicates...")
            self.manager.remove_duplicates()
            self._log_message(f"✓ Removed {self.manager.report_data['duplicates_removed']} duplicates")
            self.progress.set(0.7)
            
            # Step 4: Fix keys
            self._log_message("\n🔑 Step 4/4: Normalizing citation keys...")
            self.manager.fix_citation_keys()
            self._log_message(f"✓ Normalized {len(self.manager.report_data['keys_changed'])} keys")
            
            # Create master
            self._log_message("\n💾 Creating master bibliography...")
            master_path = self.manager.create_master_bibliography()
            self._log_message(f"✓ Created: {master_path}")
            self.progress.set(0.85)
            
            # Push back if requested
            if push_back:
                self._log_message("\n📤 Pushing master.bib to folders...")
                self.manager.push_to_folders(master_path)
                self._log_message("✓ Distribution complete")
            
            # Generate report
            self.manager.report_data['end_time'] = self.manager.report_data.get('end_time') or __import__('datetime').datetime.now()
            if generate_report:
                self._log_message("\n📊 Generating HTML report...")
                self.report_path = self.manager.generate_html_report()
                self._log_message(f"✓ Report: {self.report_path}")
                self.view_report_btn.configure(state="normal")
            
            self.progress.set(1.0)
            
            # Update results
            self._update_results()
            self._update_duplicates()
            
            self._log_message("\n" + "="*60)
            self._log_message("✨ Pipeline completed successfully!")
            self._log_message("="*60)
            
        except Exception as e:
            self._log_message(f"\n❌ Error: {str(e)}")
            import traceback
            self._log_message(traceback.format_exc())
            
        finally:
            self.processing = False
            self.run_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
            
    def _cancel_pipeline(self):
        """Cancel pipeline execution"""
        # Simple cancellation (thread will finish current operation)
        self.processing = False
        self._log_message("\n⚠️ Cancellation requested...")
        
    def _update_results(self):
        """Update results tab with statistics"""
        if not self.manager:
            return
        
        data = self.manager.report_data
        
        # Update stat cards
        self.stat_labels['files'].configure(text=str(data['files_found']))
        self.stat_labels['initial'].configure(text=str(data['initial_entries']))
        self.stat_labels['groups'].configure(text=str(len(data['duplicate_groups'])))
        self.stat_labels['removed'].configure(text=str(data['duplicates_removed']))
        self.stat_labels['final'].configure(text=str(data['final_entries']))
        
        # Calculate time
        if data['start_time'] and data['end_time']:
            duration = (data['end_time'] - data['start_time']).total_seconds()
            self.stat_labels['time'].configure(text=f"{duration:.1f}s")
        
        # Detailed summary
        reduction_rate = (data['duplicates_removed'] / max(data['initial_entries'], 1)) * 100
        
        summary = f"""
Processing Summary
{'='*50}

Files Processed: {data['files_found']}
Initial Entries: {data['initial_entries']}
Duplicate Groups: {len(data['duplicate_groups'])}
Entries Removed: {data['duplicates_removed']}
Final Entries: {data['final_entries']}

Reduction Rate: {reduction_rate:.1f}%
Keys Normalized: {len(data['keys_changed'])}

{'='*50}
✓ All original files backed up with timestamps
✓ Master bibliography created
✓ No data loss - backups available for restore
"""
        
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", summary)
        
    def _update_duplicates(self):
        """Update duplicates tab"""
        if not self.manager:
            return
        
        self.duplicates_text.delete("1.0", "end")
        
        if not self.manager.report_data['duplicate_groups']:
            self.duplicates_text.insert("1.0", "No duplicates found! ✨")
            return
        
        for idx, group_data in enumerate(self.manager.report_data['duplicate_groups'], 1):
            entries = group_data['entries']
            similarity = group_data.get('similarity', 'N/A')
            
            self.duplicates_text.insert("end", f"\n{'─'*60}\n")
            self.duplicates_text.insert("end", f"Duplicate Group {idx} | Similarity: {similarity}%\n")
            self.duplicates_text.insert("end", f"{'─'*60}\n\n")
            
            for entry_idx, entry in enumerate(entries):
                status = "✅ KEPT" if entry_idx == 0 else "❌ REMOVED"
                title = entry.get('title', 'No title').replace('{', '').replace('}', '')[:80]
                author = entry.get('author', 'Unknown')[:40]
                year = entry.get('year', 'N/A')
                key = entry.get('ID', 'unknown')
                
                self.duplicates_text.insert("end", f"{status} [{key}]\n")
                self.duplicates_text.insert("end", f"  📄 {title}...\n")
                self.duplicates_text.insert("end", f"  👤 {author} | 📅 {year}\n\n")
                
    def _view_report(self):
        """Open HTML report in browser"""
        if self.report_path and Path(self.report_path).exists():
            webbrowser.open(f"file:///{self.report_path}")
        else:
            self._log_message("❌ No report available")
            
    def run(self):
        """Start the GUI"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = ModernBibGUI()
    app.run()


if __name__ == "__main__":
    main()
