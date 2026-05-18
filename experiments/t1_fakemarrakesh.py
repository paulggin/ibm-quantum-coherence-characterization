import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

from qiskit import transpile
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh
from qiskit_aer import AerSimulator

from circuits import t1_circuit, exp_decay

# ── 1. BACKEND SETUP ──────────────────────────────────────────────────────────
# FakeMarrakesh mimics the real ibm_marrakesh device. It uses IBM-published
# calibration data (T1, T2, gate errors) so simulation is realistic.
fake_backend = FakeMarrakesh()
simulator = AerSimulator.from_backend(fake_backend)

# ── 2. EXPERIMENT PARAMETERS ─────────────────────────────────────────────────
qubit = 0
shots = 1024
delay_times_us = np.linspace(0, 300, 30)

# ── 3. BUILD AND RUN CIRCUITS ─────────────────────────────────────────────────
counts_1 = []

for tau_us in delay_times_us:
    qc = t1_circuit(tau_us)             # canonical circuit from circuits.py
    compiled = transpile(qc, simulator)
    result = simulator.run(compiled, shots=shots).result()
    counts = result.get_counts()
    p1 = counts.get('1', 0) / shots
    counts_1.append(p1)

# ── 4. FIT EXPONENTIAL DECAY ──────────────────────────────────────────────────
p0 = [1.0, 100.0, 0.0]                  # initial guess: A=1, T1=100us, C=0
popt, _ = curve_fit(
    exp_decay,
    delay_times_us,
    counts_1,
    p0=p0,
    bounds=([0, 1, 0], [1, 500, 0.5])
)
A_fit, T1_fit, C_fit = popt
print(f"\nFitted T1 = {T1_fit:.1f} microseconds")

# ── 5. PLOT ───────────────────────────────────────────────────────────────────
t_smooth = np.linspace(0, 300, 300)
plt.figure(figsize=(9, 5))
plt.scatter(delay_times_us, counts_1, color='steelblue', zorder=5, label='Simulated data')
plt.plot(t_smooth, exp_decay(t_smooth, *popt), color='crimson',
         linewidth=2, label=f'Fit: T1 = {T1_fit:.1f} µs')
plt.xlabel('Delay time (µs)', fontsize=13)
plt.ylabel('P(|1⟩)', fontsize=13)
plt.title('T1 Energy Relaxation — FakeMarrakesh Simulator', fontsize=14)
plt.legend(fontsize=12)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('t1_result.png', dpi=150)
plt.show()
print("Plot saved as t1_result.png")
