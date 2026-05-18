"""
real_hardware_anchor.py
T1 + T2 Ramsey + Randomized Benchmarking on ONE real IBM Quantum qubit.

Purpose
-------
Anchor the FakeMarrakesh / FakeNairobi simulator-based portfolio with a
real-device run so the writeup can honestly say "real hardware, not
simulation."

Design
------
- Reuses the canonical circuit definitions from circuits.py — same code that
  validates on FakeMarrakesh runs here on real silicon. The fake-backend
  scripts (t1_experiment.py, t2_ramsey.py) and this anchor differ only in
  the execution wrapper (AerSimulator vs. SamplerV2).
- Single qubit, single backend, conservative circuit budget. The 156-qubit
  characterization is already done on the fake backend; this run is the
  credibility anchor.
- Backend selection: try ibm_marrakesh first for direct comparability with
  the FakeMarrakesh portfolio. If that isn't in the account's plan, fall
  back to ibm_brisbane (Eagle r3) and frame the comparison as "methodology
  generalizes across hardware generations."
- Compute budget: ~35 circuits, ~5 sec actual quantum compute. Comfortably
  fits IBM Quantum Open Plan free tier (10 min/month).

Outputs (saved to outputs/real_hardware/)
-----------------------------------------
- <backend>_q<qubit>_metadata.json   backend + qubit calibration at runtime, job IDs
- <backend>_q<qubit>_t1.csv          delay sweep + P(|1>)
- <backend>_q<qubit>_t2.csv          delay sweep + P(|1>)
- <backend>_q<qubit>_t1_fit.png      fit plot
- <backend>_q<qubit>_t2_fit.png      fit plot
- <backend>_q<qubit>_rb_fit.png      RB decay plot
- summary.txt                        headline T1, T2, EPC, fidelity

How to run
----------
1. Confirm credentials: QiskitRuntimeService.save_account(channel=..., token=...)
2. From the source repo root:  python experiments/real_hardware_anchor.py
3. Defaults: try Marrakesh -> Brisbane fallback, qubit 0. Edit CONFIG to override.
"""

import os
import json
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

warnings.filterwarnings("ignore")

from qiskit import transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit_experiments.library import StandardRB

from circuits import t1_circuit, t2_ramsey_circuit, exp_decay, ramsey_decay


# ──────────────────────────────────────────────────────────────────────────────
# CONFIG  — edit if you want a different backend / qubit / sweep
# ──────────────────────────────────────────────────────────────────────────────
PREFERRED_BACKENDS = ["ibm_marrakesh", "ibm_brisbane"]   # try in order
PIN_QUBIT          = 0
SHOTS              = 1024

T1_DELAYS_US       = np.linspace(0, 600, 15)
T2_DELAYS_US       = np.linspace(0, 100, 20)
T2_DETUNING_MHZ    = 0.05

