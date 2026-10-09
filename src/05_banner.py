"""01 — banner: graphite slide, amber accent, four fact cells."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

k = json.loads((Path(__file__).resolve().parents[1] / "outputs" / "kpis.json").read_text())
e = json.loads((Path(__file__).resolve().parents[1] / "outputs" / "model_eval.json").read_text())

fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)
ax.set_xlim(0, 12); ax.set_ylim(0, 6.75); ax.axis("off")
fig.patch.set_facecolor("#20242a")

ax.text(0.55, 5.95, "WHO DO WE PAY TO KEEP?", fontsize=25, fontweight="bold",
        color="#f2f0eb")
ax.text(0.55, 5.35, "Telco churn, 7,043 customers — the save-list, not the churn curve",
        fontsize=12, color="#9aa0a6")

cells = [
    ("26.5%", "churn rate", 0.55),
    ("$139k", "monthly revenue\nat risk", 3.42),
    ("12 months", "median tenure\nof a churner", 6.29),
    ("42.7%", "month-to-month churn\nvs 2.8% on 2-year", 9.16),
]
for big, small, x in cells:
    ax.add_patch(FancyBboxPatch((x, 2.35), 2.5, 2.45, boxstyle="round,pad=0.06",
                                fc="#2b3038", ec="#3a4048"))
    ax.text(x + 1.25, 3.95, big, fontsize=19, fontweight="bold", color="#f2b135",
            ha="center", va="center")
    ax.text(x + 1.25, 3.1, small, fontsize=9.5, color="#b9bec4", ha="center",
            va="center", linespacing=1.4)

ax.text(0.55, 1.45, "Model: AUC 0.84 → every customer scored and ranked by dollars at risk.",
        fontsize=12.5, color="#e8e6e1")
ax.text(0.55, 0.8, f"Save-list program under written assumptions: {e['roi_12m']:.1f}x ROI over 12 months.",
        fontsize=12, color="#c8b06a")
fig.savefig(Path(__file__).resolve().parents[1] / "outputs" / "banner.png",
            dpi=100, facecolor=fig.get_facecolor())
print("banner written")
