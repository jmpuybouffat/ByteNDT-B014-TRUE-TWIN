# Byte NDT — B014 TRUE TWIN — Living Inspection Engineering

## Point 0 of the Twin method
DATA → BUILD → EVIDENCE → ENGINEERING

Fusion/CAD → 2D 8×8 PA → encoded positions → focal laws → acoustic paths/TOF →
encoded PAUT → global technician cartography → blind detection → FMC/TFM →
3D voxel → deterministic decision → online engineering report → hardware outputs.

## Locked inspection definition
- 2D matrix PA: 8×8, 64 elements
- nominal wedge: 55° shear wave
- sectorial family: 35° and 40°→70° by 2°
- skew: −10°→+10° by 5°
- 41 encoded positions
- 85 laws/position
- 3485 focal laws

## Technician sensitivity view
For continuity with the earlier B001 technician workflow:
**reference 3 mm EDM = 50% FSH**.

Blind detection remains independent. The %FSH normalization is applied afterwards
for cartography, indication reading and reporting.

## Living Engineering
The report is built from the same digital context as the scan.
Hardware-facing outputs include PA position/orientation, sound path/TOF,
sector/skew definition and 64-element focal-law delays.

## Machine learning
Current B014 decisions are deterministic and explainable.
ML is a future optional layer. The Twin preserves the contextual dataset needed
for later validated ML work.

## Streamlit Cloud
Before cloud deployment, add the frozen B009 geometry/trajectory/target files
and validated EDM truth data to the repository (recommended: `data/B009/`).
The cloud app must not rely on local Windows `D:\...` paths.
