"""
circuits.py
Root circuit-construction and fit-function definitions for T1 / T2
characterization.

Both the fake-backend validation scripts (t1_experiment.py, t2_ramsey.py) and the real-hardware anchor
(real_hardware_anchor.py) import from here.

Circuits are written as single-qubit logical circuits (QuantumCircuit(1, 1));
the physical-qubit mapping is handled by transpile() at the call site via
initial_layout=[physical_qubit].
"""

import numpy as np
from qiskit import QuantumCircuit


# ─── Circuits ────────────────────────────────────────────────────────────────

def t1_circuit(tau_us):
    """
    T1 energy-relaxation circuit:  X  →  delay(tau)  →  measure.

    The qubit is excited to |1>, then we wait tau microseconds and measure.
    P(|1>) decays as A * exp(-tau / T1) + C.
    """
    qc = QuantumCircuit(1, 1)
    qc.x(0)
    if tau_us > 0:
        qc.delay(int(tau_us * 1000), 0, "ns")
    qc.measure(0, 0)
    return qc


def t2_ramsey_circuit(tau_us, detuning_mhz=0.05):
    """
    T2 Ramsey circuit:  H  →  delay(tau)  →  Rz(2*pi*f*tau)  →  H  →  measure.

    The deliberate Rz detuning produces visible oscillations in the
    P(|1>) vs tau curve, which makes the T2 fit robust. Without the
    detuning, T2 dephasing is monotonic and harder to fit cleanly.
    """
    qc = QuantumCircuit(1, 1)
    qc.h(0)
    if tau_us > 0:
        qc.delay(int(tau_us * 1000), 0, "ns")
    qc.rz(2 * np.pi * detuning_mhz * tau_us, 0)
    qc.h(0)
    qc.measure(0, 0)
    return qc


# ─── Fit functions ───────────────────────────────────────────────────────────

def exp_decay(t, A, T1, C):
    """Exponential-decay model for T1.  P(|1>) = A * exp(-t / T1) + C."""
    return A * np.exp(-t / T1) + C


def ramsey_decay(t, A, T2, f, phi, C):
    """
    Oscillating decay model for T2 Ramsey.
    P(|1>) = A * exp(-t / T2) * cos(2*pi*f*t + phi) + C
    """
    return A * np.exp(-t / T2) * np.cos(2 * np.pi * f * t + phi) + C
