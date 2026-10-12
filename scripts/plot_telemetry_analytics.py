"""Production Telemetry & Model Performance Visualizer for Curiosity AI.

Generates real-time matplotlib dashboards tracking:
1. Model Real-time Accuracy (%) over time
2. Pipeline Latency / Execution Time (seconds)
3. Media Category Distribution (Images, Documents, Text)
4. Confidence vs Accuracy Correlation
"""

import os
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "assistant.db"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHART_PATH = OUTPUT_DIR / "model_analytics_report.png"

def generate_telemetry_dashboard(save_path: Optional[Path] = None) -> Optional[Path]:
    target_path = Path(save_path) if save_path else CHART_PATH
    print(f"Connecting to telemetry database at: {DB_PATH}")
    if not DB_PATH.exists():
        print(f"Warning: Database {DB_PATH} not found. Running inferences first will populate data.")
        return None

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Query audit logs
    cur.execute("""
        SELECT id, prompt, media_category, accuracy, confidence, duration_s, created_at 
        FROM audit_logs 
        ORDER BY id ASC
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No telemetry records found in audit_logs yet.")
        return

    ids = [r[0] for r in rows]
    categories = [r[2] or "unknown" for r in rows]
    accuracies = [r[3] for r in rows]
    confidences = [r[4] * 100.0 if r[4] <= 1.0 else r[4] for r in rows]
    latencies = [r[5] for r in rows]

    # Matplotlib styling: sleek dark cyberpunk theme
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle("Curiosity AI - Real-Time Model Performance & Accuracy Telemetry", fontsize=16, fontweight="bold", color="#00ffcc")

    # 1. Real-Time Accuracy Over Inferences
    ax1 = axes[0, 0]
    ax1.plot(ids, accuracies, color="#00e5ff", marker="o", linewidth=2, markersize=5, label="Pipeline Accuracy (%)")
    mean_acc = sum(accuracies) / len(accuracies)
    ax1.axhline(mean_acc, color="#ff007f", linestyle="--", label=f"Mean Accuracy: {mean_acc:.1f}%")
    ax1.set_title("1. Real-Time Model Accuracy Trend (%)", fontsize=12, fontweight="bold", color="#ffffff")
    ax1.set_xlabel("Inference Run #", color="#cccccc")
    ax1.set_ylabel("Accuracy (%)", color="#cccccc")
    ax1.set_ylim(40, 105)
    ax1.grid(True, linestyle=":", alpha=0.4)
    ax1.legend(loc="lower right")

    # 2. Pipeline Latency (Execution Speed in Seconds)
    ax2 = axes[0, 1]
    colors = ["#ff3366" if lat > 15.0 else ("#ffbb00" if lat > 5.0 else "#00ff88") for lat in latencies]
    ax2.bar(ids, latencies, color=colors, alpha=0.85, width=0.6)
    mean_lat = sum(latencies) / len(latencies)
    ax2.axhline(mean_lat, color="#00e5ff", linestyle="--", label=f"Mean Latency: {mean_lat:.2f}s")
    ax2.set_title("2. Inference Latency & Execution Speed (s)", fontsize=12, fontweight="bold", color="#ffffff")
    ax2.set_xlabel("Inference Run #", color="#cccccc")
    ax2.set_ylabel("Duration (Seconds)", color="#cccccc")
    ax2.grid(True, linestyle=":", alpha=0.4)
    ax2.legend(loc="upper right")

    # 3. Media Category Distribution
    ax3 = axes[1, 0]
    cat_counts = {}
    for c in categories:
        clean_c = c.replace("_", " ").title()
        cat_counts[clean_c] = cat_counts.get(clean_c, 0) + 1
    
    cat_labels = list(cat_counts.keys())
    cat_vals = list(cat_counts.values())
    pie_colors = ["#00e5ff", "#ff007f", "#7928ca", "#00ff88"][:len(cat_labels)]
    ax3.pie(cat_vals, labels=cat_labels, autopct="%1.1f%%", colors=pie_colors, startangle=140, textprops={'color': "white"})
    ax3.set_title("3. Processed Media Categories", fontsize=12, fontweight="bold", color="#ffffff")

    # 4. Accuracy vs Confidence Correlation
    ax4 = axes[1, 1]
    ax4.scatter(confidences, accuracies, c=latencies, cmap="plasma", s=70, alpha=0.9, edgecolors="white", linewidth=0.5)
    ax4.set_title("4. Confidence vs Accuracy Correlation", fontsize=12, fontweight="bold", color="#ffffff")
    ax4.set_xlabel("Model Confidence (%)", color="#cccccc")
    ax4.set_ylabel("Calculated Accuracy (%)", color="#cccccc")
    ax4.set_xlim(40, 105)
    ax4.set_ylim(40, 105)
    ax4.grid(True, linestyle=":", alpha=0.4)
    cb = plt.colorbar(ax4.collections[0], ax=ax4)
    cb.set_label("Latency (s)", color="#cccccc")

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(target_path, dpi=200, bbox_inches="tight")
    plt.close()

    print(f"\n[Telemetry Report Generated Successfully!]")
    print(f"Chart saved at: {target_path.resolve()}")
    print(f"Total Inferences Audited : {len(rows)}")
    print(f"Average Accuracy          : {mean_acc:.2f}%")
    print(f"Average Pipeline Latency : {mean_lat:.2f}s\n")
    return target_path

if __name__ == "__main__":
    generate_telemetry_dashboard()
