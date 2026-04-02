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
import importlib
from typing import TYPE_CHECKING, Any
import tempfile
import zipfile
import shutil
import os
from tkinter import filedialog
from tkinter import messagebox

if TYPE_CHECKING:
    # Provide a name for static checkers without importing the runtime module
    webview: Any  # pragma: no cover

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"


class ModernBibGUI:
    """Modern GUI for Bibliography Manager using CustomTkinter"""

    def _on_citekey_rule_changed(self, rule):
        # Only update entry if it exists
        if hasattr(self, 'citekey_custom_entry'):
            if rule == "custom":
                self.citekey_custom_entry.configure(state="normal")
            else:
                self.citekey_custom_entry.configure(state="disabled")
    
    def __init__(self):
        """Initialize the modern GUI"""
        self.root = ctk.CTk()
        self.root.title("📚 BibTeX Bibliography Manager")
        self.root.geometry("1400x900")
        
        # Manager instance
        self.manager: Optional[BibliographyManager] = None
        self.processing = False
        self.report_path = None
        self._syncing_scroll = False
        self._syncing_scroll_x = False
        self._current_changed_lines = []
        self._current_changed_idx = -1
        self._last_master_path = None
        self._last_cleaned_zip = None
        self._status_text = ctk.StringVar(value="Ready")
        self._log_count = 0
        self._log_buffer = []
        self._log_flush_job = None
        self._defer_log_render = False
        self._deferred_logs = []
        self._log_lock = threading.Lock()
        self._step_state = {}
        self._pending_step_text = "Waiting to start..."
        self._pending_step_color = "#d1d5db"
        self._pending_duplicates_refresh = False
        self._duplicate_groups_cache = []
        self._selected_duplicate_group = 0
        self._duplicate_file_order = []
        self._selected_duplicate_file = 0
        self._duplicate_highlight_positions = []
        self._selected_duplicate_highlight = 0
        self._current_duplicate_display_name = "-"
        
        # Citation key normalization rule (default and custom)
        self.citekey_rule_var = ctk.StringVar(value="author-year-title")
        self.citekey_custom_var = ctk.StringVar(value="{author}-{year}-{title}")

        # Build UI
        self._build_ui()

    def _ui_call(self, func, *args, **kwargs):
        """Run UI operation on main thread (Tkinter-safe)."""
        if threading.current_thread() is threading.main_thread():
            func(*args, **kwargs)
        else:
            # Queue to main thread with proper argument passing
            self.root.after(0, lambda: func(*args, **kwargs))
        
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
    # Citation key normalization rule (default and custom)

                        # Citation key normalization rule

                # Citation key normalization rule

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
        
        self.dir_entry = ctk.CTkEntry(sidebar, placeholder_text="Choose folder or .zip with .bib files...")
        self.dir_entry.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        self.browse_btn = ctk.CTkButton(
            sidebar,
            text="📁 Browse",
            command=self._browse_directory,
            fg_color="gray25",
            hover_color="gray30"
        )
        self.browse_btn.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")

        quick_actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        quick_actions.grid(row=5, column=0, padx=20, pady=(0, 8), sticky="ew")
        quick_actions.grid_columnconfigure((0, 1), weight=1)

        self.demo_btn = ctk.CTkButton(
            quick_actions,
            text="🧪 Use test_data",
            command=self._use_test_data,
            height=28,
            fg_color="gray25",
            hover_color="gray30"
        )
        self.demo_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.clear_btn = ctk.CTkButton(
            quick_actions,
            text="🧹 Clear",
            command=self._clear_for_next_run,
            height=28,
            fg_color="gray25",
            hover_color="gray30"
        )
        self.clear_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        # Similarity threshold slider
        threshold_label = ctk.CTkLabel(
            sidebar, 
            text="Similarity Threshold",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        threshold_label.grid(row=6, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.threshold_var = ctk.IntVar(value=85)
        self.threshold_label = ctk.CTkLabel(sidebar, text="85%", text_color="#3b8ed0")
        self.threshold_label.grid(row=7, column=0, padx=20, pady=0)
        
        self.threshold_hint = ctk.CTkLabel(
            sidebar,
            text="Balanced (recommended)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.threshold_hint.grid(row=8, column=0, padx=20, pady=(0, 4))
        
        self.threshold_slider = ctk.CTkSlider(
            sidebar,
            from_=0,
            to=100,
            variable=self.threshold_var,
            command=self._update_threshold_label
        )
        self.threshold_slider.grid(row=9, column=0, padx=20, pady=(5, 20), sticky="ew")
        
        self.push_var = ctk.BooleanVar(value=True)
        self.push_check = ctk.CTkCheckBox(
            sidebar,
            text="Push master.bib to folders",
            variable=self.push_var,
            font=ctk.CTkFont(size=13)
        )
        self.push_check.grid(row=10, column=0, padx=20, pady=5, sticky="w")
        
        self.report_var = ctk.BooleanVar(value=True)
        self.report_check = ctk.CTkCheckBox(
            sidebar,
            text="Generate HTML report",
            variable=self.report_var,
            font=ctk.CTkFont(size=13)
        )
        self.report_check.grid(row=11, column=0, padx=20, pady=5, sticky="w")

        self.status_label = ctk.CTkLabel(
            sidebar,
            textvariable=self._status_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#3b8ed0"
        )
        self.status_label.grid(row=12, column=0, padx=20, pady=(6, 0), sticky="w")
        
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
        self.run_btn.grid(row=13, column=0, padx=20, pady=(30, 10), sticky="ew")
        
        self.cancel_btn = ctk.CTkButton(
            sidebar,
            text="⏹ Cancel",
            command=self._cancel_pipeline,
            height=35,
            fg_color="gray25",
            hover_color="gray30",
            state="disabled"
        )
        self.cancel_btn.grid(row=14, column=0, padx=20, pady=5, sticky="ew")
        
        self.view_report_btn = ctk.CTkButton(
            sidebar,
            text="📊 View Report",
            command=self._view_report,
            height=35,
            fg_color="gray25",
            hover_color="gray30",
            state="disabled"
        )
        self.view_report_btn.grid(row=15, column=0, padx=20, pady=5, sticky="ew")
        
        # Citation key normalization rule UI
        rule_label = ctk.CTkLabel(sidebar, text="Citation Key Rule", font=ctk.CTkFont(size=14, weight="bold"))
        rule_label.grid(row=17, column=0, padx=20, pady=(18, 5), sticky="w")

        self.citekey_rule_menu = ctk.CTkOptionMenu(
            sidebar,
            values=["author-year-title", "author-year-titleword", "author-title", "professor-style", "professor-strict", "author-et-al-year", "lastname-only-year", "firstauthor-year-titleword", "compact-initials", "numeric", "custom"],
            variable=self.citekey_rule_var,
            command=self._on_citekey_rule_changed,
            fg_color="gray25",
            button_color="gray30",
        )
        self.citekey_rule_menu.grid(row=18, column=0, padx=20, pady=(0, 4), sticky="ew")
        self.citekey_rule_menu.set("author-year-title")

        self.citekey_custom_entry = ctk.CTkEntry(
            sidebar,
            textvariable=self.citekey_custom_var,
            placeholder_text="e.g. {author}-{year}-{title}",
            state="disabled"
        )
        self.citekey_custom_entry.grid(row=19, column=0, padx=20, pady=(0, 8), sticky="ew")

        citekey_hint = ctk.CTkLabel(
            sidebar,
            text="Tokens: {author}, {authorstem}, {authorstrict}, {authoretal}, {authorinitials}, {year}, {titleword}, {numeric}",
            wraplength=220,
            justify="left",
            text_color="gray70",
            font=ctk.CTkFont(size=11)
        )
        citekey_hint.grid(row=20, column=0, padx=20, pady=(0, 8), sticky="w")

        # Appearance mode switch (move to bottom)
        appearance_label = ctk.CTkLabel(sidebar, text="Appearance Mode", font=ctk.CTkFont(size=12))
        appearance_label.grid(row=21, column=0, padx=20, pady=(22, 5))

        self.appearance_menu = ctk.CTkOptionMenu(
            sidebar,
            values=["System", "Light", "Dark"],
            command=self._change_appearance,
            fg_color="gray25",
            button_color="gray30"
        )
        self.appearance_menu.grid(row=22, column=0, padx=20, pady=(0, 20), sticky="ew")
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
        self.tabview.add("🛠 Fixes")
        self.tabview.add("ℹ️ About")
        
        self._build_pipeline_tab()
        self._build_results_tab()
        self._build_duplicates_tab()
        self._build_fixes_tab()
        self._build_about_tab()

        # Refresh heavy tabs only when user opens them.
        try:
            self.tabview._segmented_button.configure(command=self._on_tab_changed)
        except Exception:
            pass

    def _on_tab_changed(self, tab_name: str):
        """Handle tab switch events for lazy heavy rendering."""
        # Preserve default tab behavior; overriding segmented button command
        # requires explicitly switching tabs.
        self.tabview.set(tab_name)

        # Defer heavy render slightly so the tab switch paints first.
        if tab_name == "🔍 Duplicates" and self._pending_duplicates_refresh:
            self.root.after(20, self._refresh_pending_duplicates)

    def _refresh_pending_duplicates(self):
        """Render duplicates only when needed and only on the Duplicates tab."""
        if not self._pending_duplicates_refresh:
            return
        if self.tabview.get() != "🔍 Duplicates":
            return

        self._update_duplicates()
        self._pending_duplicates_refresh = False
        
    def _build_pipeline_tab(self):
        """Build pipeline execution tab with step cards"""
        tab = self.tabview.tab("📋 Pipeline")
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        
        # Steps timeline section
        steps_section = ctk.CTkFrame(tab, fg_color="transparent")
        steps_section.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        steps_section.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Define pipeline steps with emojis
        self.step_cards = {}
        self.step_timers = {}
        step_info = [
            ('Crawl', '📁', 'Scanning .bib files'),
            ('Duplicates', '🔍', 'Finding duplicates'),
            ('Remove', '🗑️', 'Removing duplicates'),
            ('Keys', '🔑', 'Normalizing keys')
        ]
        
        for idx, (step_name, emoji, description) in enumerate(step_info):
            # Step card
            card = ctk.CTkFrame(steps_section, fg_color="transparent", corner_radius=0,
                                border_width=1, border_color="#2a2a2a")
            card.grid(row=0, column=idx, padx=4, pady=3, sticky="ew")
            card.grid_columnconfigure(0, weight=1)
            
            # Emoji + Number
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=8, pady=(8, 2))
            header.grid_columnconfigure(1, weight=1)
            
            step_num = ctk.CTkLabel(header, text=f"{emoji} Step {idx+1}",
                                   font=ctk.CTkFont(size=10, weight="bold"))
            step_num.grid(row=0, column=0, sticky="w")
            
            status_badge = ctk.CTkLabel(header, text="⌚ Pending",
                                       font=ctk.CTkFont(size=8),
                                       fg_color="transparent", text_color="#9ca3af",
                                       padx=6, pady=2)
            status_badge.grid(row=0, column=1, sticky="e")
            
            # Step name
            name_label = ctk.CTkLabel(card, text=step_name,
                                     font=ctk.CTkFont(size=11, weight="bold"))
            name_label.pack(fill="x", padx=8, pady=(1, 1))
            
            # Description (single-line and subtle)
            desc_label = ctk.CTkLabel(card, text=description,
                                     font=ctk.CTkFont(size=8),
                                     text_color="#7a7a7a")
            desc_label.pack(fill="x", padx=8, pady=(0, 1))
            
            # Timer
            timer_label = ctk.CTkLabel(card, text="0.0s",
                                      font=ctk.CTkFont(size=9, weight="bold"),
                                      text_color="#fbbf24")
            timer_label.pack(fill="x", padx=8, pady=(1, 8))
            
            self.step_cards[step_name] = {
                'card': card,
                'status': status_badge,
                'timer': timer_label,
                'start_time': None
            }
            self.step_timers[step_name] = 0.0
        
        # Compact current step strip
        step_strip = ctk.CTkFrame(tab, fg_color="#141414", corner_radius=6)
        step_strip.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 6))
        step_strip.grid_columnconfigure(1, weight=1)

        detail_label = ctk.CTkLabel(step_strip, text="Current:",
                       font=ctk.CTkFont(size=10, weight="bold"),
                       text_color="#9ca3af")
        detail_label.grid(row=0, column=0, sticky="w", padx=(10, 6), pady=6)

        self.current_step_label = ctk.CTkLabel(step_strip,
                              text="Waiting to start...",
                              font=ctk.CTkFont(size=10),
                              text_color="#d1d5db",
                              anchor="w")
        self.current_step_label.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=6)

        # Keep a reference to style the strip during state changes.
        self.step_strip = step_strip
        
        # Log textbox with better formatting (minimal height initially)
        log_label = ctk.CTkLabel(tab, text="📋 Pipeline Log",
                                font=ctk.CTkFont(size=11, weight="bold"))
        log_label.grid(row=2, column=0, sticky="w", padx=10, pady=(6, 4))
        
        self.log_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word"
        )
        self.log_text.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tab.grid_rowconfigure(3, weight=1)
        
    def _build_results_tab(self):
        """Build results summary tab with visual metrics"""
        tab = self.tabview.tab("📊 Results")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        
        # Main stats in a scrollable frame
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        scroll.grid_columnconfigure((0, 1), weight=1)
        
        # Create enhanced stat cards in grid (2 columns)
        stats = [
            ("📁 Files", "files", "Total .bib files scanned"),
            ("📝 Initial Entries", "initial", "Starting bibliography size"),
            ("🔄 Duplicate Groups", "groups", "Number of duplicate clusters"),
            ("🗑️ Entries Removed", "removed", "Duplicate entries deleted"),
            ("✅ Final Entries", "final", "Cleaned bibliography size"),
            ("⚡ Processing Time", "time", "Total runtime")
        ]
        
        self.stat_labels = {}
        self.stat_bars = {}  # For progress bars
        
        for idx, (label, key, description) in enumerate(stats):
            row = idx // 2
            col = idx % 2
            
            card = ctk.CTkFrame(scroll, fg_color="#1a1a1a", corner_radius=8)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="ew")
            card.grid_columnconfigure(0, weight=1)
            
            # Title and value row
            header_frame = ctk.CTkFrame(card, fg_color="transparent")
            header_frame.pack(fill="x", padx=12, pady=(12, 6))
            header_frame.grid_columnconfigure(0, weight=1)
            
            title = ctk.CTkLabel(header_frame, text=label, font=ctk.CTkFont(size=12, weight="bold"))
            title.grid(row=0, column=0, sticky="w")
            
            value = ctk.CTkLabel(header_frame, text="—", font=ctk.CTkFont(size=20, weight="bold"), text_color="#4ade80")
            value.grid(row=0, column=1, sticky="e")
            
            self.stat_labels[key] = value
            
            # Description
            desc = ctk.CTkLabel(card, text=description, font=ctk.CTkFont(size=10), text_color="#888888")
            desc.pack(fill="x", padx=12, pady=(0, 8))
        
        # Key metrics display
        metrics_frame = ctk.CTkFrame(scroll, fg_color="#1a1a1a", corner_radius=8)
        metrics_frame.grid(row=3, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
        metrics_frame.grid_columnconfigure(0, weight=1)
        
        metrics_title = ctk.CTkLabel(metrics_frame, text="📊 Key Metrics", font=ctk.CTkFont(size=12, weight="bold"))
        metrics_title.pack(fill="x", padx=12, pady=(12, 8))
        
        # Reduction rate bar
        rate_label = ctk.CTkLabel(metrics_frame, text="Reduction Rate", font=ctk.CTkFont(size=10))
        rate_label.pack(fill="x", padx=12)
        
        self.reduction_bar = ctk.CTkProgressBar(metrics_frame)
        self.reduction_bar.pack(fill="x", padx=12, pady=(4, 2))
        self.reduction_bar.set(0)
        
        self.reduction_text = ctk.CTkLabel(metrics_frame, text="0%", font=ctk.CTkFont(size=10, weight="bold"), text_color="#fbbf24")
        self.reduction_text.pack(fill="x", padx=12, pady=(0, 2))
        
        # Normalized keys indicator
        keys_label = ctk.CTkLabel(metrics_frame, text="Citation Keys Normalized", font=ctk.CTkFont(size=10))
        keys_label.pack(fill="x", padx=12, pady=(8, 2))
        
        self.keys_bar = ctk.CTkProgressBar(metrics_frame)
        self.keys_bar.pack(fill="x", padx=12, pady=(4, 2))
        self.keys_bar.set(0)
        
        self.keys_text = ctk.CTkLabel(metrics_frame, text="0 keys", font=ctk.CTkFont(size=10, weight="bold"), text_color="#60a5fa")
        self.keys_text.pack(fill="x", padx=12, pady=(0, 12))
        
        # Details textbox
        self.results_text = ctk.CTkTextbox(tab, font=ctk.CTkFont(size=12))
        self.results_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def _build_fixes_tab(self):
        """Build fixes side-by-side viewer tab"""
        tab = self.tabview.tab("🛠 Fixes")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=0)
        tab.grid_rowconfigure(2, weight=0)
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_columnconfigure(2, weight=0)

        # Left: file selector and original file
        left_frame = ctk.CTkFrame(tab)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10,5), pady=10)
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        self.fix_file_menu = ctk.CTkOptionMenu(left_frame, values=["No changed files yet"], command=self._show_file_fix)
        self.fix_file_menu.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        self.fix_file_menu.set("No changed files yet")

        self.orig_text = ctk.CTkTextbox(
            left_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none"
        )
        self.orig_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5,10))

        # Right: updated file
        right_frame = ctk.CTkFrame(tab)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5,10), pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        label = ctk.CTkLabel(right_frame, text="Updated (Fixed)", font=ctk.CTkFont(size=14, weight="bold"))
        label.grid(row=0, column=0, padx=10, pady=(10,5), sticky="w")

        self.updated_text = ctk.CTkTextbox(
            right_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none"
        )
        self.updated_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5,10))

        # Shared vertical scrollbar for synchronized scrolling
        self.fixes_scrollbar = ctk.CTkScrollbar(tab, orientation="vertical", command=self._on_fixes_scroll)
        self.fixes_scrollbar.grid(row=0, column=2, sticky="ns", padx=(0, 10), pady=10)

        # Shared horizontal scrollbar for synchronized scrolling
        self.fixes_h_scrollbar = ctk.CTkScrollbar(tab, orientation="horizontal", command=self._on_fixes_xscroll)
        self.fixes_h_scrollbar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(10, 10), pady=(0, 8))

        # Navigation controls
        nav_frame = ctk.CTkFrame(tab, fg_color="transparent")
        nav_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 6))
        nav_frame.grid_columnconfigure(2, weight=1)

        self.prev_change_btn = ctk.CTkButton(
            nav_frame,
            text="◀ Prev Change",
            width=130,
            height=30,
            command=self._jump_prev_changed_line,
            state="disabled"
        )
        self.prev_change_btn.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.next_change_btn = ctk.CTkButton(
            nav_frame,
            text="Next Change ▶",
            width=130,
            height=30,
            command=self._jump_next_changed_line,
            state="disabled"
        )
        self.next_change_btn.grid(row=0, column=1, padx=(0, 8), sticky="w")

        self.normalize_keys_btn = ctk.CTkButton(
            nav_frame,
            text="Normalize All Keys",
            width=160,
            height=30,
            command=self._run_pipeline,
            state="normal"
        )
        self.normalize_keys_btn.grid(row=0, column=2, padx=(0, 8), sticky="w")

        # Visual legend badges for demo clarity
        legend_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
        legend_frame.grid(row=0, column=3, sticky="e")

        self.legend_orig = ctk.CTkLabel(
            legend_frame,
            text=" 🟨 Original Change ",
            fg_color="#ffe08a",
            text_color="#111111",
            corner_radius=6,
            font=ctk.CTkFont(size=11)
        )
        self.legend_orig.grid(row=0, column=0, padx=(0, 6))

        self.legend_fixed = ctk.CTkLabel(
            legend_frame,
            text=" 🟩 Fixed Change ",
            fg_color="#b6f2c7",
            text_color="#111111",
            corner_radius=6,
            font=ctk.CTkFont(size=11)
        )
        self.legend_fixed.grid(row=0, column=1, padx=(0, 6))

        self.legend_marker = ctk.CTkLabel(
            legend_frame,
            text="🔎 >> changed line",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.legend_marker.grid(row=0, column=2)

        # Info label for changed lines
        self.changed_info = ctk.CTkLabel(tab, text="", text_color="gray")
        self.changed_info.grid(row=1, column=0, columnspan=2, sticky="e", padx=20, pady=(0,6))

        # Setup synchronized scrolling bindings
        self._setup_fixes_scroll_sync()

    def _get_text_widget(self, ctk_textbox):
        """Return underlying tkinter Text widget from CTkTextbox."""
        return (
            getattr(ctk_textbox, '_textbox', None)
            or getattr(ctk_textbox, 'textbox', None)
            or getattr(ctk_textbox, 'text', None)
        )

    def _setup_fixes_scroll_sync(self):
        """Configure synchronized scrolling between original and updated panes."""
        tk_orig = self._get_text_widget(self.orig_text)
        tk_upd = self._get_text_widget(self.updated_text)
        if not tk_orig or not tk_upd:
            return

        # Route yscroll updates through handlers so both panes stay aligned.
        tk_orig.configure(yscrollcommand=self._on_orig_yscroll)
        tk_upd.configure(yscrollcommand=self._on_upd_yscroll)
        tk_orig.configure(xscrollcommand=self._on_orig_xscroll)
        tk_upd.configure(xscrollcommand=self._on_upd_xscroll)

        # Mouse wheel sync (Windows/macOS)
        tk_orig.bind('<MouseWheel>', self._on_fixes_mousewheel, add='+')
        tk_upd.bind('<MouseWheel>', self._on_fixes_mousewheel, add='+')
        # Linux wheel events
        tk_orig.bind('<Button-4>', self._on_fixes_mousewheel, add='+')
        tk_orig.bind('<Button-5>', self._on_fixes_mousewheel, add='+')
        tk_upd.bind('<Button-4>', self._on_fixes_mousewheel, add='+')
        tk_upd.bind('<Button-5>', self._on_fixes_mousewheel, add='+')

    def _on_fixes_scroll(self, *args):
        """Scrollbar callback: scroll both panes together."""
        tk_orig = self._get_text_widget(self.orig_text)
        tk_upd = self._get_text_widget(self.updated_text)
        if not tk_orig or not tk_upd:
            return

        self._syncing_scroll = True
        try:
            tk_orig.yview(*args)
            tk_upd.yview(*args)
            first, last = tk_orig.yview()
            self.fixes_scrollbar.set(first, last)
        finally:
            self._syncing_scroll = False

    def _on_orig_yscroll(self, first, last):
        """Original pane scrolled: update scrollbar and sync updated pane."""
        if self._syncing_scroll:
            return
        tk_upd = self._get_text_widget(self.updated_text)
        self._syncing_scroll = True
        try:
            self.fixes_scrollbar.set(first, last)
            if tk_upd:
                tk_upd.yview_moveto(float(first))
        finally:
            self._syncing_scroll = False

    def _on_upd_yscroll(self, first, last):
        """Updated pane scrolled: update scrollbar and sync original pane."""
        if self._syncing_scroll:
            return
        tk_orig = self._get_text_widget(self.orig_text)
        self._syncing_scroll = True
        try:
            self.fixes_scrollbar.set(first, last)
            if tk_orig:
                tk_orig.yview_moveto(float(first))
        finally:
            self._syncing_scroll = False

    def _on_fixes_xscroll(self, *args):
        """Horizontal scrollbar callback: scroll both panes together."""
        tk_orig = self._get_text_widget(self.orig_text)
        tk_upd = self._get_text_widget(self.updated_text)
        if not tk_orig or not tk_upd:
            return

        self._syncing_scroll_x = True
        try:
            tk_orig.xview(*args)
            tk_upd.xview(*args)
            first, last = tk_orig.xview()
            self.fixes_h_scrollbar.set(first, last)
        finally:
            self._syncing_scroll_x = False

    def _on_orig_xscroll(self, first, last):
        """Original pane x-scrolled: sync updated pane and scrollbar."""
        if self._syncing_scroll_x:
            return
        tk_upd = self._get_text_widget(self.updated_text)
        self._syncing_scroll_x = True
        try:
            self.fixes_h_scrollbar.set(first, last)
            if tk_upd:
                tk_upd.xview_moveto(float(first))
        finally:
            self._syncing_scroll_x = False

    def _on_upd_xscroll(self, first, last):
        """Updated pane x-scrolled: sync original pane and scrollbar."""
        if self._syncing_scroll_x:
            return
        tk_orig = self._get_text_widget(self.orig_text)
        self._syncing_scroll_x = True
        try:
            self.fixes_h_scrollbar.set(first, last)
            if tk_orig:
                tk_orig.xview_moveto(float(first))
        finally:
            self._syncing_scroll_x = False

    def _scroll_to_changed_line(self, line_no: int):
        """Scroll both panes to a target line number."""
        tk_orig = self._get_text_widget(self.orig_text)
        tk_upd = self._get_text_widget(self.updated_text)
        idx = f"{line_no}.0"
        try:
            if tk_orig:
                tk_orig.see(idx)
            if tk_upd:
                tk_upd.see(idx)
        except Exception:
            pass

    def _jump_next_changed_line(self):
        """Jump to the next changed line."""
        if not self._current_changed_lines:
            return
        self._current_changed_idx = (self._current_changed_idx + 1) % len(self._current_changed_lines)
        ln = self._current_changed_lines[self._current_changed_idx]
        self._scroll_to_changed_line(ln)
        self.changed_info.configure(
            text=f"Change {self._current_changed_idx + 1}/{len(self._current_changed_lines)} at line {ln}"
        )

    def _jump_prev_changed_line(self):
        """Jump to the previous changed line."""
        if not self._current_changed_lines:
            return
        self._current_changed_idx = (self._current_changed_idx - 1) % len(self._current_changed_lines)
        ln = self._current_changed_lines[self._current_changed_idx]
        self._scroll_to_changed_line(ln)
        self.changed_info.configure(
            text=f"Change {self._current_changed_idx + 1}/{len(self._current_changed_lines)} at line {ln}"
        )

    def _on_fixes_mousewheel(self, event):
        """Mouse wheel handler that scrolls both panes in sync."""
        # Windows / macOS
        if hasattr(event, 'delta') and event.delta:
            units = -int(event.delta / 120) if event.delta % 120 == 0 else (-1 if event.delta > 0 else 1)
        # Linux
        elif getattr(event, 'num', None) == 4:
            units = -1
        elif getattr(event, 'num', None) == 5:
            units = 1
        else:
            units = 0

        if units != 0:
            self._on_fixes_scroll('scroll', units, 'units')
            return 'break'
        
    def _build_duplicates_tab(self):
        """Build duplicates tab with a lightweight, readable group viewer and summary/raw toggle."""
        tab = self.tabview.tab("🔍 Duplicates")
        tab.grid_rowconfigure(5, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            tab,
            text="Duplicate Groups",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#9ca3af",
        )
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        controls.grid_columnconfigure(1, weight=1)

        self.dup_prev_btn = ctk.CTkButton(
            controls,
            text="◀ Prev",
            width=70,
            command=self._show_prev_duplicate_group,
            fg_color="gray25",
            hover_color="gray30",
        )
        self.dup_prev_btn.grid(row=0, column=0, padx=(0, 6), pady=0, sticky="w")

        self.dup_group_menu = ctk.CTkOptionMenu(
            controls,
            values=["No groups"],
            command=self._on_duplicate_group_selected,
            fg_color="gray25",
            button_color="gray30",
        )
        self.dup_group_menu.grid(row=0, column=1, padx=0, pady=0, sticky="ew")
        self.dup_group_menu.set("No groups")

        self.dup_next_btn = ctk.CTkButton(
            controls,
            text="Next ▶",
            width=70,
            command=self._show_next_duplicate_group,
            fg_color="gray25",
            hover_color="gray30",
        )
        self.dup_next_btn.grid(row=0, column=2, padx=(6, 0), pady=0, sticky="e")

        self.dup_summary_label = ctk.CTkLabel(
            controls,
            text="Run pipeline, then open this tab.",
            font=ctk.CTkFont(size=10),
            text_color="#6b7280",
            anchor="w",
        )
        self.dup_summary_label.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        file_controls = ctk.CTkFrame(tab, fg_color="transparent")
        file_controls.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 4))
        file_controls.grid_columnconfigure(1, weight=1)

        self.dup_file_prev_btn = ctk.CTkButton(
            file_controls,
            text="◀ File",
            width=70,
            command=self._show_prev_duplicate_file,
            fg_color="gray25",
            hover_color="gray30",
        )
        self.dup_file_prev_btn.grid(row=0, column=0, padx=(0, 6), pady=0, sticky="w")

        self.dup_file_menu = ctk.CTkOptionMenu(
            file_controls,
            values=["No files"],
            command=self._on_duplicate_file_selected,
            fg_color="gray25",
            button_color="gray30",
        )
        self.dup_file_menu.grid(row=0, column=1, padx=0, pady=0, sticky="ew")
        self.dup_file_menu.set("No files")

        self.dup_file_next_btn = ctk.CTkButton(
            file_controls,
            text="File ▶",
            width=70,
            command=self._show_next_duplicate_file,
            fg_color="gray25",
            hover_color="gray30",
        )
        self.dup_file_next_btn.grid(row=0, column=2, padx=(6, 0), pady=0, sticky="e")

        self.dup_file_label = ctk.CTkLabel(
            tab,
            text="File: -",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#9ca3af",
            anchor="w",
        )
        self.dup_file_label.grid(row=3, column=0, sticky="w", padx=10, pady=(0, 4))

        self.dup_decision_panel = ctk.CTkFrame(tab, fg_color="transparent")
        self.dup_decision_panel.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 4))
        self.dup_decision_panel.grid_columnconfigure((0, 1), weight=1)

        self.dup_keep_box = ctk.CTkTextbox(
            self.dup_decision_panel,
            height=92,
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word",
        )
        self.dup_keep_box.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.dup_drop_box = ctk.CTkTextbox(
            self.dup_decision_panel,
            height=92,
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word",
        )
        self.dup_drop_box.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.duplicates_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="none",
        )
        self.duplicates_text.grid(row=5, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.duplicates_text.insert("1.0", "Run pipeline, then open this tab to view duplicates.\n")

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
        
                Citation Key Normalization:
                The manager regenerates keys into a consistent, informative format:
                firstauthor[-secondauthor]-year-titleword1[-titleword2]

                Examples:
                • smith-2023-advances-ai
                • chen-zhang-2021-machine-learning

                Rules:
                • Uses up to first 2 author surnames
                • Uses a 4-digit year when available
                • Uses up to first 2 meaningful title words
                • Ensures uniqueness with suffixes when needed
                    (e.g., smith-2023-advances-ai-a)

                Why it helps:
                • Keys become predictable and readable
                • Easier to cite and search across files
                • Better consistency after merging bibliographies
        
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
        score = int(value)
        self.threshold_label.configure(text=f"{score}%")
        if score < 70:
            hint = "Aggressive (more duplicates flagged)"
        elif score < 90:
            hint = "Balanced (recommended)"
        else:
            hint = "Strict (fewer false positives)"
        self.threshold_hint.configure(text=hint)

    def _set_status(self, text: str, color: str = "#3b8ed0"):
        """Update sidebar status text and color."""
        self._ui_call(self._status_text.set, text)
        self._ui_call(self.status_label.configure, text_color=color)

    def _use_test_data(self):
        """Quick-fill test_data directory for demos."""
        candidate = Path(self.root.winfo_toplevel().tk.call('pwd')) / "test_data"
        if candidate.exists():
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, str(candidate))
            self._log_message(f"ℹ️ Using demo folder: {candidate}")
        else:
            self._log_message("⚠️ test_data folder not found in current project")

    def _clear_for_next_run(self):
        """Clear logs/results quickly for a fresh demo run."""
        self.log_text.delete("1.0", "end")
        self.results_text.delete("1.0", "end")
        self.orig_text.delete("1.0", "end")
        self.updated_text.delete("1.0", "end")
        self.changed_info.configure(text="")
        self._current_changed_lines = []
        self._current_changed_idx = -1
        self.prev_change_btn.configure(state="disabled")
        self.next_change_btn.configure(state="disabled")
        self._set_status("Ready", "#3b8ed0")
        
    def _browse_directory(self):
        """Open browser for ZIP file or directory."""
        # First let user pick a ZIP file quickly.
        zip_path = filedialog.askopenfilename(
            title="Select Overleaf ZIP (or cancel to pick a folder)",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        )
        if zip_path:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, zip_path)
            return

        # Fallback to folder selection.
        directory = filedialog.askdirectory(title="Select Directory with .bib files")
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)
            
    def _change_appearance(self, mode: str):
        """Change appearance mode"""
        ctk.set_appearance_mode(mode.lower())
        
    def _log_message(self, message: str, color: str = "white"):
        """Queue log messages and flush in small batches to reduce UI redraws."""
        if self._defer_log_render:
            with self._log_lock:
                self._deferred_logs.append(message)
            return

        def _enqueue():
            self._log_buffer.append(message)
            if self._log_flush_job is None:
                # Batch frequent updates into one render pass.
                self._log_flush_job = self.root.after(80, self._flush_log_buffer)

        self._ui_call(_enqueue)

    def _flush_log_buffer(self):
        """Flush queued log messages on the UI thread."""
        self._log_flush_job = None
        if not self._log_buffer:
            return

        chunk = "\n".join(self._log_buffer) + "\n"
        self._log_buffer.clear()
        self.log_text.insert("end", chunk)

        # Keep log size manageable - keep only last 150 lines to prevent slowdown
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        while line_count > 150:
            self.log_text.delete("1.0", "2.0")
            line_count -= 1

        self.log_text.see("end")

    def _flush_deferred_logs(self):
        """Flush all deferred pipeline logs at once to avoid live repaint flashing."""
        with self._log_lock:
            if not self._deferred_logs:
                return
            pending = list(self._deferred_logs)
            self._deferred_logs.clear()

        def _write_bulk():
            chunk = "\n".join(pending) + "\n"
            self.log_text.insert("end", chunk)
            line_count = int(self.log_text.index("end-1c").split(".")[0])
            while line_count > 300:
                self.log_text.delete("1.0", "2.0")
                line_count -= 1
            self.log_text.see("end")

        self._ui_call(_write_bulk)

    def _build_output_paths_text(self) -> str:
        """Build a human-readable block of output paths."""
        lines = []
        if self._last_master_path:
            lines.append(f"Master bibliography:\n{self._last_master_path}\n")
        if self._last_cleaned_zip:
            lines.append(f"Cleaned ZIP:\n{self._last_cleaned_zip}\n")
        if self.report_path:
            lines.append(f"Report:\n{self.report_path}\n")
        return "\n".join(lines).strip()

    def _copy_output_paths_to_clipboard(self):
        """Copy latest output paths to system clipboard."""
        text = self._build_output_paths_text()
        if not text:
            return False
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()  # keep clipboard after app closes
            return True
        except Exception:
            return False
        
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
        self.report_path = None
        self._ui_call(self.view_report_btn.configure, state="disabled")
        
        # Disable run button
        self.run_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.processing = True
        self._set_status("Running...", "#f59e0b")

        # Minimize live UI churn while processing.
        self._defer_log_render = True
        with self._log_lock:
            self._deferred_logs.clear()

        # Capture UI-dependent options before entering worker thread.
        options = {
            'directory': directory,
            'threshold': float(self.threshold_var.get()),
            'push_back': bool(self.push_var.get()),
            'generate_report': bool(self.report_var.get()),
        }
        
        # Run in thread
        thread = threading.Thread(target=self._pipeline_worker, args=(options,), daemon=True)
        thread.start()
        
    def _pipeline_worker(self, options: dict[str, Any]):
        """Worker thread for pipeline execution"""
        temp_dir_obj = None
        zip_mode = False
        zip_input_path = None
        cleaned_zip = None
        try:
            # Reset step states and timers for fresh run
            for step_name in self.step_cards:
                self.step_timers[step_name] = 0.0
                self._step_state[step_name] = "pending"
                card_data = self.step_cards[step_name]
                card_data['start_time'] = None
            self._pending_step_text = "Initializing pipeline..."
            self._pending_step_color = "#d1d5db"
            self._ui_call(self._apply_pipeline_snapshot)
            
            directory = options['directory']
            threshold = options['threshold']
            push_back = options['push_back']
            generate_report = options['generate_report']

            input_path = Path(directory)
            working_directory = directory

            # ZIP mode: extract first, process extracted folder, then re-zip.
            if input_path.is_file() and input_path.suffix.lower() == ".zip":
                zip_mode = True
                zip_input_path = input_path
                self._log_message("📦 ZIP mode: Extracting archive...")
                temp_dir_obj = tempfile.TemporaryDirectory()
                with zipfile.ZipFile(str(input_path), 'r') as zf:
                    zf.extractall(temp_dir_obj.name)
                working_directory = temp_dir_obj.name
                self._log_message("✓ Archive extracted to temp workspace")
            
            self._log_message("="*60)
            self._log_message("🚀 Starting Bibliography Processing Pipeline")
            self._log_message("="*60)
            
            # Initialize manager
            self.manager = BibliographyManager(working_directory)
            
            # Step 1: Crawl
            if not self.processing:
                self._log_message("⚠️ Pipeline cancelled by user.")
                return
            self._mark_step_running("Crawl", "Scanning .bib files...")
            self._log_message("📁 Crawling for .bib files...")
            num_files, num_entries = self.manager.crawl_and_collect()
            self._log_message(f"✓ Found {num_files} file(s) with {num_entries} entries")
            self._mark_step_complete("Crawl")
            
            if num_entries == 0:
                self._log_message("\n⚠️ No entries found!")
                return
            
            # Step 2: Find duplicates
            if not self.processing:
                self._log_message("⚠️ Pipeline cancelled by user.")
                return
            self._mark_step_running("Duplicates", f"Comparing entries (threshold: {threshold}%)...")
            self._log_message(f"🔍 Finding duplicates (threshold: {threshold}%)...")
            num_groups = self.manager.find_duplicates(threshold=threshold)
            self._log_message(f"✓ Found {num_groups} duplicate group(s)")
            self._mark_step_complete("Duplicates")
            
            # Step 3: Remove duplicates
            if not self.processing:
                self._log_message("⚠️ Pipeline cancelled by user.")
                return
            self._mark_step_running("Remove", "Removing duplicate entries...")
            self._log_message("🗑️ Removing duplicates...")
            self.manager.remove_duplicates()
            self._log_message(f"✓ Removed {self.manager.report_data['duplicates_removed']} entries")
            self._mark_step_complete("Remove")
            
            # Step 4: Fix keys
            if not self.processing:
                self._log_message("⚠️ Pipeline cancelled by user.")
                return
            self._mark_step_running("Keys", "Normalizing citation keys...")
            self._log_message("🔑 Normalizing citation keys...")
            # Pass user rule to backend
            rule = self.citekey_rule_var.get()
            custom = self.citekey_custom_var.get()
            if rule == "custom":
                citekey_format = custom
            elif rule == "author-year-title":
                citekey_format = "{author}-{year}-{title}"
            elif rule == "author-year-titleword":
                citekey_format = "{author}-{year}-{titleword}"
            elif rule == "author-title":
                citekey_format = "{author}-{title}"
            elif rule == "professor-style":
                citekey_format = "{authorstem}{year}"
            elif rule == "professor-strict":
                citekey_format = "{authorstrict}{year}"
            elif rule == "author-et-al-year":
                citekey_format = "{authoretal}{year}"
            elif rule == "lastname-only-year":
                citekey_format = "{lastname}{year}"
            elif rule == "firstauthor-year-titleword":
                citekey_format = "{author}{year}{titleword}"
            elif rule == "compact-initials":
                citekey_format = "{authorinitials}{year}"
            elif rule == "numeric":
                citekey_format = "ref{numeric}"
            else:
                citekey_format = "{author}-{year}-{title}"
            self.manager.fix_citation_keys(citekey_format)
            self._log_message(f"✓ Normalized {len(self.manager.report_data['keys_changed'])} key(s)")
            self._mark_step_complete("Keys")
            
            # Create master
            self._log_message("📋 Creating master bibliography...")
            master_path = self.manager.create_master_bibliography()
            self._log_message(f"✓ Master file generated")
            self._last_master_path = str(master_path)
            
            # Push back if requested
            if push_back:
                if not self.processing:
                    self._log_message("⚠️ Pipeline cancelled by user.")
                    return
                self._log_message("\n📤 Pushing master.bib to folders...")
                self.manager.push_to_folders(master_path)
                self._log_message("✓ Distribution complete")
            
            # Generate report
            self.manager.report_data['end_time'] = self.manager.report_data.get('end_time') or __import__('datetime').datetime.now()
            if generate_report:
                self._log_message("📊 Generating HTML report...")
                self.report_path = self.manager.generate_html_report()
                self._log_message("✓ Report generated")
                self._ui_call(self.view_report_btn.configure, state="normal")

            # If input was ZIP, package processed files into a new ZIP and copy report outside temp dir.
            if zip_mode and zip_input_path is not None:
                cleaned_zip = zip_input_path.with_name(f"{zip_input_path.stem}_cleaned.zip")
                with zipfile.ZipFile(str(cleaned_zip), 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                    for root, _, files in os.walk(working_directory):
                        for name in files:
                            file_path = Path(root) / name
                            arcname = str(file_path.relative_to(working_directory))
                            zf.write(str(file_path), arcname)
                self._log_message(f"✓ Cleaned ZIP created: {cleaned_zip}")
                self._last_cleaned_zip = str(cleaned_zip)

                # Copy report to same folder as source ZIP so it persists after temp cleanup.
                if self.report_path and Path(self.report_path).exists():
                    report_src = Path(self.report_path)
                    report_dest = zip_input_path.with_name(f"{zip_input_path.stem}_{report_src.name}")
                    shutil.copy2(str(report_src), str(report_dest))
                    self.report_path = str(report_dest)
                    self._log_message(f"✓ Report copied next to ZIP: {report_dest}")

            # Final report availability check (after possible ZIP copy)
            if self.report_path and Path(self.report_path).exists():
                self._ui_call(self.view_report_btn.configure, state="normal")
            else:
                self._ui_call(self.view_report_btn.configure, state="disabled")
                self._log_message("⚠️ Report file not found at final path; View Report disabled.")

            # Populate fixes tab if file changes recorded
            file_changes = self.manager.report_data.get('file_changes', {})
            if file_changes:
                try:
                    files = list(file_changes.keys())
                    # Update option menu values on main thread
                    def _update_values():
                        self.fix_file_menu.configure(values=files)
                        if files:
                            self.fix_file_menu.set(files[0])
                            self._show_file_fix(files[0])
                    self.root.after(0, _update_values)
                except Exception:
                    pass
            
            
            # Update results
            self._ui_call(self._update_results)
            # Defer heavy duplicates rendering until user opens the Duplicates tab.
            self._pending_duplicates_refresh = True
            
            # Update current step to show completion
            self._pending_step_text = "✅ All steps completed! Results available below."
            self._pending_step_color = "#10b981"
            self._ui_call(self._apply_pipeline_snapshot)
            
            self._log_message("")
            self._log_message("="*60)
            self._log_message("✨ Pipeline completed successfully!")
            self._log_message("="*60)
            self._set_status("Completed", "#22c55e")

            # Show completion popup with output locations (on UI thread)
            def _show_done_popup():
                outputs = self._build_output_paths_text()
                if outputs:
                    msg = "Pipeline completed successfully!\n\n" + outputs + "\n\nCopy these paths to clipboard?"
                    copy_now = messagebox.askyesno("BibTeX Manager", msg)
                    if copy_now:
                        ok = self._copy_output_paths_to_clipboard()
                        if ok:
                            messagebox.showinfo("BibTeX Manager", "Output paths copied to clipboard.")
                        else:
                            messagebox.showwarning("BibTeX Manager", "Could not copy to clipboard.")
                else:
                    messagebox.showinfo("BibTeX Manager", "Pipeline completed successfully!")

            self._ui_call(_show_done_popup)
            
        except Exception as e:
            error_msg = str(e)
            self._log_message(f"\n❌ Error: {error_msg}")
            import traceback
            self._log_message(traceback.format_exc())
            self._set_status("Error", "#ef4444")
            
            # Mark current step as error
            self._pending_step_text = f"❌ Pipeline failed: {error_msg}"
            self._pending_step_color = "#ef4444"
            self._ui_call(self._apply_pipeline_snapshot)
            
        finally:
            if temp_dir_obj is not None:
                try:
                    temp_dir_obj.cleanup()
                except Exception:
                    pass

            # Render buffered logs once processing is done.
            self._defer_log_render = False
            self._flush_deferred_logs()

            self.processing = False
            self._ui_call(self.run_btn.configure, state="normal")
            self._ui_call(self.cancel_btn.configure, state="disabled")
            if self._status_text.get() == "Running...":
                self._set_status("Ready", "#3b8ed0")
            
    def _cancel_pipeline(self):
        """Cancel pipeline execution"""
        # Simple cancellation (thread will finish current operation)
        self.processing = False
        self._log_message("\n⚠️ Cancellation requested...")
        self._set_status("Cancelling...", "#f59e0b")
        
    def _update_results(self):
        """Update results tab with statistics and progress bars"""
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
        
        # Update progress bars with visual feedback
        reduction_rate = (data['duplicates_removed'] / max(data['initial_entries'], 1)) * 100
        self.reduction_bar.set(reduction_rate / 100.0)
        self.reduction_text.configure(text=f"{reduction_rate:.1f}% reduction")
        
        # Normalized keys progress (max reasonable is 500 keys)
        keys_count = len(data['keys_changed'])
        max_keys = max(500, keys_count + 1)
        self.keys_bar.set(min(keys_count / max_keys, 1.0))
        self.keys_text.configure(text=f"{keys_count} keys normalized")
        
        # Detailed summary
        lines = []
        lines.append("Processing Summary")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Files Processed: {data['files_found']}")
        lines.append(f"Initial Entries: {data['initial_entries']}")
        lines.append(f"Duplicate Groups: {len(data['duplicate_groups'])}")
        lines.append(f"Entries Removed: {data['duplicates_removed']}")
        lines.append(f"Final Entries: {data['final_entries']}")
        lines.append("")
        lines.append(f"Reduction Rate: {reduction_rate:.1f}%")
        lines.append(f"Keys Normalized: {len(data['keys_changed'])}")
        if data.get('tex_citation_updates', 0):
            lines.append(f"LaTeX Citations Updated: {data['tex_citation_updates']}")
            lines.append(f".tex Files Updated: {data.get('tex_files_updated', 0)}")
        lines.append("")
        lines.append("=" * 50)
        lines.append("✓ All original files backed up with timestamps")
        lines.append("✓ Master bibliography created")
        lines.append("✓ No data loss - backups available for restore")

        summary = "\n".join(lines)
        
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", summary)
        
    def _mark_step_complete(self, step_name: str):
        """Mark a pipeline step as complete with timing"""
        if step_name in self.step_cards:
            card_data = self.step_cards[step_name]
            self._step_state[step_name] = "complete"
            # Calculate and display time taken
            if card_data['start_time']:
                import time
                elapsed = time.time() - card_data['start_time']
                self.step_timers[step_name] = elapsed
            if not self._defer_log_render:
                self._ui_call(self._apply_pipeline_snapshot)
    
    def _mark_step_running(self, step_name: str, detail_text: str = ""):
        """Mark a pipeline step as currently running"""
        if step_name in self.step_cards:
            card_data = self.step_cards[step_name]
            import time
            card_data['start_time'] = time.time()
            self._step_state[step_name] = "running"

            # Update current step text
            detail_msg = detail_text if detail_text else f"Processing {step_name}..."
            self._pending_step_text = detail_msg
            self._pending_step_color = "#d1d5db"
            if not self._defer_log_render:
                self._ui_call(self._apply_pipeline_snapshot)
    
    def _mark_step_error(self, step_name: str, error_msg: str = ""):
        """Mark a pipeline step as failed"""
        if step_name in self.step_cards:
            self._step_state[step_name] = "error"
            error_detail = error_msg if error_msg else "An error occurred"
            self._pending_step_text = f"❌ {error_detail}"
            self._pending_step_color = "#ef4444"
            if not self._defer_log_render:
                self._ui_call(self._apply_pipeline_snapshot)

    def _apply_pipeline_snapshot(self):
        """Apply all pipeline step statuses in one UI pass to avoid flashing."""
        state_style = {
            "pending": ("⌚ Pending", "#9ca3af"),
            "running": ("⏳ Running", "#fbbf24"),
            "complete": ("✓ Complete", "#34d399"),
            "error": ("✗ Error", "#f87171"),
        }

        for step_name, card_data in self.step_cards.items():
            state = self._step_state.get(step_name, "pending")
            status_text, status_color = state_style.get(state, state_style["pending"])
            card_data['status'].configure(text=status_text, fg_color="transparent", text_color=status_color)
            card_data['timer'].configure(text=f"{self.step_timers.get(step_name, 0.0):.1f}s")

        self.current_step_label.configure(
            text=self._pending_step_text,
            text_color=self._pending_step_color,
        )
        
    def _update_duplicates(self):
        """Update duplicates tab using a single-group text render for speed and readability."""
        if not self.manager or not hasattr(self, 'duplicates_text'):
            return

        groups = self.manager.report_data.get('duplicate_groups', [])
        self._duplicate_groups_cache = groups

        if not groups:
            self.dup_group_menu.configure(values=["No groups"])
            self.dup_group_menu.set("No groups")
            self.dup_prev_btn.configure(state="disabled")
            self.dup_next_btn.configure(state="disabled")
            self.dup_summary_label.configure(text="No duplicates found. Your bibliography is clean.")
            self.duplicates_text.delete("1.0", "end")
            self.duplicates_text.insert("1.0", "No duplicates found. Your bibliography is clean.\n")
            return

        labels = []
        for idx, group_data in enumerate(groups, 1):
            similarity = group_data.get('similarity', 'N/A')
            entries = group_data.get('entries', [])
            labels.append(f"Group {idx:03d} | {similarity}% | {len(entries)} entries")

        self.dup_group_menu.configure(values=labels)
        self._selected_duplicate_group = min(self._selected_duplicate_group, len(groups) - 1)
        self.dup_group_menu.set(labels[self._selected_duplicate_group])
        self.dup_prev_btn.configure(state="normal")
        self.dup_next_btn.configure(state="normal")
        self._selected_duplicate_file = 0
        self._render_selected_duplicate_group()

    def _on_duplicate_group_selected(self, selection: str):
        """Handle dropdown selection for duplicate group."""
        if not self._duplicate_groups_cache:
            return
        try:
            idx_text = selection.split("|")[0].strip().replace("Group", "").strip()
            idx = int(idx_text) - 1
        except Exception:
            return

        if 0 <= idx < len(self._duplicate_groups_cache):
            self._selected_duplicate_group = idx
            self._render_selected_duplicate_group()

    def _show_prev_duplicate_group(self):
        """Navigate to previous duplicate group."""
        if not self._duplicate_groups_cache:
            return
        self._selected_duplicate_group = (self._selected_duplicate_group - 1) % len(self._duplicate_groups_cache)
        self._sync_duplicate_selection_and_render()

    def _show_next_duplicate_group(self):
        """Navigate to next duplicate group."""
        if not self._duplicate_groups_cache:
            return
        self._selected_duplicate_group = (self._selected_duplicate_group + 1) % len(self._duplicate_groups_cache)
        self._sync_duplicate_selection_and_render()

    def _on_duplicate_file_selected(self, selection: str):
        if not self._duplicate_file_order:
            return
        try:
            idx = self._duplicate_file_order.index(selection)
        except ValueError:
            return
        self._selected_duplicate_file = idx
        self._render_selected_duplicate_group()

    def _show_prev_duplicate_file(self):
        if not self._duplicate_file_order:
            return
        self._selected_duplicate_file = (self._selected_duplicate_file - 1) % len(self._duplicate_file_order)
        self._sync_duplicate_file_selection_and_render()

    def _show_next_duplicate_file(self):
        if not self._duplicate_file_order:
            return
        self._selected_duplicate_file = (self._selected_duplicate_file + 1) % len(self._duplicate_file_order)
        self._sync_duplicate_file_selection_and_render()

    def _sync_duplicate_file_selection_and_render(self):
        if not self._duplicate_file_order:
            return
        self.dup_file_menu.set(self._duplicate_file_order[self._selected_duplicate_file])
        self._render_selected_duplicate_group()

    def _show_prev_duplicate_highlight(self):
        if not self._duplicate_highlight_positions:
            return
        self._selected_duplicate_highlight = (self._selected_duplicate_highlight - 1) % len(self._duplicate_highlight_positions)
        self._scroll_to_duplicate_highlight()

    def _show_next_duplicate_highlight(self):
        if not self._duplicate_highlight_positions:
            return
        self._selected_duplicate_highlight = (self._selected_duplicate_highlight + 1) % len(self._duplicate_highlight_positions)
        self._scroll_to_duplicate_highlight()

    def _scroll_to_duplicate_highlight(self):
        if not self._duplicate_highlight_positions:
            return
        line_no, status = self._duplicate_highlight_positions[self._selected_duplicate_highlight]
        status_text = "KEEP" if status == 'kept' else "DROP"
        self.dup_file_label.configure(
            text=f"File: {self._current_duplicate_display_name} | Active: {status_text} line {line_no}"
        )
        tk_text = (
            getattr(self.duplicates_text, '_textbox', None)
            or getattr(self.duplicates_text, 'textbox', None)
            or getattr(self.duplicates_text, 'text', None)
        )
        if tk_text is not None:
            try:
                tk_text.see(f"{line_no}.0")
                tk_text.mark_set("insert", f"{line_no}.0")
            except Exception:
                pass

    def _sync_duplicate_selection_and_render(self):
        """Sync option menu label with selected group and re-render."""
        if not self._duplicate_groups_cache:
            return
        group = self._duplicate_groups_cache[self._selected_duplicate_group]
        similarity = group.get('similarity', 'N/A')
        entries = group.get('entries', [])
        label = f"Group {self._selected_duplicate_group + 1:03d} | {similarity}% | {len(entries)} entries"
        self.dup_group_menu.set(label)
        self._render_selected_duplicate_group()

    def _render_selected_duplicate_group(self):
        """Render the full file for the selected duplicate group, highlight KEEP/DROP lines, and allow navigation."""
        if not self._duplicate_groups_cache:
            return

        group_data = self._duplicate_groups_cache[self._selected_duplicate_group]
        entries = group_data.get('entries', [])
        similarity = group_data.get('similarity', 'N/A')

        self.dup_summary_label.configure(
            text=(
                f"Group {self._selected_duplicate_group + 1} of {len(self._duplicate_groups_cache)}"
                f" | Similarity: {similarity}% | Entries: {len(entries)}"
            )
        )

        file_map = {}
        file_order = []
        for entry in entries:
            src = entry.get('_source_file')
            start_line = entry.get('_entry_start_line') or entry.get('_line_number')
            end_line = entry.get('_entry_end_line') or start_line
            status = entry.get('_status')
            if src and start_line:
                if src not in file_map:
                    file_order.append(src)
                    file_map[src] = []
                file_map[src].append(entry)

        if not file_order:
            self._duplicate_file_order = []
            self.dup_file_menu.configure(values=["No files"])
            self.dup_file_menu.set("No files")
            self.dup_file_prev_btn.configure(state="disabled")
            self.dup_file_next_btn.configure(state="disabled")
            self.dup_file_label.configure(text="File: -")
            self.duplicates_text.delete("1.0", "end")
            self.duplicates_text.insert("1.0", "No file data for this group.")
            return

        source_files = self.manager.report_data.get('source_files', {}) if self.manager else {}
        self._duplicate_file_order = []
        for src in file_order:
            cached_source = source_files.get(src, {}) if isinstance(source_files, dict) else {}
            display_name = cached_source.get('relative_path', Path(src).name)
            self._duplicate_file_order.append(display_name)

        self.dup_file_menu.configure(values=self._duplicate_file_order)
        self.dup_file_prev_btn.configure(state="normal" if len(self._duplicate_file_order) > 1 else "disabled")
        self.dup_file_next_btn.configure(state="normal" if len(self._duplicate_file_order) > 1 else "disabled")
        self._selected_duplicate_file = min(self._selected_duplicate_file, len(self._duplicate_file_order) - 1)
        selected_display_name = self._duplicate_file_order[self._selected_duplicate_file]
        self.dup_file_menu.set(selected_display_name)

        selected_src = file_order[self._selected_duplicate_file]
        cached_source = source_files.get(selected_src, {}) if isinstance(source_files, dict) else {}
        file_text = cached_source.get('text')
        display_name = cached_source.get('relative_path', Path(selected_src).name)
        self._current_duplicate_display_name = display_name
        self.dup_file_label.configure(text=f"File: {display_name}")

        if file_text is None:
            try:
                with open(selected_src, encoding='utf-8') as f:
                    file_text = f.read()
            except Exception as e:
                self.duplicates_text.delete("1.0", "end")
                self.duplicates_text.insert("1.0", f"Could not read file: {display_name}\n{e}")
                return

        selected_entries = file_map[selected_src]
        display_lines = [f"File: {display_name}", "=" * 90]
        highlight_ranges = []
        self._duplicate_highlight_positions = []
        keep_entries = [(idx + 1, entry) for idx, entry in enumerate(entries) if entry.get('_status') == 'kept']
        drop_entries = [(idx + 1, entry) for idx, entry in enumerate(entries) if entry.get('_status') != 'kept']

        keep_lines = ["MASTER COPY (kept)", "", "One canonical record from this duplicate group is kept in the cleaned bibliography.", ""]
        drop_lines = ["DUPLICATE COPY (removed)", "", "This record is removed because it belongs to the same duplicate group as the kept record.", ""]

        def _entry_summary(record_number, entry):
            line_no = entry.get('_line_number', 'N/A')
            end_line = entry.get('_entry_end_line', line_no)
            file_name = entry.get('_source_file_display') or Path(entry.get('_source_file', '')).name
            author = str(entry.get('author', 'Unknown')).replace('{', '').replace('}', '')
            year = str(entry.get('year', 'N/A'))
            title = str(entry.get('title', 'No title')).replace('{', '').replace('}', '')
            key = str(entry.get('ID', 'unknown'))
            return f"record {record_number} | lines {line_no}-{end_line} | {file_name} | {author} ({year}) | {title} | key: {key}"

        for entry in selected_entries:
            start_line = entry.get('_entry_start_line') or entry.get('_line_number')
            end_line = entry.get('_entry_end_line') or start_line
            status = entry.get('_status')
            if not isinstance(start_line, int) or not isinstance(end_line, int):
                continue
            marker = "[KEEP]" if status == 'kept' else "[DROP]"
            text_line_no = len(display_lines) + 1
            highlight_ranges.extend((line_no, status) for line_no in range(text_line_no, text_line_no + (end_line - start_line + 1)))
            self._duplicate_highlight_positions.append((text_line_no, status))

            entry_text = entry.get('_entry_text') or ""
            if not entry_text:
                block_lines = file_text.splitlines()[start_line - 1:end_line]
                entry_text = "\n".join(block_lines)

            display_lines.append(f"{start_line:4d} {marker:7} | {entry_text.splitlines()[0].rstrip()}")
            for offset, block_line in enumerate(entry_text.splitlines()[1:], start=1):
                display_lines.append(f"{start_line + offset:4d} {'':7} | {block_line.rstrip()}")
            display_lines.append("")

        if keep_entries:
            record_number, keep_entry = keep_entries[0]
            keep_fields = keep_entry.get('_merge_field_count', 'N/A')
            keep_lines.append(f"Kept entry: {_entry_summary(record_number, keep_entry)}")
            if len(keep_entries) > 1:
                keep_lines.append(f"Additional kept entries: {len(keep_entries) - 1}")
            keep_lines.append("Reason: deduplication keeps one representative record per duplicate group.")
            keep_lines.append(f"Completeness score: {keep_fields} non-empty fields (highest in this group).")

            merged_field_names = []
            for _, drop_entry in drop_entries:
                merged_field_names.extend(drop_entry.get('_merged_into_master_fields', []))
            merged_field_names = sorted(set(merged_field_names))
            if merged_field_names:
                keep_lines.append("Fields merged from removed copies: " + ", ".join(merged_field_names))
            else:
                keep_lines.append("Fields merged from removed copies: none (kept entry already had all populated fields).")

            keep_text = keep_entry.get('_entry_text') or ""
            if keep_text:
                keep_lines.append("")
                keep_lines.append("Entry block:")
                keep_lines.append(keep_text.rstrip())
        else:
            keep_lines.append("No kept entry was recorded for this group.")

        if drop_entries:
            for record_number, drop_entry in drop_entries:
                drop_fields = drop_entry.get('_merge_field_count', 'N/A')
                drop_lines.append(_entry_summary(record_number, drop_entry))
                drop_lines.append(f"Completeness score: {drop_fields} non-empty fields")
                contributed = drop_entry.get('_merged_into_master_fields', [])
                if contributed:
                    drop_lines.append("Contributes missing fields to kept record: " + ", ".join(contributed))
                else:
                    drop_lines.append("Contributes missing fields to kept record: none")
                drop_text = drop_entry.get('_entry_text') or ""
                if drop_text:
                    drop_lines.append("Entry block:")
                    drop_lines.append(drop_text.rstrip())
                    drop_lines.append("")
            drop_lines.append("")
            drop_lines.append(f"Reason: this whole BibTeX entry block is removed because it duplicates the master copy (similarity {similarity}%).")
            drop_lines.append("Note: identical text is expected here because the duplicate entry matches the kept one.")
        else:
            drop_lines.append("No removed entry was recorded for this group.")

        self.duplicates_text.delete("1.0", "end")
        self.duplicates_text.insert("1.0", "\n".join(display_lines))
        self.dup_keep_box.delete("1.0", "end")
        self.dup_keep_box.insert("1.0", "\n".join(keep_lines))
        self.dup_drop_box.delete("1.0", "end")
        self.dup_drop_box.insert("1.0", "\n".join(drop_lines))

        try:
            tk_text = (
                getattr(self.duplicates_text, '_textbox', None)
                or getattr(self.duplicates_text, 'textbox', None)
                or getattr(self.duplicates_text, 'text', None)
            )
            if tk_text is None:
                return
            for tag in ('hl_keep', 'hl_drop'):
                try:
                    tk_text.tag_delete(tag)
                except Exception:
                    pass
            tk_text.tag_configure('hl_keep', background='#b6f2c7', foreground='#111111')
            tk_text.tag_configure('hl_drop', background='#ffb3b3', foreground='#111111')
            seen_lines = set()
            for line_no, status in highlight_ranges:
                if line_no in seen_lines:
                    continue
                seen_lines.add(line_no)
                start = f"{line_no}.0"
                end = f"{line_no}.end"
                if status == 'kept':
                    tk_text.tag_add('hl_keep', start, end)
                else:
                    tk_text.tag_add('hl_drop', start, end)
        except Exception:
            pass

        if self._duplicate_highlight_positions:
            self._selected_duplicate_highlight = min(self._selected_duplicate_highlight, len(self._duplicate_highlight_positions) - 1)
            self._scroll_to_duplicate_highlight()

    def _show_file_fix(self, selection: str):
        """Display original and updated contents for selected file, marking changed lines."""
        if not self.manager:
            return

        file_changes = self.manager.report_data.get('file_changes', {})
        if isinstance(selection, str) and selection in file_changes:
            info = file_changes[selection]
        else:
            # selection may be the widget itself calling without arg
            sel = self.fix_file_menu.get() if hasattr(self.fix_file_menu, 'get') else None
            if not sel or sel not in file_changes:
                return
            info = file_changes[sel]
            selection = sel

        orig = info.get('original', '')
        upd = info.get('updated', '')
        changed = info.get('changed_lines', [])

        # Build IDE-style indexed lines with explicit markers.
        def _indexed_view(text: str, changes):
            rows = text.splitlines()
            out = []
            for i, line in enumerate(rows, start=1):
                marker = ">>" if i in changes else "  "
                out.append(f"{i:4d} {marker} | {line}")
            return "\n".join(out)

        orig_indexed = _indexed_view(orig, changed)
        upd_indexed = _indexed_view(upd, changed)

        # Insert plain text into CTkTextboxes
        self.orig_text.delete('1.0', 'end')
        self.updated_text.delete('1.0', 'end')
        self.orig_text.insert('1.0', orig_indexed)
        self.updated_text.insert('1.0', upd_indexed)

        # Apply colored highlighting to changed lines using underlying tkinter Text
        try:
            tk_orig = (
                getattr(self.orig_text, '_textbox', None)
                or getattr(self.orig_text, 'textbox', None)
                or getattr(self.orig_text, 'text', None)
            )
            tk_upd = (
                getattr(self.updated_text, '_textbox', None)
                or getattr(self.updated_text, 'textbox', None)
                or getattr(self.updated_text, 'text', None)
            )

            # Remove previous tags
            if tk_orig:
                for tag in ('hl_changed',):
                    try:
                        tk_orig.tag_delete(tag)
                    except Exception:
                        pass
                tk_orig.tag_configure('hl_changed', background='#ffe08a', foreground='#111111')  # strong yellow

            if tk_upd:
                for tag in ('hl_changed_upd',):
                    try:
                        tk_upd.tag_delete(tag)
                    except Exception:
                        pass
                tk_upd.tag_configure('hl_changed_upd', background='#b6f2c7', foreground='#111111')  # strong green

            # Add tags to each changed line (1-based indices)
            for ln in changed:
                start = f"{ln}.0"
                end = f"{ln}.end"
                try:
                    if tk_orig:
                        tk_orig.tag_add('hl_changed', start, end)
                    if tk_upd:
                        tk_upd.tag_add('hl_changed_upd', start, end)
                except Exception:
                    # If line index out of range, skip
                    continue
        except Exception:
            # Silently ignore highlighting errors
            pass

        # Show summary of changed lines
        if changed:
            display = changed[:20]
            suffix = ' ...' if len(changed) > 20 else ''
            self.changed_info.configure(text=f"Changed lines ({len(changed)}): {display}{suffix}")
            self._current_changed_lines = sorted(changed)
            self._current_changed_idx = 0
            self.prev_change_btn.configure(state="normal")
            self.next_change_btn.configure(state="normal")
            self._scroll_to_changed_line(self._current_changed_lines[0])
        else:
            self.changed_info.configure(text="No inline changes recorded.")
            self._current_changed_lines = []
            self._current_changed_idx = -1
            self.prev_change_btn.configure(state="disabled")
            self.next_change_btn.configure(state="disabled")
                
    def _view_report(self):
        """Open HTML report in browser"""
        if not (self.report_path and Path(self.report_path).exists()):
            self._log_message("❌ No report available")
            return

        # Prefer an embedded native window using pywebview if available
        try:
            webview = importlib.import_module('webview')

            def _open_webview():
                try:
                    webview.create_window('BibTeX Report', f'file:///{self.report_path}', width=1000, height=800)
                    webview.start()
                except Exception:
                    # If webview fails, fall back to system browser
                    webbrowser.open(f"file:///{self.report_path}")

            threading.Thread(target=_open_webview, daemon=True).start()
        except Exception:
            # Fallback: open in default system browser
            webbrowser.open(f"file:///{self.report_path}")
            
    def run(self):
        """Start the GUI"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = ModernBibGUI()
    app.run()


if __name__ == "__main__":
    main()
