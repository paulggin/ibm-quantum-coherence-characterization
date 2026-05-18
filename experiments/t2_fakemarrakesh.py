import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

from qiskit import transpile
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh
from qiskit_aer import AerSimulator

from circuits import t2_ramsey_circuit, ramsey_decay

# ── 1. BACKEND ────────────────────────────────────────────────────────────────
fake_backend = FakeMarrakesh()
simulator = AerSimulator.from_backend(fake_backend)

# ── 2. PARAMETERS ─────────────────────────────────────────────────────────────
shots = 1024
delay_times_us = np.linspace(0, 80, 80)
detuning_mhz = 0.05                     # one full oscillation every ~20 µs

# ── 3. CIRCUITS ───────────────────────────────────────────────────────────────
counts_1 = []
for tau_us in delay_times_us:
    qc = t2_ramsey_circuit(tau_us, detuning_mhz=detuning_mhz)
    compiled = transpile(qc, simulator)
    result = simulator.run(compiled, shots=shots).result()
    counts = result.get_counts()
    p1 = counts.get('1', 0) / shots
    counts_1.append(p1)

counts_1 = np.array(counts_1)

# ── 4. ESTIMATE OSCILLATION FREQUENCY FROM DATA ───────────────────────────────
# FFT-seeded initial guess — much more reliable than blind guessing.
fft_vals = np.abs(np.fft.rfft(counts_1 - np.mean(counts_1)))
fft_freqs = np.fft.rfftfreq(len(delay_times_us),
                              d=(delay_times_us[1] - delay_times_us[0]))
dominant_freq = fft_freqs[np.argmax(fft_vals)]
print(f"FFT estimated frequency: {dominant_freq:.4f} MHz")

# ── 5. FIT ────────────────────────────────────────────────────────────────────
p0 = [0.4, 50.0, dominant_freq, 0.0, 0.5]

try:
    popt, pcov = curve_fit(
        ramsey_decay,
        delay_times_us,
        counts_1,
        p0=p0,
        bounds=(
            [0,    1,  max(0.001, dominant_freq*0.3), -np.pi, 0],
            [1,  400,  dominant_freq * 3,               np.pi, 1]
        ),
        maxfev=20000
    )
    A_fit, T2_fit, f_fit, phi_fit, C_fit = popt
    fit_success = True
    print(f"Fitted T2  = {T2_fit:.1f} microseconds")
    print(f"Fitted f   = {f_fit:.4f} MHz")

    T1 = 280.2
    print(f"\nT1         = {T1:.1f} µs")
    print(f"2×T1 limit = {2*T1:.1f} µs")
    print(f"T2 < 2×T1? {'YES ✓' if T2_fit < 2*T1 else 'CHECK FIT'}")

except RuntimeError as e:
    fit_success = False
    print(f"Fit failed: {e}")

# ── 6. PLOT ───────────────────────────────────────────────────────────────────
t_smooth = np.linspace(0, 80, 500)

plt.figure(figsize=(10, 5))
plt.scatter(delay_times_us, counts_1, color='steelblue',
            s=20, zorder=5, label='Simulated data')

if fit_success:
    plt.plot(t_smooth, ramsey_decay(t_smooth, *popt),
             color='crimson', linewidth=2,
             label=f'Fit: T2 = {T2_fit:.1f} µs, f = {f_fit:.4f} MHz')

    # Decay envelope
    env = popt[0] * np.exp(-t_smooth / T2_fit) + popt[4]
    env_low = -popt[0] * np.exp(-t_smooth / T2_fit) + popt[4]
    plt.plot(t_smooth, env, '--', color='gray', linewidth=1.2,
             label='Decay envelope')
    plt.plot(t_smooth, env_low, '--', color='gray', linewidth=1.2)

plt.xlabel('Delay time (µs)', fontsize=13)
plt.ylabel('P(|1⟩)', fontsize=13)
plt.title('T2 Ramsey Experiment — FakeMarrakesh Simulator', fontsize=14)
plt.legend(fontsize=11)
plt.grid(alpha=0.3)
plt.ylim(-0.1, 1.1)
plt.tight_layout()
plt.savefig('t2_ramsey_result.png', dpi=150)
plt.show()
print("Plot saved as t2_ramsey_result.png")
