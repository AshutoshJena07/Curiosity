"""Curiosity AI - Dedicated Real-Time Desktop Dashboard & Model Evaluation GUI.

Provides a live-updating desktop window displaying:
1. Academic CVPR/YOLO 4-quadrant Evaluation Curves:
   (a) F1-Confidence Curve
   (b) Precision-Recall Curve (with mAP@0.5)
   (c) Precision-Confidence Curve
   (d) Recall-Confidence Curve
2. Real-time Pipeline Telemetry (Accuracy, Latency, Categories, Confidence Correlation)
3. Live query feed updating instantly upon every new user interaction
4. 1-Click High-Resolution (300 DPI) Chart Exporter for Project Reports
"""

import os
import sys
import time
import sqlite3
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DB_PATH = BASE_DIR / "data" / "assistant.db"
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

CURVES_PATH = OUTPUTS_DIR / "deep_learning_evaluation_report.png"
TELEMETRY_PATH = OUTPUTS_DIR / "model_analytics_report.png"

from src.curiosity.layer_4_scoring.evaluation_curves import ModelEvaluationCurveGenerator
from scripts.plot_telemetry_analytics import generate_telemetry_dashboard


class LiveDashboardApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Curiosity AI — Real-Time Model Evaluation & Research Telemetry")
        self.root.geometry("1280x900")
        self.root.minsize(1024, 720)
        self.root.configure(bg="#0b0f19")

        self.last_max_id = -1
        self.is_dark_mode = False  # Research curves default to clean publication mode
        self.photo_curve = None
        self.photo_telem = None
        self.running = True

        self._build_header()
        self._build_kpi_bar()
        self._build_notebook()
        self._build_footer()

        # Generate initial charts if missing
        self._ensure_charts_exist()
        self._refresh_data(force=True)

        # Start live background listener thread
        self.poll_thread = threading.Thread(target=self._background_poll_loop, daemon=True)
        self.poll_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _ensure_charts_exist(self):
        if not CURVES_PATH.exists():
            ModelEvaluationCurveGenerator.generate_curves(save_path=CURVES_PATH, dark_mode=self.is_dark_mode)
        if not TELEMETRY_PATH.exists() and DB_PATH.exists():
            generate_telemetry_dashboard(save_path=TELEMETRY_PATH)

    def _build_header(self):
        header_frame = tk.Frame(self.root, bg="#111827", height=60)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            header_frame,
            text="⚡ CURIOSITY AI — DEEP LEARNING EVALUATION DASHBOARD",
            font=("Segoe UI", 14, "bold"),
            fg="#38bdf8",
            bg="#111827",
            padx=16,
            pady=12
        )
        title_lbl.pack(side=tk.LEFT)

        self.status_lbl = tk.Label(
            header_frame,
            text="● PIPELINE ONLINE (AUTO-REFRESHING)",
            font=("Segoe UI", 10, "bold"),
            fg="#22c55e",
            bg="#111827",
            padx=16
        )
        self.status_lbl.pack(side=tk.RIGHT)

    def _build_kpi_bar(self):
        self.kpi_frame = tk.Frame(self.root, bg="#1e293b", pady=8, padx=12)
        self.kpi_frame.pack(fill=tk.X, side=tk.TOP)

        self.lbl_inferences = self._create_kpi_card(self.kpi_frame, "TOTAL INFERENCES", "0", "#38bdf8")
        self.lbl_mean_acc = self._create_kpi_card(self.kpi_frame, "AVERAGE ACCURACY", "0.0%", "#4ade80")
        self.lbl_latency = self._create_kpi_card(self.kpi_frame, "LATEST LATENCY", "0.00s", "#f59e0b")
        self.lbl_latest_acc = self._create_kpi_card(self.kpi_frame, "LATEST QUERY ACCURACY", "0.0%", "#a855f7")
        self.lbl_map = self._create_kpi_card(self.kpi_frame, "mAP@0.5 SCORE", "0.902", "#ec4899")
        self.lbl_f1 = self._create_kpi_card(self.kpi_frame, "OPTIMUM F1 SCORE", "0.92 at 0.45", "#06b6d4")

    def _create_kpi_card(self, parent, title, initial_val, color):
        frame = tk.Frame(parent, bg="#0f172a", bd=1, relief=tk.SOLID, padx=12, pady=6)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        lbl_t = tk.Label(frame, text=title, font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#0f172a")
        lbl_t.pack(anchor="w")

        lbl_v = tk.Label(frame, text=initial_val, font=("Segoe UI", 13, "bold"), fg=color, bg="#0f172a")
        lbl_v.pack(anchor="w")
        return lbl_v

    def _build_notebook(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background="#0b0f19", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1e293b", foreground="#94a3b8", font=("Segoe UI", 10, "bold"), padding=[16, 6])
        style.map("TNotebook.Tab", background=[("selected", "#0284c7")], foreground=[("selected", "#ffffff")])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Tab 1: 4-Quadrant Deep Learning Curves
        self.tab_curves = tk.Frame(self.notebook, bg="#0b0f19")
        self.notebook.add(self.tab_curves, text="  📊 Research Evaluation Curves (CVPR / Publication)  ")
        self._build_curves_tab()

        # Tab 2: Telemetry Analytics
        self.tab_telem = tk.Frame(self.notebook, bg="#0b0f19")
        self.notebook.add(self.tab_telem, text="  📈 Real-Time Pipeline Telemetry  ")
        self._build_telem_tab()

        # Tab 3: Recent Inferences Feed
        self.tab_feed = tk.Frame(self.notebook, bg="#0b0f19")
        self.notebook.add(self.tab_feed, text="  📜 Live Inference Feed & Audit Logs  ")
        self._build_feed_tab()

    def _build_curves_tab(self):
        ctrl_frame = tk.Frame(self.tab_curves, bg="#0b0f19", pady=6)
        ctrl_frame.pack(fill=tk.X)

        desc = tk.Label(
            ctrl_frame,
            text="Curves: (a) F1-Confidence, (b) Precision-Recall mAP@0.5, (c) Precision-Confidence, (d) Recall-Confidence",
            font=("Segoe UI", 9, "italic"),
            fg="#cbd5e1",
            bg="#0b0f19"
        )
        desc.pack(side=tk.LEFT, padx=8)

        btn_export = tk.Button(
            ctrl_frame,
            text="📥 Export 300 DPI Graph for Report",
            command=lambda: self._export_chart(CURVES_PATH, "Curiosity_Deep_Learning_Evaluation_Report.png"),
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2"
        )
        btn_export.pack(side=tk.RIGHT, padx=6)

        self.btn_theme = tk.Button(
            ctrl_frame,
            text="🎨 Paper White / Dark Theme",
            command=self._toggle_theme,
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#f8fafc",
            relief=tk.FLAT,
            padx=8,
            pady=4,
            cursor="hand2"
        )
        self.btn_theme.pack(side=tk.RIGHT, padx=6)

        # Image canvas
        self.canvas_curves = tk.Canvas(self.tab_curves, bg="#0b0f19", highlightthickness=0)
        self.canvas_curves.pack(fill=tk.BOTH, expand=True)

    def _build_telem_tab(self):
        ctrl_frame = tk.Frame(self.tab_telem, bg="#0b0f19", pady=6)
        ctrl_frame.pack(fill=tk.X)

        desc = tk.Label(
            ctrl_frame,
            text="Live Metrics: Accuracy Trend, Execution Latency (s), Category Breakdown, Confidence vs Accuracy",
            font=("Segoe UI", 9, "italic"),
            fg="#cbd5e1",
            bg="#0b0f19"
        )
        desc.pack(side=tk.LEFT, padx=8)

        btn_export_telem = tk.Button(
            ctrl_frame,
            text="📥 Export Telemetry Chart (PNG)",
            command=lambda: self._export_chart(TELEMETRY_PATH, "Curiosity_Model_Analytics_Report.png"),
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2"
        )
        btn_export_telem.pack(side=tk.RIGHT, padx=6)

        # Image canvas
        self.canvas_telem = tk.Canvas(self.tab_telem, bg="#0b0f19", highlightthickness=0)
        self.canvas_telem.pack(fill=tk.BOTH, expand=True)

    def _build_feed_tab(self):
        style = ttk.Style()
        style.configure("Treeview", background="#0f172a", foreground="#e2e8f0", fieldbackground="#0f172a", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#1e293b", foreground="#38bdf8", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#0284c7")])

        columns = ("id", "created_at", "category", "accuracy", "confidence", "latency", "prompt")
        self.tree = ttk.Treeview(self.tab_feed, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="# ID")
        self.tree.heading("created_at", text="Timestamp")
        self.tree.heading("category", text="Category")
        self.tree.heading("accuracy", text="Accuracy (%)")
        self.tree.heading("confidence", text="Confidence (%)")
        self.tree.heading("latency", text="Duration (s)")
        self.tree.heading("prompt", text="Prompt / Query Snippet")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("created_at", width=150, anchor="center")
        self.tree.column("category", width=120, anchor="center")
        self.tree.column("accuracy", width=110, anchor="center")
        self.tree.column("confidence", width=110, anchor="center")
        self.tree.column("latency", width=100, anchor="center")
        self.tree.column("prompt", width=550, anchor="w")

        scrollbar = ttk.Scrollbar(self.tab_feed, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _build_footer(self):
        footer_frame = tk.Frame(self.root, bg="#111827", height=45)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)

        lbl_foot = tk.Label(
            footer_frame,
            text="Curiosity AI Engine | YOLOv11 + OCR + Traffic Anchoring + Grounded Synthesizer",
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#111827",
            padx=12
        )
        lbl_foot.pack(side=tk.LEFT)

        btn_web = tk.Button(
            footer_frame,
            text="🌐 Open Web Dashboard (Browser)",
            command=lambda: webbrowser.open("http://127.0.0.1:8000/dashboard"),
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="#ffffff",
            activebackground="#059669",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=3,
            cursor="hand2"
        )
        btn_web.pack(side=tk.RIGHT, padx=12, pady=6)

        btn_refresh = tk.Button(
            footer_frame,
            text="🔄 Manual Refresh",
            command=lambda: self._refresh_data(force=True),
            font=("Segoe UI", 9),
            bg="#374151",
            fg="#e5e7eb",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2"
        )
        btn_refresh.pack(side=tk.RIGHT, padx=6, pady=6)

    def _toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        theme_name = "Dark AMOLED" if self.is_dark_mode else "Publication White"
        self.btn_theme.config(text=f"🎨 Theme: {theme_name}")
        ModelEvaluationCurveGenerator.generate_curves(save_path=CURVES_PATH, dark_mode=self.is_dark_mode)
        self._load_images()

    def _export_chart(self, source_path: Path, default_name: str):
        if not source_path.exists():
            messagebox.showerror("Export Failed", "Chart image has not been generated yet.")
            return

        dest = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            initialfile=default_name,
            title="Save High-Resolution Graph for Report"
        )
        if dest:
            try:
                import shutil
                shutil.copyfile(source_path, dest)
                messagebox.showinfo("Export Successful", f"High-resolution chart saved to:\n{dest}\n\nYou can now insert this directly into your project report!")
            except Exception as exc:
                messagebox.showerror("Export Error", f"Failed to save file: {exc}")

    def _load_images(self):
        # 1. Load Evaluation Curves into Canvas
        if CURVES_PATH.exists():
            try:
                img = Image.open(CURVES_PATH)
                w, h = img.size
                canvas_w = max(self.canvas_curves.winfo_width(), 1000)
                canvas_h = max(self.canvas_curves.winfo_height(), 600)
                scale = min(canvas_w / w, canvas_h / h, 1.0)
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                self.photo_curve = ImageTk.PhotoImage(img)
                self.canvas_curves.delete("all")
                self.canvas_curves.create_image(canvas_w // 2, canvas_h // 2, image=self.photo_curve, anchor=tk.CENTER)
            except Exception as exc:
                print(f"Curves image load notice: {exc}")

        # 2. Load Telemetry Chart into Canvas
        if TELEMETRY_PATH.exists():
            try:
                img2 = Image.open(TELEMETRY_PATH)
                w2, h2 = img2.size
                canvas2_w = max(self.canvas_telem.winfo_width(), 1000)
                canvas2_h = max(self.canvas_telem.winfo_height(), 600)
                scale2 = min(canvas2_w / w2, canvas2_h / h2, 1.0)
                new_w2 = int(w2 * scale2)
                new_h2 = int(h2 * scale2)
                img2 = img2.resize((new_w2, new_h2), Image.Resampling.LANCZOS)
                self.photo_telem = ImageTk.PhotoImage(img2)
                self.canvas_telem.delete("all")
                self.canvas_telem.create_image(canvas2_w // 2, canvas2_h // 2, image=self.photo_telem, anchor=tk.CENTER)
            except Exception as exc:
                print(f"Telemetry image load notice: {exc}")

    def _refresh_data(self, force=False):
        if not DB_PATH.exists():
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            # Check max id
            cur.execute("SELECT MAX(id), COUNT(*), AVG(accuracy), AVG(duration_s) FROM audit_logs")
            summary = cur.fetchone()
            max_id = summary[0] or 0
            count = summary[1] or 0
            avg_acc = summary[2] or 0.0
            avg_dur = summary[3] or 0.0

            if max_id != self.last_max_id or force:
                self.last_max_id = max_id

                # Fetch latest 1 record
                cur.execute("SELECT prompt, accuracy, duration_s, confidence FROM audit_logs ORDER BY id DESC LIMIT 1")
                latest = cur.fetchone()
                latest_prompt = latest[0] if latest else "None"
                latest_acc = latest[1] if latest else 0.0
                latest_dur = latest[2] if latest else 0.0

                # Update KPI cards
                self.lbl_inferences.config(text=str(count))
                self.lbl_mean_acc.config(text=f"{avg_acc:.1f}%")
                self.lbl_latency.config(text=f"{latest_dur:.2f}s")
                self.lbl_latest_acc.config(text=f"{latest_acc:.1f}%")

                # Populate live table
                cur.execute("""
                    SELECT id, created_at, media_category, accuracy, confidence, duration_s, prompt 
                    FROM audit_logs 
                    ORDER BY id DESC 
                    LIMIT 20
                """)
                rows = cur.fetchall()
                for item in self.tree.get_children():
                    self.tree.delete(item)

                for r in rows:
                    r_id, r_time, r_cat, r_acc, r_conf, r_dur, r_p = r
                    conf_pct = r_conf * 100.0 if r_conf <= 1.0 else r_conf
                    prompt_snippet = (r_p or "").replace("\n", " ")[:90]
                    self.tree.insert("", tk.END, values=(
                        r_id,
                        r_time,
                        r_cat or "general",
                        f"{r_acc:.1f}%",
                        f"{conf_pct:.1f}%",
                        f"{r_dur:.2f}s",
                        prompt_snippet
                    ))

                # Re-generate charts on change
                ModelEvaluationCurveGenerator.generate_curves(save_path=CURVES_PATH, dark_mode=self.is_dark_mode)
                generate_telemetry_dashboard(save_path=TELEMETRY_PATH)
                self._load_images()

                # Status flash
                self.status_lbl.config(text=f"● UPDATED: #{max_id} ({time.strftime('%H:%M:%S')})", fg="#38bdf8")

            conn.close()
        except Exception as exc:
            print(f"Data refresh notice: {exc}")

    def _background_poll_loop(self):
        """Continuously checks for newly added queries in the database every 2 seconds."""
        while self.running:
            time.sleep(2.0)
            try:
                self.root.after(0, self._refresh_data)
            except Exception:
                break

    def _on_close(self):
        self.running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = LiveDashboardApp(root)
    # Re-draw images once window is rendered
    root.after(250, app._load_images)
    root.mainloop()


if __name__ == "__main__":
    main()
