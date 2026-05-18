import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
PLOTS_DIR = REPO_ROOT / "plots"
PLOTS_DIR.mkdir(exist_ok=True)

df = pd.read_csv(DATA_DIR / "marrakesh_156qubit_coherence.csv")
t1_arr = df["T1_us"].values.copy()
t2_arr = df["T2_us"].values.copy()

# Mask bad fits
t1_arr[t1_arr <= 0] = np.nan
t1_arr[t1_arr > 2000] = np.nan
t2_arr[t2_arr <= 0] = np.nan
t2_arr[t2_arr > 2000] = np.nan

num_qubits = 156
GRID_ROWS = 12
GRID_COLS = 13

fig, axes = plt.subplots(1, 2, figsize=(20, 9))
fig.suptitle(
    "Qubit Coherence Heatmap — FakeMarrakesh\n"
    "T1/T2 from Full Circuit Experiments (All 156 Qubits, 1024 shots, 25 delays)",
    fontsize=14
)

for ax, values, label, cmap in zip(
    axes,
    [t1_arr, t2_arr],
    ["T1 (µs)", "T2* (µs)"],
    ["Blues", "Greens"]
):
    padded = np.full(GRID_ROWS * GRID_COLS, np.nan)
    padded[:num_qubits] = values
    grid = padded.reshape(GRID_ROWS, GRID_COLS)

    valid = values[~np.isnan(values)]
    vmin = np.percentile(valid, 5)
    vmax = np.percentile(valid, 95)
    threshold = np.nanmean(values)

    im = ax.imshow(grid, cmap=cmap, aspect='auto',
                   vmin=vmin, vmax=vmax, interpolation='nearest')

    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            q_idx = row * GRID_COLS + col
            if q_idx < num_qubits:
                val = values[q_idx]
                if not np.isnan(val):
                    text = f"Q{q_idx}\n{val:.0f}"
                    color = "white" if val > threshold else "black"
                else:
                    text = f"Q{q_idx}\nNaN"
                    color = "red"
                ax.text(col, row, text, ha='center', va='center',
                        fontsize=5.5, color=color)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"{label} — FakeMarrakesh (Simulated)", fontsize=13)
    plt.colorbar(im, ax=ax, label=label)

plt.tight_layout()
save_path = PLOTS_DIR / "coherence_heatmap_156qubit_masked.png"
plt.savefig(save_path, dpi=150, bbox_inches='tight')
print(f"Saved: {save_path}")
plt.show()