"""
Cubed Glass - Cutting Optimization

A desktop app for 2D guillotine glass-cutting optimization.
Workflow:
  1. Enter your STOCK sheets (size + qty on hand, optional price).
  2. Enter your DEMAND pieces (size + qty needed, per job/order).
  3. Click Optimize -> see the cutting layout(s), one per unique sheet
     pattern (repeated patterns are grouped with a quantity, same idea as
     grouping duplicate layouts in commercial cut-optimizers), plus overall
     Statistics (utilization, waste, cut length, cost).
  4. Save/Load your job as a .json project file.
  5. Import/export stock & pieces as CSV; export the cutting list as CSV;
     export layout images as PNG.

Run with:  python cubed_glass_optimizer.py
Package as a Windows .exe with PyInstaller (see README.md).
"""

import csv
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from packer import Piece, StockSheet, optimize, group_sheet_results, compute_stats

APP_TITLE = "Cubed Glass — Cutting Optimizer"
TAGLINE = "Cut clean.  Fitted true.  Built to last."
ADDRESS = "46 Fabriek Street, Gants Plaza, Cape Town, 7140"
PHONE = "073 176 1636"

# ---------------------------------------------------------------------------
# Theme — the company colour is Fiat 188/A "Rosa Poste Tedesche" (a soft
# rose-pink), paired with a deep plum-black for contrast and a rose-gold
# CTA accent.
# ---------------------------------------------------------------------------
ACCENT = "#e07b96"        # Rosa Poste Tedesche, constant across both themes
ACCENT_DEEP = "#b85570"   # deeper rose for hovers / secondary accents (light mode)

THEMES = {
    "light": {
        "bg": "#f9f5f6", "panel": "#ffffff", "fg": "#2a1e22", "muted": "#8a6b73",
        "accent": ACCENT, "accent_deep": ACCENT_DEEP, "accent_fg": "#ffffff", "border": "#ecd9de",
        "table_alt": "#fbeef2", "canvas_bg": "#ffffff", "sheet_outline": "#2a1e22",
        "waste": "#f3e6ea", "header_bg": "#241016", "header_fg": "#f8eef1",
        "btn_bg": "#fbe4ea", "btn_fg": "#a8395c",
        "cta": "#caa14a", "cta_fg": "#231708",
        "piece_colors": ["#bfe6ec", "#ffd9a0", "#c8ead0", "#f0c7dc", "#d3cdef", "#f2ecb0"],
    },
    "dark": {
        "bg": "#1c1215", "panel": "#241820", "fg": "#f3e6ea", "muted": "#b98d97",
        "accent": ACCENT, "accent_deep": "#f0a8bb", "accent_fg": "#241016", "border": "#3a2630",
        "table_alt": "#2c1e26", "canvas_bg": "#201620", "sheet_outline": "#f3e6ea",
        "waste": "#33232b", "header_bg": "#140b0e", "header_fg": "#f6ecef",
        "btn_bg": "#33202a", "btn_fg": "#f0a8bb",
        "cta": "#d9b565", "cta_fg": "#1c1208",
        "piece_colors": ["#2c5c66", "#78562c", "#375c3d", "#65395a", "#453d68", "#65612c"],
    },
}

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo_mark.png")

FONT = "Segoe UI"  # falls back gracefully on non-Windows systems


class Card(tk.Frame):
    """
    A panel with a thin 1px border, used to visually group related content
    (stock table, pieces table, results area) into distinct "cards" instead
    of everything floating on the same flat background.
    """
    def __init__(self, parent, app, **kwargs):
        self.app = app
        t = app.theme()
        super().__init__(parent, bg=t["border"], bd=0, highlightthickness=0, **kwargs)
        self.inner = tk.Frame(self, bg=t["panel"])
        self.inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.content = tk.Frame(self.inner, bg=t["panel"])
        self.content.pack(fill="both", expand=True, padx=16, pady=14)

    def refresh_theme(self):
        t = self.app.theme()
        self.configure(bg=t["border"])
        self.inner.configure(bg=t["panel"])
        self.content.configure(bg=t["panel"])


class ToolTip:
    """Small hover tooltip for a widget."""
    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, background="#333333", foreground="white",
                 font=("", 9), padx=6, pady=3).pack()

    def _hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ---------------------------------------------------------------------------
