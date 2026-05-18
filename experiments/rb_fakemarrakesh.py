# rb_marrakesh.py
# Randomized Benchmarking using qiskit_experiments StandardRB
# FakeMarrakesh — comparison baseline: FakeNairobi EPC = 7.9e-4, Fidelity = 99.92%

import warnings
from pathlib import Path
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt

from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh
from qiskit_experiments.library import StandardRB

PLOTS_DIR = Path(__file__).resolve().parent.parent / "plots"
PLOTS_DIR.mkdir(exist_ok=True)

# ── 1. BACKEND ────────────────────────────────────────────────────────────────
backend = AerSimulator.from_backend(FakeMarrakesh())
print(f"Backend: FakeMarrakesh (AerSimulator)\n")

# ── 2. RB EXPERIMENT SETUP ────────────────────────────────────────────────────
QUBIT = 0
SEQUENCE_LENGTHS = [1, 2, 3, 5, 8, 12, 18, 25, 35, 50, 75, 100]
NUM_SAMPLES = 50
SHOTS = 2048

print("Setting up StandardRB experiment...")
rb_exp = StandardRB(
    physical_qubits=(QUBIT,),
    lengths=SEQUENCE_LENGTHS,
    num_samples=NUM_SAMPLES,
    seed=42
)

# ── 3. RUN ────────────────────────────────────────────────────────────────────
print(f"Running {NUM_SAMPLES} seeds x {len(SEQUENCE_LENGTHS)} lengths = "
      f"{NUM_SAMPLES * len(SEQUENCE_LENGTHS)} circuits...")
print(f"Shots per circuit: {SHOTS}\n")

rb_exp.set_transpile_options(optimization_level=0)

result = rb_exp.run(
    backend,
    shots=SHOTS
).block_for_results()

# ── 4. RESULTS ────────────────────────────────────────────────────────────────
print("── ANALYSIS RESULTS ─────────────────────────────")
for res in result.analysis_results():
    print(f"  {res.name}: {res.value}")

try:
    epc = result.analysis_results("EPC")
    epc_val = epc.value.nominal_value
    epc_err = epc.value.std_dev
    gate_fidelity = 1 - epc_val

    print(f"\n  Error Per Clifford (EPC) = {epc_val:.6f} ± {epc_err:.6f}")
    print(f"  Gate Fidelity            = {gate_fidelity:.6f} ({gate_fidelity*100:.4f}%)")

except Exception as e:
    print(f"  Could not extract EPC directly: {e}")

# ── 5. COMPARISON ─────────────────────────────────────────────────────────────
print("\n── BACKEND COMPARISON ───────────────────────────")
print(f"  FakeNairobi   — EPC: 7.900e-04  Fidelity: 99.9210%  (Eagle r1,  7 qubits)")
print(f"  FakeMarrakesh — EPC: {epc_val:.3e}  Fidelity: {gate_fidelity*100:.4f}%  (Heron r2, 156 qubits)")

# ── 6. PLOT ───────────────────────────────────────────────────────────────────
save_path = PLOTS_DIR / "rb_fakemarrakesh.png"

print("\nGenerating plot...")
fig_data = result.figure(0)
mpl_fig = fig_data.figure
mpl_fig.savefig(save_path, dpi=150, bbox_inches='tight')
print(f"Plot saved to: {save_path}")

plt.show()