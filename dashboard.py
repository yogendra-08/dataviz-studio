"""
dashboard.py
------------
The main Tkinter window: header, sidebar navigation, the six pages and the
status bar.  It connects the GUI to the other modules:

    data_handler     -> loading, filtering, sorting
    chart_generator  -> building charts
    stats_calculator -> statistics
    export_handler   -> saving PNG / CSV
"""

import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import chart_generator as charts
import export_handler
import stats_calculator
import styles
from data_handler import (ALL_COLUMNS, FILTER_MODES, DataHandler, DataLoadError,
                          FilterError)
from widgets import Card, ScrollableFrame, StatCard

C = styles.COLORS
APP_NAME = "DataViz Studio"
PAGES = ["Home", "Data & Preview", "Visualize", "Statistics", "Export", "About"]
SAMPLE_FILE = Path(__file__).resolve().parent / "sample_data.csv"
PAGE_SIZE = 200  # rows shown per preview page (keeps big files fast)

CHART_HINTS = {
    "Bar": "Groups the X column and shows a total (or the row count) for each group.",
    "Line": "Plots a numeric Y column against X. Repeated X values are combined.",
    "Pie": "Shows each category's share of the whole. Needs positive values.",
    "Scatter": "Plots two numeric columns to reveal relationships.",
    "Histogram": "Shows how the values of one numeric column are spread.",
}


