"""
B014_C2_MASTER_VIDEO_GLOBAL_FINAL_BIS.py
TRUE TWIN B014 - VERSION BIS CORRIGEE
- ORIGINAL conserve : B014_C2_MASTER_VIDEO_GLOBAL_FINAL.py
- BIS : seule correction = overview 180 deg + TFM Voxel
ByteNDT - 07/10/2026
"""
import streamlit as st
from PIL import Image
import numpy as np
import os

st.set_page_config(page_title="B014 TRUE TWIN - BIS 180 deg", layout="wide")
st.title("B014 TRUE TWIN - VERSION BIS - Overview corrige 180 deg")
st.markdown("**Original conserve intact** | **BIS = Overview rotate 180 deg + TFM Voxel**")

st.header("1. Overview B014 - CORRIGE 180 deg")
overview_paths = ["B014_C2_DATA/overview.png","B014_C2_DATA/overview.jpg","B014_C2_DATA/B014_overview.png","overview.png"]
img_found=False
for p in overview_paths:
    if os.path.exists(p):
        try:
            img=Image.open(p)
            img_corrected=img.rotate(180, expand=True)
            st.image(img_corrected, caption=f"BIS - 180 deg corrige depuis {p}", use_column_width=True)
            st.success(f"Overview corrige 180 deg - ORIGINAL conserve ({p})")
            img_found=True
            break
        except Exception as e:
            st.warning(f"Erreur {p}: {e}")
if not img_found:
    st.info("Place ton overview dans B014_C2_DATA/overview.png - correction auto 180 deg en BIS")

st.header("2. TFM Voxel Analysis - Implementation")
st.code("""
# TFM VOXEL B014 - I(r) = | sum_tx sum_rx FMC(t=TOF_exact_tx_r + TOF_exact_r_rx) |
# Grille 3D depuis CAO turbine reelle
# for voxel: tof_tx = TOF_EXACT_CAD[tx, voxel]; tof_rx = TOF_EXACT_CAD[voxel, rx]
# I[voxel] += FMC[tx,rx, t=tof_tx+tof_rx]
""", language="python")
st.markdown("- [ ] Charger BYTE_NDT_V53_path_PA2_to_C2.csv\n- [ ] TOF_EXACT_B014.csv depuis CAO\n- [ ] Generer VOXEL_3D_B014.npy\n- [ ] Export STL defaut")

st.header("3. Passage Real-World - LSB Turbine 941")
st.markdown("1. CAO 941_CAO.stl\n2. Eau 1480 m/s + Acier 5900 m/s\n3. TOF Exact ray tracing immersion\n4. Green G=exp(ikR)/4piR + Born + Kirchhoff + GTD\n5. Twin Vivant")

st.sidebar.header("Traceabilite BIS")
st.sidebar.markdown("ORIGINAL: FINAL.py intact\nBIS: FINAL_BIS.py 180 deg + TFM Voxel\nRev: B014-C2-BIS-20261007")
st.sidebar.success("BIS pret")
