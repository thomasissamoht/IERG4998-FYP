#!/usr/bin/env python3
"""
Modern BibTeX Bibliography Manager GUI
Using CustomTkinter for a beautiful, modern interface
"""

import customtkinter as ctk
import ctypes
import threading
import webbrowser
import difflib
from collections import Counter
from pathlib import Path
import tarfile
from typing import Optional
from bib import BibliographyManager
import importlib
from typing import TYPE_CHECKING, Any
import tempfile
import zipfile
import shutil
import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

if TYPE_CHECKING:
    # Provide a name for static checkers without importing the runtime module
    webview: Any  # pragma: no cover

# Set appearance mode and color theme
ctk.set_appearance_mode("light")  # Modes: "System" (default), "Dark", "Light"
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
        self._current_changed_display_lines = []
        self._current_changed_idx = -1
        self._show_unchanged_var = ctk.BooleanVar(value=True)
        self._diff_context_lines = 2
        self._last_master_path = None
        self._last_cleaned_zip = None
        self._sidebar_mode = None
        self._sidebar_icon_buttons = {}
        self._sidebar_sections = {}
        self._redraw_suspend_count = 0
        self._theme_mode = "light"
        self._theme_apply_job = None
        self._last_applied_theme = None
        self._tooltip_window = None
        self._tooltip_job = None
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
        self._library_entries = []
        self._library_filtered_entries = []
        self._library_scope = "All References"
        self._library_scope_buttons = {}
        self._library_left_mode = None
        self._library_left_icon_buttons = {}
        self._library_left_minsize = 220
        self._custom_collections: dict[str, set[str]] = {}
        self._active_collection_name: Optional[str] = None
        self._library_notes: dict[str, str] = {}
        self._library_tags: dict[str, str] = {}
        self._selected_library_key: str = ""
        self._selected_library_entry = None
        self.library_context_menu = None
        self._library_tree_style_name = "Library.Treeview"
        self._library_density_var = ctk.StringVar(value="Compact")
        # Legacy placeholders for previously split fixes view helpers.
        self.orig_text = None
        self.updated_text = None
        self.fixes_scrollbar = None
        self.fixes_h_scrollbar = None
        
        # Citation key normalization rule (default and custom)
        self.citekey_rule_var = ctk.StringVar(value="author-year-title")
        self.citekey_custom_var = ctk.StringVar(value="{author}-{year}-{title}")

        # Build UI
        self._build_ui()

    def _theme_palette(self, mode: Optional[str] = None) -> dict[str, str]:
        mode = (mode or self._theme_mode or "dark").lower()
        if mode == "light":
            return {
                "root": "#eef2f7",
                "main": "#f7f9fc",
                "header": "#ffffff",
                "panel": "#ffffff",
                "panel2": "#eef3f9",
                "card": "#ffffff",
                "surface": "#f4f7fb",
                "rail": "#e7edf5",
                "rail_active": "#d7e4f5",
                "border": "#d3dce8",
                "text": "#162133",
                "muted": "#5d6c82",
                "muted2": "#8090a6",
                "accent": "#0f6fff",
                "accent_text": "#ffffff",
                "badge_bg": "#eaf2ff",
                "badge_text": "#0f4eb8",
                "button": "#e5ebf4",
                "button_hover": "#d6e0ee",
                "button_text": "#162133",
                "input_bg": "#ffffff",
                "input_border": "#cbd5e2",
                "tree_bg": "#ffffff",
                "tree_head": "#e7eef8",
                "tree_sel": "#cde0ff",
                "tree_sel_text": "#10233f",
                "textbox_bg": "#ffffff",
                "icon_rail": "#e9eef6",
                "icon_active": "#d8e5f7",
            }
        return {
            "root": "#101218",
            "main": "#0f1218",
            "header": "#161b24",
            "panel": "#161b24",
            "panel2": "#141922",
            "card": "#161b24",
            "surface": "#161b24",
            "rail": "#0b1322",
            "rail_active": "#2b3a54",
            "border": "#222938",
            "text": "#e5edf9",
            "muted": "#8f99ab",
            "muted2": "#7f8ba1",
            "accent": "#2878ff",
            "accent_text": "#ffffff",
            "badge_bg": "#1f2937",
            "badge_text": "#93c5fd",
            "button": "#1f2a3c",
            "button_hover": "#2b3b57",
            "button_text": "#e5edf9",
            "input_bg": "#10151d",
            "input_border": "#222938",
            "tree_bg": "#0d1523",
            "tree_head": "#1c2840",
            "tree_sel": "#2c5d93",
            "tree_sel_text": "#ffffff",
            "textbox_bg": "#10151d",
            "icon_rail": "#0b1322",
            "icon_active": "#2b3a54",
        }

    def _apply_theme_palette(self, mode: Optional[str] = None):
        """Apply a light or dark palette to the major app surfaces."""
        applied_mode = (mode or self._theme_mode or "light").lower()
        palette = self._theme_palette(applied_mode)

        def set_cfg(widget, **kwargs):
            if widget is None:
                return
            try:
                changed = False
                for key, value in kwargs.items():
                    try:
                        current_value = widget.cget(key)
                    except Exception:
                        changed = True
                        break
                    if current_value != value:
                        changed = True
                        break
                if not changed:
                    return
                widget.configure(**kwargs)
            except Exception:
                pass

        set_cfg(self.root, fg_color=palette["root"])
        set_cfg(getattr(self, "_sidebar_root", None), fg_color=palette["panel"])
        set_cfg(getattr(self, "_sidebar_panel_host", None), fg_color="transparent")
        set_cfg(getattr(self, "_sidebar_brand", None), fg_color="transparent")
        set_cfg(getattr(self, "sidebar_root", None), fg_color=palette["panel"])
        set_cfg(getattr(self, "sidebar_icon_rail", None), fg_color=palette["icon_rail"])
        set_cfg(getattr(self, "library_icon_rail", None), fg_color=palette["icon_rail"])
        for card_name in ("workspace_card", "options_card", "keys_card", "actions_card", "appearance_card"):
            set_cfg(getattr(self, card_name, None), fg_color=palette["card"], border_color=palette["border"])

        set_cfg(getattr(self, "main_frame", None), fg_color=palette["main"])
        set_cfg(getattr(self, "header", None), fg_color=palette["header"], border_color=palette["border"])
        set_cfg(getattr(self, "top_status_badge", None), fg_color=palette["badge_bg"], text_color=palette["badge_text"])
        set_cfg(getattr(self, "header_actions", None), fg_color="transparent")

        set_cfg(
            getattr(self, "tabview", None),
            fg_color=palette["panel2"],
            segmented_button_fg_color=palette["button"],
            segmented_button_selected_color=palette["accent"],
            segmented_button_selected_hover_color=palette["accent"],
            segmented_button_unselected_color=palette["button"],
            segmented_button_unselected_hover_color=palette["button_hover"],
            text_color=palette["button_text"],
            text_color_disabled=palette["muted2"],
        )
        set_cfg(getattr(self, "library_tab", None), fg_color=palette["panel2"])
        set_cfg(getattr(self, "library_left_shell", None), fg_color="transparent")
        set_cfg(getattr(self, "library_left_content", None), fg_color=palette["panel2"])
        set_cfg(getattr(self, "library_left_frame", None), fg_color=palette["card"], border_color=palette["border"])
        set_cfg(getattr(self, "library_scopes_panel", None), fg_color="transparent")
        set_cfg(getattr(self, "library_collections_panel", None), fg_color="transparent")
        set_cfg(getattr(self, "library_center_frame", None), fg_color=palette["card"])
        set_cfg(getattr(self, "library_top_frame", None), fg_color="transparent")
        set_cfg(getattr(self, "library_toolbar_frame", None), fg_color="transparent")
        set_cfg(getattr(self, "library_filters_frame", None), fg_color="transparent")
        set_cfg(getattr(self, "library_tree_frame", None), fg_color=palette["surface"])
        set_cfg(getattr(self, "library_right_frame", None), fg_color=palette["card"])
        set_cfg(getattr(self, "library_detail_actions", None), fg_color="transparent")
        set_cfg(getattr(self, "library_details_tabs", None), fg_color=palette["card"])
        set_cfg(getattr(self, "library_metadata_frame", None), fg_color=palette["card"])

        set_cfg(getattr(self, "pipeline_tab", None), fg_color=palette["panel2"])
        set_cfg(getattr(self, "pipeline_steps_section", None), fg_color="transparent")
        set_cfg(getattr(self, "pipeline_step_strip", None), fg_color=palette["surface"])
        set_cfg(getattr(self, "pipeline_log_box", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "results_tab", None), fg_color=palette["panel2"])
        set_cfg(getattr(self, "results_hero_frame", None), fg_color="transparent")
        set_cfg(getattr(self, "results_scroll", None), fg_color="transparent")
        set_cfg(getattr(self, "results_metrics_frame", None), fg_color=palette["card"])
        set_cfg(getattr(self, "results_summary_frame", None), fg_color=palette["card"])
        set_cfg(getattr(self, "results_files_frame", None), fg_color=palette["card"])
        set_cfg(getattr(self, "results_folders_frame", None), fg_color=palette["card"])
        set_cfg(getattr(self, "results_title_label", None), text_color=palette["text"])
        set_cfg(getattr(self, "results_subtitle_label", None), text_color=palette["muted"])
        set_cfg(getattr(self, "results_scope_label", None), text_color=palette["muted2"])
        set_cfg(getattr(self, "results_text_box", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "results_files_box", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "results_folders_box", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "fixes_tab", None), fg_color=palette["panel2"])
        set_cfg(getattr(self, "fixes_controls", None), fg_color="transparent")
        set_cfg(getattr(self, "fixes_nav", None), fg_color="transparent")
        set_cfg(getattr(self, "fixes_diff_box", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "duplicates_tab", None), fg_color=palette["panel2"])
        set_cfg(getattr(self, "duplicates_controls", None), fg_color="transparent")
        set_cfg(getattr(self, "duplicates_file_controls", None), fg_color="transparent")
        set_cfg(getattr(self, "duplicates_decision_panel", None), fg_color="transparent")
        set_cfg(getattr(self, "duplicates_text_box", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "about_tab", None), fg_color=palette["panel2"])
        set_cfg(getattr(self, "about_scroll", None), fg_color="transparent")
        set_cfg(getattr(self, "about_label", None), text_color=palette["text"])

        set_cfg(getattr(self, "library_info_text", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "library_notes_text", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "library_tags_text", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "meta_author_entry", None), fg_color=palette["input_bg"], border_color=palette["input_border"], text_color=palette["text"], placeholder_text_color=palette["muted2"])
        set_cfg(getattr(self, "meta_year_entry", None), fg_color=palette["input_bg"], border_color=palette["input_border"], text_color=palette["text"], placeholder_text_color=palette["muted2"])
        set_cfg(getattr(self, "meta_source_entry", None), fg_color=palette["input_bg"], border_color=palette["input_border"], text_color=palette["text"], placeholder_text_color=palette["muted2"])
        set_cfg(getattr(self, "meta_doi_entry", None), fg_color=palette["input_bg"], border_color=palette["input_border"], text_color=palette["text"], placeholder_text_color=palette["muted2"])
        set_cfg(getattr(self, "meta_title_entry", None), fg_color=palette["input_bg"], border_color=palette["input_border"], text_color=palette["text"], placeholder_text_color=palette["muted2"])
        set_cfg(getattr(self, "library_tree_y_scroll", None), fg_color=palette["surface"], button_color=palette["button"], button_hover_color=palette["button_hover"])
        set_cfg(getattr(self, "library_tree_x_scroll", None), fg_color=palette["surface"], button_color=palette["button"], button_hover_color=palette["button_hover"])
        set_cfg(getattr(self, "results_text", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "log_text", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "fixes_diff_text", None), fg_color=palette["textbox_bg"], text_color=palette["text"])
        set_cfg(getattr(self, "duplicates_text", None), fg_color=palette["textbox_bg"], text_color=palette["text"])

        for entry_name in ("dir_entry", "collection_entry", "citekey_custom_entry", "library_search_entry"):
            set_cfg(getattr(self, entry_name, None), fg_color=palette["input_bg"], border_color=palette["input_border"], text_color=palette["text"], placeholder_text_color=palette["muted2"])

        for button_name in ("browse_btn", "source_file_btn", "demo_btn", "clear_btn", "run_btn", "cancel_btn", "view_report_btn", "library_add_btn", "library_delete_btn", "library_export_btn", "copy_key_btn", "add_selected_btn", "review_duplicate_btn", "meta_save_btn", "library_note_save_btn", "library_tag_save_btn", "collection_add_btn", "add_to_collection_btn", "remove_collection_btn"):
            btn = getattr(self, button_name, None)
            if btn is None:
                continue
            if button_name == "run_btn":
                set_cfg(btn, fg_color=palette["accent"], hover=False, text_color=palette["accent_text"])
            else:
                set_cfg(btn, fg_color=palette["button"], hover=False, text_color=palette["button_text"])

        for menu_name in ("appearance_menu", "citekey_rule_menu", "library_density_menu", "collection_menu"):
            menu = getattr(self, menu_name, None)
            set_cfg(menu, fg_color=palette["button"], button_color=palette["button_hover"], text_color=palette["button_text"])

        for label_name in ("library_left_title_label", "library_left_tip_label", "library_count_badge", "main_title_label", "main_subtitle_label", "library_left_header_label", "library_shortcut_hint", "library_details_title", "status_label"):
            label = getattr(self, label_name, None)
            if label is None:
                continue
            if label_name in ("library_count_badge", "top_status_badge"):
                continue
            set_cfg(label, text_color=palette["text"] if mode == "light" else getattr(label, "cget", lambda *_: None)("text_color"))

        set_cfg(getattr(self, "library_left_title_label", None), text_color=palette["text"])
        set_cfg(getattr(self, "library_left_tip_label", None), text_color=palette["muted"])
        set_cfg(getattr(self, "main_title_label", None), text_color=palette["text"])
        set_cfg(getattr(self, "main_subtitle_label", None), text_color=palette["muted"])
        set_cfg(getattr(self, "library_details_title", None), text_color=palette["text"])
        set_cfg(getattr(self, "library_shortcut_hint", None), text_color=palette["muted"])
        set_cfg(getattr(self, "library_count_badge", None), fg_color=palette["badge_bg"], text_color=palette["badge_text"])

        for label_name in ("pipeline_log_label", "pipeline_step_strip", "pipeline_log_box", "results_metrics_frame", "fixes_diff_box", "duplicates_text_box"):
            widget = getattr(self, label_name, None)
            if widget is not None and hasattr(widget, "configure"):
                try:
                    widget.configure(text_color=palette["text"])
                except Exception:
                    pass

        for label_name in ("pipeline_log_label",):
            label = getattr(self, label_name, None)
            if label is not None:
                set_cfg(label, text_color=palette["text"])

        if hasattr(self, "library_tree"):
            style = ttk.Style()
            try:
                style.theme_use("default")
            except Exception:
                pass
            style.configure(
                self._library_tree_style_name,
                background=palette["tree_bg"],
                foreground=palette["text"],
                fieldbackground=palette["tree_bg"],
                rowheight=26,
                borderwidth=0,
                relief="flat",
                font=("Segoe UI", 10),
            )
            style.configure(
                "Library.Treeview.Heading",
                background=palette["tree_head"],
                foreground=palette["text"],
                relief="flat",
                borderwidth=0,
                font=("Segoe UI", 10, "bold"),
            )
            style.map(
                self._library_tree_style_name,
                background=[("selected", palette["tree_sel"])],
                foreground=[("selected", palette["tree_sel_text"])],
            )
            set_cfg(self.library_tree, style=self._library_tree_style_name)

        # Dynamic button groups keep their own active-state styling and must be refreshed after palette changes.
        try:
            self._update_sidebar_icon_rail()
        except Exception:
            pass
        try:
            self._update_library_left_rail()
        except Exception:
            pass
        try:
            self._update_library_scope_buttons()
        except Exception:
            pass

        self._last_applied_theme = applied_mode

    def _ui_call(self, func, *args, **kwargs):
        """Run UI operation on main thread (Tkinter-safe)."""
        if threading.current_thread() is threading.main_thread():
            func(*args, **kwargs)
        else:
            # Queue to main thread with proper argument passing
            self.root.after(0, lambda: func(*args, **kwargs))

    def _suspend_window_redraw(self):
        """Temporarily stop window redraws while doing a large visual update."""
        if os.name != "nt":
            return
        self._redraw_suspend_count += 1
        if self._redraw_suspend_count > 1:
            return
        try:
            hwnd = self.root.winfo_id()
            ctypes.windll.user32.SendMessageW(hwnd, 0x000B, 0, 0)
        except Exception:
            pass

    def _resume_window_redraw(self):
        """Re-enable redraws after a large visual update."""
        if os.name != "nt":
            return
        if self._redraw_suspend_count == 0:
            return
        self._redraw_suspend_count -= 1
        if self._redraw_suspend_count > 0:
            return
        try:
            hwnd = self.root.winfo_id()
            ctypes.windll.user32.SendMessageW(hwnd, 0x000B, 1, 0)
            ctypes.windll.user32.RedrawWindow(hwnd, None, None, 0x0001 | 0x0080 | 0x0100)
        except Exception:
            pass

    def _bind_tooltip(self, widget, text: str):
        """Attach hover tooltip behavior to a widget."""
        widget.bind("<Enter>", lambda _e, w=widget, t=text: self._schedule_tooltip(w, t), add="+")
        widget.bind("<Leave>", lambda _e: self._hide_tooltip(), add="+")
        widget.bind("<ButtonPress>", lambda _e: self._hide_tooltip(), add="+")

    def _schedule_tooltip(self, widget, text: str):
        """Delay tooltip slightly to avoid visual noise when moving mouse quickly."""
        if self._tooltip_job is not None:
            try:
                self.root.after_cancel(self._tooltip_job)
            except Exception:
                pass
        self._tooltip_job = self.root.after(280, lambda: self._show_tooltip(widget, text))

    def _show_tooltip(self, widget, text: str):
        if self._tooltip_window is not None:
            self._hide_tooltip()

        x = widget.winfo_pointerx() + 14
        y = widget.winfo_pointery() + 10

        tip = tk.Toplevel(self.root)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)
        tip.geometry(f"+{x}+{y}")

        label = tk.Label(
            tip,
            text=text,
            bg="#1b2435",
            fg="#e8effd",
            padx=8,
            pady=4,
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9),
        )
        label.pack()
        self._tooltip_window = tip

    def _hide_tooltip(self):
        if self._tooltip_job is not None:
            try:
                self.root.after_cancel(self._tooltip_job)
            except Exception:
                pass
            self._tooltip_job = None

        if self._tooltip_window is not None:
            try:
                self._tooltip_window.destroy()
            except Exception:
                pass
            self._tooltip_window = None

    def _build_ui(self):
        """Build the user interface"""
        # Configure grid
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Left sidebar for controls
        self._build_sidebar()
        
        # Main content area with tabs
        self._build_main_content()

        # Apply theme after all widgets are created, so no pane keeps construction-time colors.
        self._apply_theme_palette(self._theme_mode)
        
    def _build_sidebar(self):
        """Build a single-icon collapsible sidebar drawer for app controls."""
        sidebar = ctk.CTkFrame(self.root, width=320, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar_root = sidebar
        self.sidebar_root = sidebar
        sidebar.grid_columnconfigure(1, weight=1)
        sidebar.grid_rowconfigure(1, weight=1)

        icon_rail = ctk.CTkFrame(sidebar, width=52)
        icon_rail.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 8), pady=0)
        icon_rail.grid_propagate(False)
        self.sidebar_icon_rail = icon_rail
        icon_rail.grid_columnconfigure(0, weight=1)
        icon_rail.grid_rowconfigure(6, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=1, sticky="ew", padx=(10, 14), pady=(16, 12))
        self._sidebar_brand = brand
        self.sidebar_brand = brand
        brand.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            brand,
            text="Bibliography Workspace",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            brand,
            text="Click left icons to open tools",
            font=ctk.CTkFont(size=11),
            text_color="#8f99ab"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        panel_host = ctk.CTkFrame(sidebar, fg_color="transparent")
        panel_host.grid(row=1, column=1, sticky="nsew")
        self._sidebar_panel_host = panel_host
        self.sidebar_panel_host = panel_host
        panel_host.grid_columnconfigure(0, weight=1)
        panel_host.grid_rowconfigure(5, weight=1)

        self.sidebar_controls_btn = ctk.CTkButton(
            icon_rail,
            text="☰",
            width=34,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            command=lambda: self._set_sidebar_mode("controls"),
        )
        self.sidebar_controls_btn.grid(row=0, column=0, padx=8, pady=(14, 8), sticky="ew")

        self._sidebar_icon_buttons = {
            "controls": self.sidebar_controls_btn,
        }
        self._bind_tooltip(self.sidebar_controls_btn, "Controls Drawer")

        workspace_card = ctk.CTkFrame(panel_host)
        workspace_card.grid(row=0, column=0, sticky="ew", padx=(0, 14), pady=(0, 10))
        self.workspace_card = workspace_card
        workspace_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(workspace_card, text="Project Source", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6)
        )

        self.dir_entry = ctk.CTkEntry(workspace_card, placeholder_text="Choose folder, archive, .bib, or .tex source...")
        self.dir_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 6))

        self.browse_btn = ctk.CTkButton(
            workspace_card,
            text="Folder",
            command=self._browse_directory,
            height=30
        )
        self.browse_btn.grid(row=2, column=0, sticky="ew", padx=(12, 6), pady=(0, 8))

        self.source_file_btn = ctk.CTkButton(
            workspace_card,
            text="File / Archive",
            command=self._browse_project_source_file,
            height=30
        )
        self.source_file_btn.grid(row=2, column=1, sticky="ew", padx=(6, 12), pady=(0, 8))

        self.demo_btn = ctk.CTkButton(
            workspace_card,
            text="Use test_data",
            command=self._use_test_data,
            height=28
        )
        self.demo_btn.grid(row=3, column=0, sticky="ew", padx=(12, 6), pady=(0, 10))

        self.clear_btn = ctk.CTkButton(
            workspace_card,
            text="Clear",
            command=self._clear_for_next_run,
            height=28
        )
        self.clear_btn.grid(row=3, column=1, sticky="ew", padx=(6, 12), pady=(0, 10))

        options_card = ctk.CTkFrame(panel_host)
        options_card.grid(row=1, column=0, sticky="ew", padx=(0, 14), pady=(0, 10))
        self.options_card = options_card
        options_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(options_card, text="Pipeline Options", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )

        row = ctk.CTkFrame(options_card, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 0))
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(row, text="Duplicate Similarity", font=ctk.CTkFont(size=11), text_color="#d2d8e5").grid(row=0, column=0, sticky="w")

        self.threshold_var = ctk.IntVar(value=85)
        self.threshold_label = ctk.CTkLabel(row, text="85%", text_color="#66b3ff", font=ctk.CTkFont(size=11, weight="bold"))
        self.threshold_label.grid(row=0, column=1, sticky="e")

        self.threshold_slider = ctk.CTkSlider(
            options_card,
            from_=0,
            to=100,
            variable=self.threshold_var,
            command=self._update_threshold_label
        )
        self.threshold_slider.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 2))

        self.threshold_hint = ctk.CTkLabel(
            options_card,
            text="Balanced (recommended)",
            font=ctk.CTkFont(size=10),
            text_color="#7f8ba1"
        )
        self.threshold_hint.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 8))

        self.push_var = ctk.BooleanVar(value=True)
        self.push_check = ctk.CTkCheckBox(options_card, text="Distribute master.bib to project folders", variable=self.push_var)
        self.push_check.grid(row=4, column=0, sticky="w", padx=12, pady=(0, 4))

        self.report_var = ctk.BooleanVar(value=True)
        self.report_check = ctk.CTkCheckBox(options_card, text="Generate HTML report", variable=self.report_var)
        self.report_check.grid(row=5, column=0, sticky="w", padx=12, pady=(0, 10))

        keys_card = ctk.CTkFrame(panel_host)
        keys_card.grid(row=2, column=0, sticky="ew", padx=(0, 14), pady=(0, 10))
        self.keys_card = keys_card
        keys_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(keys_card, text="Citation Key Policy", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )

        self.citekey_rule_menu = ctk.CTkOptionMenu(
            keys_card,
            values=["author-year-title", "author-year-titleword", "author-title", "professor-style", "professor-strict", "author-et-al-year", "lastname-only-year", "firstauthor-year-titleword", "compact-initials", "numeric", "custom"],
            variable=self.citekey_rule_var,
            command=self._on_citekey_rule_changed,
        )
        self.citekey_rule_menu.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self.citekey_rule_menu.set("author-year-title")

        self.citekey_custom_entry = ctk.CTkEntry(
            keys_card,
            textvariable=self.citekey_custom_var,
            placeholder_text="Custom pattern, e.g. {author}{year}{titleword}",
            state="disabled"
        )
        self.citekey_custom_entry.grid(row=2, column=0, padx=12, pady=(0, 6), sticky="ew")

        ctk.CTkLabel(
            keys_card,
            text="Tokens: {author}, {authorstem}, {authorstrict}, {authoretal}, {lastname}, {authorinitials}, {year}, {titleword}, {numeric}",
            wraplength=274,
            justify="left",
            text_color="#7f8ba1",
            font=ctk.CTkFont(size=10),
        ).grid(row=3, column=0, padx=12, pady=(0, 10), sticky="w")

        actions_card = ctk.CTkFrame(panel_host)
        actions_card.grid(row=3, column=0, sticky="ew", padx=(0, 14), pady=(0, 10))
        self.actions_card = actions_card
        actions_card.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            actions_card,
            textvariable=self._status_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#6ab8ff",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 10))

        appearance_card = ctk.CTkFrame(panel_host)
        appearance_card.grid(row=4, column=0, sticky="ew", padx=(0, 14), pady=(0, 10))
        self.appearance_card = appearance_card
        appearance_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(appearance_card, text="Appearance", font=ctk.CTkFont(size=13, weight="bold"), text_color="#d2d8e5").grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )
        self.appearance_menu = ctk.CTkOptionMenu(
            appearance_card,
            values=["System", "Light", "Dark"],
            command=self._change_appearance,
            fg_color="gray25",
            button_color="gray30"
        )
        self.appearance_menu.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.appearance_menu.set("Light")

        self._set_sidebar_mode("controls", force_open=True)

    def _set_sidebar_mode(self, mode: Optional[str], force_open: bool = False):
        """Toggle the single controls drawer from the left icon rail."""
        if mode not in {None, "controls"}:
            return

        if mode is None:
            self._sidebar_mode = None
        else:
            if not force_open and self._sidebar_mode == mode:
                self._sidebar_mode = None
            else:
                self._sidebar_mode = mode

        if self._sidebar_mode is None:
            self._sidebar_panel_host.grid_remove()
            self._sidebar_brand.grid_remove()
        else:
            self._sidebar_brand.grid(row=0, column=1, sticky="ew", padx=(10, 14), pady=(16, 12))
            self._sidebar_panel_host.grid(row=1, column=1, sticky="nsew")

        self._update_sidebar_icon_rail()

    def _update_sidebar_icon_rail(self):
        """Highlight active sidebar icon and dim inactive ones."""
        palette = self._theme_palette(self._theme_mode)
        for mode, btn in self._sidebar_icon_buttons.items():
            active = mode == self._sidebar_mode
            btn.configure(
                fg_color=palette["button"],
                hover=False,
                text_color=palette["accent"] if active else palette["muted2"],
            )
        
    def _build_main_content(self):
        """Build main content area with reference-manager style header and tabs."""
        main_frame = ctk.CTkFrame(self.root)
        main_frame.grid(row=0, column=1, sticky="nsew", padx=(14, 14), pady=14)
        self.main_frame = main_frame
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(main_frame, border_width=1)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 10))
        self.header = header
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=0)

        self.main_title_label = ctk.CTkLabel(
            header,
            text="All References Workspace",
            font=ctk.CTkFont(size=17, weight="bold")
        )
        self.main_title_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))

        self.main_subtitle_label = ctk.CTkLabel(
            header,
            text="Track pipeline progress, inspect duplicates, and verify fixes before export",
            font=ctk.CTkFont(size=11),
            text_color="#8f99ab"
        )
        self.main_subtitle_label.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

        self.top_status_badge = ctk.CTkLabel(
            header,
            textvariable=self._status_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=8,
            padx=10,
            pady=6,
        )
        self.top_status_badge.grid(row=0, column=1, rowspan=2, sticky="e", padx=(12, 8), pady=8)

        header_actions = ctk.CTkFrame(header, fg_color="transparent")
        header_actions.grid(row=0, column=2, rowspan=2, sticky="e", padx=(0, 12), pady=8)
        self.header_actions = header_actions

        self.run_btn = ctk.CTkButton(
            header_actions,
            text="Clean and Normalize",
            command=self._run_pipeline,
            height=30,
            width=116,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.run_btn.grid(row=0, column=0, padx=(0, 6))

        self.cancel_btn = ctk.CTkButton(
            header_actions,
            text="Cancel",
            command=self._cancel_pipeline,
            height=30,
            width=80,
            state="disabled"
        )
        self.cancel_btn.grid(row=0, column=1, padx=(0, 6))

        self.view_report_btn = ctk.CTkButton(
            header_actions,
            text="Open Report",
            command=self._view_report,
            height=30,
            width=100,
            state="disabled"
        )
        self.view_report_btn.grid(row=0, column=2)

        ctk.CTkLabel(
            header,
            text="Folder selection previews references. Use Clean and Normalize for full dedupe/key cleanup.",
            font=ctk.CTkFont(size=10),
            text_color="#8f99ab",
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 8))

        self.tabview = ctk.CTkTabview(main_frame, corner_radius=10)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        
        # Create tabs
        self.tabview.add("📚 Library")
        self.tabview.add("📋 Pipeline")
        self.tabview.add("📈 Dashboard")
        self.tabview.add("🔍 Duplicates")
        self.tabview.add("🛠 Fixes")
        self.tabview.add("ℹ️ About")
        
        self._build_library_tab()
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

    def _build_library_tab(self):
        """Build a reference-manager style three-pane library workspace."""
        tab = self.tabview.tab("📚 Library")
        self._library_tab = tab
        self.library_tab = tab
        control_h = 30
        side_pad = 10
        palette = self._theme_palette(self._theme_mode)
        pane_left_bg = palette["card"]
        pane_center_bg = palette["card"]
        pane_right_bg = palette["card"]
        card_bg = palette["card"]
        text_primary = palette["text"]
        text_secondary = palette["muted"]
        neutral_btn = palette["button"]
        neutral_btn_hover = palette["button_hover"]

        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=2, minsize=220)
        tab.grid_columnconfigure(1, weight=7)
        tab.grid_columnconfigure(2, weight=5)

        left_shell = ctk.CTkFrame(tab, fg_color="transparent")
        left_shell.grid(row=0, column=0, sticky="nsew", padx=(10, 6), pady=10)
        self._library_left_shell = left_shell
        self.library_left_shell = left_shell
        left_shell.grid_columnconfigure(1, weight=1)
        left_shell.grid_rowconfigure(0, weight=1)

        icon_rail = ctk.CTkFrame(left_shell, fg_color=palette["icon_rail"], width=48)
        icon_rail.grid(row=0, column=0, sticky="nsw", padx=(0, 6))
        icon_rail.grid_propagate(False)
        self.library_icon_rail = icon_rail
        icon_rail.grid_columnconfigure(0, weight=1)
        icon_rail.grid_rowconfigure(4, weight=1)

        self.library_nav_scopes_btn = ctk.CTkButton(
            icon_rail,
            text="📚",
            width=34,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover=False,
            command=lambda: self._set_library_left_mode("scopes"),
        )
        self.library_nav_scopes_btn.grid(row=0, column=0, padx=6, pady=(10, 6), sticky="ew")

        self.library_nav_collections_btn = ctk.CTkButton(
            icon_rail,
            text="🗂",
            width=34,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover=False,
            command=lambda: self._set_library_left_mode("collections"),
        )
        self.library_nav_collections_btn.grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        self._library_left_icon_buttons = {
            "scopes": self.library_nav_scopes_btn,
            "collections": self.library_nav_collections_btn,
        }
        self._bind_tooltip(self.library_nav_scopes_btn, "Library Scopes")
        self._bind_tooltip(self.library_nav_collections_btn, "Collections")

        left = ctk.CTkFrame(left_shell, fg_color=pane_left_bg, width=230)
        left.grid(row=0, column=1, sticky="nsew")
        self._library_left_content = left
        self.library_left_frame = left
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        self.library_left_title_label = ctk.CTkLabel(
            left,
            text="Library Scopes",
            text_color=text_primary,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.library_left_title_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))

        self.library_left_tip_label = ctk.CTkLabel(
            left,
            text="Tip: choose a folder to preview references instantly.",
            text_color=text_secondary,
            font=ctk.CTkFont(size=10),
            wraplength=180,
            justify="left",
        )
        self.library_left_tip_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))

        self.library_scopes_panel = ctk.CTkFrame(left, fg_color="transparent")
        self.library_scopes_panel.grid(row=2, column=0, sticky="nsew", padx=side_pad, pady=(0, 8))
        self.library_scopes_panel.grid_columnconfigure(0, weight=1)
        self.library_scopes_panel.grid_rowconfigure(5, weight=1)

        scopes = ["All References", "Recently Added", "Favorites", "Duplicate Items"]
        for idx, scope in enumerate(scopes):
            btn = ctk.CTkButton(
                self.library_scopes_panel,
                text=scope,
                height=control_h,
                fg_color="transparent",
                hover_color=palette["button_hover"],
                text_color=palette["text"],
                anchor="w",
                command=lambda s=scope: self._set_library_scope(s),
            )
            btn.grid(row=idx, column=0, sticky="ew", pady=2)
            self._library_scope_buttons[scope] = btn

        self.library_collections_panel = ctk.CTkFrame(left, fg_color="transparent")
        self.library_collections_panel.grid(row=2, column=0, sticky="nsew", padx=side_pad, pady=(0, 8))
        self.library_collections_panel.grid_columnconfigure(0, weight=1)
        self.library_collections_panel.grid_rowconfigure(4, weight=1)

        collection_row = ctk.CTkFrame(self.library_collections_panel, fg_color="transparent")
        collection_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        collection_row.grid_columnconfigure(0, weight=1)

        self.collection_name_var = ctk.StringVar(value="")
        self.collection_entry = ctk.CTkEntry(collection_row, textvariable=self.collection_name_var, placeholder_text="New collection")
        self.collection_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.collection_add_btn = ctk.CTkButton(collection_row, text="Add", width=50, height=control_h, command=self._add_collection)
        self.collection_add_btn.grid(row=0, column=1, sticky="e")

        self.collection_menu = ctk.CTkOptionMenu(
            self.library_collections_panel,
            values=["No collections"],
            command=self._on_collection_selected,
            height=control_h,
            fg_color=neutral_btn,
            button_color=neutral_btn_hover,
        )
        self.collection_menu.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.collection_menu.set("No collections")

        collection_actions = ctk.CTkFrame(self.library_collections_panel, fg_color="transparent")
        collection_actions.grid(row=2, column=0, sticky="ew")
        collection_actions.grid_columnconfigure((0, 1), weight=1)
        self.add_to_collection_btn = ctk.CTkButton(
            collection_actions,
            text="Add selected",
            height=control_h,
            fg_color=neutral_btn,
            hover=False,
            command=self._add_selected_to_active_collection,
        )
        self.add_to_collection_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.remove_collection_btn = ctk.CTkButton(
            collection_actions,
            text="Remove",
            height=control_h,
            fg_color=neutral_btn,
            hover=False,
            command=self._remove_active_collection,
        )
        self.remove_collection_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self._set_library_left_mode(None, force_open=True)

        center = ctk.CTkFrame(tab, fg_color=pane_center_bg)
        center.grid(row=0, column=1, sticky="nsew", padx=(0, 6), pady=10)
        self.library_center_frame = center
        center.grid_rowconfigure(3, weight=1)
        center.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(center, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
        self.library_top_frame = top
        top.grid_columnconfigure(0, weight=0)
        top.grid_columnconfigure(1, weight=0)
        top.grid_columnconfigure(2, weight=0)
        top.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(top, text="All References", text_color=text_primary, font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )

        self.library_count_badge = ctk.CTkLabel(
            top,
            text="0 refs",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=8,
            padx=8,
            pady=3,
        )
        self.library_count_badge.grid(row=0, column=1, sticky="w", padx=(0, 8))

        self.library_search_var = ctk.StringVar(value="")
        search_entry = ctk.CTkEntry(top, textvariable=self.library_search_var, placeholder_text="Search title, author, year, key...")
        search_entry.configure(height=control_h)
        search_entry.grid(row=0, column=3, sticky="ew")
        search_entry.bind("<KeyRelease>", lambda _e: self._apply_library_filter())
        self.library_search_entry = search_entry

        toolbar = ctk.CTkFrame(top, fg_color="transparent")
        toolbar.grid(row=1, column=0, columnspan=4, pady=(8, 0), sticky="w")
        self.library_toolbar_frame = toolbar

        self.library_add_btn = ctk.CTkButton(toolbar, text="Add", width=58, height=control_h, command=self._add_library_entry_manual)
        self.library_add_btn.grid(row=0, column=0, padx=(0, 4))
        self.library_delete_btn = ctk.CTkButton(toolbar, text="Delete", width=58, height=control_h, command=self._delete_selected_library_entry)
        self.library_delete_btn.grid(row=0, column=1, padx=(0, 4))
        self.library_export_btn = ctk.CTkButton(toolbar, text="Export", width=62, height=control_h, command=self._export_selected_library_entry)
        self.library_export_btn.grid(row=0, column=2, padx=(0, 6))

        self.library_density_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["Compact", "Comfortable"],
            variable=self._library_density_var,
            command=self._change_library_density,
            width=116,
            height=control_h,
            fg_color=neutral_btn,
            button_color=neutral_btn_hover,
        )
        self.library_density_menu.grid(row=0, column=3)

        self.library_delete_btn.configure(fg_color=neutral_btn, hover_color=neutral_btn_hover)
        self.library_export_btn.configure(fg_color=neutral_btn, hover_color=neutral_btn_hover)

        self.library_shortcut_hint = ctk.CTkLabel(
            center,
            text="Shortcuts: Ctrl+F search   Ctrl+C copy key   Ctrl+D delete   Ctrl+M favorite",
            text_color=text_secondary,
            font=ctk.CTkFont(size=10),
        )
        self.library_shortcut_hint.grid(row=1, column=0, sticky="w", padx=10, pady=(2, 2))

        filters = ctk.CTkFrame(center, fg_color="transparent")
        filters.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
        self.library_filters_frame = filters
        filters.grid_columnconfigure((0, 1, 2), weight=0)
        self.filter_duplicates_var = ctk.BooleanVar(value=False)
        self.filter_doi_var = ctk.BooleanVar(value=False)
        self.filter_missing_year_var = ctk.BooleanVar(value=False)

        self.filter_duplicates_chip = ctk.CTkCheckBox(
            filters,
            text="Duplicates",
            variable=self.filter_duplicates_var,
            onvalue=True,
            offvalue=False,
            command=self._apply_library_filter,
        )
        self.filter_duplicates_chip.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="w")

        self.filter_doi_chip = ctk.CTkCheckBox(
            filters,
            text="Has DOI",
            variable=self.filter_doi_var,
            onvalue=True,
            offvalue=False,
            command=self._apply_library_filter,
        )
        self.filter_doi_chip.grid(row=0, column=1, padx=(0, 8), pady=0, sticky="w")

        self.filter_missing_year_chip = ctk.CTkCheckBox(
            filters,
            text="Missing Year",
            variable=self.filter_missing_year_var,
            onvalue=True,
            offvalue=False,
            command=self._apply_library_filter,
        )
        self.filter_missing_year_chip.grid(row=0, column=2, padx=(0, 8), pady=0, sticky="w")

        tree_frame = ctk.CTkFrame(center, fg_color=card_bg)
        tree_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.library_tree_frame = tree_frame
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        try:
            style.theme_use("default")
        except Exception:
            pass
        style.configure(
            self._library_tree_style_name,
            background=palette["tree_bg"],
            foreground=palette["text"],
            fieldbackground=palette["tree_bg"],
            rowheight=26,
            borderwidth=0,
            relief="flat",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Library.Treeview.Heading",
            background=palette["tree_head"],
            foreground=palette["text"],
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            self._library_tree_style_name,
            background=[("selected", palette["tree_sel"])],
            foreground=[("selected", palette["tree_sel_text"])],
        )

        self.library_tree = ttk.Treeview(
            tree_frame,
            columns=("status", "authors", "year", "title", "source", "key"),
            show="headings",
            selectmode="browse",
            height=20,
            style=self._library_tree_style_name,
        )
        self.library_tree.heading("status", text="★", command=lambda: self._sort_library_tree("status", False))
        self.library_tree.heading("authors", text="Authors", command=lambda: self._sort_library_tree("authors", False))
        self.library_tree.heading("year", text="Year", command=lambda: self._sort_library_tree("year", True))
        self.library_tree.heading("title", text="Title", command=lambda: self._sort_library_tree("title", False))
        self.library_tree.heading("source", text="Source", command=lambda: self._sort_library_tree("source", False))
        self.library_tree.heading("key", text="Key", command=lambda: self._sort_library_tree("key", False))
        self.library_tree.column("status", width=44, anchor="center")
        self.library_tree.column("authors", width=220, anchor="w")
        self.library_tree.column("year", width=60, anchor="center")
        self.library_tree.column("title", width=420, anchor="w")
        self.library_tree.column("source", width=150, anchor="w")
        self.library_tree.column("key", width=150, anchor="w")

        y_scroll = ctk.CTkScrollbar(tree_frame, orientation="vertical", command=self.library_tree.yview)
        x_scroll = ctk.CTkScrollbar(tree_frame, orientation="horizontal", command=self.library_tree.xview)
        self.library_tree_y_scroll = y_scroll
        self.library_tree_x_scroll = x_scroll
        self.library_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.library_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.library_tree.bind("<<TreeviewSelect>>", self._on_library_row_selected)
        self.library_tree.bind("<Double-1>", self._toggle_selected_favorite)
        self.library_tree.bind("<ButtonRelease-1>", self._on_library_tree_click)
        self.library_tree.bind("<Button-3>", self._show_library_context_menu)
        self._bind_library_shortcuts(search_entry)

        right = ctk.CTkFrame(tab, fg_color=pane_right_bg)
        right.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)
        self.library_right_frame = right
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="Details", text_color=text_primary, font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 8)
        )

        detail_actions = ctk.CTkFrame(right, fg_color="transparent")
        detail_actions.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        self.library_detail_actions = detail_actions
        detail_actions.grid_columnconfigure(0, weight=1)

        self.copy_key_btn = ctk.CTkButton(
            detail_actions,
            text="Copy Key",
            height=control_h,
            fg_color=neutral_btn,
            hover=False,
            command=self._copy_selected_key,
        )
        self.copy_key_btn.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self.add_selected_btn = ctk.CTkButton(
            detail_actions,
            text="Add to Collection",
            height=control_h,
            fg_color=neutral_btn,
            hover=False,
            command=self._add_selected_to_active_collection,
        )
        self.add_selected_btn.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        self.review_duplicate_btn = ctk.CTkButton(
            detail_actions,
            text="Review Duplicates",
            height=control_h,
            fg_color=neutral_btn,
            hover=False,
            command=self._review_selected_duplicates,
        )
        self.review_duplicate_btn.grid(row=2, column=0, sticky="ew")

        self.library_details_tabs = ctk.CTkTabview(right)
        self.library_details_tabs.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.library_details_tabs.add("Info")
        self.library_details_tabs.add("Notes")
        self.library_details_tabs.add("Tags")

        info_tab = self.library_details_tabs.tab("Info")
        info_tab.grid_rowconfigure(0, weight=1)
        info_tab.grid_rowconfigure(1, weight=0)
        info_tab.grid_columnconfigure(0, weight=1)
        self.library_info_text = ctk.CTkTextbox(info_tab, font=ctk.CTkFont(family="Segoe UI", size=11), wrap="word")
        self.library_info_text.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.library_info_text.insert("1.0", "Choose a folder, then select a reference to view metadata.")

        edit_box = ctk.CTkFrame(info_tab, fg_color=card_bg)
        edit_box.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.library_metadata_frame = edit_box
        for col in range(2):
            edit_box.grid_columnconfigure(col, weight=1)

        self.meta_author_var = ctk.StringVar(value="")
        self.meta_year_var = ctk.StringVar(value="")
        self.meta_title_var = ctk.StringVar(value="")
        self.meta_source_var = ctk.StringVar(value="")
        self.meta_doi_var = ctk.StringVar(value="")

        ctk.CTkLabel(edit_box, text="Author", font=ctk.CTkFont(size=10)).grid(row=0, column=0, sticky="w", padx=6, pady=(6, 0))
        ctk.CTkLabel(edit_box, text="Year", font=ctk.CTkFont(size=10)).grid(row=0, column=1, sticky="w", padx=6, pady=(6, 0))
        self.meta_author_entry = ctk.CTkEntry(edit_box, textvariable=self.meta_author_var, height=control_h)
        self.meta_author_entry.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 4))
        self.meta_year_entry = ctk.CTkEntry(edit_box, textvariable=self.meta_year_var, height=control_h)
        self.meta_year_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=(0, 4))

        ctk.CTkLabel(edit_box, text="Source", font=ctk.CTkFont(size=10)).grid(row=2, column=0, sticky="w", padx=6, pady=(0, 0))
        ctk.CTkLabel(edit_box, text="DOI", font=ctk.CTkFont(size=10)).grid(row=2, column=1, sticky="w", padx=6, pady=(0, 0))
        self.meta_source_entry = ctk.CTkEntry(edit_box, textvariable=self.meta_source_var, height=control_h)
        self.meta_source_entry.grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 4))
        self.meta_doi_entry = ctk.CTkEntry(edit_box, textvariable=self.meta_doi_var, height=control_h)
        self.meta_doi_entry.grid(row=3, column=1, sticky="ew", padx=6, pady=(0, 4))

        ctk.CTkLabel(edit_box, text="Title", font=ctk.CTkFont(size=10)).grid(row=4, column=0, sticky="w", padx=6, pady=(0, 0))
        self.meta_title_entry = ctk.CTkEntry(edit_box, textvariable=self.meta_title_var, height=control_h)
        self.meta_title_entry.grid(row=5, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))
        self.meta_save_btn = ctk.CTkButton(edit_box, text="Save Metadata", height=control_h, command=self._save_selected_metadata)
        self.meta_save_btn.grid(row=6, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))

        notes_tab = self.library_details_tabs.tab("Notes")
        notes_tab.grid_rowconfigure(0, weight=1)
        notes_tab.grid_columnconfigure(0, weight=1)
        self.library_notes_text = ctk.CTkTextbox(notes_tab, font=ctk.CTkFont(size=11), wrap="word")
        self.library_notes_text.grid(row=0, column=0, sticky="nsew", padx=6, pady=(6, 4))
        self.library_note_save_btn = ctk.CTkButton(notes_tab, text="Save Note", height=control_h, command=self._save_selected_note)
        self.library_note_save_btn.grid(row=1, column=0, sticky="e", padx=6, pady=(0, 6))

        tags_tab = self.library_details_tabs.tab("Tags")
        tags_tab.grid_rowconfigure(0, weight=1)
        tags_tab.grid_columnconfigure(0, weight=1)
        self.library_tags_text = ctk.CTkTextbox(tags_tab, font=ctk.CTkFont(size=11), wrap="word")
        self.library_tags_text.grid(row=0, column=0, sticky="nsew", padx=6, pady=(6, 4))
        self.library_tag_save_btn = ctk.CTkButton(tags_tab, text="Save Tags", height=control_h, command=self._save_selected_tags)
        self.library_tag_save_btn.grid(row=1, column=0, sticky="e", padx=6, pady=(0, 6))

        self._update_library_scope_buttons()

    def _set_library_left_mode(self, mode: Optional[str], force_open: bool = False):
        """Toggle Library drawer between Scopes/Collections, collapse on repeat click."""
        if mode is not None and mode not in {"scopes", "collections"}:
            return

        if mode is None:
            self._library_left_mode = None
        else:
            if not force_open and self._library_left_mode == mode:
                self._library_left_mode = None
            else:
                self._library_left_mode = mode

        if not hasattr(self, 'library_scopes_panel') or not hasattr(self, 'library_collections_panel'):
            return

        self.library_scopes_panel.grid_forget()
        self.library_collections_panel.grid_forget()

        self._library_left_content.grid(row=0, column=1, sticky="nsew")
        if self._library_left_mode is None:
            if hasattr(self, "_library_tab"):
                self._library_tab.grid_columnconfigure(0, weight=0, minsize=52)
            self.library_left_title_label.configure(text="Library Scopes")
            self.library_left_tip_label.configure(text="Choose a scope to focus your reference list.")
            self.library_scopes_panel.grid_remove()
            self.library_collections_panel.grid_remove()
            self._library_left_content.grid_remove()
        elif self._library_left_mode == "scopes":
            if hasattr(self, "_library_tab"):
                self._library_tab.grid_columnconfigure(0, weight=2, minsize=220)
            self.library_left_title_label.configure(text="Library Scopes")
            self.library_left_tip_label.configure(text="Choose a scope to focus your reference list.")
            self.library_scopes_panel.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 8))
        else:
            if hasattr(self, "_library_tab"):
                self._library_tab.grid_columnconfigure(0, weight=2, minsize=220)
            self.library_left_title_label.configure(text="Collections")
            self.library_left_tip_label.configure(text="Create named groups and quickly add selected references.")
            self.library_collections_panel.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 8))

        self._update_library_left_rail()

    def _update_library_left_rail(self):
        """Highlight active icon in Library side rail."""
        palette = self._theme_palette(self._theme_mode)
        for mode, btn in self._library_left_icon_buttons.items():
            active = mode == self._library_left_mode
            btn.configure(
                fg_color=palette["button"],
                hover=False,
                text_color=palette["accent"] if active else palette["muted2"],
            )

    def _set_library_scope(self, scope: str):
        self._library_scope = scope
        self._active_collection_name = None
        self._set_library_left_mode("scopes", force_open=True)
        self._update_library_scope_buttons()
        self._apply_library_filter()

    def _update_library_scope_buttons(self):
        palette = self._theme_palette(self._theme_mode)
        counts = self._library_scope_counts()
        for scope, btn in self._library_scope_buttons.items():
            active = scope == self._library_scope
            count = counts.get(scope, 0)
            btn.configure(
                text=f"{scope} ({count})",
                fg_color=palette["button"],
                hover=False,
                text_color=palette["accent"] if active else palette["muted2"],
            )

    def _library_scope_counts(self) -> dict[str, int]:
        entries = self._library_entries
        duplicate_keys = set()
        if self.manager:
            for group in self.manager.report_data.get('duplicate_groups', []):
                for entry in group.get('entries', []):
                    key = str(entry.get('ID', '')).strip()
                    if key:
                        duplicate_keys.add(key)
        return {
            "All References": len(entries),
            "Recently Added": min(len(entries), 200),
            "Favorites": sum(1 for e in entries if e.get('_favorite')),
            "Duplicate Items": sum(1 for e in entries if str(e.get('ID', '')).strip() in duplicate_keys),
        }

    def _refresh_collection_menu(self):
        if not hasattr(self, 'collection_menu'):
            return
        names = sorted(self._custom_collections.keys())
        if not names:
            self.collection_menu.configure(values=["No collections"])
            self.collection_menu.set("No collections")
            return
        self.collection_menu.configure(values=names)
        current = self._active_collection_name if self._active_collection_name in names else names[0]
        self._active_collection_name = current
        self.collection_menu.set(current)

    def _add_collection(self):
        name = (self.collection_name_var.get() if hasattr(self, 'collection_name_var') else "").strip()
        if not name:
            return
        if name not in self._custom_collections:
            self._custom_collections[name] = set()
        self._active_collection_name = name
        self._set_library_left_mode("collections", force_open=True)
        self._refresh_collection_menu()
        self.collection_name_var.set("")

    def _on_collection_selected(self, selection: str):
        if selection == "No collections":
            self._active_collection_name = None
            self._set_library_scope("All References")
            return
        if selection in self._custom_collections:
            self._active_collection_name = selection
            self._library_scope = "Collection"
            self._set_library_left_mode("collections", force_open=True)
            self._update_library_scope_buttons()
            self._apply_library_filter()

    def _remove_active_collection(self):
        if not self._active_collection_name:
            return
        self._custom_collections.pop(self._active_collection_name, None)
        self._active_collection_name = None
        self._refresh_collection_menu()
        self._set_library_scope("All References")

    def _get_selected_library_entry(self):
        if not hasattr(self, 'library_tree'):
            return None
        selected = self.library_tree.selection()
        if not selected:
            return None
        try:
            idx = int(selected[0])
        except Exception:
            return None
        if idx < 0 or idx >= len(self._library_filtered_entries):
            return None
        return self._library_filtered_entries[idx]

    def _add_selected_to_active_collection(self):
        if not self._active_collection_name or self._active_collection_name not in self._custom_collections:
            return
        entry = self._get_selected_library_entry()
        if not entry:
            return
        key = str(entry.get('ID', '')).strip()
        if not key:
            return
        self._custom_collections[self._active_collection_name].add(key)
        if self._library_scope == "Collection":
            self._apply_library_filter()

    def _change_library_density(self, mode: str):
        """Switch table row density between compact and comfortable."""
        row_height = 26 if mode == "Compact" else 34
        style = ttk.Style()
        style.configure(self._library_tree_style_name, rowheight=row_height)

    def _bind_library_shortcuts(self, search_entry):
        """Bind keyboard shortcuts for fast library navigation and actions."""
        self.root.bind_all('<Control-f>', lambda e: self._focus_library_search(search_entry))
        self.root.bind_all('<Control-d>', lambda e: self._delete_selected_library_entry())
        self.root.bind_all('<Control-c>', lambda e: self._copy_selected_key())
        self.root.bind_all('<Control-m>', lambda e: self._toggle_selected_favorite())

    def _focus_library_search(self, search_entry):
        try:
            search_entry.focus_set()
            search_entry.icursor('end')
        except Exception:
            pass

    def _add_library_entry_manual(self):
        """Quick-add a placeholder entry to speed manual curation demos."""
        new_entry = {
            'ID': f"new{len(self._library_entries) + 1}",
            'ENTRYTYPE': 'article',
            'author': 'New Author',
            'title': 'New Reference',
            'year': '',
            'journal': '',
            'doi': '',
            '_source_file_display': 'manual',
        }
        self._library_entries.append(new_entry)
        if self.manager:
            self.manager.all_entries = self._library_entries
        self._apply_library_filter()

    def _delete_selected_library_entry(self):
        """Delete selected entry from in-memory library view and manager dataset."""
        entry = self._get_selected_library_entry()
        if not entry:
            return
        try:
            self._library_entries.remove(entry)
        except ValueError:
            return
        if self.manager:
            self.manager.all_entries = self._library_entries
        self._selected_library_entry = None
        self._selected_library_key = ""
        self._apply_library_filter()

    def _export_selected_library_entry(self):
        """Export currently selected entry as a .bib snippet."""
        entry = self._get_selected_library_entry()
        if not entry:
            return
        path = filedialog.asksaveasfilename(
            title="Export Selected Entry",
            defaultextension=".bib",
            filetypes=[("BibTeX file", "*.bib"), ("All files", "*.*")],
            initialfile=f"{entry.get('ID', 'reference')}.bib",
        )
        if not path:
            return
        entrytype = str(entry.get('ENTRYTYPE', 'article'))
        key = str(entry.get('ID', 'reference'))
        lines = [f"@{entrytype}{{{key},"]
        for k in sorted(entry.keys()):
            if k.startswith('_') or k in {'ENTRYTYPE', 'ID'}:
                continue
            value = str(entry.get(k, '')).strip()
            if value:
                lines.append(f"  {k} = {{{value}}},")
        if lines[-1].endswith(','):
            lines[-1] = lines[-1][:-1]
        lines.append("}")
        with open(path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")
        self._set_status(f"Exported: {Path(path).name}", "#22c55e")

    def _show_library_context_menu(self, event):
        """Show row context menu with quick actions."""
        if not hasattr(self, 'library_tree'):
            return

        row = self.library_tree.identify_row(event.y)
        if not row:
            return
        self.library_tree.selection_set(row)
        self._on_library_row_selected()

        if self.library_context_menu is None:
            self.library_context_menu = tk.Menu(self.root, tearoff=0)
            self.library_context_menu.add_command(label="Copy Key", command=self._copy_selected_key)
            self.library_context_menu.add_command(label="Add to Active Collection", command=self._add_selected_to_active_collection)
            self.library_context_menu.add_command(label="Toggle Favorite", command=self._toggle_selected_favorite)
            self.library_context_menu.add_separator()
            self.library_context_menu.add_command(label="Review Duplicates", command=self._review_selected_duplicates)

        try:
            self.library_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.library_context_menu.grab_release()

    def _copy_selected_key(self):
        entry = self._get_selected_library_entry()
        if not entry:
            return
        key = str(entry.get('ID', '')).strip()
        if not key:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(key)
            self.root.update()
            self._set_status(f"Copied key: {key}", "#60a5fa")
        except Exception:
            pass

    def _review_selected_duplicates(self):
        entry = self._get_selected_library_entry()
        if not entry or not self.manager:
            return
        key = str(entry.get('ID', '')).strip()
        if not key:
            return

        self._update_duplicates()
        for idx, group in enumerate(self.manager.report_data.get('duplicate_groups', [])):
            group_keys = {str(e.get('ID', '')).strip() for e in group.get('entries', [])}
            if key in group_keys:
                self._selected_duplicate_group = idx
                self._sync_duplicate_selection_and_render()
                self.tabview.set("🔍 Duplicates")
                return

        self._set_status("No duplicate group for selected entry", "#f59e0b")

    def _save_selected_note(self):
        entry = self._get_selected_library_entry()
        if not entry or not hasattr(self, 'library_notes_text'):
            return
        key = str(entry.get('ID', '')).strip()
        if not key:
            return
        self._library_notes[key] = self.library_notes_text.get("1.0", "end").strip()
        self._set_status("Note saved", "#22c55e")

    def _save_selected_tags(self):
        entry = self._get_selected_library_entry()
        if not entry or not hasattr(self, 'library_tags_text'):
            return
        key = str(entry.get('ID', '')).strip()
        if not key:
            return
        self._library_tags[key] = self.library_tags_text.get("1.0", "end").strip()
        self._set_status("Tags saved", "#22c55e")

    def _save_selected_metadata(self):
        """Persist edits from the metadata mini-form back to selected entry."""
        entry = self._get_selected_library_entry()
        if not entry:
            return
        entry['author'] = self.meta_author_var.get().strip()
        entry['year'] = self.meta_year_var.get().strip()
        entry['title'] = self.meta_title_var.get().strip()
        source = self.meta_source_var.get().strip()
        if source:
            entry['journal'] = source
        else:
            entry.pop('journal', None)
        doi = self.meta_doi_var.get().strip()
        if doi:
            entry['doi'] = doi
        else:
            entry.pop('doi', None)
        self._refresh_library_tree()
        self._on_library_row_selected()
        self._set_status("Metadata saved (warnings update in status column)", "#22c55e")

    def _on_library_tree_click(self, event):
        """Single-click on status column toggles favorite, like desktop managers."""
        if not hasattr(self, 'library_tree'):
            return
        region = self.library_tree.identify_region(event.x, event.y)
        column = self.library_tree.identify_column(event.x)
        row = self.library_tree.identify_row(event.y)
        if region != "cell" or column != "#1" or not row:
            return
        try:
            idx = int(row)
        except Exception:
            return
        if idx < 0 or idx >= len(self._library_filtered_entries):
            return
        entry = self._library_filtered_entries[idx]
        entry['_favorite'] = not bool(entry.get('_favorite'))
        self._update_library_scope_buttons()
        self._refresh_library_tree()
        self.library_tree.selection_set(row)
        self._on_library_row_selected()

    def _toggle_selected_favorite(self, _event=None):
        entry = self._get_selected_library_entry()
        if not entry:
            return
        entry['_favorite'] = not bool(entry.get('_favorite'))
        self._update_library_scope_buttons()
        self._refresh_library_tree()

    def _load_library_entries(self):
        if not self.manager:
            self._library_entries = []
            self._library_filtered_entries = []
            self._update_library_scope_buttons()
            self._refresh_collection_menu()
            self._refresh_library_tree()
            return

        old_favorites = {
            str(e.get('ID', '')).strip(): bool(e.get('_favorite'))
            for e in self._library_entries
            if str(e.get('ID', '')).strip()
        }
        self._library_entries = list(self.manager.all_entries)
        for e in self._library_entries:
            key = str(e.get('ID', '')).strip()
            if key and key in old_favorites:
                e['_favorite'] = old_favorites[key]

        valid_keys = {str(e.get('ID', '')).strip() for e in self._library_entries if str(e.get('ID', '')).strip()}
        for name in list(self._custom_collections.keys()):
            self._custom_collections[name] = {k for k in self._custom_collections[name] if k in valid_keys}

        self._update_library_scope_buttons()
        self._refresh_collection_menu()
        self._apply_library_filter()

    def _apply_library_filter(self):
        entries = list(self._library_entries)
        duplicate_keys = set()
        if self.manager:
            for group in self.manager.report_data.get('duplicate_groups', []):
                for entry in group.get('entries', []):
                    key = str(entry.get('ID', '')).strip()
                    if key:
                        duplicate_keys.add(key)

        if self._library_scope == "Recently Added":
            entries = entries[-200:]
        elif self._library_scope == "Favorites":
            entries = [e for e in entries if e.get('_favorite')]
        elif self._library_scope == "Duplicate Items":
            entries = [e for e in entries if str(e.get('ID', '')).strip() in duplicate_keys]
        elif self._library_scope == "Collection" and self._active_collection_name in self._custom_collections:
            members = self._custom_collections[self._active_collection_name]
            entries = [e for e in entries if str(e.get('ID', '')).strip() in members]

        query = ""
        if hasattr(self, 'library_search_var'):
            query = (self.library_search_var.get() or "").strip().lower()
        if query:
            def _match(e):
                blob = " ".join([
                    str(e.get('ID', '')),
                    str(e.get('author', '')),
                    str(e.get('title', '')),
                    str(e.get('year', '')),
                    str(e.get('journal', '')),
                ]).lower()
                return query in blob
            entries = [e for e in entries if _match(e)]

        if hasattr(self, 'filter_duplicates_var') and self.filter_duplicates_var.get():
            entries = [e for e in entries if str(e.get('ID', '')).strip() in duplicate_keys]
        if hasattr(self, 'filter_doi_var') and self.filter_doi_var.get():
            entries = [e for e in entries if str(e.get('doi', '')).strip()]
        if hasattr(self, 'filter_missing_year_var') and self.filter_missing_year_var.get():
            entries = [e for e in entries if not str(e.get('year', '')).strip()]

        self._library_filtered_entries = entries
        self._refresh_library_tree()

    def _refresh_library_tree(self):
        if not hasattr(self, 'library_tree'):
            return

        if hasattr(self, 'library_count_badge'):
            shown = len(self._library_filtered_entries)
            total = len(self._library_entries)
            badge_text = f"{shown}/{total} refs" if total else "0 refs"
            self.library_count_badge.configure(text=badge_text)

        for item in self.library_tree.get_children():
            self.library_tree.delete(item)

        duplicate_key_set = {
            str(item.get('ID', '')).strip()
            for group in (self.manager.report_data.get('duplicate_groups', []) if self.manager else [])
            for item in group.get('entries', [])
            if str(item.get('ID', '')).strip()
        }

        for idx, entry in enumerate(self._library_filtered_entries):
            is_favorite = bool(entry.get('_favorite'))
            is_duplicate = str(entry.get('ID', '')).strip() in duplicate_key_set
            missing_core = not str(entry.get('author', '')).strip() or not str(entry.get('title', '')).strip() or not str(entry.get('year', '')).strip()
            markers = []
            if is_favorite:
                markers.append("★")
            if is_duplicate:
                markers.append("●")
            if missing_core:
                markers.append("⚠")
            status = " ".join(markers)
            author = str(entry.get('author', 'Unknown')).replace('{', '').replace('}', '')
            year = str(entry.get('year', ''))
            title = str(entry.get('title', 'No title')).replace('{', '').replace('}', '')
            source = str(entry.get('journal') or entry.get('booktitle') or entry.get('_source_file_display') or '')
            key = str(entry.get('ID', ''))
            self.library_tree.insert('', 'end', iid=str(idx), values=(status, author, year, title, source, key))

    def _sort_library_tree(self, column: str, numeric: bool):
        if not hasattr(self, 'library_tree'):
            return
        rows = [(self.library_tree.set(k, column), k) for k in self.library_tree.get_children('')]
        if numeric:
            rows.sort(key=lambda t: int(''.join(ch for ch in str(t[0]) if ch.isdigit()) or 0), reverse=True)
        else:
            rows.sort(key=lambda t: str(t[0]).lower())
        for pos, (_val, iid) in enumerate(rows):
            self.library_tree.move(iid, '', pos)

    def _on_library_row_selected(self, _event=None):
        if not hasattr(self, 'library_tree'):
            return
        selected = self.library_tree.selection()
        if not selected:
            return
        try:
            idx = int(selected[0])
        except Exception:
            return
        if idx < 0 or idx >= len(self._library_filtered_entries):
            return
        entry = self._library_filtered_entries[idx]
        self._selected_library_entry = entry
        self._selected_library_key = str(entry.get('ID', '')).strip()

        details = []
        details.append(f"Key: {entry.get('ID', '')}")
        details.append(f"Type: {entry.get('ENTRYTYPE', '')}")
        details.append(f"Author: {entry.get('author', '')}")
        details.append(f"Title: {entry.get('title', '')}")
        details.append(f"Year: {entry.get('year', '')}")
        details.append(f"Journal/Book: {entry.get('journal', entry.get('booktitle', ''))}")
        details.append(f"DOI: {entry.get('doi', '')}")
        details.append(f"Source File: {entry.get('_source_file_display', entry.get('_source_file', ''))}")
        details.append("")
        details.append("Raw fields")
        details.append("-" * 40)
        for k in sorted(entry.keys()):
            if k.startswith('_'):
                continue
            details.append(f"{k}: {entry.get(k, '')}")

        if hasattr(self, 'library_info_text'):
            self.library_info_text.delete("1.0", "end")
            self.library_info_text.insert("1.0", "\n".join(details))

        if hasattr(self, 'meta_author_var'):
            self.meta_author_var.set(str(entry.get('author', '')))
        if hasattr(self, 'meta_year_var'):
            self.meta_year_var.set(str(entry.get('year', '')))
        if hasattr(self, 'meta_title_var'):
            self.meta_title_var.set(str(entry.get('title', '')))
        if hasattr(self, 'meta_source_var'):
            self.meta_source_var.set(str(entry.get('journal', entry.get('booktitle', ''))))
        if hasattr(self, 'meta_doi_var'):
            self.meta_doi_var.set(str(entry.get('doi', '')))

        if hasattr(self, 'library_notes_text'):
            note = self._library_notes.get(self._selected_library_key, "")
            self.library_notes_text.delete("1.0", "end")
            self.library_notes_text.insert("1.0", note)

        if hasattr(self, 'library_tags_text'):
            tags = self._library_tags.get(self._selected_library_key, "")
            self.library_tags_text.delete("1.0", "end")
            self.library_tags_text.insert("1.0", tags)
        
    def _build_pipeline_tab(self):
        """Build pipeline execution tab with step cards"""
        tab = self.tabview.tab("📋 Pipeline")
        self.pipeline_tab = tab
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        
        # Steps timeline section
        steps_section = ctk.CTkFrame(tab, fg_color="transparent")
        steps_section.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        self.pipeline_steps_section = steps_section
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
        step_strip = ctk.CTkFrame(tab, corner_radius=6)
        step_strip.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 6))
        self.pipeline_step_strip = step_strip
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
        self.pipeline_log_label = log_label
        
        self.log_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word"
        )
        self.log_text.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tab.grid_rowconfigure(3, weight=1)
        self.pipeline_log_box = self.log_text
        
    def _build_results_tab(self):
        """Build the post-run dashboard surface."""
        tab = self.tabview.tab("📈 Dashboard")
        self.results_tab = tab
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        self.results_hero_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.results_hero_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        self.results_hero_frame.grid_columnconfigure(0, weight=1)

        self.results_title_label = ctk.CTkLabel(
            self.results_hero_frame,
            text="Post-run dashboard",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.results_title_label.grid(row=0, column=0, sticky="w")

        self.results_subtitle_label = ctk.CTkLabel(
            self.results_hero_frame,
            text="This view translates the pipeline into file, folder, and citation changes you can inspect.",
            font=ctk.CTkFont(size=10),
            text_color="#8f99ab",
        )
        self.results_subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.results_scope_label = ctk.CTkLabel(
            self.results_hero_frame,
            text="No run yet",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#94a3b8",
        )
        self.results_scope_label.grid(row=0, column=1, rowspan=2, sticky="e")

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.results_scroll = scroll
        scroll.grid_columnconfigure((0, 1), weight=1)

        self.stat_labels = {}
        self.stat_bars = {}
        stats = [
            ("📁 Files Scanned", "files", "Total .bib files discovered"),
            ("🗂 Folders Scanned", "folders", "Unique folders containing bibliography files"),
            ("📝 Initial Entries", "initial", "Entries before cleanup"),
            ("🔄 Duplicate Groups", "groups", "Clusters found during matching"),
            ("🗑️ Entries Removed", "removed", "Redundant entries dropped"),
            ("✅ Final Entries", "final", "Unique entries kept"),
            ("🔑 Keys Normalized", "keys", "Citation labels rewritten"),
            ("⚡ Processing Time", "time", "Total runtime"),
        ]

        for idx, (label, key, description) in enumerate(stats):
            row = idx // 2
            col = idx % 2
            card = ctk.CTkFrame(scroll, corner_radius=8)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="ew")
            card.grid_columnconfigure(0, weight=1)

            header_frame = ctk.CTkFrame(card, fg_color="transparent")
            header_frame.pack(fill="x", padx=12, pady=(12, 6))
            header_frame.grid_columnconfigure(0, weight=1)

            title = ctk.CTkLabel(header_frame, text=label, font=ctk.CTkFont(size=12, weight="bold"))
            title.grid(row=0, column=0, sticky="w")

            value = ctk.CTkLabel(header_frame, text="—", font=ctk.CTkFont(size=20, weight="bold"), text_color="#4ade80")
            value.grid(row=0, column=1, sticky="e")

            self.stat_labels[key] = value

            desc = ctk.CTkLabel(card, text=description, font=ctk.CTkFont(size=10), text_color="#888888")
            desc.pack(fill="x", padx=12, pady=(0, 8))

        self.results_metrics_frame = ctk.CTkFrame(scroll, corner_radius=8)
        self.results_metrics_frame.grid(row=4, column=0, columnspan=2, padx=8, pady=8, sticky="ew")
        self.results_metrics_frame.grid_columnconfigure((0, 1), weight=1)

        metrics_title = ctk.CTkLabel(self.results_metrics_frame, text="What changed", font=ctk.CTkFont(size=12, weight="bold"))
        metrics_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8))

        reduction_frame = ctk.CTkFrame(self.results_metrics_frame, fg_color="transparent")
        reduction_frame.grid(row=1, column=0, sticky="ew", padx=(12, 8), pady=(0, 12))
        reduction_frame.grid_columnconfigure(0, weight=1)

        rate_label = ctk.CTkLabel(reduction_frame, text="Duplicate reduction", font=ctk.CTkFont(size=10))
        rate_label.pack(fill="x")

        self.reduction_bar = ctk.CTkProgressBar(reduction_frame)
        self.reduction_bar.pack(fill="x", pady=(4, 2))
        self.reduction_bar.set(0)

        self.reduction_text = ctk.CTkLabel(reduction_frame, text="0%", font=ctk.CTkFont(size=10, weight="bold"), text_color="#fbbf24")
        self.reduction_text.pack(fill="x")

        keys_frame = ctk.CTkFrame(self.results_metrics_frame, fg_color="transparent")
        keys_frame.grid(row=1, column=1, sticky="ew", padx=(8, 12), pady=(0, 12))
        keys_frame.grid_columnconfigure(0, weight=1)

        keys_label = ctk.CTkLabel(keys_frame, text="Citation keys normalized", font=ctk.CTkFont(size=10))
        keys_label.pack(fill="x")

        self.keys_bar = ctk.CTkProgressBar(keys_frame)
        self.keys_bar.pack(fill="x", pady=(4, 2))
        self.keys_bar.set(0)

        self.keys_text = ctk.CTkLabel(keys_frame, text="0 keys", font=ctk.CTkFont(size=10, weight="bold"), text_color="#60a5fa")
        self.keys_text.pack(fill="x")

        insights = ctk.CTkFrame(scroll, fg_color="transparent")
        insights.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=0, pady=(4, 0))
        insights.grid_columnconfigure((0, 1), weight=1)

        self.results_summary_frame = ctk.CTkFrame(insights, corner_radius=8)
        self.results_summary_frame.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        self.results_summary_frame.grid_columnconfigure(0, weight=1)

        summary_header = ctk.CTkLabel(self.results_summary_frame, text="Executive summary", font=ctk.CTkFont(size=12, weight="bold"))
        summary_header.pack(fill="x", padx=12, pady=(12, 8))

        self.results_text = ctk.CTkTextbox(self.results_summary_frame, font=ctk.CTkFont(size=12), wrap="word", height=220)
        self.results_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.results_text_box = self.results_text
        self.results_text.insert("1.0", "Run the pipeline to see a summary of what changed.")

        self.results_files_frame = ctk.CTkFrame(insights, corner_radius=8)
        self.results_files_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.results_files_frame.grid_columnconfigure(0, weight=1)

        files_header = ctk.CTkLabel(self.results_files_frame, text="Most impacted files", font=ctk.CTkFont(size=12, weight="bold"))
        files_header.pack(fill="x", padx=12, pady=(12, 8))

        self.results_files_box = ctk.CTkTextbox(self.results_files_frame, font=ctk.CTkFont(family="Consolas", size=11), wrap="word", height=220)
        self.results_files_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.results_files_box.insert("1.0", "Changed files will appear here after a run.")

        self.results_folders_frame = ctk.CTkFrame(scroll, corner_radius=8)
        self.results_folders_frame.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))
        self.results_folders_frame.grid_columnconfigure(0, weight=1)

        folders_header = ctk.CTkLabel(self.results_folders_frame, text="Folders touched", font=ctk.CTkFont(size=12, weight="bold"))
        folders_header.pack(fill="x", padx=12, pady=(12, 8))

        self.results_folders_box = ctk.CTkTextbox(self.results_folders_frame, font=ctk.CTkFont(family="Consolas", size=11), wrap="word", height=180)
        self.results_folders_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.results_folders_box.insert("1.0", "Folder impact will appear here after a run.")

    def _build_fixes_tab(self):
        """Build fixes tab with a single inline IDE-style diff viewer."""
        tab = self.tabview.tab("🛠 Fixes")
        self.fixes_tab = tab
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=0)
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        self.fixes_controls = controls
        controls.grid_columnconfigure(1, weight=1)

        self.fix_file_menu = ctk.CTkOptionMenu(controls, values=["No changed files yet"], command=self._show_file_fix)
        self.fix_file_menu.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="w")
        self.fix_file_menu.set("No changed files yet")

        self.changed_info = ctk.CTkLabel(
            controls,
            text="Choose a file to inspect inline fixes",
            text_color="gray",
            anchor="w",
        )
        self.changed_info.grid(row=0, column=1, sticky="ew")

        self.show_unchanged_switch = ctk.CTkSwitch(
            controls,
            text="Show unchanged lines",
            variable=self._show_unchanged_var,
            onvalue=True,
            offvalue=False,
            command=self._refresh_current_fix_selection,
        )
        self.show_unchanged_switch.grid(row=0, column=2, padx=(10, 0), sticky="e")

        nav = ctk.CTkFrame(tab, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        self.fixes_nav = nav

        self.prev_change_btn = ctk.CTkButton(
            nav,
            text="◀ Prev Change",
            width=130,
            height=30,
            command=self._jump_prev_changed_line,
            state="disabled"
        )
        self.prev_change_btn.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.next_change_btn = ctk.CTkButton(
            nav,
            text="Next Change ▶",
            width=130,
            height=30,
            command=self._jump_next_changed_line,
            state="disabled"
        )
        self.next_change_btn.grid(row=0, column=1, padx=(0, 8), sticky="w")

        legend = ctk.CTkLabel(
            nav,
            text="IDE diff: ↺ replace (red old + green new), − delete (red), + insert (green)",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=11),
        )
        legend.grid(row=0, column=2, sticky="w")

        self.fixes_diff_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none"
        )
        self.fixes_diff_text.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.fixes_diff_box = self.fixes_diff_text

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
            if self.fixes_scrollbar:
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
            if self.fixes_scrollbar:
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
            if self.fixes_scrollbar:
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
            if self.fixes_h_scrollbar:
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
            if self.fixes_h_scrollbar:
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
            if self.fixes_h_scrollbar:
                self.fixes_h_scrollbar.set(first, last)
            if tk_orig:
                tk_orig.xview_moveto(float(first))
        finally:
            self._syncing_scroll_x = False

    def _scroll_to_changed_line(self, line_no: int):
        """Scroll unified fixes diff pane and center a target line number."""
        tk_diff = self._get_text_widget(self.fixes_diff_text)
        idx = f"{line_no}.0"
        try:
            if tk_diff:
                tk_diff.see(idx)
                # Keep the current navigation target visually obvious.
                try:
                    tk_diff.tag_delete('hl_current_change')
                except Exception:
                    pass
                tk_diff.tag_configure('hl_current_change', background='#fef08a', foreground='#111111')
                tk_diff.tag_add('hl_current_change', f"{line_no}.0", f"{line_no}.end")

                # Center the selected line in the viewport for unambiguous navigation.
                tk_diff.update_idletasks()
                last_line = int(float(tk_diff.index('end-1c').split('.')[0]))
                first_fraction, last_fraction = tk_diff.yview()
                visible_lines = max(int((last_fraction - first_fraction) * max(last_line, 1)), 1)
                desired_first_line = max(1, int(line_no - (visible_lines / 2)))
                max_first_line = max(1, last_line - visible_lines + 1)
                desired_first_line = min(desired_first_line, max_first_line)
                tk_diff.yview_moveto((desired_first_line - 1) / max(last_line, 1))
        except Exception:
            pass

    def _refresh_current_fix_selection(self):
        """Re-render current file in Fixes tab (used after diff display option changes)."""
        try:
            current = self.fix_file_menu.get()
        except Exception:
            current = None
        if current and current != "No changed files yet":
            self._show_file_fix(current)

    def _jump_next_changed_line(self):
        """Jump to the next changed line."""
        if not self._current_changed_display_lines:
            return
        self._current_changed_idx = (self._current_changed_idx + 1) % len(self._current_changed_display_lines)
        display_ln = self._current_changed_display_lines[self._current_changed_idx]
        self._scroll_to_changed_line(display_ln)
        source_ln = self._current_changed_lines[min(self._current_changed_idx, len(self._current_changed_lines) - 1)] if self._current_changed_lines else "?"
        self.changed_info.configure(
            text=f"Change {self._current_changed_idx + 1}/{len(self._current_changed_display_lines)} (source line {source_ln})"
        )

    def _jump_prev_changed_line(self):
        """Jump to the previous changed line."""
        if not self._current_changed_display_lines:
            return
        self._current_changed_idx = (self._current_changed_idx - 1) % len(self._current_changed_display_lines)
        display_ln = self._current_changed_display_lines[self._current_changed_idx]
        self._scroll_to_changed_line(display_ln)
        source_ln = self._current_changed_lines[min(self._current_changed_idx, len(self._current_changed_lines) - 1)] if self._current_changed_lines else "?"
        self.changed_info.configure(
            text=f"Change {self._current_changed_idx + 1}/{len(self._current_changed_display_lines)} (source line {source_ln})"
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
        self.duplicates_tab = tab
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
        self.duplicates_controls = controls
        controls.grid_columnconfigure(1, weight=1)

        self.dup_prev_btn = ctk.CTkButton(
            controls,
            text="◀ Prev",
            width=70,
            command=self._show_prev_duplicate_group,
            fg_color="gray25",
            hover=False,
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
            hover=False,
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
        self.duplicates_file_controls = file_controls
        file_controls.grid_columnconfigure(1, weight=1)

        self.dup_file_prev_btn = ctk.CTkButton(
            file_controls,
            text="◀ File",
            width=70,
            command=self._show_prev_duplicate_file,
            fg_color="gray25",
            hover=False,
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
            hover=False,
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
        self.duplicates_decision_panel = self.dup_decision_panel
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
        self.duplicates_text_box = self.duplicates_text
        self.duplicates_text.insert("1.0", "Run pipeline, then open this tab to view duplicates.\n")

    def _build_about_tab(self):
        """Build about/help tab"""
        tab = self.tabview.tab("ℹ️ About")
        self.about_tab = tab
        
        # Scrollable frame
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        self.about_scroll = scroll
        
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
        self.about_label = about_label
        
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
            self._load_library_preview_from_source(str(candidate))
        else:
            self._log_message("⚠️ test_data folder not found in current project")

    def _clear_for_next_run(self):
        """Clear logs/results quickly for a fresh demo run."""
        self.log_text.delete("1.0", "end")
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", "Run the pipeline to see a summary of what changed.")
        if hasattr(self, 'results_files_box'):
            self.results_files_box.delete("1.0", "end")
            self.results_files_box.insert("1.0", "Changed files will appear here after a run.")
        if hasattr(self, 'results_folders_box'):
            self.results_folders_box.delete("1.0", "end")
            self.results_folders_box.insert("1.0", "Folder impact will appear here after a run.")
        if hasattr(self, 'fixes_diff_text'):
            self.fixes_diff_text.delete("1.0", "end")
        self.changed_info.configure(text="")
        self._current_changed_lines = []
        self._current_changed_display_lines = []
        self._current_changed_idx = -1
        self.prev_change_btn.configure(state="disabled")
        self.next_change_btn.configure(state="disabled")
        self._library_entries = []
        self._library_filtered_entries = []
        self._selected_library_key = ""
        self._selected_library_entry = None
        if hasattr(self, 'library_info_text'):
            self.library_info_text.delete("1.0", "end")
            self.library_info_text.insert("1.0", "Choose a folder, then select a reference to view metadata.")
        if hasattr(self, 'meta_author_var'):
            self.meta_author_var.set("")
        if hasattr(self, 'meta_year_var'):
            self.meta_year_var.set("")
        if hasattr(self, 'meta_title_var'):
            self.meta_title_var.set("")
        if hasattr(self, 'meta_source_var'):
            self.meta_source_var.set("")
        if hasattr(self, 'meta_doi_var'):
            self.meta_doi_var.set("")
        if hasattr(self, 'library_notes_text'):
            self.library_notes_text.delete("1.0", "end")
        if hasattr(self, 'library_tags_text'):
            self.library_tags_text.delete("1.0", "end")
        self._update_library_scope_buttons()
        self._refresh_library_tree()
        self._set_status("Ready", "#3b8ed0")
        
    def _browse_directory(self):
        """Select a project folder and preview all discovered references immediately."""
        directory = filedialog.askdirectory(title="Select folder with .bib files")
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)
            self._load_library_preview_from_source(directory)

    def _browse_project_source_file(self):
        """Select a source file or archive and preview its bibliography content."""
        file_path = filedialog.askopenfilename(
            title="Select project source file",
            filetypes=[
                ("Supported sources", "*.zip *.tar *.tar.gz *.tgz *.bib *.tex"),
                ("Zip archives", "*.zip"),
                ("Tar archives", "*.tar *.tar.gz *.tgz"),
                ("BibTeX files", "*.bib"),
                ("LaTeX files", "*.tex"),
                ("All files", "*.*"),
            ],
        )
        if file_path:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, file_path)
            self._load_library_preview_from_source(file_path)

    def _load_library_preview_from_source(self, source_path: str):
        """Load raw references from a folder, archive, or bibliography file."""
        selected = Path(source_path)
        if not selected.exists():
            return

        temp_dir_obj = None
        working_directory = selected

        try:
            if selected.is_file():
                suffixes = [suffix.lower() for suffix in selected.suffixes]
                if selected.suffix.lower() == ".zip":
                    temp_dir_obj = tempfile.TemporaryDirectory()
                    with zipfile.ZipFile(str(selected), 'r') as zf:
                        zf.extractall(temp_dir_obj.name)
                    working_directory = Path(temp_dir_obj.name)
                elif selected.name.lower().endswith(('.tar.gz', '.tgz', '.tar')):
                    temp_dir_obj = tempfile.TemporaryDirectory()
                    mode = 'r:gz' if selected.name.lower().endswith(('.tar.gz', '.tgz')) else 'r'
                    with tarfile.open(str(selected), mode) as tf:
                        tf.extractall(temp_dir_obj.name)
                    working_directory = Path(temp_dir_obj.name)
                elif selected.suffix.lower() in {'.bib', '.tex'}:
                    working_directory = selected.parent
                else:
                    self._set_status("Unsupported source format", "#ef4444")
                    self._log_message(f"⚠️ Unsupported source file: {selected.name}")
                    return
            elif not selected.is_dir():
                return

            self.manager = BibliographyManager(str(working_directory))
            num_files, num_entries = self.manager.crawl_and_collect()
            self._load_library_entries()

            if num_entries > 0:
                self._set_status(f"Loaded {num_entries} refs from {num_files} files", "#22c55e")
                self._log_message(f"✓ Loaded {num_entries} references from {num_files} .bib file(s)")
            else:
                self._set_status("No references found", "#f59e0b")
                self._log_message("⚠️ No .bib entries found in selected source")
        except Exception as e:
            self._set_status("Preview load failed", "#ef4444")
            self._log_message(f"❌ Could not load references from source: {e}")
        finally:
            if temp_dir_obj is not None:
                try:
                    temp_dir_obj.cleanup()
                except Exception:
                    pass
            
    def _change_appearance(self, mode: str):
        """Change appearance mode without showing intermediate paint states."""
        requested_mode = (mode or "light").lower()
        if requested_mode == "system":
            requested_mode = "light"

        if requested_mode == self._theme_mode and self._last_applied_theme == requested_mode:
            return

        self._theme_mode = requested_mode

        if self._theme_apply_job is not None:
            try:
                self.root.after_cancel(self._theme_apply_job)
            except Exception:
                pass

        # Defer repaint so the option menu can fully close first.
        self._theme_apply_job = self.root.after(120, self._apply_pending_theme)

    def _apply_pending_theme(self):
        self._theme_apply_job = None
        self._apply_theme_palette(self._theme_mode)
        
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

    def _prepare_project_source(self, source_path: str):
        """Resolve a project source into a working directory and optional temp workspace."""
        selected = Path(source_path)
        temp_dir_obj = None

        if selected.is_dir():
            return selected, temp_dir_obj

        if not selected.is_file():
            raise FileNotFoundError(f"Source does not exist: {source_path}")

        source_name = selected.name.lower()
        if selected.suffix.lower() == ".zip":
            temp_dir_obj = tempfile.TemporaryDirectory()
            with zipfile.ZipFile(str(selected), 'r') as zf:
                zf.extractall(temp_dir_obj.name)
            return Path(temp_dir_obj.name), temp_dir_obj

        if source_name.endswith(('.tar.gz', '.tgz', '.tar')):
            temp_dir_obj = tempfile.TemporaryDirectory()
            mode = 'r:gz' if source_name.endswith(('.tar.gz', '.tgz')) else 'r'
            with tarfile.open(str(selected), mode) as tf:
                tf.extractall(temp_dir_obj.name)
            return Path(temp_dir_obj.name), temp_dir_obj

        if selected.suffix.lower() in {'.bib', '.tex'}:
            return selected.parent, temp_dir_obj

        raise ValueError(f"Unsupported project source format: {selected.suffix or source_name}")
        
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

            if input_path.is_file():
                source_name = input_path.name.lower()
                if input_path.suffix.lower() == ".zip" or source_name.endswith(('.tar.gz', '.tgz', '.tar')):
                    zip_mode = True
                    zip_input_path = input_path
                    self._log_message("📦 Source archive: extracting to temp workspace...")
                working_directory, temp_dir_obj = self._prepare_project_source(directory)
                if zip_mode:
                    self._log_message("✓ Archive extracted to temp workspace")
            elif input_path.is_dir():
                working_directory, temp_dir_obj = self._prepare_project_source(directory)
            
            self._log_message("="*60)
            self._log_message("🚀 Starting Bibliography Processing Pipeline")
            self._log_message("="*60)
            
            # Initialize manager
            self.manager = BibliographyManager(str(working_directory))
            self.manager.report_data['push_back'] = push_back
            self.manager.report_data['generate_report'] = generate_report
            
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
                archive_stem = zip_input_path.name
                for suffix in ('.tar.gz', '.tgz', '.tar', '.zip'):
                    if archive_stem.lower().endswith(suffix):
                        archive_stem = archive_stem[: -len(suffix)]
                        break
                cleaned_zip = zip_input_path.with_name(f"{archive_stem}_cleaned.zip")
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
            self._ui_call(self._load_library_entries)
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
        """Update the dashboard with a concrete summary of what changed."""
        if not self.manager:
            return
        
        data = self.manager.report_data
        file_changes = data.get('file_changes', {}) or {}
        source_files = data.get('source_files', {}) or {}

        scanned_folder_count = len({str(Path(info.get('relative_path', path)).parent) for path, info in source_files.items()}) if source_files else 0
        changed_file_items = list(file_changes.items())
        changed_file_count = len(changed_file_items)
        bib_changed_count = sum(1 for path in file_changes if str(path).lower().endswith('.bib'))
        tex_changed_count = sum(1 for path in file_changes if str(path).lower().endswith('.tex'))
        changed_folder_counts = Counter(str(Path(path).parent) for path in file_changes)

        def _change_rank(item):
            path, payload = item
            changed_lines = len(payload.get('changed_lines', []))
            original_text = payload.get('original', '') or ''
            updated_text = payload.get('updated', '') or ''
            size_delta = abs(len(updated_text) - len(original_text))
            return (changed_lines, size_delta, str(path).lower())

        sorted_file_changes = sorted(changed_file_items, key=_change_rank, reverse=True)
        
        # Update stat cards
        self.stat_labels['files'].configure(text=str(data['files_found']))
        self.stat_labels['folders'].configure(text=str(scanned_folder_count))
        self.stat_labels['initial'].configure(text=str(data['initial_entries']))
        self.stat_labels['groups'].configure(text=str(len(data['duplicate_groups'])))
        self.stat_labels['removed'].configure(text=str(data['duplicates_removed']))
        self.stat_labels['final'].configure(text=str(data['final_entries']))
        self.stat_labels['keys'].configure(text=str(len(data['keys_changed'])))
        
        # Calculate time
        if data['start_time'] and data['end_time']:
            duration = (data['end_time'] - data['start_time']).total_seconds()
            self.stat_labels['time'].configure(text=f"{duration:.1f}s")
        else:
            self.stat_labels['time'].configure(text="—")
        
        # Update progress bars with visual feedback
        reduction_rate = (data['duplicates_removed'] / max(data['initial_entries'], 1)) * 100
        self.reduction_bar.set(reduction_rate / 100.0)
        self.reduction_text.configure(text=f"{reduction_rate:.1f}% reduction")
        
        # Normalized keys progress (max reasonable is 500 keys)
        keys_count = len(data['keys_changed'])
        max_keys = max(500, keys_count + 1)
        self.keys_bar.set(min(keys_count / max_keys, 1.0))
        self.keys_text.configure(text=f"{keys_count} keys normalized")

        if hasattr(self, 'results_scope_label'):
            if data.get('push_back'):
                scope_text = "Changes pushed back to source folders"
            else:
                scope_text = "Review-only run; nothing was written back"
            self.results_scope_label.configure(text=scope_text)
        
        summary_lines = []
        summary_lines.append("What changed")
        summary_lines.append("=" * 50)
        summary_lines.append("")
        summary_lines.append(f"Scanned {data['files_found']} .bib file(s) across {scanned_folder_count} folder(s).")
        summary_lines.append(
            f"Removed {data['duplicates_removed']} duplicate entries from {data['initial_entries']} initial entries, leaving {data['final_entries']} unique references."
        )
        summary_lines.append(
            f"Normalized {len(data['keys_changed'])} citation key(s) and updated {data.get('tex_citation_updates', 0)} citation reference(s) in {data.get('tex_files_updated', 0)} .tex file(s)."
            if data.get('tex_citation_updates', 0)
            else f"Normalized {len(data['keys_changed'])} citation key(s)."
        )
        summary_lines.append(
            f"Changed {changed_file_count} file(s) across {len(changed_folder_counts)} folder(s): {bib_changed_count} .bib file(s) and {tex_changed_count} .tex file(s)."
        )
        summary_lines.append("")
        if data.get('push_back'):
            summary_lines.append("Changes were pushed back into the source folders.")
            summary_lines.append("Backups are available in timestamped backup folders beside the original .bib files.")
        else:
            summary_lines.append("This was a review-only run. Nothing was written back to the source folders.")
            summary_lines.append("Use the Pipeline tab to rerun with push-back enabled if you want the files updated in place.")
        summary_lines.append("")
        summary_lines.append("Next step: inspect the most changed files below, then open Fixes for line-level diffs if something looks off.")

        file_lines = []
        if sorted_file_changes:
            for path, payload in sorted_file_changes[:8]:
                changed_lines = len(payload.get('changed_lines', []))
                original_text = payload.get('original', '') or ''
                updated_text = payload.get('updated', '') or ''
                size_delta = len(updated_text) - len(original_text)
                delta_prefix = "+" if size_delta >= 0 else ""
                file_lines.append(f"{path}")
                file_lines.append(f"  {changed_lines} changed line(s), {delta_prefix}{size_delta} chars")
                file_lines.append("")
        else:
            file_lines.append("No file-level changes were recorded.")

        folder_lines = []
        if changed_folder_counts:
            folder_lines.append("Changed folders")
            folder_lines.append("=" * 40)
            for folder, count in sorted(changed_folder_counts.items(), key=lambda item: (-item[1], item[0])):
                folder_lines.append(f"{folder or '.'}: {count} changed file(s)")
        else:
            folder_lines.append("No folders were modified.")

        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", "\n".join(summary_lines))

        self.results_files_box.delete("1.0", "end")
        self.results_files_box.insert("1.0", "\n".join(file_lines).strip())

        self.results_folders_box.delete("1.0", "end")
        self.results_folders_box.insert("1.0", "\n".join(folder_lines).strip())

    def _format_dashboard_change_counts(self, data: dict) -> tuple[int, int, int]:
        """Return files, folders, and change counts for the dashboard."""
        file_changes = data.get('file_changes', {}) or {}
        source_files = data.get('source_files', {}) or {}
        scanned_folder_count = len({str(Path(info.get('relative_path', path)).parent) for path, info in source_files.items()}) if source_files else 0
        changed_folder_count = len({str(Path(path).parent) for path in file_changes}) if file_changes else 0
        changed_file_count = len(file_changes)
        return scanned_folder_count, changed_folder_count, changed_file_count
        
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
        """Display IDE-style unified inline diff for selected changed file."""
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

        orig_lines = orig.splitlines()
        upd_lines = upd.splitlines()
        matcher = difflib.SequenceMatcher(None, orig_lines, upd_lines)
        show_unchanged = bool(self._show_unchanged_var.get())
        context = self._diff_context_lines

        render_lines = []
        red_display_lines = []
        green_display_lines = []
        display_change_lines = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                block_len = i2 - i1
                if show_unchanged or block_len <= context * 2:
                    for offset in range(block_len):
                        src_ln = i1 + offset + 1
                        render_lines.append(f"{src_ln:4d}   {orig_lines[i1 + offset]}")
                else:
                    for offset in range(context):
                        src_ln = i1 + offset + 1
                        render_lines.append(f"{src_ln:4d}   {orig_lines[i1 + offset]}")
                    hidden = block_len - (context * 2)
                    render_lines.append(f"{'....':>4}   ... {hidden} unchanged lines hidden ...")
                    for offset in range(block_len - context, block_len):
                        src_ln = i1 + offset + 1
                        render_lines.append(f"{src_ln:4d}   {orig_lines[i1 + offset]}")
                continue

            chunk_first_display = len(render_lines) + 1
            marker = '↺' if tag == 'replace' else ('−' if tag == 'delete' else '+')
            render_lines.append(f"{'----':>4} {marker} --- {tag.upper()} ---")
            block_header_line = len(render_lines)

            if tag in ('replace', 'delete'):
                for idx in range(i1, i2):
                    src_ln = idx + 1
                    render_lines.append(f"{src_ln:4d} - {orig_lines[idx]}")
                    red_display_lines.append(len(render_lines))

            if tag in ('replace', 'insert'):
                for idx in range(j1, j2):
                    src_ln = idx + 1
                    render_lines.append(f"{src_ln:4d} + {upd_lines[idx]}")
                    green_display_lines.append(len(render_lines))

            display_change_lines.append(block_header_line if block_header_line else chunk_first_display)

        self.fixes_diff_text.delete('1.0', 'end')
        self.fixes_diff_text.insert('1.0', "\n".join(render_lines))

        tk_diff = self._get_text_widget(self.fixes_diff_text)
        if tk_diff:
            try:
                for tag_name in ('hl_removed', 'hl_added', 'hl_block_header', 'hl_fold'):
                    try:
                        tk_diff.tag_delete(tag_name)
                    except Exception:
                        pass
                tk_diff.tag_configure('hl_removed', background='#3a1f1f', foreground='#ffb4b4')
                tk_diff.tag_configure('hl_added', background='#153524', foreground='#b7f7cd')
                tk_diff.tag_configure('hl_block_header', background='#1f2937', foreground='#93c5fd')
                tk_diff.tag_configure('hl_fold', foreground='#94a3b8')

                for ln in red_display_lines:
                    tk_diff.tag_add('hl_removed', f"{ln}.0", f"{ln}.end")
                for ln in green_display_lines:
                    tk_diff.tag_add('hl_added', f"{ln}.0", f"{ln}.end")

                for i, content in enumerate(render_lines, start=1):
                    if content.endswith("---") and " --- " in content:
                        tk_diff.tag_add('hl_block_header', f"{i}.0", f"{i}.end")
                    if "unchanged lines hidden" in content:
                        tk_diff.tag_add('hl_fold', f"{i}.0", f"{i}.end")
            except Exception:
                pass

        # Show summary of changed lines
        if changed and display_change_lines:
            display = changed[:20]
            suffix = ' ...' if len(changed) > 20 else ''
            self._current_changed_lines = sorted(changed)
            self._current_changed_display_lines = sorted(set(display_change_lines))
            self._current_changed_idx = 0
            self.prev_change_btn.configure(state="normal")
            self.next_change_btn.configure(state="normal")
            source_ln = self._current_changed_lines[0] if self._current_changed_lines else "?"
            self.changed_info.configure(
                text=f"Change 1/{len(self._current_changed_display_lines)} (source line {source_ln})"
            )
            self._scroll_to_changed_line(self._current_changed_display_lines[0])
        else:
            self.changed_info.configure(text="No inline changes recorded.")
            self._current_changed_lines = []
            self._current_changed_display_lines = []
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