class DashboardApp(tk.Tk):
    """The whole application window."""

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - Interactive Data Visualization")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        styles.apply_theme(self)

        self.data = DataHandler()
        self.figure = None              # the chart currently on screen
        self.chart_color = C["accent"]
        self.preview_page = 0
        self.pages = {}
        self.nav_items = {}

        self._build_layout()
        self.show_page("Home")
        self._on_dataset_changed()
        self.set_status("Welcome! Upload a dataset or load the sample data to begin.")

    # ======================================================================
    # Window skeleton: header, sidebar, content area, status bar
    # ======================================================================
    def _build_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header()

        body = tk.Frame(self, bg=C["bg"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        self._build_sidebar(body)

        content = tk.Frame(body, bg=C["bg"])
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        builders = {
            "Home": self._build_home_page,
            "Data & Preview": self._build_preview_page,
            "Visualize": self._build_visualize_page,
            "Statistics": self._build_statistics_page,
            "Export": self._build_export_page,
            "About": self._build_about_page,
        }
        for name in PAGES:
            page = tk.Frame(content, bg=C["bg"])
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_columnconfigure(0, weight=1)
            self.pages[name] = page
            builders[name](page)

        self._build_status_bar()

    def _build_header(self):
        header = tk.Frame(self, bg=C["navy"], height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(2, weight=1)

        # A small bar-chart icon drawn on a canvas
        icon = tk.Canvas(header, width=38, height=38, bg=C["navy"], highlightthickness=0)
        icon.grid(row=0, column=0, padx=(20, 10), pady=13)
        icon.create_rectangle(4, 22, 12, 34, fill="#60A5FA", outline="")
        icon.create_rectangle(15, 12, 23, 34, fill="#3B82F6", outline="")
        icon.create_rectangle(26, 4, 34, 34, fill="#93C5FD", outline="")

        titles = tk.Frame(header, bg=C["navy"])
        titles.grid(row=0, column=1, sticky="w")
        tk.Label(titles, text=APP_NAME, bg=C["navy"], fg=C["white"],
                 font=styles.font(17, "bold")).pack(anchor="w")
        tk.Label(titles, text="Interactive Data Visualization", bg=C["navy"], fg="#8FA8D6",
                 font=styles.font(9)).pack(anchor="w")

        self.header_info = tk.Label(header, text="", bg=C["navy"], fg="#C9D6EE",
                                    font=styles.font(10))
        self.header_info.grid(row=0, column=2, sticky="e", padx=24)

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=C["sidebar"], width=210)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="MENU", bg=C["sidebar"], fg="#7F97C4",
                 font=styles.font(9, "bold")).pack(anchor="w", padx=24, pady=(24, 8))
        for name in PAGES:
            self._add_nav_item(sidebar, name)
        tk.Label(sidebar, text="v1.0  -  College Project", bg=C["sidebar"], fg="#7F97C4",
                 font=styles.font(9)).pack(side="bottom", anchor="w", padx=24, pady=16)

    def _add_nav_item(self, parent, name):
        row = tk.Frame(parent, bg=C["sidebar"], height=44, cursor="hand2")
        row.pack(fill="x")
        row.pack_propagate(False)
        indicator = tk.Frame(row, bg=C["sidebar"], width=4)
        indicator.pack(side="left", fill="y")
        label = tk.Label(row, text=name, bg=C["sidebar"], fg=C["sidebar_text"],
                         font=styles.font(11), anchor="w", cursor="hand2")
        label.pack(side="left", fill="both", expand=True, padx=(20, 0))
        self.nav_items[name] = (row, indicator, label)

        def on_enter(_e):
            if self._active_page != name:
                self._paint_nav(name, C["sidebar_hover"], C["sidebar"], C["white"])

        def on_leave(_e):
            if self._active_page != name:
                self._paint_nav(name, C["sidebar"], C["sidebar"], C["sidebar_text"])

        for widget in (row, indicator, label):
            widget.bind("<Button-1>", lambda _e, n=name: self.show_page(n))
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    _active_page = None

    def _paint_nav(self, name, bg, indicator_bg, fg):
        row, indicator, label = self.nav_items[name]
        row.configure(bg=bg)
        label.configure(bg=bg, fg=fg)
        indicator.configure(bg=indicator_bg)

    def _build_status_bar(self):
        bar = tk.Frame(self, bg=C["card"], height=30, highlightthickness=1,
                       highlightbackground=C["border"])
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)
        self.status_dot = tk.Label(bar, text="\u25CF", bg=C["card"], fg=C["muted"],
                                   font=styles.font(9))
        self.status_dot.grid(row=0, column=0, padx=(14, 4), pady=4)
        self.status_label = tk.Label(bar, text="", bg=C["card"], fg=C["muted"],
                                     font=styles.font(10), anchor="w")
        self.status_label.grid(row=0, column=1, sticky="ew")
        tk.Label(bar, text=APP_NAME, bg=C["card"], fg=C["muted"],
                 font=styles.font(9)).grid(row=0, column=2, padx=14)

    # ======================================================================
    # Navigation and status
    # ======================================================================
    def show_page(self, name):
        """Bring one page to the front and highlight its menu item."""
        self.pages[name].tkraise()
        if self._active_page and self._active_page != name:
            self._paint_nav(self._active_page, C["sidebar"], C["sidebar"], C["sidebar_text"])
        self._active_page = name
        self._paint_nav(name, C["sidebar_active"], C["accent"], C["white"])

    def set_status(self, message, kind="info"):
        """Show a message in the status bar (kind: info, success or error)."""
        color = styles.STATUS_COLORS.get(kind, C["muted"])
        self.status_dot.configure(fg=color)
        self.status_label.configure(text=message, fg=color if kind != "info" else C["text"])

    # ======================================================================
    # Reusable GUI helpers
    # ======================================================================
    def _page_header(self, page, title, subtitle):
        frame = tk.Frame(page, bg=C["bg"])
        frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        tk.Label(frame, text=title, bg=C["bg"], fg=C["navy"],
                 font=styles.font(20, "bold")).pack(anchor="w")
        tk.Label(frame, text=subtitle, bg=C["bg"], fg=C["muted"],
                 font=styles.font(10)).pack(anchor="w", pady=(2, 0))

    @staticmethod
    def _caption(parent, text, pady=(12, 3)):
        label = tk.Label(parent, text=text, bg=C["card"], fg=C["muted"],
                         font=styles.font(9, "bold"), anchor="w")
        label.pack(fill="x", pady=pady)
        return label

    def _make_table(self, parent, height=8):
        """A Treeview with vertical and horizontal scrollbars. Returns (holder, tree)."""
        holder = tk.Frame(parent, bg=C["card"])
        holder.grid_rowconfigure(0, weight=1)
        holder.grid_columnconfigure(0, weight=1)
        tree = ttk.Treeview(holder, show="headings", selectmode="browse", height=height)
        vsb = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(holder, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree.tag_configure("odd", background=C["row_alt"])
        return holder, tree

    @staticmethod
    def _fill_table(tree, columns, rows, right_align=(), stretch=False,
                    sort_command=None, sort_state=None):
        """Replace the contents of a Treeview with new columns and rows."""
        tree.delete(*tree.get_children())
        ids = [f"c{i}" for i in range(len(columns))]
        tree["columns"] = ids
        sample = rows[:60]
        for i, (cid, name) in enumerate(zip(ids, columns)):
            arrow = ""
            if sort_state and sort_state[0] == name:
                arrow = "  \u25B2" if sort_state[1] else "  \u25BC"
            command = (lambda n=name: sort_command(n)) if sort_command else ""
            tree.heading(cid, text=name + arrow, command=command, anchor="w")
            longest = max([len(str(r[i])) for r in sample] + [len(name) + 3])
            tree.column(cid, width=min(max(longest * 8 + 24, 80), 280), minwidth=60,
                        anchor="e" if name in right_align else "w", stretch=stretch)
        for index, row in enumerate(rows):
            tree.insert("", "end", values=row, tags=("odd",) if index % 2 else ())

    def _primary_button(self, parent, text, command):
        return ttk.Button(parent, text=text, command=command, style="Accent.TButton",
                          cursor="hand2")

    def _secondary_button(self, parent, text, command):
        return ttk.Button(parent, text=text, command=command, style="Secondary.TButton",
                          cursor="hand2")

    # ======================================================================
    # HOME PAGE
    # ======================================================================
    def _build_home_page(self, page):
        self._page_header(page, "Welcome to DataViz Studio",
                          "Load a dataset, explore it, build charts and export your results.")
        page.grid_columnconfigure(0, weight=1)

        # --- Upload card -------------------------------------------------
        upload = Card(page, title="Upload Dataset")
        upload.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 14))
        body = upload.body
        body.grid_columnconfigure(0, weight=1)
        tk.Label(body, text="Supported files: CSV (.csv) and Excel (.xlsx, .xls)",
                 bg=C["card"], fg=C["muted"], font=styles.font(10)).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        self.home_file_label = tk.Label(body, text="No file selected", bg=C["heading_bg"],
                                        fg=C["navy"], font=styles.font(11, "bold"),
                                        anchor="w", padx=14, pady=9)
        self.home_file_label.grid(row=1, column=0, sticky="ew", padx=(0, 12))
        self._primary_button(body, "Browse...", self.browse_file).grid(row=1, column=1,
                                                                       padx=(0, 8))
        self._secondary_button(body, "Load Sample Data", self.load_sample).grid(row=1, column=2)
        self.home_dim_label = tk.Label(body, text="", bg=C["card"], fg=C["muted"],
                                       font=styles.font(10), anchor="w")
        self.home_dim_label.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

        # --- Stat cards --------------------------------------------------
        cards = tk.Frame(page, bg=C["bg"])
        cards.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 14))
        self.home_cards = {}
        for i, (key, caption, accent) in enumerate([
                ("rows", "Rows", C["accent"]), ("columns", "Columns", C["teal"]),
                ("missing", "Missing values", C["amber"]),
                ("numeric_columns", "Numeric columns", C["violet"])]):
            cards.grid_columnconfigure(i, weight=1, uniform="home_cards")
            card = StatCard(cards, caption, accent)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 7, 7 if i < 3 else 0))
            self.home_cards[key] = card

        # --- Quick actions and guide ------------------------------------------
        lower = tk.Frame(page, bg=C["bg"])
        lower.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 20))
        lower.grid_columnconfigure(0, weight=1, uniform="lower")
        lower.grid_columnconfigure(1, weight=1, uniform="lower")
        page.grid_rowconfigure(3, weight=1)

        actions = Card(lower, title="Quick Actions")
        actions.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        for text, target in [("Preview & filter data", "Data & Preview"),
                             ("Create a chart", "Visualize"),
                             ("View statistics", "Statistics"),
                             ("Export results", "Export")]:
            self._secondary_button(actions.body, text,
                                   lambda t=target: self.show_page(t)).pack(fill="x", pady=4)

        guide = Card(lower, title="Getting Started")
        guide.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        steps = ("1.  Upload a CSV or Excel file (or load the sample data).\n\n"
                 "2.  Open Data & Preview to browse rows, search and filter.\n\n"
                 "3.  Open Visualize, pick a chart type and columns, then click Generate Chart.\n\n"
                 "4.  Check Statistics for a summary of every column.\n\n"
                 "5.  Use Export to save the chart (PNG) or the filtered data (CSV).")
        tk.Label(guide.body, text=steps, bg=C["card"], fg=C["text"], font=styles.font(10),
                 justify="left", anchor="nw", wraplength=440).pack(anchor="w")

    # ======================================================================
    # DATA & PREVIEW PAGE
    # ======================================================================
    def _build_preview_page(self, page):
        self._page_header(page, "Data & Preview",
                          "Browse your dataset, search a column and filter the rows. "
                          "Click a column heading to sort.")
        page.grid_rowconfigure(2, weight=1)

        # --- Search / filter bar ----------------------------------------
        bar = Card(page, padding=14)
        bar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        b = bar.body
        b.grid_columnconfigure(4, weight=1)

        self.filter_col_var = tk.StringVar(value=ALL_COLUMNS)
        self.filter_mode_var = tk.StringVar(value=FILTER_MODES[0])
        self.filter_value_var = tk.StringVar()

        def field(col, caption, widget):
            tk.Label(b, text=caption, bg=C["card"], fg=C["muted"],
                     font=styles.font(9, "bold")).grid(row=0, column=col, sticky="w", padx=(0, 10))
            widget.grid(row=1, column=col, sticky="ew", padx=(0, 10))

        self.filter_col_combo = ttk.Combobox(b, textvariable=self.filter_col_var,
                                             state="readonly", width=20)
        field(0, "COLUMN", self.filter_col_combo)
        field(1, "MATCH", ttk.Combobox(b, textvariable=self.filter_mode_var,
                                       values=FILTER_MODES, state="readonly", width=13))
        entry = ttk.Entry(b, textvariable=self.filter_value_var, width=26)
        entry.bind("<Return>", lambda _e: self.apply_filter())
        field(2, "VALUE", entry)
        buttons = tk.Frame(b, bg=C["card"])
        buttons.grid(row=1, column=3, sticky="w")
        self._primary_button(buttons, "Apply Filter", self.apply_filter).pack(side="left")
        self._secondary_button(buttons, "Clear Filter", self.clear_filter).pack(side="left",
                                                                                padx=(8, 0))

        # --- Table card -----------------------------------------------------
        card = Card(page, padding=12)
        card.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 20))
        card.body.grid_rowconfigure(1, weight=1)
        card.body.grid_columnconfigure(0, weight=1)

        self.preview_info = tk.Label(card.body, text="", bg=C["card"], fg=C["muted"],
                                     font=styles.font(10), anchor="w")
        self.preview_info.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        holder, self.preview_tree = self._make_table(card.body, height=10)
        holder.grid(row=1, column=0, sticky="nsew")

        pager = tk.Frame(card.body, bg=C["card"])
        pager.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.prev_btn = self._secondary_button(pager, "\u25C0  Previous",
                                               lambda: self._change_preview_page(-1))
        self.prev_btn.pack(side="left")
        self.page_label = tk.Label(pager, text="", bg=C["card"], fg=C["text"],
                                   font=styles.font(10))
        self.page_label.pack(side="left", padx=14)
        self.next_btn = self._secondary_button(pager, "Next  \u25B6",
                                               lambda: self._change_preview_page(1))
        self.next_btn.pack(side="left")
        self._secondary_button(pager, "Export Current View as CSV",
                               self.export_dataset).pack(side="right")

    # ---- preview actions --------------------------------------------------
    def apply_filter(self):
        if not self.data.has_data:
            self._warn("No dataset", "Load a dataset first.")
            return
        try:
            self.data.apply_filter(self.filter_col_var.get(), self.filter_mode_var.get(),
                                   self.filter_value_var.get())
        except FilterError as exc:
            self.set_status(str(exc), "error")
            messagebox.showwarning("Cannot apply filter", str(exc))
            return
        self.preview_page = 0
        self._refresh_data_views()
        count = len(self.data.current)
        if count:
            self.set_status(f"Filter applied: {count:,} of {len(self.data.original):,} "
                            "rows match.", "success")
        else:
            self.set_status("Filter applied, but no rows match. Try a different value.", "error")

    def clear_filter(self):
        if not self.data.has_data:
            return
        self.data.clear_filter()
        self.filter_value_var.set("")
        self.filter_col_var.set(ALL_COLUMNS)
        self.preview_page = 0
        self._refresh_data_views()
        self.set_status("Filter cleared - showing all rows again.", "success")

    def _sort_by(self, column):
        ascending = True
        if self.data.sort_state and self.data.sort_state[0] == column:
            ascending = not self.data.sort_state[1]
        self.data.sort_current(column, ascending)
        self.preview_page = 0
        self._refresh_data_views()
        self.set_status(f"Sorted by '{column}' ({'ascending' if ascending else 'descending'}).")

    def _change_preview_page(self, step):
        self.preview_page += step
        self._refresh_preview()

    # ======================================================================
    # VISUALIZE PAGE
    # ======================================================================
    def _build_visualize_page(self, page):
        self._page_header(page, "Visualize",
                          "Choose a chart type and columns, customise the look, then generate.")
        page.grid_rowconfigure(1, weight=1)

        pane = ttk.PanedWindow(page, orient="horizontal")
        pane.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))

        # --- Left: settings ------------------------------------------------
        settings = Card(pane, title="Chart Settings", padding=12)
        # Action buttons stay pinned at the bottom, always visible
        actions = tk.Frame(settings.body, bg=C["card"])
        actions.pack(side="bottom", fill="x", pady=(10, 0))
        self._primary_button(actions, "Generate Chart", self.generate_chart).pack(fill="x")
        self._secondary_button(actions, "Save Chart as PNG", self.export_chart).pack(
            fill="x", pady=(6, 0))

        scroll = ScrollableFrame(settings.body, width=290)
        scroll.pack(side="top", fill="both", expand=True)
        form = scroll.inner
        form.configure(padx=2)

        self.chart_type_var = tk.StringVar(value="Bar")
        self.x_var = tk.StringVar()
        self.y_var = tk.StringVar()
        self.agg_var = tk.StringVar(value="Sum")
        self.bins_var = tk.StringVar(value="10")
        self.title_var = tk.StringVar()
        self.xlabel_var = tk.StringVar()
        self.ylabel_var = tk.StringVar()
        self.grid_var = tk.BooleanVar(value=True)

        self._caption(form, "CHART TYPE", pady=(0, 3))
        type_combo = ttk.Combobox(form, textvariable=self.chart_type_var,
                                  values=charts.CHART_TYPES, state="readonly")
        type_combo.pack(fill="x")
        type_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_axis_options())
        self.chart_hint = tk.Label(form, text="", bg=C["card"], fg=C["muted"],
                                   font=styles.font(9), justify="left", anchor="w",
                                   wraplength=260)
        self.chart_hint.pack(fill="x", pady=(4, 0))

        self._caption(form, "X-AXIS COLUMN")
        self.x_combo = ttk.Combobox(form, textvariable=self.x_var, state="readonly")
        self.x_combo.pack(fill="x")
        self._caption(form, "Y-AXIS COLUMN")
        self.y_combo = ttk.Combobox(form, textvariable=self.y_var, state="readonly")
        self.y_combo.pack(fill="x")

        self._caption(form, "AGGREGATION")
        self.agg_combo = ttk.Combobox(form, textvariable=self.agg_var,
                                      values=list(charts.AGGREGATIONS), state="readonly")
        self.agg_combo.pack(fill="x")
        self._caption(form, "NUMBER OF BINS (HISTOGRAM)")
        self.bins_spin = ttk.Spinbox(form, from_=1, to=200, textvariable=self.bins_var,
                                     width=8)
        self.bins_spin.pack(anchor="w")

        self._caption(form, "CHART TITLE")
        ttk.Entry(form, textvariable=self.title_var).pack(fill="x")
        self._caption(form, "X-AXIS LABEL")
        ttk.Entry(form, textvariable=self.xlabel_var).pack(fill="x")
        self._caption(form, "Y-AXIS LABEL")
        ttk.Entry(form, textvariable=self.ylabel_var).pack(fill="x")
        tk.Label(form, text="Leave titles and labels empty to generate them automatically.",
                 bg=C["card"], fg=C["muted"], font=styles.font(9), anchor="w",
                 justify="left", wraplength=260).pack(fill="x", pady=(4, 0))

        self._caption(form, "CHART COLOUR")
        colour_row = tk.Frame(form, bg=C["card"])
        colour_row.pack(fill="x")
        self.color_swatch = tk.Label(colour_row, bg=self.chart_color, width=4, height=1,
                                     highlightthickness=1, highlightbackground=C["border"])
        self.color_swatch.pack(side="left")
        self.color_label = tk.Label(colour_row, text=self.chart_color, bg=C["card"],
                                    fg=C["text"], font=styles.font(10))
        self.color_label.pack(side="left", padx=8)
        ttk.Button(colour_row, text="Pick...", style="Secondary.TButton",
                   command=self.pick_color, cursor="hand2").pack(side="right")
        presets = tk.Frame(form, bg=C["card"])
        presets.pack(fill="x", pady=(8, 0))
        for colour in styles.CHART_PALETTE:
            chip = tk.Label(presets, bg=colour, width=2, cursor="hand2",
                            highlightthickness=1, highlightbackground=C["border"])
            chip.pack(side="left", padx=(0, 5))
            chip.bind("<Button-1>", lambda _e, col=colour: self._set_chart_color(col))

        ttk.Checkbutton(form, text="Show grid lines", variable=self.grid_var,
                        style="Card.TCheckbutton").pack(anchor="w", pady=(14, 0))

        pane.add(settings, weight=0)

        # --- Right: chart preview -----------------------------------------
        preview = Card(pane, title="Chart Preview", padding=12)
        self.chart_note = tk.Label(preview.body, text="", bg=C["card"], fg=C["muted"],
                                   font=styles.font(9), anchor="w")
        self.chart_note.pack(fill="x", pady=(0, 6))
        self.chart_holder = tk.Frame(preview.body, bg=C["card"])
        self.chart_holder.pack(fill="both", expand=True)
        pane.add(preview, weight=1)

        self._show_chart_placeholder()
        self._update_axis_options()

    # ---- axis controls ----------------------------------------------------
    def _update_axis_options(self):
        """Refill the X / Y lists to suit the selected chart type."""
        ctype = self.chart_type_var.get()
        self.chart_hint.configure(text=CHART_HINTS.get(ctype, ""))
        all_cols = self.data.columns()
        numeric = self.data.numeric_columns()

        x_options = numeric if ctype in ("Scatter", "Histogram") else all_cols
        if ctype in ("Bar", "Pie"):
            y_options = [charts.COUNT_OPTION] + numeric
        elif ctype in ("Line", "Scatter"):
            y_options = numeric
        else:
            y_options = []

        self.x_combo.configure(values=x_options)
        if self.x_var.get() not in x_options:
            self.x_var.set(x_options[0] if x_options else "")
        self.y_combo.configure(values=y_options)
        if self.y_var.get() not in y_options:
            if ctype in ("Bar", "Pie"):
                self.y_var.set(charts.COUNT_OPTION)
            elif y_options:
                # Prefer a numeric column different from X (nicer default for scatter)
                others = [c for c in y_options if c != self.x_var.get()]
                self.y_var.set((others or y_options)[0])
            else:
                self.y_var.set("")

        def toggle(widget, enabled, readonly=True):
            widget.configure(state=("readonly" if readonly else "normal") if enabled
                             else "disabled")

        toggle(self.y_combo, ctype != "Histogram")
        toggle(self.agg_combo, ctype in ("Bar", "Line", "Pie"))
        toggle(self.bins_spin, ctype == "Histogram", readonly=False)

    def _set_chart_color(self, colour):
        self.chart_color = colour
        self.color_swatch.configure(bg=colour)
        self.color_label.configure(text=colour.upper())

    def pick_color(self):
        _rgb, hex_colour = colorchooser.askcolor(color=self.chart_color,
                                                 title="Choose chart colour", parent=self)
        if hex_colour:
            self._set_chart_color(hex_colour)

    # ---- chart actions ----------------------------------------------------
    def generate_chart(self):
        if not self.data.has_data:
            self._warn("No dataset", "Load a dataset first (Home > Browse...).")
            self.show_page("Home")
            return
        try:
            bins = int(self.bins_var.get())
        except ValueError:
            bins = 0  # chart_generator reports a friendly error for histograms
        spec = charts.ChartSpec(
            chart_type=self.chart_type_var.get(), x=self.x_var.get(), y=self.y_var.get(),
            agg=self.agg_var.get(), bins=bins, title=self.title_var.get().strip(),
            xlabel=self.xlabel_var.get().strip(), ylabel=self.ylabel_var.get().strip(),
            color=self.chart_color, grid=self.grid_var.get())
        try:
            figure = charts.create_chart(self.data.current, spec)
        except charts.ChartError as exc:
            self.set_status(str(exc).splitlines()[0], "error")
            messagebox.showwarning("Cannot create chart", str(exc))
            return
        except Exception as exc:  # unexpected problem: report, do not crash
            self.set_status("Chart could not be created.", "error")
            messagebox.showerror("Chart error", f"Something went wrong:\n\n{exc}")
            return
        self._show_figure(figure)
        self.set_status(f"{spec.chart_type} chart generated from "
                        f"{len(self.data.current):,} rows.", "success")

    def _show_figure(self, figure):
        """Embed a Matplotlib figure inside the chart preview area."""
        for child in self.chart_holder.winfo_children():
            child.destroy()
        self.figure = figure
        toolbar_frame = tk.Frame(self.chart_holder, bg=C["card"])
        toolbar_frame.pack(side="bottom", fill="x")
        canvas = FigureCanvasTkAgg(figure, master=self.chart_holder)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        for widget in [toolbar, *toolbar.winfo_children()]:  # match the card colour
            try:
                widget.configure(background=C["card"])
            except tk.TclError:
                pass
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.draw()
        self._update_export_info()

    def _show_chart_placeholder(self):
        for child in self.chart_holder.winfo_children():
            child.destroy()
        self.figure = None
        tk.Label(self.chart_holder, bg=C["card"], fg=C["muted"], font=styles.font(12),
                 justify="center",
                 text="Your chart will appear here.\n\n"
                      "Pick a chart type and columns on the left,\n"
                      "then click  Generate Chart.").place(relx=0.5, rely=0.45,
                                                          anchor="center")
        self._update_export_info()

    # ======================================================================
    # STATISTICS PAGE
    # ======================================================================
    def _build_statistics_page(self, page):
        self._page_header(page, "Statistics",
                          "A summary of the dataset as currently filtered.")
        page.grid_rowconfigure(2, weight=1)
        page.grid_rowconfigure(3, weight=1)

        cards = tk.Frame(page, bg=C["bg"])
        cards.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        self.stat_cards = {}
        for i, (key, caption, accent) in enumerate([
                ("rows", "Rows", C["accent"]), ("columns", "Columns", C["teal"]),
                ("missing", "Missing values", C["amber"]),
                ("duplicates", "Duplicate rows", C["rose"])]):
            cards.grid_columnconfigure(i, weight=1, uniform="stat_cards")
            card = StatCard(cards, caption, accent)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 7, 7 if i < 3 else 0))
            self.stat_cards[key] = card

        numeric_card = Card(page, title="Numeric Columns", padding=12)
        numeric_card.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 12))
        numeric_card.body.grid_rowconfigure(0, weight=1)
        numeric_card.body.grid_columnconfigure(0, weight=1)
        holder, self.numeric_tree = self._make_table(numeric_card.body, height=4)
        holder.grid(row=0, column=0, sticky="nsew")

        text_card = Card(page, title="Text & Date Columns", padding=12)
        text_card.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 20))
        text_card.body.grid_rowconfigure(0, weight=1)
        text_card.body.grid_columnconfigure(0, weight=1)
        holder, self.category_tree = self._make_table(text_card.body, height=4)
        holder.grid(row=0, column=0, sticky="nsew")

    def _refresh_statistics(self):
        if not self.data.has_data:
            for card in self.stat_cards.values():
                card.set("-")
            self._fill_table(self.numeric_tree, ["Info"], [["No dataset loaded"]], stretch=True)
            self._fill_table(self.category_tree, ["Info"], [["No dataset loaded"]], stretch=True)
            return
        df = self.data.current
        overview = stats_calculator.dataset_overview(df)
        for key, card in self.stat_cards.items():
            card.set(f"{overview[key]:,}")

        numeric = stats_calculator.numeric_summary(df)
        if numeric.empty:
            self._fill_table(self.numeric_tree, ["Info"],
                             [["This dataset has no numeric columns."]], stretch=True)
        else:
            rows = [[row["Column"]] + [stats_calculator.format_number(row[c])
                                       for c in stats_calculator.NUMERIC_COLUMNS[1:]]
                    for _, row in numeric.iterrows()]
            self._fill_table(self.numeric_tree, stats_calculator.NUMERIC_COLUMNS, rows,
                             right_align=stats_calculator.NUMERIC_COLUMNS[1:], stretch=True)

        text = stats_calculator.categorical_summary(df)
        if text.empty:
            self._fill_table(self.category_tree, ["Info"],
                             [["This dataset has no text or date columns."]], stretch=True)
        else:
            rows = [[row[c] if c in ("Column", "Type", "Most Common")
                     else stats_calculator.format_number(row[c])
                     for c in stats_calculator.CATEGORY_COLUMNS] for _, row in text.iterrows()]
            self._fill_table(self.category_tree, stats_calculator.CATEGORY_COLUMNS, rows,
                             right_align=("Unique", "Frequency", "Missing"), stretch=True)

    # ======================================================================
    # EXPORT PAGE
    # ======================================================================
    def _build_export_page(self, page):
        self._page_header(page, "Export", "Save your chart as an image or your data as a CSV file.")
        row = tk.Frame(page, bg=C["bg"])
        row.grid(row=1, column=0, sticky="new", padx=24)
        row.grid_columnconfigure(0, weight=1, uniform="export")
        row.grid_columnconfigure(1, weight=1, uniform="export")

        chart_card = Card(row, title="Export Chart")
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        tk.Label(chart_card.body, text="Save the chart currently shown on the Visualize page "
                 "as a high-resolution PNG image.", bg=C["card"], fg=C["muted"],
                 font=styles.font(10), justify="left", wraplength=340).pack(anchor="w")
        self.export_chart_info = tk.Label(chart_card.body, text="", bg=C["card"], fg=C["text"],
                                          font=styles.font(10, "bold"))
        self.export_chart_info.pack(anchor="w", pady=14)
        self._primary_button(chart_card.body, "Save Chart as PNG", self.export_chart).pack(
            anchor="w")

        data_card = Card(row, title="Export Dataset")
        data_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        tk.Label(data_card.body, text="Save the rows you are currently viewing (including any "
                 "filter and sorting) as a CSV file.", bg=C["card"], fg=C["muted"],
                 font=styles.font(10), justify="left", wraplength=340).pack(anchor="w")
        self.export_data_info = tk.Label(data_card.body, text="", bg=C["card"], fg=C["text"],
                                         font=styles.font(10, "bold"), justify="left")
        self.export_data_info.pack(anchor="w", pady=14)
        self._primary_button(data_card.body, "Export Dataset as CSV", self.export_dataset).pack(
            anchor="w")

    def _update_export_info(self):
        if not hasattr(self, "export_chart_info"):
            return  # pages are still being built
        if self.figure is None:
            self.export_chart_info.configure(text="No chart yet - generate one first.",
                                             fg=C["amber"])
        else:
            self.export_chart_info.configure(text="Chart ready to export.", fg=C["green"])
        if self.data.has_data:
            df = self.data.current
            filt = ("Filter: " + self.data.filter_description()) if self.data.is_filtered \
                else "No filter applied"
            self.export_data_info.configure(
                text=f"{len(df):,} rows x {df.shape[1]} columns\n{filt}", fg=C["text"])
        else:
            self.export_data_info.configure(text="No dataset loaded.", fg=C["amber"])

    def export_chart(self):
        if self.figure is None:
            self.set_status("There is no chart to save yet.", "error")
            self._warn("No chart yet", "Generate a chart on the Visualize page first.")
            return
        stem = self.data.path.stem if self.data.path else "chart"
        path = filedialog.asksaveasfilename(
            parent=self, title="Save chart as PNG", defaultextension=".png",
            initialfile=f"{stem}_chart.png", filetypes=[("PNG image", "*.png")])
        if not path:
            return
        try:
            saved = export_handler.export_chart_png(self.figure, path)
        except export_handler.ExportError as exc:
            self.set_status("Chart export failed.", "error")
            messagebox.showerror("Export failed", str(exc))
            return
        self.set_status(f"Chart saved to {saved}", "success")
        messagebox.showinfo("Chart saved", f"Your chart was saved to:\n{saved}")

    def export_dataset(self):
        if not self.data.has_data:
            self.set_status("There is no dataset to export.", "error")
            self._warn("No dataset", "Load a dataset first.")
            return
        stem = self.data.path.stem if self.data.path else "dataset"
        path = filedialog.asksaveasfilename(
            parent=self, title="Export dataset as CSV", defaultextension=".csv",
            initialfile=f"{stem}_filtered.csv" if self.data.is_filtered else f"{stem}_export.csv",
            filetypes=[("CSV file", "*.csv")])
        if not path:
            return
        try:
            saved = export_handler.export_dataset_csv(self.data.current, path)
        except export_handler.ExportError as exc:
            self.set_status("Dataset export failed.", "error")
            messagebox.showerror("Export failed", str(exc))
            return
        self.set_status(f"Exported {len(self.data.current):,} rows to {saved}", "success")
        messagebox.showinfo("Dataset exported",
                            f"{len(self.data.current):,} rows were saved to:\n{saved}")

    # ======================================================================
    # ABOUT PAGE
    # ======================================================================
    def _build_about_page(self, page):
        self._page_header(page, "About", "What this application is and how it works.")
        page.grid_rowconfigure(1, weight=1)
        card = Card(page)
        card.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))
        text = tk.Text(card.body, wrap="word", bg=C["card"], fg=C["text"], relief="flat",
                       font=styles.font(11), padx=4, pady=4, highlightthickness=0,
                       spacing3=6, cursor="arrow")
        text.pack(fill="both", expand=True)
        text.tag_configure("h", font=styles.font(13, "bold"), foreground=C["navy"],
                           spacing1=10, spacing3=4)

        sections = [
            ("DataViz Studio", "A desktop tool for exploring data without writing code. "
             "Upload a CSV or Excel file, preview it, filter it, summarise it and turn it "
             "into charts you can save. Everything runs locally on your computer - no "
             "internet, database or AI is used."),
            ("Features", "Upload CSV / Excel files  |  Scrollable preview with sorting  |  "
             "Search and filter  |  Bar, Line, Pie, Scatter and Histogram charts  |  "
             "Custom titles, labels, colours and grid  |  Statistics tables  |  "
             "Export chart (PNG) and filtered data (CSV)"),
            ("Technologies", "Python, Tkinter / ttk (interface), Pandas (data and statistics), "
             "Matplotlib (charts), OpenPyXL (Excel files)."),
            ("How the code is organised", "dashboard.py builds the window and connects "
             "everything.  data_handler.py loads and filters data.  chart_generator.py draws "
             "charts.  stats_calculator.py computes statistics.  export_handler.py saves "
             "files.  styles.py holds colours and fonts."),
        ]
        for heading, body in sections:
            text.insert("end", heading + "\n", "h")
            text.insert("end", body + "\n")
        text.configure(state="disabled")

    # ======================================================================
    # Loading data and refreshing the screens
    # ======================================================================
    def browse_file(self):
        """Open the native file dialog and load the chosen file."""
        path = filedialog.askopenfilename(
            parent=self, title="Select a dataset",
            filetypes=[("Data files", "*.csv *.xlsx *.xls"), ("CSV files", "*.csv"),
                       ("Excel files", "*.xlsx *.xls"), ("All files", "*.*")])
        if path:
            self.load_dataset(path)

    def load_sample(self):
        self.load_dataset(SAMPLE_FILE)

    def load_dataset(self, path):
        try:
            self.data.load_file(path)
        except DataLoadError as exc:
            self.set_status("Could not load the file.", "error")
            messagebox.showerror("Could not load dataset", str(exc))
            return
        self.preview_page = 0
        self.filter_value_var.set("")
        self.filter_col_var.set(ALL_COLUMNS)
        self._on_dataset_changed()
        rows, cols = self.data.original.shape
        self.set_status(f"Loaded {self.data.filename}: {rows:,} rows x {cols} columns.",
                        "success")

    def _on_dataset_changed(self):
        """A new file was loaded (or the app just started): refresh everything."""
        has = self.data.has_data
        if has:
            rows, cols = self.data.original.shape
            self.header_info.configure(text=f"{self.data.filename}   |   {rows:,} rows x {cols} columns")
            self.home_file_label.configure(text=self.data.filename)
            self.home_dim_label.configure(text=f"Dataset size: {rows:,} rows x {cols} columns")
            overview = stats_calculator.dataset_overview(self.data.original)
            for key, card in self.home_cards.items():
                card.set(f"{overview[key]:,}")
            self.filter_col_combo.configure(values=[ALL_COLUMNS] + self.data.columns())
        else:
            self.header_info.configure(text="No dataset loaded")
            self.home_file_label.configure(text="No file selected")
            self.home_dim_label.configure(text="")
            for card in self.home_cards.values():
                card.set("-")
            self.filter_col_combo.configure(values=[ALL_COLUMNS])
        self._update_axis_options()
        self._show_chart_placeholder()
        self._refresh_data_views()

    def _refresh_data_views(self):
        """The visible rows changed (filter / sort): refresh dependent screens."""
        self._refresh_preview()
        self._refresh_statistics()
        self._update_export_info()
        if self.data.has_data:
            self.chart_note.configure(
                text=f"Charts use the current view: {len(self.data.current):,} rows"
                     + (f"  (filter: {self.data.filter_description()})"
                        if self.data.is_filtered else ""))
        else:
            self.chart_note.configure(text="Load a dataset to start charting.")

    def _refresh_preview(self):
        tree = self.preview_tree
        if not self.data.has_data:
            self._fill_table(tree, ["Info"], [["No dataset loaded - go to Home and click Browse."]],
                             stretch=True)
            self.preview_info.configure(text="No dataset loaded.")
            self.page_label.configure(text="")
            self.prev_btn.state(["disabled"])
            self.next_btn.state(["disabled"])
            return

        total = len(self.data.current)
        pages = self.data.total_pages(PAGE_SIZE)
        self.preview_page = max(0, min(self.preview_page, pages - 1))
        rows = self.data.get_page_rows(self.preview_page, PAGE_SIZE)
        numeric = set(self.data.numeric_columns())
        self._fill_table(tree, list(self.data.current.columns), rows, right_align=numeric,
                         sort_command=self._sort_by, sort_state=self.data.sort_state)

        start = self.preview_page * PAGE_SIZE
        info = (f"Showing rows {start + 1:,}-{start + len(rows):,} of {total:,}"
                if total else "No rows match the current filter.")
        if self.data.is_filtered:
            info += f"   |   Filter: {self.data.filter_description()}  (of {len(self.data.original):,} total rows)"
        self.preview_info.configure(text=info)
        self.page_label.configure(text=f"Page {self.preview_page + 1} of {pages}")
        self.prev_btn.state(["!disabled"] if self.preview_page > 0 else ["disabled"])
        self.next_btn.state(["!disabled"] if self.preview_page < pages - 1 else ["disabled"])

    def _warn(self, title, message):
        messagebox.showwarning(title, message)
