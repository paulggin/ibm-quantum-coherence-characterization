import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
df = pd.read_csv(DATA_DIR / "marrakesh_156qubit_coherence.csv")
t1_arr = df["T1_us"].values.copy()
t2_arr = df["T2_us"].values.copy()

# Mask bad fits
t1_arr[t1_arr <= 0] = np.nan
t1_arr[t1_arr > 2000] = np.nan
t2_arr[t2_arr <= 0] = np.nan
t2_arr[t2_arr > 2000] = np.nan

print(f"\n── SUMMARY (bad fits masked) ────────────────")
print(f"  T1: mean={np.nanmean(t1_arr):.1f} µs  "
      f"min={np.nanmin(t1_arr):.1f} µs  "
      f"max={np.nanmax(t1_arr):.1f} µs")
print(f"  T2: mean={np.nanmean(t2_arr):.1f} µs  "
      f"min={np.nanmin(t2_arr):.1f} µs  "
      f"max={np.nanmax(t2_arr):.1f} µs")
print(f"  T1 NaN/bad fit count: {np.sum(np.isnan(t1_arr))}")
print(f"  T2 NaN/bad fit count: {np.sum(np.isnan(t2_arr))}")

num_qubits = len(df)
violations = [q for q in range(num_qubits)
              if not np.isnan(t1_arr[q]) and not np.isnan(t2_arr[q])
              and t2_arr[q] > 2 * t1_arr[q]]
print(f"  T2 > 2×T1 violations: {violations if violations else 'None'}")