RB_LENGTHS = [1, 10, 50, 100, 200, 300]
RB_NUM_SAMPLES = 50

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "real_hardware"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR = Path(__file__).resolve().parent.parent / "plots"
PLOTS_DIR.mkdir(exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# 1. CONNECT TO IBM QUANTUM, SELECT BACKEND
# ──────────────────────────────────────────────────────────────────────────────
print("Connecting to IBM Quantum Runtime...")
service = QiskitRuntimeService()

backend = None
for name in PREFERRED_BACKENDS:
    try:
        backend = service.backend(name)
        print(f"Backend selected: {name}")
        break
    except Exception as e:
        print(f"  {name}: not available ({type(e).__name__})")

if backend is None:
    backend = service.least_busy(operational=True, simulator=False, min_num_qubits=5)
    print(f"Falling back to least_busy: {backend.name}")

status = backend.status()
print(f"Status: {status.status_msg}, pending jobs: {status.pending_jobs}")


# ──────────────────────────────────────────────────────────────────────────────
# 2. CAPTURE BACKEND METADATA AT RUNTIME
# ──────────────────────────────────────────────────────────────────────────────
props = backend.properties()
try:
    q_t1 = props.t1(PIN_QUBIT) * 1e6
    q_t2 = props.t2(PIN_QUBIT) * 1e6
    q_readout_err = props.readout_error(PIN_QUBIT)
except Exception:
    q_t1 = q_t2 = q_readout_err = None

metadata = {
    "timestamp_utc": datetime.utcnow().isoformat(),
    "backend": backend.name,
    "qubit": PIN_QUBIT,
    "shots": SHOTS,
    "backend_published_t1_us": q_t1,
    "backend_published_t2_us": q_t2,
    "backend_published_readout_err": q_readout_err,
}
print(f"\nBackend-published Q{PIN_QUBIT} calibration:")
print(f"  T1 = {q_t1} us")
print(f"  T2 = {q_t2} us")
print(f"  Readout error = {q_readout_err}")


# ──────────────────────────────────────────────────────────────────────────────
# 3. BUILD AND TRANSPILE CIRCUITS  (same definitions as the fake-backend runs)
# ──────────────────────────────────────────────────────────────────────────────
t1_circs = [t1_circuit(tau) for tau in T1_DELAYS_US]
t2_circs = [t2_ramsey_circuit(tau, detuning_mhz=T2_DETUNING_MHZ) for tau in T2_DELAYS_US]

print(f"\nTranspiling {len(t1_circs) + len(t2_circs)} T1/T2 circuits for "
      f"{backend.name}, pinned to physical qubit {PIN_QUBIT}...")
t1_compiled = transpile(t1_circs, backend, initial_layout=[PIN_QUBIT],
                        optimization_level=1)
t2_compiled = transpile(t2_circs, backend, initial_layout=[PIN_QUBIT],
                        optimization_level=1)


# ──────────────────────────────────────────────────────────────────────────────
# 4. RUN T1 + T2 IN ONE SAMPLER JOB
# ──────────────────────────────────────────────────────────────────────────────
sampler = Sampler(mode=backend)
total_circs = len(t1_compiled) + len(t2_compiled)
print(f"Submitting T1+T2 job: {total_circs} circuits, {SHOTS} shots each...")

job = sampler.run(t1_compiled + t2_compiled, shots=SHOTS)
print(f"Job ID: {job.job_id()}  — waiting for results...")
result = job.result()
metadata["t1_t2_job_id"] = job.job_id()


def p1_from_pub(pub_result):
    """Extract P(|1>) from a SamplerV2 PubResult, classical reg name 'c'."""
    bits = pub_result.data.c.get_bitstrings()
    return sum(1 for b in bits if b[-1] == "1") / len(bits)


t1_probs = [p1_from_pub(result[i]) for i in range(len(t1_compiled))]
t2_probs = [p1_from_pub(result[i + len(t1_compiled)]) for i in range(len(t2_compiled))]


# ──────────────────────────────────────────────────────────────────────────────
# 5. FIT T1
# ──────────────────────────────────────────────────────────────────────────────
T1_seed = q_t1 if q_t1 else 150.0
t1_popt, _ = curve_fit(
    exp_decay, T1_DELAYS_US, t1_probs,
    p0=[1.0, T1_seed, 0.0],
    bounds=([0, 1, 0], [1, 1000, 0.5]),
    maxfev=10000,
)
T1_fit = t1_popt[1]
print(f"\nFitted T1 = {T1_fit:.1f} us   (backend-published: {q_t1} us)")


# ──────────────────────────────────────────────────────────────────────────────
# 6. FIT T2 RAMSEY  (FFT-seeded)
# ──────────────────────────────────────────────────────────────────────────────
t2_probs_arr = np.array(t2_probs)
fft_vals = np.abs(np.fft.rfft(t2_probs_arr - np.mean(t2_probs_arr)))
fft_freqs = np.fft.rfftfreq(len(T2_DELAYS_US), d=(T2_DELAYS_US[1] - T2_DELAYS_US[0]))
dom_freq = fft_freqs[np.argmax(fft_vals[1:]) + 1] if len(fft_vals) > 1 else T2_DETUNING_MHZ

T2_seed = q_t2 if q_t2 else 60.0
t2_popt, _ = curve_fit(
    ramsey_decay, T2_DELAYS_US, t2_probs,
    p0=[0.4, T2_seed, dom_freq, 0.0, 0.5],
    bounds=([0, 1, max(0.001, dom_freq * 0.3), -np.pi, 0],
            [1, 500, dom_freq * 3, np.pi, 1]),
    maxfev=20000,
)
T2_fit = t2_popt[1]
print(f"Fitted T2 = {T2_fit:.1f} us   (backend-published: {q_t2} us)")
print(f"T2 < 2*T1?  {'YES' if T2_fit < 2 * T1_fit else 'CHECK FIT'}")


# ──────────────────────────────────────────────────────────────────────────────
# 7. RUN RB
# ──────────────────────────────────────────────────────────────────────────────
print(f"\nRunning RB on physical qubit {PIN_QUBIT}: "
      f"{len(RB_LENGTHS)} lengths x {RB_NUM_SAMPLES} samples = "
      f"{len(RB_LENGTHS) * RB_NUM_SAMPLES} circuits...")
rb_exp = StandardRB(physical_qubits=(PIN_QUBIT,), lengths=RB_LENGTHS,
                    num_samples=RB_NUM_SAMPLES, seed=42)
rb_exp.set_transpile_options(optimization_level=1)
rb_result = rb_exp.run(backend, shots=SHOTS).block_for_results()

epc_data = rb_result.analysis_results("EPC")
epc_val = epc_data.value.nominal_value
epc_err = epc_data.value.std_dev
fidelity = 1 - epc_val
print(f"EPC = {epc_val:.6f} +/- {epc_err:.6f}")
print(f"Single-qubit gate fidelity = {fidelity * 100:.4f}%")

try:
    metadata["rb_job_ids"] = [j.job_id() for j in rb_result.jobs()]
except Exception:
    metadata["rb_job_ids"] = []


# ──────────────────────────────────────────────────────────────────────────────
# 8. SAVE EVERYTHING
# ──────────────────────────────────────────────────────────────────────────────
tag = f"{backend.name}_q{PIN_QUBIT}"

pd.DataFrame({"delay_us": T1_DELAYS_US, "p1": t1_probs}).to_csv(
    OUTPUT_DIR / f"{tag}_t1.csv", index=False)
pd.DataFrame({"delay_us": T2_DELAYS_US, "p1": t2_probs}).to_csv(
    OUTPUT_DIR / f"{tag}_t2.csv", index=False)

# T1 plot
plt.figure(figsize=(8, 4))
plt.scatter(T1_DELAYS_US, t1_probs, color="steelblue", label="Real data", zorder=5)
ts = np.linspace(0, T1_DELAYS_US.max(), 300)
plt.plot(ts, exp_decay(ts, *t1_popt), color="crimson",
         label=f"Fit: T1 = {T1_fit:.1f} us")
plt.xlabel("Delay (us)"); plt.ylabel("P(|1>)")
plt.title(f"T1 — {backend.name}, qubit {PIN_QUBIT}")
plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
plt.savefig(OUTPUT_DIR / f"{tag}_t1_fit.png", dpi=150); plt.close()

# T2 plot
plt.figure(figsize=(8, 4))
plt.scatter(T2_DELAYS_US, t2_probs, color="steelblue", label="Real data", zorder=5)
ts = np.linspace(0, T2_DELAYS_US.max(), 500)
plt.plot(ts, ramsey_decay(ts, *t2_popt), color="crimson",
         label=f"Fit: T2 = {T2_fit:.1f} us, f = {t2_popt[2]:.3f} MHz")
plt.xlabel("Delay (us)"); plt.ylabel("P(|1>)")
plt.title(f"T2 Ramsey — {backend.name}, qubit {PIN_QUBIT}")
plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
plt.savefig(OUTPUT_DIR / f"{tag}_t2_fit.png", dpi=150); plt.close()

# RB plot
try:
    fig = rb_result.figure(0).figure
    fig.savefig(OUTPUT_DIR / f"{tag}_rb_fit.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
except Exception as e:
    print(f"RB figure save failed: {e}")

metadata.update({
    "T1_fit_us": float(T1_fit),
    "T2_fit_us": float(T2_fit),
    "T2_oscillation_freq_mhz": float(t2_popt[2]),
    "EPC": float(epc_val),
    "EPC_err": float(epc_err),
    "single_qubit_gate_fidelity": float(fidelity),
})
with open(OUTPUT_DIR / f"{tag}_metadata.json", "w") as f:
    json.dump(metadata, f, indent=2, default=str)

summary = f"""Real-Hardware Anchor — {backend.name}, qubit {PIN_QUBIT}
Timestamp (UTC): {metadata['timestamp_utc']}

T1 measured:        {T1_fit:.1f} us      (backend-published: {q_t1} us)
T2 measured:        {T2_fit:.1f} us      (backend-published: {q_t2} us)
T2 / 2*T1 ratio:    {T2_fit / (2 * T1_fit):.3f}   (must be <= 1)
EPC:                {epc_val:.6f} +/- {epc_err:.6f}
Gate fidelity:      {fidelity * 100:.4f}%

Files saved to: {OUTPUT_DIR}
"""
with open(OUTPUT_DIR / "summary.txt", "w") as f:
    f.write(summary)
print("\n" + summary)
print("Done.")