# Small reusable dialog for adding/editing a Piece or Stock row
# ---------------------------------------------------------------------------
class RowDialog(simpledialog.Dialog):
    def __init__(self, parent, title, fields, initial=None):
        """fields: list of (key, label, type). type in 'str','float','int','bool'."""
        self.fields = fields
        self.initial = initial or {}
        self.result_values = None
        super().__init__(parent, title=title)

    def body(self, master):
        self.vars = {}
        for i, (key, label, ftype) in enumerate(self.fields):
            tk.Label(master, text=label).grid(row=i, column=0, sticky="w", padx=4, pady=4)
            if ftype == "bool":
                var = tk.BooleanVar(value=self.initial.get(key, True))
                tk.Checkbutton(master, variable=var).grid(row=i, column=1, sticky="w", padx=4, pady=4)
            else:
                default = self.initial.get(key, "")
                var = tk.StringVar(value=str(default))
                entry = tk.Entry(master, textvariable=var, width=22)
                entry.grid(row=i, column=1, padx=4, pady=4)
                if i == 0:
                    entry.focus_set()
            self.vars[key] = (var, ftype)
        return master

    def validate(self):
        try:
            values = {}
            for key, (var, ftype) in self.vars.items():
                if ftype == "float":
                    values[key] = float(var.get())
                elif ftype == "int":
                    values[key] = int(var.get())
                elif ftype == "bool":
                    values[key] = bool(var.get())
                else:
                    values[key] = var.get().strip()
            self.result_values = values
            return True
        except ValueError:
            messagebox.showerror("Invalid input", "Please check that width/height/qty/price are numbers.")
            return False

    def apply(self):
        pass


