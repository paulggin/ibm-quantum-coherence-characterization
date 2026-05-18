# multiqubit_heatmap_marrakesh_full.py
# Full T1 + T2Ramsey circuit experiments on all 156 FakeMarrakesh qubits
# Runtime estimate: 60–90 min on modern laptop

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh
from qiskit_aer import AerSimulator
from qiskit_experiments.library import T1, T2Ramsey

# ── Backend ───────────────────────────────────────────────────────────────────
backend = AerSimulator.from_backend(FakeMarrakesh())
num_qubits = 156
print(f"Backend: FakeMarrakesh — {num_qubits} qubits")
print(f"Started: {datetime.now().strftime('%H:%M:%S')}\n")

# ── Delay parameters ──────────────────────────────────────────────────────────
T1_DELAYS = np.linspace(1e-6, 500e-6, 25)
T2_DELAYS = np.linspace(1e-6, 200e-6, 25)
OSC_FREQ  = 1e5
SHOTS     = 1024

# ── Storage ───────────────────────────────────────────────────────────────────
t1_vals = {}
t2_vals = {}
t1_errs = {}
t2_errs = {}

# ── Header ────────────────────────────────────────────────────────────────────
print(f"{'Qubit':<8} {'T1 (µs)':<14} {'T2 (µs)':<14} {'Status'}")
print("-" * 55)

# ── Main loop ─────────────────────────────────────────────────────────────────
for qubit in range(num_qubits):

    # T1
    try:
        exp = T1(physical_qubits=(qubit,), delays=T1_DELAYS)
        exp.set_transpile_options(optimization_level=0)
        result = exp.run(backend, shots=SHOTS).block_for_results()
        val = result.analysis_results("T1").value
        t1_vals[qubit] = val.nominal_value * 1e6
        t1_errs[qubit] = val.std_dev * 1e6
    except Exception as e:
        t1_vals[qubit] = np.nan
        t1_errs[qubit] = np.nan

    # T2 Ramsey
    try:
        exp = T2Ramsey(
            physical_qubits=(qubit,),
            delays=T2_DELAYS,
            osc_freq=OSC_FREQ
        )
        exp.set_transpile_options(optimization_level=0)
        result = exp.run(backend, shots=SHOTS).block_for_results()
        val = result.analysis_results("T2star").value
        t2_vals[qubit] = val.nominal_value * 1e6
        t2_errs[qubit] = val.std_dev * 1e6
    except Exception as e:
        t2_vals[qubit] = np.nan
        t2_errs[qubit] = np.nan

    # ── Per-qubit status line ─────────────────────────────────────────────────
    t1 = t1_vals[qubit]
    t2 = t2_vals[qubit]

    t1_str = f"{t1:.1f}" if not np.isnan(t1) else "NaN"
    t2_str = f"{t2:.1f}" if not np.isnan(t2) else "NaN"

    if np.isnan(t1) and np.isnan(t2):
        status = "both NaN"
    elif np.isnan(t1):
        status = "T1 NaN"
    elif np.isnan(t2):
        status = "T2 NaN"
    elif t2 > 2 * t1:
        status = "⚠ T2 > 2×T1"
    elif t1 < 30:
        status = "⚠ T1 low"
    elif t2 < 10:
        status = "⚠ T2 low"
    else:
        status = "✓"

    print(f"  Q{qubit:<6} {t1_str:<14} {t2_str:<14} {status}")

    # ── Checkpoint every 10 qubits ────────────────────────────────────────────
    if (qubit + 1) % 10 == 0:
        pd.DataFrame({
            "qubit":     list(range(qubit + 1)),
            "T1_us":     [t1_vals.get(q, np.nan) for q in range(qubit + 1)],
            "T1_err_us": [t1_errs.get(q, np.nan) for q in range(qubit + 1)],
            "T2_us":     [t2_vals.get(q, np.nan) for q in range(qubit + 1)],
            "T2_err_us": [t2_errs.get(q, np.nan) for q in range(qubit + 1)],
        }).to_csv(DATA_DIR / "marrakesh_156qubit_coherence_checkpoint.csv", index=False)
        pct = (qubit + 1) / num_qubits * 100
        print(f"\n  ── checkpoint saved @ {datetime.now().strftime('%H:%M:%S')} "
              f"({pct:.0f}%) ──\n")
        print(f"{'Qubit':<8} {'T1 (µs)':<14} {'T2 (µs)':<14} {'Status'}")
        print("-" * 55)

