# Repository Inventory

Snapshot of the IBM Quantum Coherence Characterization project

## Install

```bash
pip install -r requirements.txt
```

## Layout

```
.
├── README.md                              
├── INVENTORY.md                           
├── .gitignore
├── requirements.txt
│
├── experiments/                           ← circuit construction + execution
│   ├── circuits.py                        ← canonical t1_circuit, t2_ramsey_circuit, exp_decay, ramsey_decay
│   ├── t1_fakemarrakesh.py                ← single-qubit T1 on FakeMarrakesh simulator
│   ├── t2_fakemarrakesh.py                ← single-qubit T2 Ramsey on FakeMarrakesh
│   ├── rb_fakenairobi.py                  ← RB on FakeNairobi (Eagle r1, 7 qubits)
│   ├── rb_fakemarrakesh.py                ← RB on FakeMarrakesh (Heron r2, 156 qubits)
│   ├── multiqubit_characterization.py     ← all-156-qubit T1 + T2 sweep (1-2 hr runtime)
│   └── real_hardware_anchor.py            ← T1 + T2 + RB on real ibm_marrakesh, multi-qubit capable
│
├── analysis/                              ← post-processing
│   ├── mask_outliers.py                   ← physical-bounds mask for the 156-qubit CSV
│   └── plot_coherence_heatmap.py          ← regenerate masked heatmap from the CSV
│
├── data/                                  ← raw + processed datasets
│   ├── marrakesh_156qubit_coherence.csv   ← full 156-qubit dataset from FakeMarrakesh
│   └── real_hardware/
│       ├── ibm_marrakesh_q0_*.csv         ← per-qubit T1/T2 sweep data
│       ├── ibm_marrakesh_q0_metadata.json ← backend calibration + fit results + job IDs
│       ├── (same for q1, q2, q3)
│       ├── ibm_marrakesh_4qubit_summary.csv  ← aggregate of all 4 qubits
│       └── summary.txt                   
│
└── plots/                                 ← final figures
    ├── coherence_heatmap_156qubit_masked.png    ← masked heatmap
    ├── t1_fakemarrakesh_singlequbit.png         ← single-qubit T1 fit on simulator
    ├── t2_fakemarrakesh_singlequbit.png         ← single-qubit T2 Ramsey fit on simulator
    ├── rb_fakenairobi.png                       ← RB decay on Eagle r1 simulator
    ├── rb_fakemarrakesh.png                     ← RB decay on Heron r2 simulator
    ├── t1_ibm_marrakesh_q[0-3].png              ← real-hardware T1 fits (4 qubits)
    ├── t2_ibm_marrakesh_q[0-3].png              ← real-hardware T2 fits (4 qubits)
    └── rb_ibm_marrakesh_q[0-3].png              ← real-hardware RB fits (4 qubits)
```