# ---------------------------------------------------------------------------
# A labeled table (Treeview) with Add / Edit / Delete + CSV import/export
# ---------------------------------------------------------------------------
class EditableTable(ttk.Frame):
    def __init__(self, parent, columns, fields, title, app):
        """
        columns: list of (key, header, width) for the Treeview display
        fields: list of (key, label, type) passed to RowDialog for add/edit
        """
        super().__init__(parent, style="Panel.TFrame")
        self.columns = columns
        self.fields = fields
        self.title = title
        self.app = app
        self.rows = []

        top = ttk.Frame(self, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text=title, style="SectionTitle.TLabel").pack(side="left")

        btns = ttk.Frame(top, style="Panel.TFrame")
        btns.pack(side="right")
        for text, cmd, tip in [
            ("Add", self.add_row, "Add a new row"),
            ("Edit", self.edit_row, "Edit the selected row"),
            ("Delete", self.delete_row, "Delete the selected row"),
            ("Import CSV", self.import_csv, "Import rows from a CSV file"),
            ("Export CSV", self.export_csv, "Export current rows to a CSV file"),
        ]:
            b = ttk.Button(btns, text=text, command=cmd, style="Toolbar.TButton")
            b.pack(side="left", padx=2)
            ToolTip(b, tip)

        col_ids = [c[0] for c in columns]
        self.tree = ttk.Treeview(self, columns=col_ids, show="headings", height=7, style="Custom.Treeview")
        for key, header, width in columns:
            self.tree.heading(key, text=header)
            self.tree.column(key, width=width, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.edit_row())
        self.tree.tag_configure("odd", background=self.app.theme()["table_alt"])

        self.empty_hint = ttk.Label(self, text=f"Nothing here yet — click Add to create your first row.",
                                     style="Hint.TLabel")
        self.refresh()

    def add_row(self):
        singular = self.title[:-1] if self.title.endswith("s") else self.title
        dlg = RowDialog(self, f"Add {singular}", self.fields)
        if dlg.result_values:
            self.rows.append(dlg.result_values)
            self.refresh()

    def edit_row(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Edit", "Select a row first.")
            return
        idx = self.tree.index(sel[0])
        dlg = RowDialog(self, f"Edit {self.title}", self.fields, initial=self.rows[idx])
        if dlg.result_values:
            self.rows[idx] = dlg.result_values
            self.refresh()

    def delete_row(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if messagebox.askyesno("Delete row", "Delete the selected row?"):
            del self.rows[idx]
            self.refresh()

    def refresh(self):
        self.tree.tag_configure("odd", background=self.app.theme()["table_alt"])
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.rows):
            values = [row.get(c[0], "") for c in self.columns]
            tag = "odd" if i % 2 else ""
            self.tree.insert("", "end", values=values, tags=(tag,))
        if self.rows:
            self.empty_hint.pack_forget()
        else:
            self.empty_hint.pack(fill="x", pady=(6, 0))

    def set_rows(self, rows):
        self.rows = rows
        self.refresh()

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            new_rows = []
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                for raw in reader:
                    row = {}
                    for key, _label, ftype in self.fields:
                        val = raw.get(key, "")
                        if ftype == "float":
                            row[key] = float(val) if val not in (None, "") else 0.0
                        elif ftype == "int":
                            row[key] = int(float(val)) if val not in (None, "") else 0
                        elif ftype == "bool":
                            row[key] = str(val).strip().lower() in ("1", "true", "yes", "y")
                        else:
                            row[key] = (val or "").strip()
                    new_rows.append(row)
            if not new_rows:
                messagebox.showwarning("Import CSV", "No rows found in that file.")
                return
            self.rows.extend(new_rows)
            self.refresh()
            messagebox.showinfo("Import CSV", f"Imported {len(new_rows)} row(s).")
        except Exception as e:
            messagebox.showerror("Import CSV failed", f"Could not read that CSV:\n{e}\n\n"
                                  f"Expected columns: {', '.join(k for k, _, _ in self.fields)}")

    def export_csv(self):
        if not self.rows:
            messagebox.showinfo("Export CSV", "Nothing to export yet.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        keys = [k for k, _, _ in self.fields]
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in self.rows:
                writer.writerow({k: row.get(k, "") for k in keys})
        messagebox.showinfo("Export CSV", f"Saved: {path}")


# ---------------------------------------------------------------------------
# Results canvas: draws one grouped sheet layout using plain tkinter Canvas
# ---------------------------------------------------------------------------
class ResultsView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Panel.TFrame")
        self.app = app
        self.groups = []       # list of {"sheet": SheetResult, "count": int}
        self.current = 0
        self.zoom = 1.0

        nav = ttk.Frame(self, style="Panel.TFrame")
        nav.pack(fill="x")
        ttk.Button(nav, text="< Prev", command=self.prev_sheet, style="Toolbar.TButton").pack(side="left")
        self.nav_label = ttk.Label(nav, text="No results yet", style="Muted.TLabel")
        self.nav_label.pack(side="left", padx=10)
        ttk.Button(nav, text="Next >", command=self.next_sheet, style="Toolbar.TButton").pack(side="left")

        zoom_box = ttk.Frame(nav, style="Panel.TFrame")
        zoom_box.pack(side="left", padx=20)
        ttk.Button(zoom_box, text="-", width=2, command=lambda: self.adjust_zoom(0.85),
                   style="Toolbar.TButton").pack(side="left")
        ttk.Button(zoom_box, text="Fit", command=self.reset_zoom, style="Toolbar.TButton").pack(side="left", padx=2)
        ttk.Button(zoom_box, text="+", width=2, command=lambda: self.adjust_zoom(1.15),
                   style="Toolbar.TButton").pack(side="left")

        ttk.Button(nav, text="Export image", command=self.export_image, style="Toolbar.TButton").pack(side="left", padx=10)

        self.util_label = ttk.Label(nav, text="", style="Accent.TLabel")
        self.util_label.pack(side="right", padx=10)

        canvas_wrap = ttk.Frame(self, style="Panel.TFrame")
        canvas_wrap.pack(fill="both", expand=True, pady=6)
        self.canvas = tk.Canvas(canvas_wrap, bg="white", width=760, height=520, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())

    def set_results(self, sheet_results):
        self.groups = group_sheet_results(sheet_results)
        self.current = 0
        self.zoom = 1.0
        self.draw()

    def adjust_zoom(self, factor):
        self.zoom = max(0.3, min(4.0, self.zoom * factor))
        self.draw()

    def reset_zoom(self):
        self.zoom = 1.0
        self.draw()

    def prev_sheet(self):
        if self.groups:
            self.current = (self.current - 1) % len(self.groups)
            self.draw()

    def next_sheet(self):
        if self.groups:
            self.current = (self.current + 1) % len(self.groups)
            self.draw()

    def current_group(self):
        return self.groups[self.current] if self.groups else None

    def draw(self):
        theme = self.app.theme()
        self.canvas.configure(bg=theme["canvas_bg"])
        self.canvas.delete("all")
        if not self.groups:
            self.nav_label.config(text="")
            self.util_label.config(text="")
            cw = max(200, self.canvas.winfo_width())
            ch = max(200, self.canvas.winfo_height())
            cx, cy = cw / 2, ch / 2 - 20
            # simple "empty sheet" glyph
            self.canvas.create_rectangle(cx - 46, cy - 34, cx + 46, cy + 34,
                                          outline=theme["border"], width=2, dash=(4, 3))
            self.canvas.create_line(cx - 46, cy - 34, cx + 46, cy + 34, fill=theme["border"], width=2)
            self.canvas.create_line(cx + 46, cy - 34, cx - 46, cy + 34, fill=theme["border"], width=2)
            self.canvas.create_text(cx, cy + 60, text="No layout yet",
                                     font=(FONT, 12, "bold"), fill=theme["fg"])
            self.canvas.create_text(cx, cy + 82, text="Add stock sheets & pieces on the left, then click Optimize",
                                     font=(FONT, 9), fill=theme["muted"])
            return

        g = self.groups[self.current]
        r, count = g["sheet"], g["count"]
        qty_text = f"  |  Quantity: {count} identical sheet(s)" if count > 1 else ""
        self.nav_label.config(
            text=f"Layout {self.current + 1} / {len(self.groups)}  "
                 f"({r.sheet_label}: {r.sheet_width:g} x {r.sheet_height:g}){qty_text}"
        )
        self.util_label.config(text=f"Utilization: {r.utilization * 100:.1f}%")

        pad = 24
        cw = max(100, self.canvas.winfo_width() - 2 * pad)
        ch = max(100, self.canvas.winfo_height() - 2 * pad)
        base_scale = min(cw / r.sheet_width, ch / r.sheet_height)
        scale = base_scale * self.zoom

        def to_px(x, y, w, h):
            px = pad + x * scale
            py = pad + (r.sheet_height - y - h) * scale
            return px, py, px + w * scale, py + h * scale

        x0, y0, x1, y1 = to_px(0, 0, r.sheet_width, r.sheet_height)
        self.canvas.create_rectangle(x0, y0, x1, y1, outline=theme["sheet_outline"], width=2)

        colors = theme["piece_colors"]
        for i, p in enumerate(r.placements):
            px0, py0, px1, py1 = to_px(p.x, p.y, p.width, p.height)
            self.canvas.create_rectangle(px0, py0, px1, py1, fill=colors[i % len(colors)],
                                          outline=theme["sheet_outline"])
            label = f"{p.label}\n{p.width:g}x{p.height:g}"
            if getattr(p, "customer", ""):
                label += f"\n{p.customer}"
            if p.rotated:
                label += " (R)"
            self.canvas.create_text((px0 + px1) / 2, (py0 + py1) / 2, text=label,
                                     font=("", 8), fill=theme["fg"])

        for (wx, wy, ww, wh) in r.waste_rects:
            wx0, wy0, wx1, wy1 = to_px(wx, wy, ww, wh)
            self.canvas.create_rectangle(wx0, wy0, wx1, wy1, fill=theme["waste"], outline=theme["muted"],
                                          stipple="gray25")

    def export_image(self):
        if not self.groups:
            messagebox.showinfo("Export image", "Nothing to export yet.")
            return
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            messagebox.showerror("Export image", "Pillow is required for image export.\n"
                                                    "Install it with:  pip install Pillow")
            return

        folder = filedialog.askdirectory(title="Choose a folder to save layout image(s)")
        if not folder:
            return

        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        for idx, g in enumerate(self.groups, start=1):
            r = g["sheet"]
            W, H = 900, 650
            pad = 30
            scale = min((W - 2 * pad) / r.sheet_width, (H - 2 * pad) / r.sheet_height)
            img = Image.new("RGB", (W, H), "white")
            draw = ImageDraw.Draw(img)

            def to_px(x, y, w, h):
                px = pad + x * scale
                py = pad + (r.sheet_height - y - h) * scale
                return px, py, px + w * scale, py + h * scale

            x0, y0, x1, y1 = to_px(0, 0, r.sheet_width, r.sheet_height)
            draw.rectangle([x0, y0, x1, y1], outline="black", width=2)
            palette = ["#bfe3ee", "#ffdca8", "#c9e8c3", "#f2c9de", "#d6cdf0", "#f5eeb8"]
            for i, p in enumerate(r.placements):
                px0, py0, px1, py1 = to_px(p.x, p.y, p.width, p.height)
                draw.rectangle([px0, py0, px1, py1], fill=palette[i % len(palette)], outline="black")
                label = f"{p.label} {p.width:g}x{p.height:g}" + (" (R)" if p.rotated else "")
                draw.text(((px0 + px1) / 2, (py0 + py1) / 2), label, fill="black", anchor="mm", font=font)
            for (wx, wy, ww, wh) in r.waste_rects:
                wx0, wy0, wx1, wy1 = to_px(wx, wy, ww, wh)
                draw.rectangle([wx0, wy0, wx1, wy1], fill="#e8e8e8", outline="gray")

            caption = f"{r.sheet_label} {r.sheet_width:g}x{r.sheet_height:g} | Utilization {r.utilization*100:.1f}%"
            if g["count"] > 1:
                caption += f" | Qty {g['count']}"
            draw.text((pad, H - 20), caption, fill="black", font=font)

            img.save(os.path.join(folder, f"layout_{idx:02d}.png"))

        messagebox.showinfo("Export image", f"Saved {len(self.groups)} image(s) to:\n{folder}")


# ---------------------------------------------------------------------------
# Statistics panel
# ---------------------------------------------------------------------------
class StatsView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Panel.TFrame")
        self.app = app
        self.rows = {}
        grid = ttk.Frame(self, style="Panel.TFrame")
        grid.pack(fill="both", expand=True, padx=20, pady=20)

        labels = [
            ("sheets_used", "Sheets used"),
            ("overall_utilization", "Overall utilization"),
            ("total_sheet_area", "Total sheet area (mm²)"),
            ("total_used_area", "Used area (mm²)"),
            ("total_waste_area", "Waste area (mm²)"),
            ("total_cut_length", "Total cut length (mm)"),
            ("pieces_placed", "Pieces placed"),
            ("pieces_unplaced", "Pieces NOT placed"),
            ("total_cost", "Estimated material cost"),
        ]
        for i, (key, text) in enumerate(labels):
            ttk.Label(grid, text=text + ":", style="Muted.TLabel").grid(row=i, column=0, sticky="w", pady=6, padx=(0, 12))
            val = ttk.Label(grid, text="—", style="StatValue.TLabel")
            val.grid(row=i, column=1, sticky="w", pady=6)
            self.rows[key] = val

    def update_stats(self, sheet_results, unplaced):
        if not sheet_results:
            for lbl in self.rows.values():
                lbl.config(text="—")
            return
        stats = compute_stats(sheet_results, unplaced)
        self.rows["sheets_used"].config(text=str(stats.sheets_used))
        self.rows["overall_utilization"].config(text=f"{stats.overall_utilization * 100:.1f}%")
        self.rows["total_sheet_area"].config(text=f"{stats.total_sheet_area:,.0f}")
        self.rows["total_used_area"].config(text=f"{stats.total_used_area:,.0f}")
        self.rows["total_waste_area"].config(text=f"{stats.total_waste_area:,.0f}")
        self.rows["total_cut_length"].config(text=f"{stats.total_cut_length:,.0f}")
        self.rows["pieces_placed"].config(text=str(stats.pieces_placed))
        unplaced_color = "Bad.TLabel" if stats.pieces_unplaced else "StatValue.TLabel"
        self.rows["pieces_unplaced"].config(text=str(stats.pieces_unplaced), style=unplaced_color)
        cost_text = f"R {stats.total_cost:,.2f}" if stats.total_cost else "— (add sheet prices to estimate)"
        self.rows["total_cost"].config(text=cost_text)


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1250x760")
        self.minsize(980, 620)
        self.project_path = None
        self.theme_name = "light"
        self.last_results = []
        self.last_unplaced = []

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.logo_img = None
        try:
            if os.path.exists(LOGO_PATH):
                self.logo_img = tk.PhotoImage(file=LOGO_PATH)
                # Tk has no built-in resize for PhotoImage; subsample to a header-friendly size
                self.logo_img = self.logo_img.subsample(4, 4)
                self.iconphoto(True, tk.PhotoImage(file=LOGO_PATH))
        except tk.TclError:
            self.logo_img = None

        self._apply_theme()

        self._build_menu()
        self._build_header()
        self._build_footer()

        content = ttk.Frame(self, style="App.TFrame")
        content.pack(fill="both", expand=True)

        toolbar_card = Card(content, app=self)
        toolbar_card.pack(fill="x", padx=16, pady=16)
        self.toolbar_card = toolbar_card
        toolbar = toolbar_card.content

        actions = tk.Frame(toolbar, bg=self.theme()["panel"])
        actions.pack(side="left")
        ttk.Label(actions, text="Blade / kerf thickness (mm):", style="Body2.TLabel").pack(side="left")
        self.kerf_var = tk.StringVar(value="0")
        ttk.Entry(actions, textvariable=self.kerf_var, width=6).pack(side="left", padx=(6, 16))

        opt_btn = ttk.Button(actions, text="▶  Optimize", command=self.run_optimize, style="Accent.TButton")
        opt_btn.pack(side="left")
        ToolTip(opt_btn, "Run the cutting optimization on the current stock & pieces")

        ttk.Button(actions, text="Export cutting list (CSV)", command=self.export_cutting_list,
                   style="Toolbar.TButton").pack(side="left", padx=(10, 0))

        self.status_label = ttk.Label(toolbar, text="", style="Muted.TLabel")
        self.status_label.pack(side="left", padx=20)

        theme_btn = ttk.Button(toolbar, text="🌙  Dark mode", command=self.toggle_theme, style="Toolbar.TButton")
        theme_btn.pack(side="right")
        self.theme_btn = theme_btn

        main = ttk.Panedwindow(content, orient="horizontal", style="App.TPanedwindow")
        main.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        left = ttk.Frame(main, style="App.TFrame")
        main.add(left, weight=1)

        stock_card = Card(left, app=self)
        stock_card.pack(fill="both", expand=True, pady=(0, 14))
        self.stock_card = stock_card
        self.stock_table = EditableTable(
            stock_card.content,
            columns=[("label", "Label", 55), ("material", "Material", 75), ("texture", "Texture", 70),
                     ("width", "Width (mm)", 70), ("height", "Height (mm)", 70),
                     ("qty", "Qty", 40), ("price", "Price", 55)],
            fields=[("label", "Label", "str"), ("material", "Material (e.g. Float, Mirror, Laminated)", "str"),
                    ("texture", "Texture (e.g. Clear, Frosted, Patterned)", "str"),
                    ("width", "Sheet width (mm)", "float"), ("height", "Sheet height (mm)", "float"),
                    ("qty", "Quantity on hand", "int"), ("price", "Price per sheet (optional)", "float")],
            title="Stock Sheets", app=self,
        )
        self.stock_table.pack(fill="both", expand=True)

        piece_card = Card(left, app=self)
        piece_card.pack(fill="both", expand=True)
        self.piece_card = piece_card
        self.piece_table = EditableTable(
            piece_card.content,
            columns=[("label", "Label", 50), ("customer", "Customer", 70), ("material", "Material", 70),
                     ("texture", "Texture", 65), ("width", "Width (mm)", 65), ("height", "Height (mm)", 65),
                     ("qty", "Qty", 40), ("allow_rotation", "Rotate?", 50)],
            fields=[("label", "Label", "str"), ("customer", "Customer / job name", "str"),
                    ("material", "Material (must match stock to be cuttable)", "str"),
                    ("texture", "Texture (must match stock to be cuttable)", "str"),
                    ("width", "Piece width (mm)", "float"), ("height", "Piece height (mm)", "float"),
                    ("qty", "Quantity needed", "int"), ("allow_rotation", "Allow rotation", "bool")],
            title="Demand Pieces", app=self,
        )
        self.piece_table.pack(fill="both", expand=True)

        right = ttk.Frame(main, style="App.TFrame")
        main.add(right, weight=2)

        results_card = Card(right, app=self)
        results_card.pack(fill="both", expand=True)
        self.results_card = results_card

        self.notebook = ttk.Notebook(results_card.content, style="Custom.TNotebook")
        self.notebook.pack(fill="both", expand=True)
        self.results_view = ResultsView(self.notebook, self)
        self.stats_view = StatsView(self.notebook, self)
        self.notebook.add(self.results_view, text="  Results (2D)  ")
        self.notebook.add(self.stats_view, text="  Statistics  ")


        # Starts empty — no example rows. Use Add (or Import CSV) to get going.

    # ---- Theming --------------------------------------------------------------
    def theme(self):
        return THEMES[self.theme_name]

    def toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self._apply_theme()
        self.theme_btn.config(text="☀  Light mode" if self.theme_name == "dark" else "🌙  Dark mode")
        self.stock_table.refresh()
        self.piece_table.refresh()
        self.results_view.draw()
        if hasattr(self, "_header_rule"):
            self._header_rule.configure(bg=self.theme()["accent"])

    def _apply_theme(self):
        t = self.theme()
        self.configure(bg=t["bg"])
        s = self.style
        s.configure("App.TFrame", background=t["bg"])
        s.configure("Panel.TFrame", background=t["panel"])
        s.configure("App.TPanedwindow", background=t["bg"])
        s.configure("Body.TLabel", background=t["bg"], foreground=t["fg"], font=(FONT, 10))
        s.configure("Body2.TLabel", background=t["panel"], foreground=t["fg"], font=(FONT, 10))
        s.configure("Muted.TLabel", background=t["panel"], foreground=t["muted"], font=(FONT, 9))
        s.configure("Hint.TLabel", background=t["panel"], foreground=t["muted"], font=(FONT, 9, "italic"))
        s.configure("Accent.TLabel", background=t["panel"], foreground=t["accent"], font=(FONT, 10, "bold"))
        s.configure("StatValue.TLabel", background=t["panel"], foreground=t["fg"], font=(FONT, 12, "bold"))
        s.configure("Bad.TLabel", background=t["panel"], foreground="#c0392b", font=(FONT, 12, "bold"))
        s.configure("SectionTitle.TLabel", background=t["panel"], foreground=t["fg"], font=(FONT, 12, "bold"))
        s.configure("Header.TFrame", background=t["header_bg"])
        s.configure("HeaderTitle.TLabel", background=t["header_bg"], foreground=t["header_fg"], font=(FONT, 18, "bold"))
        s.configure("HeaderTitleAccent.TLabel", background=t["header_bg"], foreground=t["accent"], font=(FONT, 18, "italic"))
        s.configure("HeaderSubtitle.TLabel", background=t["header_bg"], foreground=t["muted"], font=(FONT, 9))
        s.configure("FooterText.TLabel", background=t["header_bg"], foreground=t["muted"], font=(FONT, 8))

        # Pill-style secondary buttons: tinted background, flips to full accent on hover
        s.configure("Toolbar.TButton", padding=(10, 6), font=(FONT, 9), borderwidth=0, relief="flat",
                    background=t["btn_bg"], foreground=t["btn_fg"])
        try:
            s.map("Toolbar.TButton",
                  background=[("active", t["accent"]), ("!disabled", t["btn_bg"])],
                  foreground=[("active", t["accent_fg"]), ("!disabled", t["btn_fg"])])
        except tk.TclError:
            pass

        # Primary CTA button: warm accent, stands out against the teal UI
        s.configure("Accent.TButton", padding=(14, 8), font=(FONT, 11, "bold"), borderwidth=0, relief="flat")
        try:
            s.map("Accent.TButton",
                  background=[("active", t["accent_deep"]), ("!disabled", t["cta"])],
                  foreground=[("!disabled", t["cta_fg"])])
        except tk.TclError:
            pass

        s.configure("Custom.Treeview", background=t["panel"], fieldbackground=t["panel"], foreground=t["fg"],
                    rowheight=24, bordercolor=t["border"], font=(FONT, 9))
        s.map("Custom.Treeview", background=[("selected", t["accent"])], foreground=[("selected", t["accent_fg"])])
        s.configure("Custom.Treeview.Heading", background=t["header_bg"], foreground=t["header_fg"], font=(FONT, 9, "bold"))
        s.configure("Custom.TNotebook", background=t["panel"], borderwidth=0)
        s.configure("Custom.TNotebook.Tab", padding=(16, 8), font=(FONT, 10))
        s.map("Custom.TNotebook.Tab",
              background=[("selected", t["panel"]), ("!selected", t["table_alt"])],
              foreground=[("selected", t["accent"]), ("!selected", t["muted"])])

        if hasattr(self, "toolbar_card"):
            self.toolbar_card.refresh_theme()
        if hasattr(self, "stock_card"):
            self.stock_card.refresh_theme()
        if hasattr(self, "piece_card"):
            self.piece_card.refresh_theme()
        if hasattr(self, "results_card"):
            self.results_card.refresh_theme()
        if hasattr(self, "results_view"):
            self.results_view.draw()

    def _build_header(self):
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x")
        inner = ttk.Frame(header, style="Header.TFrame")
        inner.pack(fill="x", padx=18, pady=12)

        if self.logo_img:
            tk.Label(inner, image=self.logo_img, bg=self.theme()["header_bg"]).pack(side="left", padx=(0, 12))

        text_col = ttk.Frame(inner, style="Header.TFrame")
        text_col.pack(side="left")

        wordmark = ttk.Frame(text_col, style="Header.TFrame")
        wordmark.pack(anchor="w")
        ttk.Label(wordmark, text="Cubed", style="HeaderTitle.TLabel").pack(side="left")
        ttk.Label(wordmark, text="Glass", style="HeaderTitleAccent.TLabel").pack(side="left")

        ttk.Label(text_col, text=TAGLINE, style="HeaderSubtitle.TLabel").pack(anchor="w")

        # A thin accent rule under the header, echoing a glass edge highlight
        rule = tk.Frame(header, height=3, bg=self.theme()["accent"])
        rule.pack(fill="x")
        self._header_rule = rule

    def _build_footer(self):
        footer = ttk.Frame(self, style="Header.TFrame")
        footer.pack(fill="x", side="bottom")
        inner = ttk.Frame(footer, style="Header.TFrame")
        inner.pack(fill="x", padx=18, pady=6)
        ttk.Label(inner, text=f"{ADDRESS}   |   {PHONE}", style="FooterText.TLabel").pack(side="left")
        ttk.Label(inner, text="Cubed Glass — Glass & Mirror Specialists, Cape Town",
                  style="FooterText.TLabel").pack(side="right")

    def _build_menu(self):
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Project", command=self.new_project)
        filemenu.add_command(label="Open Project...", command=self.open_project)
        filemenu.add_command(label="Save Project", command=self.save_project)
        filemenu.add_command(label="Save Project As...", command=self.save_project_as)
        filemenu.add_separator()
        filemenu.add_command(label="Export Cutting List (CSV)", command=self.export_cutting_list)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)

        viewmenu = tk.Menu(menubar, tearoff=0)
        viewmenu.add_command(label="Toggle Dark / Light Mode", command=self.toggle_theme)
        menubar.add_cascade(label="View", menu=viewmenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.config(menu=menubar)

    def show_about(self):
        messagebox.showinfo(
            "About",
            "Cubed Glass — Cutting Optimizer\n\n"
            "2D guillotine cutting-stock optimization for glass sheets.\n"
            "Built for Cubed Glass, Cape Town."
        )

    # ---- Project persistence ---------------------------------------------------
    def new_project(self):
        self.stock_table.set_rows([])
        self.piece_table.set_rows([])
        self.results_view.set_results([])
        self.stats_view.update_stats([], [])
        self.project_path = None
        self.status_label.config(text="New project")

    def _project_data(self):
        return {
            "kerf": self.kerf_var.get(),
            "stock": self.stock_table.rows,
            "pieces": self.piece_table.rows,
        }

    def save_project(self):
        if not self.project_path:
            return self.save_project_as()
        with open(self.project_path, "w") as f:
            json.dump(self._project_data(), f, indent=2)
        self.status_label.config(text=f"Saved: {self.project_path}")

    def save_project_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Cutting project", "*.json")])
        if path:
            self.project_path = path
            self.save_project()

    def open_project(self):
        path = filedialog.askopenfilename(filetypes=[("Cutting project", "*.json")])
        if not path:
            return
        with open(path) as f:
            data = json.load(f)
        self.kerf_var.set(data.get("kerf", "0"))
        self.stock_table.set_rows(data.get("stock", []))
        self.piece_table.set_rows(data.get("pieces", []))
        self.project_path = path
        self.status_label.config(text=f"Loaded: {path}")

    # ---- Optimization -----------------------------------------------------------
    def run_optimize(self):
        try:
            kerf = float(self.kerf_var.get() or 0)
        except ValueError:
            messagebox.showerror("Invalid kerf", "Blade thickness must be a number.")
            return

        if not self.stock_table.rows:
            messagebox.showinfo("No stock", "Add at least one stock sheet first.")
            return
        if not self.piece_table.rows:
            messagebox.showinfo("No pieces", "Add at least one demand piece first.")
            return

        stock = [StockSheet(r["label"], r["width"], r["height"], r["qty"],
                             material=r.get("material", ""), texture=r.get("texture", ""),
                             price=r.get("price", 0.0) or 0.0)
                 for r in self.stock_table.rows]
        pieces = [Piece(r["label"], r["width"], r["height"], r["qty"], r.get("allow_rotation", True),
                        material=r.get("material", ""), texture=r.get("texture", ""),
                        customer=r.get("customer", ""))
                  for r in self.piece_table.rows]

        try:
            results, unplaced = optimize(stock, pieces, kerf=kerf)
        except Exception as e:
            messagebox.showerror("Optimization error", str(e))
            return

        self.last_results, self.last_unplaced = results, unplaced
        self.results_view.set_results(results)
        self.stats_view.update_stats(results, unplaced)

        groups = group_sheet_results(results)
        avg_util = (sum(r.utilization for r in results) / len(results) * 100) if results else 0
        msg = f"{len(results)} sheet(s) used ({len(groups)} unique layout(s)), avg utilization {avg_util:.1f}%"
        if unplaced:
            msg += f"  |  WARNING: {len(unplaced)} piece(s) could not be placed"
            messagebox.showwarning(
                "Not all pieces placed",
                "These pieces could not be placed:\n\n" +
                "\n".join(f"- {p['label']} ({p['width']:g} x {p['height']:g} mm) — {p.get('reason', 'out of stock')}"
                          for p in unplaced)
            )
        self.status_label.config(text=msg)

    def export_cutting_list(self):
        if not self.last_results:
            messagebox.showinfo("Export cutting list", "Run Optimize first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["sheet_number", "stock_label", "piece_label", "customer",
                              "x_mm", "y_mm", "width_mm", "height_mm", "rotated"])
            for sheet_num, r in enumerate(self.last_results, start=1):
                for p in r.placements:
                    writer.writerow([sheet_num, r.sheet_label, p.label, getattr(p, "customer", ""),
                                      f"{p.x:g}", f"{p.y:g}",
                                      f"{p.width:g}", f"{p.height:g}", "yes" if p.rotated else "no"])
        messagebox.showinfo("Export cutting list", f"Saved: {path}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