print(f"\nFinished: {datetime.now().strftime('%H:%M:%S')}")

# ── Final CSV ─────────────────────────────────────────────────────────────────
df = pd.DataFrame({
    "qubit":     list(range(num_qubits)),
    "T1_us":     [t1_vals.get(q, np.nan) for q in range(num_qubits)],
    "T1_err_us": [t1_errs.get(q, np.nan) for q in range(num_qubits)],
    "T2_us":     [t2_vals.get(q, np.nan) for q in range(num_qubits)],
    "T2_err_us": [t2_errs.get(q, np.nan) for q in range(num_qubits)],
})
csv_out = DATA_DIR / "marrakesh_156qubit_coherence.csv"
df.to_csv(csv_out, index=False)
print(f"Saved: {csv_out}")

# ── Summary ───────────────────────────────────────────────────────────────────
t1_arr = np.array([t1_vals.get(q, np.nan) for q in range(num_qubits)])
t2_arr = np.array([t2_vals.get(q, np.nan) for q in range(num_qubits)])

print(f"\n── SUMMARY ──────────────────────────────────")
print(f"  T1: mean={np.nanmean(t1_arr):.1f} µs  "
      f"min={np.nanmin(t1_arr):.1f} µs  "
      f"max={np.nanmax(t1_arr):.1f} µs")
print(f"  T2: mean={np.nanmean(t2_arr):.1f} µs  "
      f"min={np.nanmin(t2_arr):.1f} µs  "
      f"max={np.nanmax(t2_arr):.1f} µs")
print(f"  T1 NaN count: {np.sum(np.isnan(t1_arr))}")
print(f"  T2 NaN count: {np.sum(np.isnan(t2_arr))}")

violations = [q for q in range(num_qubits)
              if not np.isnan(t1_arr[q]) and not np.isnan(t2_arr[q])
              and t2_arr[q] > 2 * t1_arr[q]]
print(f"  T2 > 2×T1 violations: {violations if violations else 'None'}")

# ── Plot ──────────────────────────────────────────────────────────────────────
from pathlib import Path
GRID_ROWS = 12
GRID_COLS = 13
REPO_ROOT = Path(__file__).resolve().parent.parent
PLOTS_DIR = REPO_ROOT / "plots"
DATA_DIR  = REPO_ROOT / "data"
PLOTS_DIR.mkdir(exist_ok=True); DATA_DIR.mkdir(exist_ok=True)

fig, axes = plt.subplots(1, 2, figsize=(20, 9))

for ax, values, label, cmap in zip(
    axes,
    [t1_arr, t2_arr],
    ["T1 (µs)", "T2* (µs)"],
    ["Blues", "Greens"]
):
    padded = np.full(GRID_ROWS * GRID_COLS, np.nan)
    padded[:len(values)] = values
    grid = padded.reshape(GRID_ROWS, GRID_COLS)

    valid = values[~np.isnan(values)]
    if len(valid) == 0:
        ax.set_title(f"{label} — No Data")
        continue

    im = ax.imshow(grid, cmap=cmap, aspect='auto',
                   vmin=np.nanpercentile(values, 5),
                   vmax=np.nanpercentile(values, 95))

    threshold = np.nanmean(values)
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

plt.suptitle(
    "Qubit Coherence Heatmap — FakeMarrakesh\n"
    "T1/T2 from Full Circuit Experiments (All 156 Qubits, 1024 shots, 25 delays)",
    fontsize=14
)
plt.tight_layout()

save_path = PLOTS_DIR / "coherence_heatmap_156qubit_unmasked.png"
plt.savefig(save_path, dpi=150, bbox_inches='tight')
print(f"\nHeatmap saved to: {save_path}")
plt.show()