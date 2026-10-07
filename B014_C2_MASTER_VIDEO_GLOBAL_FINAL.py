from __future__ import annotations

import math
import os
import struct
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

APP_TITLE = "Byte NDT — B014 TRUE TWIN — C2 — INTRADOS → EXTRADOS — 199 POSITIONS — 6 EDM"

REPO = Path(__file__).resolve().parent
DOWNLOADS = Path.home() / "Downloads"
DATA_DIR = REPO / "B014_C2_DATA"

# -----------------------------------------------------------------------------
# FROZEN FUSION INPUTS — no legacy B001 image is used to build the scan.
# -----------------------------------------------------------------------------
FUSION_REFERENCE_STL = "ByteNDT_B009_FUSION_REFERENCE_BLADE_WOODENBLOCK.stl"
FUSION_BLADE_STL = "B014_C2_BLADE.stl"
PA_PATH_CSV = "BYTE_NDT_V53_path_PA2_to_C2.csv"
TARGET_CSV = "C2_INDICATION_VALIDATED.csv"
FACE2_DETECTIONS = "BYTE_NDT_LSB941_DETECTIONS_PA2_C2.csv"
FACE2_METROLOGY = "BYTE_NDT_LSB941_EDM_METROLOGY_PA2_C2.csv"
FACE2_COVERAGE = "BYTE_NDT_LSB941_FULL_GROOVE_COVERAGE_PA2_C2.csv"
FACE2_FOCAL = "focal_laws_B_PA2_to_C2_2D8x8.csv"
FACE2_BEAM = "beam_field_B_PA2_to_C2_2D8x8.csv"
FACE2_SCAN3D = "scan3D_groove_B_PA2_to_C2_2D8x8.csv"

# Only the mechanical truth coordinates/lengths are reused as specimen inputs.
# They are NEVER sent to the blind detector.
EDM_MASTER_NAME = "EDM_TUMELO_MASTER_VALIDATED.csv"
EDM_CARTO_FALLBACK = "ByteNDT_C2_CARTOGRAPHY_VALIDATION_B001.csv"
B001_FOCAL_NAME = "ByteNDT_C2_FOCAL_LAWS_8x8_B001.csv"
B001_C2_REFERENCE_NAME = "C2_INDICATION_Fusion_SAFE.csv"

# Locked Twin -> CAO transform from the validated B001 reference.
R_TWIN_TO_CAO = np.array([
    [0.338962571711, 0.940625695776, 0.018101807228],
    [0.938655748872, -0.336829183447, -0.073969495656],
    [-0.063480391370, 0.042064255895, -0.997096203126],
], dtype=float)
T_TWIN_TO_CAO = np.array([-26.823870012336, 150.164186762802, -94.009525515099], dtype=float)

STL_SCALE = 1.0
# LOCKED Face-2 display registration validated on Wooden Block + blade.
FUSION_ASSEMBLY_SCALE = 0.0908023186789272
FUSION_ASSEMBLY_R = np.array([
    [ 0.29512841,  0.95444327, -0.04401452],
    [ 0.95528462, -0.29388517,  0.03260077],
    [ 0.01818037, -0.05166780, -0.99849883],
], dtype=float)
FUSION_ASSEMBLY_T = np.array([-145.27965177, 152.26765862, -49.43855245], dtype=float)
STEEL_SHEAR_MM_US = 3.23
FREQUENCY_MHZ = 5.0
ARRAY_NX = 8
ARRAY_NY = 8
ARRAY_PITCH_MM = 0.6

SECTORS_DEG = np.unique(np.concatenate([np.array([35.0]), np.arange(40.0, 70.1, 2.0)]))
SKEWS_DEG = np.arange(-10.0, 10.1, 5.0)

RANGE_MIN_MM = 0.0
RANGE_MAX_MM = 130.0
RANGE_SAMPLES = 520
PULSE_SIGMA_MM = 0.75
EDM_BEAM_SIGMA_DEG = 4.0
GEOMETRY_BEAM_SIGMA_DEG = 4.5
EDM_FIXED_SCALE = 4.8
GEOMETRY_FIXED_SCALE = 0.45
NOISE_RMS_RAW = 0.0015

SHOW_DB_FLOOR = -50.0
SCAN3D_POINT_CLOUD_DB = -30.0
BLIND_THRESHOLD_DB = -18.0
MAX_BLIND_PEAKS_PER_SHOT = 6
GEOMETRY_RANGE_TOL_MM = 2.2
CLUSTER_RADIUS_MM = 5.0
VALIDATION_TOL_MM = 6.0
SENSITIVITY_REFERENCE_EDM_ID = "EDM_10"
SENSITIVITY_REFERENCE_LENGTH_MM = 3.0
SENSITIVITY_REFERENCE_FSH_PERCENT = 50.0
A_NA_THRESHOLD_FSH = 50.0

TFM_HALF_U_MM = 6.0
TFM_HALF_V_MM = 6.0
TFM_STEP_MM = 0.30
TFM_PULSE_SIGMA_US = 0.18
TFM_FLOOR_DB = -40.0

VOXEL_HALF_MM = 2.5
VOXEL_STEP_MM = 0.50
VOXEL_PULSE_SIGMA_US = 0.18
VOXEL_FLOOR_DB = -40.0


def unit(v):
    a = np.asarray(v, dtype=float)
    n = float(np.linalg.norm(a))
    return a / n if n > 1e-12 else np.zeros_like(a)


def rodrigues(v, axis, angle_deg):
    v = np.asarray(v, dtype=float)
    a = unit(axis)
    if np.linalg.norm(a) < 1e-12:
        return v.copy()
    th = math.radians(float(angle_deg))
    return (
        v * math.cos(th)
        + np.cross(a, v) * math.sin(th)
        + a * float(np.dot(a, v)) * (1.0 - math.cos(th))
    )


def find_asset(filename: str) -> Path | None:
    candidates = [
        REPO / filename,
        REPO / "data" / "B009" / filename,
        DOWNLOADS / filename,
    ]
    for p in candidates:
        if p.exists():
            return p
    for root in (REPO, DOWNLOADS):
        try:
            p = next(root.rglob(filename), None)
        except Exception:
            p = None
        if p is not None and p.is_file():
            return p
    return None


def to_cao(points):
    pts = np.asarray(points, dtype=float)
    return (R_TWIN_TO_CAO @ pts.T).T + T_TWIN_TO_CAO


def find_truth_asset() -> Path | None:
    # 1) Prefer the validated mechanical master used by the B001 reference.
    explicit = [
        REPO / EDM_MASTER_NAME,
        DOWNLOADS / EDM_MASTER_NAME,
        Path(r"D:\ARCHIVES_PROJETS\PROJET_BYTENDT_AI\01_SCRIPTS\09_RESULTS_REPORTS\LSB941_TWIN_V1\01_INPUTS_VALIDATED_GEOMETRY\EDM_TUMELO_MASTER_VALIDATED.csv"),
        Path(r"D:\PROJET_BYTENDT_AI\01_SCRIPTS\09_RESULTS_REPORTS\LSB941_TWIN_V1\01_INPUTS_VALIDATED_GEOMETRY\EDM_TUMELO_MASTER_VALIDATED.csv"),
    ]
    for p in explicit:
        if p.exists():
            return p

    # 2) Search Downloads recursively for the validated master.
    try:
        p = next(DOWNLOADS.rglob(EDM_MASTER_NAME), None)
    except Exception:
        p = None
    if p is not None and p.is_file():
        return p

    # 3) Fallback ONLY to a cartography CSV that really contains mechanical truth columns.
    fallback = find_asset(EDM_CARTO_FALLBACK)
    if fallback is not None:
        try:
            df = read_csv_auto(str(fallback))
            req = {"truth_X_mm", "truth_Y_mm", "truth_Z_mm"}
            if req.issubset(df.columns):
                return fallback
        except Exception:
            pass

    return None



def find_b001_reference_asset() -> Path | None:
    explicit = [
        Path(r"D:\ARCHIVES_PROJETS\PROJET_BYTENDT_AI\01_SCRIPTS\03_SCAN_PATHS\output\C2_UT_B001\ByteNDT_C2_FOCAL_LAWS_8x8_B001.csv"),
        Path(r"D:\PROJET_BYTENDT_AI\01_SCRIPTS\03_SCAN_PATHS\output\C2_UT_B001\ByteNDT_C2_FOCAL_LAWS_8x8_B001.csv"),
        REPO / B001_FOCAL_NAME,
        DOWNLOADS / B001_FOCAL_NAME,
    ]
    for p in explicit:
        if p.exists():
            return p
    try:
        p = next(DOWNLOADS.rglob(B001_FOCAL_NAME), None)
    except Exception:
        p = None
    return p if p is not None and p.is_file() else None


def find_b001_c1_reference_asset() -> Path | None:
    explicit = [
        Path(r"D:\ARCHIVES_PROJETS\PROJET_BYTENDT_AI\01_SCRIPTS\03_SCAN_PATHS\output\00_VALID_REFERENCE\C2_INDICATION_Fusion_SAFE.csv"),
        Path(r"D:\PROJET_BYTENDT_AI\01_SCRIPTS\03_SCAN_PATHS\output\00_VALID_REFERENCE\C2_INDICATION_Fusion_SAFE.csv"),
        REPO / B001_C2_REFERENCE_NAME,
        DOWNLOADS / B001_C2_REFERENCE_NAME,
    ]
    for p in explicit:
        if p.exists():
            return p
    try:
        p = next(DOWNLOADS.rglob(B001_C2_REFERENCE_NAME), None)
    except Exception:
        p = None
    return p if p is not None and p.is_file() else None


def polyline_arclength(curve):
    c = np.asarray(curve, dtype=float)
    if len(c) < 2:
        return np.array([0.0])
    seg = np.linalg.norm(np.diff(c, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])


def interp_polyline(curve, u):
    c = np.asarray(curve, dtype=float)
    s = polyline_arclength(c)
    total = float(s[-1]) if len(s) else 0.0
    if total <= 1e-12:
        return np.repeat(c[:1], np.size(np.atleast_1d(u)), axis=0)
    uu = np.clip(np.atleast_1d(u).astype(float), 0.0, 1.0)
    ss = uu * total
    out = np.column_stack([np.interp(ss, s, c[:,j]) for j in range(3)])
    return out


def nearest_polyline_u(point, curve):
    q = np.asarray(point, dtype=float)
    c = np.asarray(curve, dtype=float)
    s = polyline_arclength(c)
    total = max(float(s[-1]), 1e-12)
    best_d = float("inf")
    best_s = 0.0
    for i in range(len(c)-1):
        a, b = c[i], c[i+1]
        ab = b-a
        den = float(np.dot(ab,ab))
        t = 0.0 if den <= 1e-12 else float(np.clip(np.dot(q-a,ab)/den,0.0,1.0))
        p = a + t*ab
        d = float(np.linalg.norm(q-p))
        if d < best_d:
            best_d = d
            best_s = float(s[i] + t*np.linalg.norm(ab))
    return best_s/total, best_d


def kabsch_rigid(a, b):
    A = np.asarray(a, dtype=float)
    B = np.asarray(b, dtype=float)
    ca = A.mean(axis=0)
    cb = B.mean(axis=0)
    H = (A-ca).T @ (B-cb)
    U, _, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1,:] *= -1
        R = Vt.T @ U.T
    t = cb - R @ ca
    fit = (R @ A.T).T + t
    rms = float(np.sqrt(np.mean(np.sum((fit-B)**2, axis=1))))
    return R, t, rms


def fit_old_curve_to_b009(old_curve, new_curve):
    old = np.asarray(old_curve, dtype=float)
    new = np.asarray(new_curve, dtype=float)
    u = np.linspace(0.0, 1.0, 61)
    B = interp_polyline(new, u)
    best = None
    # Search a possible B009 sub-course inside the older 233-position scan.
    starts = np.linspace(0.0, 0.30, 13)
    ends = np.linspace(0.70, 1.0, 13)
    for a in starts:
        for b in ends:
            if b-a < 0.55:
                continue
            for reverse in (False, True):
                ou = a + (b-a)*u if not reverse else b - (b-a)*u
                A = interp_polyline(old, ou)
                R, t, rms = kabsch_rigid(A, B)
                rec = dict(R=R,t=t,rms=rms,a=float(a),b=float(b),reverse=reverse)
                if best is None or rms < best["rms"]:
                    best = rec
    return best


def read_xyz_any(path: Path):
    attempts = [
        dict(sep=";", engine="python", header=None),
        dict(sep=",", engine="python", header=None),
        dict(sep=r"\s+", engine="python", header=None),
    ]
    for kwargs in attempts:
        try:
            df = pd.read_csv(path, **kwargs)
            num = df.apply(pd.to_numeric, errors="coerce").dropna(how="all")
            cols = [c for c in num.columns if num[c].notna().sum() >= 3]
            if len(cols) >= 3:
                arr = num[cols[:3]].dropna().to_numpy(dtype=float)
                if len(arr) >= 3:
                    return arr
        except Exception:
            pass
    raise ValueError(f"Unable to read XYZ / Lecture XYZ impossible: {path}")


def load_old_reference_curve():
    focal = find_b001_reference_asset()
    if focal is not None:
        try:
            df = pd.read_csv(focal, sep=";")
            req = {"step_id","C2_target_X_mm","C2_target_Y_mm","C2_target_Z_mm"}
            if req.issubset(df.columns):
                old = (df.sort_values(["step_id"])
                         .drop_duplicates("step_id")
                         [["C2_target_X_mm","C2_target_Y_mm","C2_target_Z_mm"]]
                         .apply(pd.to_numeric, errors="coerce")
                         .dropna().to_numpy(dtype=float))
                if len(old) >= 10:
                    return old, focal, "B001 focal-law target curve"
        except Exception:
            pass

    cref = find_b001_c1_reference_asset()
    if cref is not None:
        raw = read_xyz_any(cref)
        return raw, cref, "B001 C2 reference curve"
    return None, None, ""


def transfer_truth_to_b009(truth_df, new_target):
    """
    Re-register the validated mechanical EDM truth to the B009 Fusion frame
    using the OLD C2 target/reference curve versus the NEW B009 target curve.
    EDM coordinates are not fitted to detections and are never sent to detector.
    """
    old_curve, ref_path, ref_kind = load_old_reference_curve()
    if old_curve is None:
        raise FileNotFoundError(
            "B001 reference target curve not found. Expected ByteNDT_C2_FOCAL_LAWS_8x8_B001.csv "
            "or C2_INDICATION_Fusion_SAFE.csv."
        )

    # If fallback reference is raw Twin coordinates, test raw and locked TWIN->CAO.
    candidates = [("RAW", old_curve)]
    if ref_kind == "B001 C2 reference curve":
        candidates.append(("TWIN->CAO", to_cao(old_curve)))

    best = None
    for frame_name, curve in candidates:
        try:
            fit = fit_old_curve_to_b009(curve, new_target)
            if fit is not None and (best is None or fit["rms"] < best["fit"]["rms"]):
                best = dict(frame=frame_name, curve=np.asarray(curve,float), fit=fit)
        except Exception:
            pass
    if best is None:
        raise ValueError("Unable to register B001 C2 reference curve to B009 Fusion target curve.")

    old = best["curve"]
    fit = best["fit"]
    R = fit["R"]

    out = truth_df.copy()
    new_xyz = []
    old_xyz = out[["truth_X_mm","truth_Y_mm","truth_Z_mm"]].to_numpy(dtype=float)

    for q in old_xyz:
        u_old, _ = nearest_polyline_u(q, old)
        # Convert old global path coordinate into the registered B009 course.
        if not fit["reverse"]:
            u_new = (u_old-fit["a"]) / max(fit["b"]-fit["a"],1e-9)
        else:
            u_new = (fit["b"]-u_old) / max(fit["b"]-fit["a"],1e-9)
        u_new = float(np.clip(u_new, 0.0, 1.0))
        old_base = interp_polyline(old, [u_old])[0]
        new_base = interp_polyline(new_target, [u_new])[0]
        # Preserve the mechanical offset from the old target curve, rotated
        # by the rigid old-C2 -> B009 curve registration.
        offset = q-old_base
        new_xyz.append(new_base + R @ offset)

    new_xyz = np.asarray(new_xyz,float)
    out["old_truth_X_mm"] = out["truth_X_mm"]
    out["old_truth_Y_mm"] = out["truth_Y_mm"]
    out["old_truth_Z_mm"] = out["truth_Z_mm"]
    out["truth_X_mm"] = new_xyz[:,0]
    out["truth_Y_mm"] = new_xyz[:,1]
    out["truth_Z_mm"] = new_xyz[:,2]

    dists = [nearest_polyline_u(q,new_target)[1] for q in new_xyz]
    diag = {
        "reference_path": str(ref_path),
        "reference_kind": ref_kind,
        "reference_frame": best["frame"],
        "curve_registration_rms_mm": float(fit["rms"]),
        "edm_to_b009_target_median_mm": float(np.median(dists)),
        "edm_to_b009_target_max_mm": float(np.max(dists)),
        "old_course_start": float(fit["a"]),
        "old_course_end": float(fit["b"]),
        "reversed": bool(fit["reverse"]),
    }
    return out, diag


def sample_surface(points, max_points):
    p = np.asarray(points, dtype=float)
    if len(p) <= max_points:
        return p
    idx = np.linspace(0, len(p)-1, max_points).astype(int)
    return p[idx]


@st.cache_data(show_spinner=False)
def read_csv_auto(path_str: str) -> pd.DataFrame:
    p = Path(path_str)
    for sep in (None, ";", ",", "\t"):
        try:
            if sep is None:
                df = pd.read_csv(p, sep=None, engine="python")
            else:
                df = pd.read_csv(p, sep=sep)
            if len(df.columns) >= 2:
                return df
        except Exception:
            pass
    return pd.read_csv(p)


@st.cache_data(show_spinner=False)
def read_stl_mesh(path_str: str, scale: float = STL_SCALE):
    p = Path(path_str)
    size = p.stat().st_size
    vertices = []
    faces = []
    with p.open("rb") as f:
        header = f.read(80)
        count_raw = f.read(4)
        n_tri = struct.unpack("<I", count_raw)[0] if len(count_raw) == 4 else 0
        binary = len(header) == 80 and len(count_raw) == 4 and (84 + 50 * n_tri == size)
        if binary:
            for _ in range(n_tri):
                rec = f.read(50)
                if len(rec) != 50:
                    break
                vals = struct.unpack("<12fH", rec)
                base = len(vertices)
                vertices.extend([
                    (vals[3]*scale, vals[4]*scale, vals[5]*scale),
                    (vals[6]*scale, vals[7]*scale, vals[8]*scale),
                    (vals[9]*scale, vals[10]*scale, vals[11]*scale),
                ])
                faces.append((base, base+1, base+2))
        else:
            f.seek(0)
            tri = []
            for raw in f:
                line = raw.decode("utf-8", errors="ignore").strip()
                if line.startswith("vertex "):
                    parts = line.split()
                    if len(parts) >= 4:
                        tri.append(tuple(float(parts[i])*scale for i in (1,2,3)))
                        if len(tri) == 3:
                            base = len(vertices)
                            vertices.extend(tri)
                            faces.append((base, base+1, base+2))
                            tri = []
    if not vertices or not faces:
        raise ValueError(f"No triangles in STL / Aucun triangle STL: {p.name}")
    v = np.asarray(vertices, dtype=float)
    f = np.asarray(faces, dtype=int)
    return v, f


def xyz_df(path: Path) -> pd.DataFrame:
    """Read App1 x_mm/y_mm/z_mm files OR Face2 PA2/C2 CSVs without changing scale."""
    df = read_csv_auto(str(path)).copy()

    # Native App1 schema.
    if {"x_mm","y_mm","z_mm"}.issubset(df.columns):
        pass
    else:
        # Face2 files have historically used several headers. Map coordinates only;
        # never rescale/recenter them.
        norm = {str(c).strip().lower(): c for c in df.columns}
        aliases = [
            ("x","y","z"),
            ("x_pa_mm","y_pa_mm","z_pa_mm"),
            ("pa_x_mm","pa_y_mm","pa_z_mm"),
            ("x_center_mm","y_center_mm","z_center_mm"),
            ("probe_x","probe_y","probe_z"),
            ("focus_x","focus_y","focus_z"),
        ]
        mapped = None
        for ax,ay,az in aliases:
            if ax in norm and ay in norm and az in norm:
                mapped = (norm[ax],norm[ay],norm[az]); break
        if mapped is not None:
            df = df.rename(columns={mapped[0]:"x_mm",mapped[1]:"y_mm",mapped[2]:"z_mm"})
        else:
            # C2_INDICATION_VALIDATED is headerless in the validated C2 app.
            raw = pd.read_csv(path, header=None)
            if raw.shape[1] >= 3:
                q = raw.iloc[:, :3].apply(pd.to_numeric, errors="coerce")
                q.columns=["x_mm","y_mm","z_mm"]
                q=q.dropna()
                if len(q):
                    df=q
                else:
                    raise ValueError(f"{path.name}: no usable XYZ coordinate columns; columns={list(df.columns)}")
            else:
                raise ValueError(f"{path.name}: no usable XYZ coordinate columns; columns={list(df.columns)}")

    for c in ("x_mm","y_mm","z_mm"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["x_mm","y_mm","z_mm"]).copy()
    if "point_id" in df.columns:
        df = df.sort_values("point_id")
    return df.reset_index(drop=True)


def _face2_truth_from_csv(path: Path):
    df = read_csv_auto(str(path)).copy()
    if "edm_id" not in df.columns:
        return None
    norm={str(c).strip().lower():c for c in df.columns}
    xyz_candidates=[
        ("edm_x_mm","edm_y_mm","edm_z_mm"),
        ("truth_x_mm","truth_y_mm","truth_z_mm"),
        ("truth_x","truth_y","truth_z"),
        ("nominal_x_mm","nominal_y_mm","nominal_z_mm"),
        ("x_mm","y_mm","z_mm"),
    ]
    xyz=None
    for a,b,c in xyz_candidates:
        if a in norm and b in norm and c in norm:
            xyz=(norm[a],norm[b],norm[c]); break
    if xyz is None:
        return None
    out=pd.DataFrame()
    out["edm_id"]=df["edm_id"].astype(str)
    out["truth_X_mm"]=pd.to_numeric(df[xyz[0]],errors="coerce")
    out["truth_Y_mm"]=pd.to_numeric(df[xyz[1]],errors="coerce")
    out["truth_Z_mm"]=pd.to_numeric(df[xyz[2]],errors="coerce")
    length_col=next((norm[k] for k in ("nominal_length_mm","edm_length_mm","length_mm") if k in norm),None)
    out["edm_length_mm"]=pd.to_numeric(df[length_col],errors="coerce") if length_col else 3.0
    out=out[out["edm_id"].isin([f"EDM_{i:02d}" for i in range(6,12)])]
    out=out.dropna(subset=["truth_X_mm","truth_Y_mm","truth_Z_mm"]).reset_index(drop=True)
    return out if len(out)==6 else None


def load_truth(path: Path) -> pd.DataFrame:
    # FACE 2 first: use the six EDM_06...EDM_11 records already present in C2 metrology.
    face2=_face2_truth_from_csv(path)
    if face2 is not None:
        return face2
    # Preferred source: validated mechanical EDM master, identical parsing logic
    # to the B001 reference. No old detection/cartography result is reused.
    if path.name.lower() == EDM_MASTER_NAME.lower():
        rows = []
        for raw in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
            parts = [p.strip() for p in raw.strip().split(";")]
            if len(parts) < 8 or not parts[0].upper().startswith("EDM"):
                continue

            def val(s):
                return float(s.replace(",", "."))

            try:
                x_center = 0.5 * (val(parts[1]) + val(parts[2]))
                z_center = val(parts[3])
                y_center = 0.5 * (val(parts[4]) + val(parts[5]))
                length_mm = val(parts[6])
                side = parts[7].upper()
            except Exception:
                continue

            twin = np.array([x_center, y_center, z_center], dtype=float)
            cao = to_cao(twin.reshape(1, 3))[0]
            rows.append({
                "edm_id": f"EDM_{len(rows)+1:02d}",
                "edm_name": parts[0],
                "side": side,
                "edm_length_mm": float(length_mm),
                "truth_X_mm": float(cao[0]),
                "truth_Y_mm": float(cao[1]),
                "truth_Z_mm": float(cao[2]),
            })

        df = pd.DataFrame(rows)
        if df.empty:
            raise ValueError(
                f"No numeric EDM rows found in validated mechanical master / "
                f"Aucune ligne EDM numérique trouvée: {path}"
            )

        c1 = df[df["side"] == "C2"].copy()
        if c1.empty:
            c1 = df[df["edm_id"].isin({"EDM_06","EDM_07","EDM_08","EDM_09","EDM_10","EDM_11"})].copy()

        if c1.empty:
            raise ValueError("No C2 EDM found in validated mechanical master / Aucun EDM C2 trouvé.")
        return c1.reset_index(drop=True)

    # Safe fallback: a generated validation CSV is accepted only when it
    # explicitly contains the mechanical truth coordinates.
    df = read_csv_auto(str(path)).copy()
    required = {"edm_id","truth_X_mm","truth_Y_mm","truth_Z_mm"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"{path.name}: this file is an old/stale cartography output and does not contain "
            "mechanical truth coordinates. The TRUE TWIN will not use it."
        )
    for c in ("truth_X_mm","truth_Y_mm","truth_Z_mm","edm_length_mm"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "edm_length_mm" not in df.columns:
        df["edm_length_mm"] = 3.0
    df = df.dropna(subset=["truth_X_mm","truth_Y_mm","truth_Z_mm"]).copy()
    if "side" in df.columns:
        c1 = df[df["side"].astype(str).str.upper() == "C2"].copy()
        if not c1.empty:
            df = c1
    if len(df) > 5 and "edm_id" in df.columns:
        df = df[df["edm_id"].astype(str).isin(["EDM_06","EDM_07","EDM_08","EDM_09","EDM_10","EDM_11"])].copy()
    return df.reset_index(drop=True)


def local_tangent(points, i):
    n = len(points)
    if n < 2:
        return np.array([1.0,0.0,0.0])
    if i == 0:
        return unit(points[1] - points[0])
    if i == n-1:
        return unit(points[-1] - points[-2])
    return unit(points[i+1] - points[i-1])


def array_elements(pa, beam, tangent):
    # Build an 8x8 local aperture centered at the Fusion PA position.
    b = unit(beam)
    t = tangent - np.dot(tangent, b) * b
    if np.linalg.norm(t) < 1e-8:
        t = np.cross([0,0,1], b)
    t = unit(t)
    s = unit(np.cross(b, t))
    offsets_x = (np.arange(ARRAY_NX) - (ARRAY_NX-1)/2.0) * ARRAY_PITCH_MM
    offsets_y = (np.arange(ARRAY_NY) - (ARRAY_NY-1)/2.0) * ARRAY_PITCH_MM
    elems = []
    for ox in offsets_x:
        for oy in offsets_y:
            elems.append(pa + ox*t + oy*s)
    return np.asarray(elems, dtype=float)


def build_steps(pa_xyz, target_xyz):
    steps = []
    for i, (pa, tgt) in enumerate(zip(pa_xyz, target_xyz)):
        beam = unit(tgt-pa)
        tan = local_tangent(pa_xyz, i)
        elems = array_elements(pa, beam, tan)
        steps.append({
            "step_id": i,
            "s_mm": float(i),
            "pa": pa,
            "target_nominal": tgt,
            "tangent": tan,
            "beam_nominal": beam,
            "focus_distance_mm": float(np.linalg.norm(tgt-pa)),
            "elements": elems,
        })
    return steps


def vectorized_coherent_gain(elements_xyz, delays_us, scatter_xyz):
    q = np.asarray(scatter_xyz, dtype=float)
    if q.ndim == 1:
        q = q[None,:]
    d = np.linalg.norm(q[:,None,:] - elements_xyz[None,:,:], axis=2)
    t = delays_us[None,:] + d / STEEL_SHEAR_MM_US
    phase = 2*np.pi*FREQUENCY_MHZ*t
    g = np.abs(np.sum(np.exp(-1j*phase), axis=1)) / elements_xyz.shape[0]
    return g*g


def build_laws(step):
    b0 = unit(step["beam_nominal"])
    tangent = unit(step["tangent"])
    laws = []
    # 55° is the local nominal engineering direction already represented by Fusion p->target.
    for sector in SECTORS_DEG:
        b_sector = unit(rodrigues(b0, tangent, sector-55.0))
        skew_axis = unit(np.cross(tangent, b_sector))
        if np.linalg.norm(skew_axis) < 1e-8:
            skew_axis = unit(np.cross(b_sector, [0,0,1]))
        for skew in SKEWS_DEG:
            beam = unit(rodrigues(b_sector, skew_axis, skew))
            target = step["pa"] + step["focus_distance_mm"] * beam
            travel = np.linalg.norm(target[None,:] - step["elements"], axis=1) / STEEL_SHEAR_MM_US
            delays = np.max(travel) - travel
            laws.append((float(sector), float(skew), beam, delays))
    return laws


def add_gaussian(trace, range_axis, center_mm, amplitude, sigma_mm):
    lo = max(0, int(np.searchsorted(range_axis, center_mm-4*sigma_mm)))
    hi = min(len(range_axis), int(np.searchsorted(range_axis, center_mm+4*sigma_mm, side="right")))
    if hi <= lo:
        return
    x = range_axis[lo:hi]
    trace[lo:hi] += amplitude*np.exp(-0.5*((x-center_mm)/sigma_mm)**2)


@st.cache_data(show_spinner=False)
def run_true_twin_scan(pa_values, target_values, truth_values, geometry_values):
    pa_xyz = np.asarray(pa_values, dtype=float)
    target_xyz = np.asarray(target_values, dtype=float)
    geometry = np.asarray(geometry_values, dtype=float)
    truth = pd.DataFrame(truth_values, columns=["edm_id","x","y","z","length_mm"])
    steps = build_steps(pa_xyz, target_xyz)

    range_axis = np.linspace(RANGE_MIN_MM, RANGE_MAX_MM, RANGE_SAMPLES)
    nstep = len(steps)
    nlaw = len(SECTORS_DEG)*len(SKEWS_DEG)
    total_cube = np.zeros((nstep,nlaw,RANGE_SAMPLES), dtype=np.float32)
    geometry_cube = np.zeros_like(total_cube)
    law_beams = np.zeros((nstep,nlaw,3), dtype=np.float32)
    rng = np.random.default_rng(941)

    edm_xyz = truth[["x","y","z"]].to_numpy(dtype=float)
    edm_lengths = truth["length_mm"].to_numpy(dtype=float)

    for k, step in enumerate(steps):
        pa = step["pa"]
        v = geometry - pa[None,:]
        ranges = np.linalg.norm(v, axis=1)
        valid = (ranges >= 3.0) & (ranges <= RANGE_MAX_MM)
        directions = np.zeros_like(v)
        directions[valid] = v[valid] / ranges[valid,None]
        laws = build_laws(step)

        for li, (sector, skew, beam, delays) in enumerate(laws):
            law_beams[k,li] = beam
            gtrace = np.zeros(RANGE_SAMPLES, dtype=float)
            etrace = np.zeros(RANGE_SAMPLES, dtype=float)

            # Fusion B009 blade geometry response — exact B001 principle,
            # but the geometry cloud now comes from the Fusion STL.
            cosang = np.clip(directions @ beam, -1.0, 1.0)
            ids = np.flatnonzero(valid & (cosang > math.cos(math.radians(12.0))))
            if ids.size:
                order = np.argsort(-cosang[ids])
                ids = ids[order[:24]]
                qg = geometry[ids]
                angle_deg = np.degrees(np.arccos(np.clip(cosang[ids],-1.0,1.0)))
                gains = vectorized_coherent_gain(step["elements"],delays,qg)
                beam_w = np.exp(-0.5*(angle_deg/GEOMETRY_BEAM_SIGMA_DEG)**2)
                distance_w = 1.0/(1.0+(ranges[ids]/65.0)**2)
                amps = GEOMETRY_FIXED_SCALE*gains*beam_w*distance_w
                for rr, amp in zip(ranges[ids],amps):
                    add_gaussian(gtrace,range_axis,float(rr),float(amp),PULSE_SIGMA_MM)

            # EDM responses belong to the digital specimen.
            # Coordinates are never supplied to the detector below.
            for ei,q in enumerate(edm_xyz):
                dvec = q-pa
                rr = float(np.linalg.norm(dvec))
                if not (RANGE_MIN_MM <= rr <= RANGE_MAX_MM):
                    continue
                direction = unit(dvec)
                off_axis = math.degrees(math.acos(float(np.clip(np.dot(direction,beam),-1,1))))
                if off_axis > 14.0:
                    continue
                gain = float(vectorized_coherent_gain(step["elements"],delays,q)[0])
                beam_w = math.exp(-0.5*(off_axis/EDM_BEAM_SIGMA_DEG)**2)
                length_w = max(0.45,min(1.8,edm_lengths[ei]/3.0))
                distance_w = 1.0/(1.0+(rr/70.0)**2)
                amp = EDM_FIXED_SCALE*gain*beam_w*length_w*distance_w
                add_gaussian(etrace,range_axis,rr,amp,0.85*PULSE_SIGMA_MM)

            noise = rng.normal(0.0,NOISE_RMS_RAW,size=RANGE_SAMPLES)
            total_cube[k,li] = np.maximum(gtrace+etrace+noise,0.0).astype(np.float32)
            geometry_cube[k,li] = gtrace.astype(np.float32)

    encoded_raw = np.max(total_cube,axis=1)
    geometry_encoded_raw = np.max(geometry_cube,axis=1)
    winning_law = np.argmax(total_cube,axis=1)

    peak = max(float(np.max(encoded_raw)),1e-12)
    encoded_db = 20*np.log10(np.clip(encoded_raw/peak,10**(SHOW_DB_FLOOR/20),None))
    encoded_db = np.clip(encoded_db,SHOW_DB_FLOOR,0.0)

    # Derive two dominant geometry tracks exactly from the geometry response.
    top = np.full(nstep,np.nan,dtype=float)
    bottom = np.full(nstep,np.nan,dtype=float)
    for k, trace in enumerate(geometry_encoded_raw):
        if float(np.max(trace)) <= 0:
            continue
        floor = 0.02*float(np.max(trace))
        peaks = [i for i in range(1,len(trace)-1)
                 if trace[i] >= floor and trace[i] >= trace[i-1] and trace[i] > trace[i+1]]
        if not peaks:
            continue
        peaks = sorted(peaks,key=lambda i: trace[i],reverse=True)
        first = peaks[0]
        second = None
        for idx in peaks[1:]:
            if abs(float(range_axis[idx]-range_axis[first])) >= 3.5:
                second = idx
                break
        if second is None:
            top[k] = range_axis[first]
        else:
            rr = sorted([float(range_axis[first]),float(range_axis[second])])
            top[k],bottom[k] = rr
    for arr in (top,bottom):
        arr[:] = (pd.Series(arr).interpolate(limit_direction="both")
                  .rolling(5,center=True,min_periods=1).median().to_numpy(dtype=float))

    # Blind detector: signal + geometry tracks only.
    candidates = []
    nskew = len(SKEWS_DEG)
    for k, step in enumerate(steps):
        trace = encoded_db[k]
        peaks = [i for i in range(1,len(trace)-1)
                 if trace[i] >= BLIND_THRESHOLD_DB and trace[i] >= trace[i-1] and trace[i] > trace[i+1]]
        peaks = sorted(peaks,key=lambda i: trace[i],reverse=True)[:MAX_BLIND_PEAKS_PER_SHOT]
        for idx in peaks:
            rr = float(range_axis[idx])
            is_geometry = False
            for gr in (top[k],bottom[k]):
                if np.isfinite(gr) and abs(rr-float(gr)) <= GEOMETRY_RANGE_TOL_MM:
                    is_geometry = True
            li = int(winning_law[k,idx])
            beam = law_beams[k,li]
            xyz = step["pa"] + rr*beam
            candidates.append({
                "step_id": k,
                "shot": k+1,
                "range_mm": rr,
                "amplitude_db": float(trace[idx]),
                "sector_deg": float(SECTORS_DEG[li//nskew]),
                "skew_deg": float(SKEWS_DEG[li%nskew]),
                "x_mm": float(xyz[0]),
                "y_mm": float(xyz[1]),
                "z_mm": float(xyz[2]),
                "classification": "GEOMETRY / GÉOMÉTRIE" if is_geometry else "INDICATION / INDICATION",
            })

    return {
        "range_axis": range_axis,
        "encoded_db": encoded_db,
        "top_range": top,
        "bottom_range": bottom,
        "law_beams": law_beams,
        "winning_law": winning_law,
        "candidates": pd.DataFrame(candidates),
    }


def cluster_candidates(cand_df: pd.DataFrame, max_shot: int) -> pd.DataFrame:
    if cand_df.empty:
        return cand_df.copy()
    src = cand_df[cand_df["shot"] <= max_shot].copy()
    if "classification" in src.columns:
        src = src[src["classification"].astype(str).str.startswith("INDICATION")]
    src = src.sort_values("amplitude_db", ascending=False)
    kept = []
    for _, row in src.iterrows():
        q = row[["x_mm","y_mm","z_mm"]].to_numpy(dtype=float)
        if all(np.linalg.norm(q-k[0]) > CLUSTER_RADIUS_MM for k in kept):
            kept.append((q,row))
    if not kept:
        return pd.DataFrame(columns=cand_df.columns)
    return pd.DataFrame([r.to_dict() for _,r in kept]).reset_index(drop=True)


def load_validated_c2_blind(data_dir: Path) -> pd.DataFrame:
    """Load the already-calculated PA2→C2 examination maxima.

    This is the frozen Face-2 evidence layer produced before mechanical validation:
    TFM/voxel peak position + acquisition shot/law + calibrated amplitude.  It avoids
    regenerating detections from EDM truth coordinates inside the Streamlit display.
    """
    det_path = data_dir / FACE2_DETECTIONS
    met_path = data_dir / FACE2_METROLOGY
    if not det_path.exists() or not met_path.exists():
        raise FileNotFoundError(f"Face-2 evidence missing: {det_path.name} / {met_path.name}")
    det = pd.read_csv(det_path)
    met = pd.read_csv(met_path)
    for df in (det, met):
        if "edm_id" not in df.columns:
            raise ValueError("Face-2 evidence has no edm_id column")
        df["edm_id"] = df["edm_id"].astype(str)
    ids=[f"EDM_{i:02d}" for i in range(6,12)]
    det=det[det.edm_id.isin(ids)].copy()
    met=met[met.edm_id.isin(ids)].copy()
    if len(det)!=6 or len(met)!=6:
        raise ValueError(f"Face-2 evidence must contain EDM_06…EDM_11 exactly once; detections={len(det)}, metrology={len(met)}")
    d=det.merge(met,on="edm_id",how="inner",suffixes=("_det","_met"))
    rows=[]
    for _,r in d.iterrows():
        def pick(*names, default=np.nan):
            for n in names:
                if n in r.index and pd.notna(r[n]): return r[n]
            return default
        fsh=float(pick("amplitude_FSH_percent_det","amplitude_FSH_percent_met","amplitude_FSH_percent"))
        amp_db=20.0*math.log10(max(fsh,1e-9)/SENSITIVITY_REFERENCE_FSH_PERCENT)
        shot=int(round(float(pick("pa_index","best_shot_row","scan_index",default=1))))
        shot=max(1,min(199,shot))
        rows.append({
            "step_id":shot-1,"shot":shot,
            "range_mm":float(pick("sound_path_mm","range_mm",default=np.nan)),
            "amplitude_db":amp_db,
            "sector_deg":float(pick("theta_deg_met","theta_deg_det","theta_deg")),
            "skew_deg":float(pick("skew_deg_met","skew_deg_det","skew_deg")),
            "x_mm":float(pick("max_x_mm")),"y_mm":float(pick("max_y_mm")),"z_mm":float(pick("max_z_mm")),
            "classification":"INDICATION / INDICATION","source":"VALIDATED_C2_EXAMINATION",
            "edm_label":str(r.edm_id),"fsh_percent_source":fsh,
        })
    out=pd.DataFrame(rows)
    if not np.isfinite(out[["x_mm","y_mm","z_mm"]].to_numpy(float)).all():
        raise ValueError("Face-2 metrology maxima max_x/max_y/max_z are incomplete")
    return out.sort_values("shot").reset_index(drop=True)


def match_truth(clusters: pd.DataFrame, truth: pd.DataFrame):
    rows = []
    used = set()
    for _, edm in truth.iterrows():
        q = edm[["truth_X_mm","truth_Y_mm","truth_Z_mm"]].to_numpy(dtype=float)
        best = None
        for ci, c in clusters.iterrows():
            if ci in used:
                continue
            p = c[["x_mm","y_mm","z_mm"]].to_numpy(dtype=float)
            d = float(np.linalg.norm(p-q))
            if best is None or d < best[0]:
                best = (d,ci,c)
        ok = best is not None and best[0] <= VALIDATION_TOL_MM
        if ok:
            used.add(best[1])
            c = best[2]
        else:
            c = None
        rows.append({
            "edm_id": edm["edm_id"],
            "detected": "YES / OUI" if ok else "NO / NON",
            "error_mm": best[0] if ok else np.nan,
            "blind_shot": int(c["shot"]) if ok else np.nan,
            "blind_amplitude_db": float(c["amplitude_db"]) if ok else np.nan,
            "blind_range_mm": float(c["range_mm"]) if ok and "range_mm" in c else np.nan,
            "blind_sector_deg": float(c["sector_deg"]) if ok and "sector_deg" in c else np.nan,
            "blind_skew_deg": float(c["skew_deg"]) if ok and "skew_deg" in c else np.nan,
            "truth_X_mm": float(q[0]),
            "truth_Y_mm": float(q[1]),
            "truth_Z_mm": float(q[2]),
            "detected_X_mm": float(c["x_mm"]) if ok else np.nan,
            "detected_Y_mm": float(c["y_mm"]) if ok else np.nan,
            "detected_Z_mm": float(c["z_mm"]) if ok else np.nan,
        })
    return pd.DataFrame(rows)



def build_progressive_scan3d_cloud(scan, pa, current_shot, db_threshold=SCAN3D_POINT_CLOUD_DB):
    """Build the growing 3D ultrasonic response cloud from Fusion-driven acquisition."""
    range_axis = np.asarray(scan["range_axis"], dtype=float)
    encoded_db = np.asarray(scan["encoded_db"], dtype=float)
    winning = np.asarray(scan["winning_law"], dtype=int)
    law_beams = np.asarray(scan["law_beams"], dtype=float)

    xyz_all = []
    db_all = []
    shot_all = []

    for k in range(min(int(current_shot), len(pa))):
        idx = np.flatnonzero(encoded_db[k] >= float(db_threshold))
        if idx.size == 0:
            continue
        if idx.size > 260:
            idx = idx[np.linspace(0, idx.size - 1, 260).astype(int)]

        laws = winning[k, idx]
        beams = law_beams[k, laws]
        rr = range_axis[idx]
        xyz = pa[k][None, :] + rr[:, None] * beams

        xyz_all.append(xyz)
        db_all.append(encoded_db[k, idx])
        shot_all.append(np.full(len(idx), k + 1, dtype=int))

    if not xyz_all:
        return np.empty((0,3)), np.empty((0,)), np.empty((0,), dtype=int)

    xyz = np.vstack(xyz_all)
    db = np.concatenate(db_all)
    shots = np.concatenate(shot_all)

    if len(xyz) > 12000:
        take = np.linspace(0, len(xyz) - 1, 12000).astype(int)
        xyz, db, shots = xyz[take], db[take], shots[take]

    return xyz, db, shots


def make_true_scan3d_scene(mesh_v, mesh_f, pa, target, scan, current_shot, clusters):
    import plotly.graph_objects as go

    cloud_xyz, cloud_db, cloud_shot = build_progressive_scan3d_cloud(
        scan, pa, current_shot, SCAN3D_POINT_CLOUD_DB
    )

    fig = go.Figure()

    if mesh_v is not None and mesh_f is not None:
        fig.add_trace(go.Mesh3d(
            x=mesh_v[:,0], y=mesh_v[:,1], z=mesh_v[:,2],
            i=mesh_f[:,0], j=mesh_f[:,1], k=mesh_f[:,2],
            color="lightgray", opacity=0.10,
            name="Fusion blade + woodenblock",
            hoverinfo="skip",
        ))

    if len(cloud_xyz):
        fig.add_trace(go.Scatter3d(
            x=cloud_xyz[:,0], y=cloud_xyz[:,1], z=cloud_xyz[:,2],
            mode="markers",
            marker=dict(
                size=3.0,
                color=cloud_db,
                colorscale="Turbo",
                cmin=SCAN3D_POINT_CLOUD_DB,
                cmax=0.0,
                opacity=0.75,
                showscale=True,
                colorbar=dict(title="UT dB", x=0.02),
            ),
            customdata=np.c_[cloud_shot, cloud_db],
            hovertemplate=(
                "TRUE 3D Scan"
                "<br>Shot=%{customdata[0]:.0f}"
                "<br>Level=%{customdata[1]:.1f} dB"
                "<br>X=%{x:.1f} mm"
                "<br>Y=%{y:.1f} mm"
                "<br>Z=%{z:.1f} mm"
                "<extra></extra>"
            ),
            name="Growing UT 3D scan / Scan UT 3D progressif",
        ))

    fig.add_trace(go.Scatter3d(
        x=pa[:,0], y=pa[:,1], z=pa[:,2],
        mode="lines", line=dict(width=5, color="#009DFF"),
        name="Fusion PA trajectory",
    ))
    fig.add_trace(go.Scatter3d(
        x=pa[:current_shot,0], y=pa[:current_shot,1], z=pa[:current_shot,2],
        mode="lines+markers",
        line=dict(width=7, color="#00B7FF"),
        marker=dict(size=3, color="#00B7FF"),
        name="Acquired PA path / Parcours acquis",
    ))

    idx = int(current_shot) - 1
    p = pa[idx]
    q = target[idx]

    fig.add_trace(go.Scatter3d(
        x=[p[0]], y=[p[1]], z=[p[2]],
        mode="markers",
        marker=dict(size=11, color="#FF9800", symbol="square"),
        name=f"Active PA — shot {current_shot}",
    ))
    fig.add_trace(go.Scatter3d(
        x=[p[0],q[0]], y=[p[1],q[1]], z=[p[2],q[2]],
        mode="lines",
        line=dict(width=10, color="#00D66B"),
        name="Active acoustic path / Chemin acoustique actif",
    ))

    if clusters is not None and not clusters.empty:
        fig.add_trace(go.Scatter3d(
            x=clusters["x_mm"], y=clusters["y_mm"], z=clusters["z_mm"],
            mode="markers",
            marker=dict(
                size=9, color="#8B0000", symbol="circle",
                line=dict(width=2, color="white")
            ),
            name="Blind detections / Détections aveugles",
        ))

    fig.update_layout(
        title=f"TRUE 3D SCAN — growing ultrasonic volume / SCAN 3D UT progressif — shots 1…{current_shot}",
        height=720,
        margin=dict(l=0, r=0, t=55, b=0),
        scene=dict(
            xaxis_title="X [mm]",
            yaxis_title="Y [mm]",
            zaxis_title="Z [mm]",
            aspectmode="data",
            camera=dict(eye=dict(x=1.45, y=1.55, z=0.95)),
        ),
        legend=dict(orientation="h", y=1.02, x=0.03),
    )
    return fig


def make_current_ascan(scan, current_shot):
    import plotly.graph_objects as go
    k = int(current_shot) - 1
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=scan["range_axis"],
        y=scan["encoded_db"][k],
        mode="lines",
        line=dict(width=2),
        name="Current A-scan / A-scan courant",
    ))
    fig.add_hline(
        y=BLIND_THRESHOLD_DB,
        line_dash="dash",
        annotation_text=f"Blind threshold {BLIND_THRESHOLD_DB:.0f} dB",
    )
    fig.update_layout(
        title=f"Current A-scan / A-scan courant — shot {current_shot}",
        height=310,
        margin=dict(l=45, r=20, t=45, b=40),
        xaxis_title="Sound path / Parcours acoustique [mm]",
        yaxis_title="Relative amplitude [dB]",
        yaxis=dict(range=[SHOW_DB_FLOOR, 2]),
    )
    return fig


def make_3d_scene(mesh_v, mesh_f, pa, target, current_shot, clusters, show_truth=False, truth=None):
    import plotly.graph_objects as go
    fig = go.Figure()
    if mesh_v is not None and mesh_f is not None:
        fig.add_trace(go.Mesh3d(
            x=mesh_v[:,0], y=mesh_v[:,1], z=mesh_v[:,2],
            i=mesh_f[:,0], j=mesh_f[:,1], k=mesh_f[:,2],
            color="lightgray", opacity=0.17, name="Fusion blade + woodenblock",
            hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter3d(
        x=pa[:,0], y=pa[:,1], z=pa[:,2],
        mode="lines+markers", line=dict(width=6,color="#009DFF"),
        marker=dict(size=3,color="#009DFF"), name="Fusion PA trajectory",
    ))
    fig.add_trace(go.Scatter3d(
        x=target[:,0], y=target[:,1], z=target[:,2],
        mode="lines+markers", line=dict(width=5,color="#FF2D2D"),
        marker=dict(size=3,color="#FF2D2D"), name="Fusion C2 target",
    ))
    idx = current_shot-1
    p = pa[idx]; q = target[idx]
    fig.add_trace(go.Scatter3d(
        x=[p[0]],y=[p[1]],z=[p[2]],mode="markers",
        marker=dict(size=10,color="#FF9800",symbol="square"),
        name=f"Active PA — shot {current_shot}",
    ))
    fig.add_trace(go.Scatter3d(
        x=[p[0],q[0]],y=[p[1],q[1]],z=[p[2],q[2]],mode="lines",
        line=dict(width=10,color="#00D66B"),name="Current Fusion UT path",
    ))
    if clusters is not None and not clusters.empty:
        fig.add_trace(go.Scatter3d(
            x=clusters["x_mm"],y=clusters["y_mm"],z=clusters["z_mm"],
            mode="markers",
            marker=dict(size=8,color=clusters["amplitude_db"],colorscale="Turbo",
                        cmin=SHOW_DB_FLOOR,cmax=0,showscale=True,
                        colorbar=dict(title="Blind dB")),
            name="Blind detections accumulated",
            hovertemplate="Blind detection<br>X=%{x:.1f}<br>Y=%{y:.1f}<br>Z=%{z:.1f}<extra></extra>",
        ))
    if show_truth and truth is not None and not truth.empty:
        fig.add_trace(go.Scatter3d(
            x=truth["truth_X_mm"],y=truth["truth_Y_mm"],z=truth["truth_Z_mm"],
            mode="markers+text", text=truth["edm_id"], textposition="top center",
            marker=dict(size=8,color="#00AA44",symbol="x"),
            name="Mechanical EDM truth — validation only",
        ))
    fig.update_layout(
        height=650, margin=dict(l=0,r=0,t=35,b=0),
        scene=dict(xaxis_title="X [mm]",yaxis_title="Y [mm]",zaxis_title="Z [mm]",aspectmode="data"),
        legend=dict(orientation="h",y=1.02),
    )
    return fig


def make_encoded_map(encoded_db, range_axis, current_shot, clusters, top_range=None, bottom_range=None):
    import plotly.graph_objects as go
    z = encoded_db[:current_shot,:]
    fig = go.Figure(go.Heatmap(
        z=z, x=range_axis, y=np.arange(1,current_shot+1),
        zmin=SHOW_DB_FLOOR,zmax=0,colorscale="Jet",
        colorbar=dict(title="dB"),
    ))
    yy = np.arange(1,current_shot+1)
    if top_range is not None:
        fig.add_trace(go.Scatter(x=np.asarray(top_range)[:current_shot],y=yy,mode="lines",
                                 line=dict(width=2,dash="dash"),name="TOP geometry"))
    if bottom_range is not None:
        fig.add_trace(go.Scatter(x=np.asarray(bottom_range)[:current_shot],y=yy,mode="lines",
                                 line=dict(width=2,dash="dot"),name="BOTTOM geometry"))
    if clusters is not None and not clusters.empty:
        fig.add_trace(go.Scatter(
            x=clusters["range_mm"],y=clusters["shot"],mode="markers",
            marker=dict(size=9,color="white",symbol="x",line=dict(width=2,color="black")),
            name="Blind detections",
        ))
    fig.update_layout(
        height=650, margin=dict(l=45,r=20,t=35,b=45),
        xaxis_title="Sound path / Parcours acoustique [mm]",
        yaxis_title="Encoded shot / Tir encodé",
        title=f"TRUE TWIN encoded scan — shots 1…{current_shot}",
    )
    return fig



def make_2d_matrix_fan_scene(mesh_v, mesh_f, pa, target, shot):
    """Show the 8x8 2D matrix and the complete 35-70 / -10..+10 beam family."""
    import plotly.graph_objects as go

    steps = build_steps(pa, target)
    step = steps[int(shot) - 1]
    laws = build_laws(step)
    p = step["pa"]
    focus = step["focus_distance_mm"]

    fig = go.Figure()
    if mesh_v is not None and mesh_f is not None:
        fig.add_trace(go.Mesh3d(
            x=mesh_v[:,0], y=mesh_v[:,1], z=mesh_v[:,2],
            i=mesh_f[:,0], j=mesh_f[:,1], k=mesh_f[:,2],
            color="lightgray", opacity=0.10,
            name="Fusion geometry", hoverinfo="skip"
        ))

    # 64 matrix elements.
    elems = step["elements"]
    fig.add_trace(go.Scatter3d(
        x=elems[:,0], y=elems[:,1], z=elems[:,2],
        mode="markers",
        marker=dict(size=4, color="#FF9800"),
        name="8×8 matrix — 64 elements"
    ))

    # 85 spatial laws at this mechanical position.
    rx, ry, rz = [], [], []
    ex, ey, ez, ec = [], [], [], []
    for sector, skew, beam, delays in laws:
        q = p + focus * beam
        rx += [p[0], q[0], None]
        ry += [p[1], q[1], None]
        rz += [p[2], q[2], None]
        ex.append(q[0]); ey.append(q[1]); ez.append(q[2]); ec.append(sector)

    fig.add_trace(go.Scatter3d(
        x=rx, y=ry, z=rz, mode="lines",
        line=dict(width=2, color="#00B7FF"),
        opacity=0.20,
        name="85 sector/skew laws"
    ))
    fig.add_trace(go.Scatter3d(
        x=ex, y=ey, z=ez, mode="markers",
        marker=dict(
            size=4, color=ec, colorscale="Turbo",
            cmin=float(np.min(SECTORS_DEG)), cmax=float(np.max(SECTORS_DEG)),
            showscale=True, colorbar=dict(title="Sector °")
        ),
        name="Law endpoints / Extrémités des lois"
    ))

    # Nominal Fusion target.
    qn = step["target_nominal"]
    fig.add_trace(go.Scatter3d(
        x=[p[0], qn[0]], y=[p[1], qn[1]], z=[p[2], qn[2]],
        mode="lines+markers",
        line=dict(width=9, color="#00D66B"),
        marker=dict(size=7, color="#00D66B"),
        name="Fusion nominal path / Chemin nominal Fusion"
    ))

    fig.update_layout(
        height=700,
        margin=dict(l=0,r=0,t=55,b=0),
        title=f"2D matrix beam family — shot {shot}/{len(pa)} — 85 laws",
        scene=dict(
            xaxis_title="X [mm]", yaxis_title="Y [mm]", zaxis_title="Z [mm]",
            aspectmode="data",
            camera=dict(eye=dict(x=1.35,y=1.55,z=1.0)),
        ),
        legend=dict(orientation="h", y=1.02),
    )
    return fig


def _tfm_basis(step, center_xyz):
    pa0 = np.asarray(step["pa"], dtype=float)
    v_axis = unit(np.asarray(center_xyz, dtype=float) - pa0)
    tangent = unit(np.asarray(step["tangent"], dtype=float))
    u_axis = tangent - float(np.dot(tangent, v_axis)) * v_axis
    if np.linalg.norm(u_axis) < 1e-8:
        u_axis = np.cross(v_axis, np.array([0.0,0.0,1.0]))
    if np.linalg.norm(u_axis) < 1e-8:
        u_axis = np.cross(v_axis, np.array([0.0,1.0,0.0]))
    return unit(u_axis), unit(v_axis)


def _mask_metrics_2d(u, v, image_db, threshold_db):
    mask = np.asarray(image_db >= float(threshold_db))
    if not np.any(mask):
        return {"pixels":0,"area_mm2":0.0,"width_u_mm":np.nan,"width_v_mm":np.nan}
    iv, iu = np.nonzero(mask)
    du = float(np.median(np.diff(u))) if len(u)>1 else TFM_STEP_MM
    dv = float(np.median(np.diff(v))) if len(v)>1 else TFM_STEP_MM
    return {
        "pixels": int(mask.sum()),
        "area_mm2": float(mask.sum())*abs(du*dv),
        "width_u_mm": float(u[iu].max()-u[iu].min()+abs(du)),
        "width_v_mm": float(v[iv].max()-v[iv].min()+abs(dv)),
    }


@st.cache_data(show_spinner=False)
def compute_tfm_selected(pa_values, target_values, truth_values, blind_xyz, blind_shot):
    """
    Full 64×64 FMC-equivalent local TFM, centred on the BLIND detection.
    Truth scatterers belong only to the virtual specimen signal generator.
    """
    pa_arr = np.asarray(pa_values, dtype=float)
    target_arr = np.asarray(target_values, dtype=float)
    truth = pd.DataFrame(truth_values, columns=["edm_id","x","y","z","length_mm"])
    steps = build_steps(pa_arr, target_arr)
    step = steps[int(blind_shot)-1]
    center = np.asarray(blind_xyz, dtype=float)
    u_axis, v_axis = _tfm_basis(step, center)
    elements = np.asarray(step["elements"], dtype=float)

    scatter = truth[["x","y","z"]].to_numpy(dtype=float)
    weights = np.asarray([
        max(0.45, min(1.8, float(x)/3.0))
        for x in truth["length_mm"].to_numpy(dtype=float)
    ], dtype=float)
    dloc = np.linalg.norm(scatter-center[None,:],axis=1)
    ids = np.flatnonzero(dloc <= 18.0)
    if ids.size == 0:
        ids = np.arange(len(scatter))

    u = np.arange(-TFM_HALF_U_MM, TFM_HALF_U_MM+0.5*TFM_STEP_MM, TFM_STEP_MM)
    v = np.arange(-TFM_HALF_V_MM, TFM_HALF_V_MM+0.5*TFM_STEP_MM, TFM_STEP_MM)
    uu,vv = np.meshgrid(u,v)
    pixels = (
        center[None,None,:]
        + uu[...,None]*u_axis[None,None,:]
        + vv[...,None]*v_axis[None,None,:]
    ).reshape(-1,3)

    scatter_times = []
    for q in scatter[ids]:
        d = np.linalg.norm(elements-q[None,:],axis=1)
        scatter_times.append(((d[:,None]+d[None,:])/STEEL_SHEAR_MM_US).reshape(-1))
    scatter_times = np.asarray(scatter_times,dtype=float)

    out = np.zeros(len(pixels),dtype=float)
    two_pi_f = 2*np.pi*FREQUENCY_MHZ
    chunk = 96
    for i0 in range(0,len(pixels),chunk):
        q = pixels[i0:i0+chunk]
        d = np.linalg.norm(q[:,None,:]-elements[None,:,:],axis=2)
        pt = (d[:,:,None]+d[:,None,:]).reshape(len(q),-1)/STEEL_SHEAR_MM_US
        coh = np.zeros_like(pt)
        for si in range(len(ids)):
            dt = pt-scatter_times[si][None,:]
            coh += float(weights[ids[si]]) * (
                np.exp(-0.5*(dt/TFM_PULSE_SIGMA_US)**2) * np.cos(two_pi_f*dt)
            )
        out[i0:i0+len(q)] = np.abs(np.sum(coh,axis=1))

    image = out.reshape(len(v),len(u))
    raw_peak = max(float(np.max(image)),1e-15)
    image_db = 20*np.log10(np.clip(image/raw_peak,10**(TFM_FLOOR_DB/20),None))
    image_db = np.clip(image_db,TFM_FLOOR_DB,0.0)
    iv,iu = np.unravel_index(np.argmax(image),image.shape)
    peak_xyz = center + float(u[iu])*u_axis + float(v[iv])*v_axis

    return {
        "u":u, "v":v, "image_db":image_db, "raw_peak":raw_peak,
        "peak_xyz":peak_xyz, "center_xyz":center,
        "minus6":_mask_metrics_2d(u,v,image_db,-6.0),
        "minus12":_mask_metrics_2d(u,v,image_db,-12.0),
    }


def make_tfm_figure(result, edm_id):
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        x=result["u"], y=result["v"], z=result["image_db"],
        zmin=TFM_FLOOR_DB, zmax=0, colorscale="Jet",
        colorbar=dict(title="TFM dB"), name="TFM"
    ))
    # Measurement contours, exactly as an analysis tool rather than a decorative image.
    fig.add_trace(go.Contour(
        x=result["u"], y=result["v"], z=result["image_db"],
        contours=dict(start=-12,end=-12,size=1,coloring="lines"),
        line=dict(width=2,color="white"), showscale=False,
        name="−12 dB"
    ))
    fig.add_trace(go.Contour(
        x=result["u"], y=result["v"], z=result["image_db"],
        contours=dict(start=-6,end=-6,size=1,coloring="lines"),
        line=dict(width=3,color="black"), showscale=False,
        name="−6 dB"
    ))
    fig.add_trace(go.Scatter(
        x=[0],y=[0],mode="markers",
        marker=dict(size=12,symbol="cross",color="white",line=dict(width=1,color="black")),
        name="Blind centre / Centre aveugle"
    ))
    fig.update_layout(
        height=620,
        title=f"{edm_id} — 64×64 FMC-equivalent TFM — −6/−12 dB measurement",
        xaxis_title="Local scan U [mm]",
        yaxis_title="Local acoustic V [mm]",
        yaxis=dict(scaleanchor="x",scaleratio=1),
        margin=dict(l=45,r=20,t=60,b=45),
        legend=dict(orientation="h",y=1.02)
    )
    return fig



def _voxel_basis(step, center_xyz):
    u_axis,v_axis = _tfm_basis(step,center_xyz)
    w_axis = unit(np.cross(u_axis,v_axis))
    return u_axis,v_axis,w_axis


@st.cache_data(show_spinner=False)
def compute_voxel_selected(pa_values, target_values, truth_values, blind_xyz, blind_shot):
    """
    3D 64×64 FMC-equivalent voxel reconstruction around the blind detection.
    Grid is deliberately local for interactive Streamlit performance.
    """
    pa_arr = np.asarray(pa_values,dtype=float)
    target_arr = np.asarray(target_values,dtype=float)
    truth = pd.DataFrame(truth_values,columns=["edm_id","x","y","z","length_mm"])
    steps = build_steps(pa_arr,target_arr)
    step = steps[int(blind_shot)-1]
    center = np.asarray(blind_xyz,dtype=float)
    u_axis,v_axis,w_axis = _voxel_basis(step,center)
    elements = np.asarray(step["elements"],dtype=float)

    scatter = truth[["x","y","z"]].to_numpy(dtype=float)
    weights = np.asarray([
        max(0.45,min(1.8,float(x)/3.0))
        for x in truth["length_mm"].to_numpy(dtype=float)
    ])
    dloc = np.linalg.norm(scatter-center[None,:],axis=1)
    ids = np.flatnonzero(dloc<=18.0)
    if ids.size==0:
        ids=np.arange(len(scatter))

    ax = np.arange(-VOXEL_HALF_MM,VOXEL_HALF_MM+0.5*VOXEL_STEP_MM,VOXEL_STEP_MM)
    u=v=w=ax.copy()
    ww,vv,uu = np.meshgrid(w,v,u,indexing="ij")
    voxels = (
        center[None,None,None,:]
        + uu[...,None]*u_axis
        + vv[...,None]*v_axis
        + ww[...,None]*w_axis
    ).reshape(-1,3)

    scatter_times=[]
    for q in scatter[ids]:
        d=np.linalg.norm(elements-q[None,:],axis=1)
        scatter_times.append(((d[:,None]+d[None,:])/STEEL_SHEAR_MM_US).reshape(-1))
    scatter_times=np.asarray(scatter_times)

    out=np.zeros(len(voxels),dtype=float)
    two_pi_f=2*np.pi*FREQUENCY_MHZ
    chunk=64
    for i0 in range(0,len(voxels),chunk):
        q=voxels[i0:i0+chunk]
        d=np.linalg.norm(q[:,None,:]-elements[None,:,:],axis=2)
        pt=(d[:,:,None]+d[:,None,:]).reshape(len(q),-1)/STEEL_SHEAR_MM_US
        coh=np.zeros_like(pt)
        for si in range(len(ids)):
            dt=pt-scatter_times[si][None,:]
            coh += float(weights[ids[si]]) * (
                np.exp(-0.5*(dt/VOXEL_PULSE_SIGMA_US)**2)*np.cos(two_pi_f*dt)
            )
        out[i0:i0+len(q)] = np.abs(np.sum(coh,axis=1))

    vol=out.reshape(len(w),len(v),len(u))
    raw_peak=max(float(np.max(vol)),1e-15)
    db=20*np.log10(np.clip(vol/raw_peak,10**(VOXEL_FLOOR_DB/20),None))
    db=np.clip(db,VOXEL_FLOOR_DB,0.0)
    iw,iv,iu=np.unravel_index(np.argmax(vol),vol.shape)
    peak_xyz=center+float(u[iu])*u_axis+float(v[iv])*v_axis+float(w[iw])*w_axis

    return {
        "u":u,"v":v,"w":w,"volume_db":db,
        "raw_peak":raw_peak,"peak_xyz":peak_xyz,"center_xyz":center
    }


def voxel_threshold_metrics(result, threshold_db):
    u,v,w=result["u"],result["v"],result["w"]
    db=result["volume_db"]
    mask=db>=float(threshold_db)
    if not np.any(mask):
        return {"voxels":0,"volume_mm3":0.0,"extent_u_mm":np.nan,"extent_v_mm":np.nan,"extent_w_mm":np.nan}
    iw,iv,iu=np.nonzero(mask)
    du=abs(float(np.median(np.diff(u)))) if len(u)>1 else VOXEL_STEP_MM
    dv=abs(float(np.median(np.diff(v)))) if len(v)>1 else VOXEL_STEP_MM
    dw=abs(float(np.median(np.diff(w)))) if len(w)>1 else VOXEL_STEP_MM
    return {
        "voxels":int(mask.sum()),
        "volume_mm3":float(mask.sum())*du*dv*dw,
        "extent_u_mm":float(u[iu].max()-u[iu].min()+du),
        "extent_v_mm":float(v[iv].max()-v[iv].min()+dv),
        "extent_w_mm":float(w[iw].max()-w[iw].min()+dw),
    }


def make_voxel_figure(result, edm_id, threshold_db=-6.0):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    u,v,w=result["u"],result["v"],result["w"]
    db=result["volume_db"]
    mip_uv=np.max(db,axis=0)  # V,U
    mip_uw=np.max(db,axis=1)  # W,U
    mip_vw=np.max(db,axis=2)  # W,V
    ww,vv,uu=np.meshgrid(w,v,u,indexing="ij")
    mask=db>=float(threshold_db)

    fig=make_subplots(
        rows=2,cols=2,
        specs=[[{"type":"xy"},{"type":"xy"}],
               [{"type":"xy"},{"type":"scene"}]],
        subplot_titles=(
            "U-V maximum projection / Projection max U-V",
            "U-W maximum projection / Projection max U-W",
            "V-W maximum projection / Projection max V-W",
            f"{threshold_db:.0f} dB voxel cloud / Nuage voxel {threshold_db:.0f} dB",
        ),
        horizontal_spacing=0.08,vertical_spacing=0.12,
    )
    fig.add_trace(go.Heatmap(x=u,y=v,z=mip_uv,zmin=VOXEL_FLOOR_DB,zmax=0,colorscale="Jet",showscale=False),row=1,col=1)
    fig.add_trace(go.Heatmap(x=u,y=w,z=mip_uw,zmin=VOXEL_FLOOR_DB,zmax=0,colorscale="Jet",showscale=False),row=1,col=2)
    fig.add_trace(go.Heatmap(x=v,y=w,z=mip_vw,zmin=VOXEL_FLOOR_DB,zmax=0,colorscale="Jet",showscale=False),row=2,col=1)

    if np.any(mask):
        fig.add_trace(go.Scatter3d(
            x=uu[mask],y=vv[mask],z=ww[mask],mode="markers",
            marker=dict(size=5,color=db[mask],colorscale="Turbo",cmin=float(threshold_db),cmax=0,opacity=0.72,
                        showscale=True,colorbar=dict(title="Voxel dB",x=1.02)),
            name=f"Voxel ≥ {threshold_db:.0f} dB"
        ),row=2,col=2)
    fig.add_trace(go.Scatter3d(
        x=[0],y=[0],z=[0],mode="markers",
        marker=dict(size=8,color="white",symbol="x"),name="Blind centre"
    ),row=2,col=2)

    fig.update_xaxes(title_text="U [mm]",row=1,col=1); fig.update_yaxes(title_text="V [mm]",row=1,col=1)
    fig.update_xaxes(title_text="U [mm]",row=1,col=2); fig.update_yaxes(title_text="W [mm]",row=1,col=2)
    fig.update_xaxes(title_text="V [mm]",row=2,col=1); fig.update_yaxes(title_text="W [mm]",row=2,col=1)
    fig.update_layout(
        height=900,
        title=f"BYTE NDT — {edm_id} — 3D FMC/TFM VOXEL ANALYSIS / ANALYSE VOXEL 3D",
        margin=dict(l=45,r=45,t=75,b=45),
        legend=dict(orientation="h",y=1.02),
    )
    fig.update_scenes(xaxis_title="U [mm]",yaxis_title="V [mm]",zaxis_title="W [mm]",aspectmode="cube")
    return fig


def make_overview_scene(mesh_v,mesh_f,pa,target,clusters,truth):
    import plotly.graph_objects as go
    fig=go.Figure()
    if mesh_v is not None and mesh_f is not None:
        fig.add_trace(go.Mesh3d(
            x=mesh_v[:,0],y=mesh_v[:,1],z=mesh_v[:,2],
            i=mesh_f[:,0],j=mesh_f[:,1],k=mesh_f[:,2],
            color="lightgray",opacity=0.11,name="Fusion B009 geometry",hoverinfo="skip"
        ))
    fig.add_trace(go.Scatter3d(
        x=pa[:,0],y=pa[:,1],z=pa[:,2],mode="lines+markers",
        line=dict(width=6,color="#009DFF"),marker=dict(size=3,color="#009DFF"),name=f"{len(pa)} PA positions"
    ))
    fig.add_trace(go.Scatter3d(
        x=target[:,0],y=target[:,1],z=target[:,2],mode="lines+markers",
        line=dict(width=5,color="#FF3B30"),marker=dict(size=3,color="#FF3B30"),name=f"{len(target)} C2 target points"
    ))
    # All nominal acoustic paths give the overview the same inspection-reading role as the first application.
    lx=[];ly=[];lz=[]
    for p,q in zip(pa,target):
        lx += [p[0],q[0],None]; ly += [p[1],q[1],None]; lz += [p[2],q[2],None]
    fig.add_trace(go.Scatter3d(x=lx,y=ly,z=lz,mode="lines",line=dict(width=2,color="#00B86B"),opacity=.16,name=f"{len(pa)} nominal acoustic paths"))
    if clusters is not None and not clusters.empty:
        fig.add_trace(go.Scatter3d(
            x=clusters["x_mm"],y=clusters["y_mm"],z=clusters["z_mm"],mode="markers",
            marker=dict(size=7,color=clusters["amplitude_db"],colorscale="Turbo",cmin=SHOW_DB_FLOOR,cmax=0,showscale=True,colorbar=dict(title="Blind dB")),
            name="Blind indications"
        ))
    if truth is not None and not truth.empty:
        fig.add_trace(go.Scatter3d(
            x=truth["truth_X_mm"],y=truth["truth_Y_mm"],z=truth["truth_Z_mm"],mode="markers+text",
            text=truth["edm_id"],textposition="top center",marker=dict(size=8,color="#00AA44",symbol="x"),
            name="Mechanical EDM truth — post-validation"
        ))
    fig.update_layout(
        height=720,title="Twin overview — geometry → trajectory → acoustic paths → blind indications",
        margin=dict(l=0, r=0, t=55, b=0),
        scene=dict(
            xaxis_title="X [mm]",
            yaxis_title="Y [mm]",
            zaxis_title="Z [mm]",
            aspectmode="data",
            camera=dict(eye=dict(x=-1.45, y=1.55, z=.95)),
        ),
        legend=dict(orientation="h", y=1.02),
    )
    return fig


def make_indication_focus_scene(mesh_v,mesh_f,pa,target,validation_row,clusters):
    import plotly.graph_objects as go
    shot=int(validation_row["blind_shot"])
    p=pa[shot-1]; q=target[shot-1]
    det=np.array([validation_row["detected_X_mm"],validation_row["detected_Y_mm"],validation_row["detected_Z_mm"]],dtype=float)
    tru=np.array([validation_row["truth_X_mm"],validation_row["truth_Y_mm"],validation_row["truth_Z_mm"]],dtype=float)
    fig=go.Figure()
    if mesh_v is not None and mesh_f is not None:
        fig.add_trace(go.Mesh3d(x=mesh_v[:,0],y=mesh_v[:,1],z=mesh_v[:,2],i=mesh_f[:,0],j=mesh_f[:,1],k=mesh_f[:,2],
                                color="lightgray",opacity=.09,name="Fusion geometry",hoverinfo="skip"))
    fig.add_trace(go.Scatter3d(x=pa[:,0],y=pa[:,1],z=pa[:,2],mode="lines",line=dict(width=4,color="#009DFF"),name="PA trajectory"))
    fig.add_trace(go.Scatter3d(x=target[:,0],y=target[:,1],z=target[:,2],mode="lines",line=dict(width=4,color="#FF3B30"),name="C2 target"))
    fig.add_trace(go.Scatter3d(x=[p[0]],y=[p[1]],z=[p[2]],mode="markers",marker=dict(size=11,color="#FF9800",symbol="square"),name=f"Blind shot {shot}"))
    fig.add_trace(go.Scatter3d(x=[p[0],q[0]],y=[p[1],q[1]],z=[p[2],q[2]],mode="lines",line=dict(width=9,color="#00D66B"),name="Associated Fusion acoustic path"))
    if clusters is not None and not clusters.empty:
        fig.add_trace(go.Scatter3d(x=clusters["x_mm"],y=clusters["y_mm"],z=clusters["z_mm"],mode="markers",
                                    marker=dict(size=4,color="#A0A0A0",opacity=.35),name="Other blind clusters"))
    fig.add_trace(go.Scatter3d(x=[det[0]],y=[det[1]],z=[det[2]],mode="markers+text",text=[str(validation_row["edm_id"])],textposition="top center",
                                marker=dict(size=12,color="#B00020",symbol="diamond"),name="Selected blind indication"))
    fig.add_trace(go.Scatter3d(x=[tru[0]],y=[tru[1]],z=[tru[2]],mode="markers",marker=dict(size=12,color="#00AA44",symbol="x"),name="Truth — post-validation only"))
    fig.update_layout(height=680,title=f"Indication Explorer — {validation_row['edm_id']} — blind shot {shot}",margin=dict(l=0,r=0,t=55,b=0),
                      scene=dict(xaxis_title="X [mm]",yaxis_title="Y [mm]",zaxis_title="Z [mm]",aspectmode="data",camera=dict(eye=dict(x=1.4,y=1.4,z=1.0))),
                      legend=dict(orientation="h",y=1.02))
    return fig


def make_auto_scan3d_animation(mesh_v,mesh_f,pa,target,scan):
    import plotly.graph_objects as go
    fig=go.Figure()
    if mesh_v is not None and mesh_f is not None:
        fig.add_trace(go.Mesh3d(x=mesh_v[:,0],y=mesh_v[:,1],z=mesh_v[:,2],i=mesh_f[:,0],j=mesh_f[:,1],k=mesh_f[:,2],
                                color="lightgray",opacity=.08,name="Fusion geometry",hoverinfo="skip"))
    fig.add_trace(go.Scatter3d(x=pa[:,0],y=pa[:,1],z=pa[:,2],mode="lines",line=dict(width=5,color="#009DFF"),name="PA trajectory"))
    fig.add_trace(go.Scatter3d(x=target[:,0],y=target[:,1],z=target[:,2],mode="lines",line=dict(width=4,color="#FF3B30"),name="C2 target"))

    # Dynamic trace placeholders: cloud, active PA, active path, detections.
    fig.add_trace(go.Scatter3d(x=[],y=[],z=[],mode="markers",marker=dict(size=3,colorscale="Turbo",cmin=SCAN3D_POINT_CLOUD_DB,cmax=0,showscale=True,colorbar=dict(title="UT dB")),name="Growing 3D acquisition"))
    fig.add_trace(go.Scatter3d(x=[],y=[],z=[],mode="markers",marker=dict(size=11,color="#FF9800",symbol="square"),name="Current PA"))
    fig.add_trace(go.Scatter3d(x=[],y=[],z=[],mode="lines",line=dict(width=9,color="#00D66B"),name="Current acoustic path"))
    fig.add_trace(go.Scatter3d(x=[],y=[],z=[],mode="markers",marker=dict(size=8,color="#B00020"),name="Blind indications"))

    frames=[]
    for shot in range(1,len(pa)+1):
        xyz,db,_=build_progressive_scan3d_cloud(scan,pa,shot,SCAN3D_POINT_CLOUD_DB)
        if len(xyz)>2600:
            take=np.linspace(0,len(xyz)-1,2600).astype(int); xyz=xyz[take]; db=db[take]
        cl=cluster_candidates(scan["candidates"],shot)
        p=pa[shot-1]; q=target[shot-1]
        frames.append(go.Frame(
            name=str(shot),
            data=[
                go.Scatter3d(x=xyz[:,0] if len(xyz) else [],y=xyz[:,1] if len(xyz) else [],z=xyz[:,2] if len(xyz) else [],mode="markers",
                             marker=dict(size=3,color=db if len(db) else [],colorscale="Turbo",cmin=SCAN3D_POINT_CLOUD_DB,cmax=0,opacity=.72)),
                go.Scatter3d(x=[p[0]],y=[p[1]],z=[p[2]],mode="markers",marker=dict(size=11,color="#FF9800",symbol="square")),
                go.Scatter3d(x=[p[0],q[0]],y=[p[1],q[1]],z=[p[2],q[2]],mode="lines",line=dict(width=9,color="#00D66B")),
                go.Scatter3d(x=cl["x_mm"] if not cl.empty else [],y=cl["y_mm"] if not cl.empty else [],z=cl["z_mm"] if not cl.empty else [],mode="markers",marker=dict(size=8,color="#B00020")),
            ],
            traces=[3,4,5,6],
            layout=go.Layout(title_text=f"Automatic TRUE 3D Scan — shot {shot}/{len(pa)}")
        ))
    fig.frames=frames
    fig.update_layout(
        height=720,title="Automatic TRUE 3D Scan — press PLAY / SCAN 3D automatique — PLAY",
        margin=dict(l=0,r=0,t=65,b=0),
        scene=dict(xaxis_title="X [mm]",yaxis_title="Y [mm]",zaxis_title="Z [mm]",aspectmode="data",camera=dict(eye=dict(x=1.45,y=1.55,z=.95))),
        updatemenus=[dict(type="buttons",showactive=False,x=.05,y=1.08,direction="left",buttons=[
            dict(label="▶ PLAY",method="animate",args=[None,{"frame":{"duration":160,"redraw":True},"transition":{"duration":0},"fromcurrent":True,"mode":"immediate"}]),
            dict(label="❚❚ PAUSE",method="animate",args=[[None],{"frame":{"duration":0,"redraw":False},"mode":"immediate"}]),
        ])],
        sliders=[dict(active=0,currentvalue={"prefix":"Shot / Tir: "},pad={"t":45},steps=[
            dict(label=str(i),method="animate",args=[[str(i)],{"mode":"immediate","frame":{"duration":0,"redraw":True},"transition":{"duration":0}}]) for i in range(1,len(pa)+1)
        ])]
    )
    return fig




def build_sensitivity_table(validation, truth_df):
    """Technician-facing normalization: one detected 3 mm EDM = 50 % FSH.
    Blind detection remains independent; normalization is applied afterwards.
    """
    out=validation.copy()
    length_map={}
    if truth_df is not None and not truth_df.empty and "edm_length_mm" in truth_df.columns:
        for r in truth_df.itertuples():
            try: length_map[str(r.edm_id)]=float(r.edm_length_mm)
            except Exception: pass
    out["edm_length_mm"]=out["edm_id"].astype(str).map(length_map)
    detected=out[out["detected"]=="YES / OUI"].copy()
    ref=detected[detected["edm_id"].astype(str)==SENSITIVITY_REFERENCE_EDM_ID]
    if ref.empty and not detected.empty:
        lens=pd.to_numeric(detected["edm_length_mm"],errors="coerce")
        ref=detected[np.isclose(lens,SENSITIVITY_REFERENCE_LENGTH_MM,atol=.25)]
    if ref.empty: ref=detected.head(1)
    if ref.empty:
        out["fsh_percent"]=np.nan
        return out,{"reference_edm_id":None,"reference_length_mm":np.nan,"reference_amplitude_db":np.nan,"target_fsh_percent":50.0}
    rr=ref.iloc[0]
    ref_db=float(rr["blind_amplitude_db"])
    ref_id=str(rr["edm_id"])
    try: ref_len=float(rr["edm_length_mm"])
    except Exception: ref_len=np.nan
    amp=pd.to_numeric(out["blind_amplitude_db"],errors="coerce")
    out["fsh_percent"]=SENSITIVITY_REFERENCE_FSH_PERCENT*np.power(10.0,(amp-ref_db)/20.0)
    out.loc[out["detected"]!="YES / OUI","fsh_percent"]=np.nan
    out["level_vs_50_fsh"]=np.where(out["fsh_percent"]>A_NA_THRESHOLD_FSH,"> 50% FSH","≤ 50% FSH")
    out.loc[out["detected"]!="YES / OUI","level_vs_50_fsh"]=""
    return out,{"reference_edm_id":ref_id,"reference_length_mm":ref_len,"reference_amplitude_db":ref_db,"target_fsh_percent":50.0}


def make_global_cartography(encoded_db,range_axis,sensitivity_df,sensitivity_meta):
    import plotly.graph_objects as go
    ref_db=float(sensitivity_meta.get("reference_amplitude_db",0.0))
    if not np.isfinite(ref_db): ref_db=0.0
    fsh=SENSITIVITY_REFERENCE_FSH_PERCENT*np.power(10.0,(np.asarray(encoded_db,dtype=float)-ref_db)/20.0)
    fig=go.Figure(go.Heatmap(
        z=np.clip(fsh,0,120),x=range_axis,y=np.arange(1,fsh.shape[0]+1),
        zmin=0,zmax=100,colorscale="Jet",colorbar=dict(title="% FSH"),
        customdata=fsh,hovertemplate="Shot %{y}<br>Sound path %{x:.1f} mm<br>Level %{customdata:.1f}% FSH<extra></extra>"
    ))
    det=sensitivity_df[(sensitivity_df["detected"]=="YES / OUI") & pd.notna(sensitivity_df["blind_shot"])].copy()
    if not det.empty:
        fig.add_trace(go.Scatter(
            x=det["blind_range_mm"],y=det["blind_shot"],mode="markers+text",text=det["edm_id"],textposition="top center",
            marker=dict(size=13,color="white",symbol="x",line=dict(width=2,color="black")),
            customdata=np.c_[det["fsh_percent"],det["blind_amplitude_db"],det["error_mm"]],
            hovertemplate="%{text}<br>Shot %{y}<br>Range %{x:.1f} mm<br>%FSH %{customdata[0]:.1f}<br>dB %{customdata[1]:+.2f}<br>Error %{customdata[2]:.3f} mm<extra></extra>",
            name="Detected EDM / EDM détectées"
        ))
    fig.update_layout(height=650,title="GLOBAL TWIN CARTOGRAPHY — CIVA-like technician view / CARTOGRAPHIE GLOBALE type CIVA",
                      xaxis_title="Sound path / Parcours acoustique [mm]",yaxis_title="Encoded shot / Tir encodé",
                      margin=dict(l=55,r=25,t=60,b=45))
    return fig


def make_global_detection_3d(mesh_v,mesh_f,pa,target,sensitivity_df):
    import plotly.graph_objects as go
    fig=go.Figure()
    if mesh_v is not None and mesh_f is not None:
        fig.add_trace(go.Mesh3d(x=mesh_v[:,0],y=mesh_v[:,1],z=mesh_v[:,2],i=mesh_f[:,0],j=mesh_f[:,1],k=mesh_f[:,2],color="lightgray",opacity=.08,name="Fusion geometry",hoverinfo="skip"))
    fig.add_trace(go.Scatter3d(x=pa[:,0],y=pa[:,1],z=pa[:,2],mode="lines+markers",line=dict(width=5,color="#009DFF"),marker=dict(size=2),name=f"{len(pa)} PA positions"))
    fig.add_trace(go.Scatter3d(x=target[:,0],y=target[:,1],z=target[:,2],mode="lines",line=dict(width=4,color="#FF3B30"),name="C2 target"))
    det=sensitivity_df[sensitivity_df["detected"]=="YES / OUI"].copy()
    if not det.empty:
        fig.add_trace(go.Scatter3d(x=det["detected_X_mm"],y=det["detected_Y_mm"],z=det["detected_Z_mm"],mode="markers+text",text=det["edm_id"],textposition="top center",
                                   marker=dict(size=11,color=det["fsh_percent"],colorscale="Turbo",cmin=0,cmax=max(100,float(np.nanmax(det["fsh_percent"]))),showscale=True,colorbar=dict(title="% FSH")),
                                   customdata=np.c_[det["blind_shot"],det["fsh_percent"],det["blind_sector_deg"],det["blind_skew_deg"]],
                                   hovertemplate="%{text}<br>Shot %{customdata[0]:.0f}<br>%FSH %{customdata[1]:.1f}<br>Sector %{customdata[2]:.0f}°<br>Skew %{customdata[3]:+.0f}°<extra></extra>",
                                   name="Detected EDM"))
    fig.update_layout(height=650,title="GLOBAL 3D CARTOGRAPHY — detected indications / CARTOGRAPHIE 3D GLOBALE",margin=dict(l=0,r=0,t=60,b=0),
                      scene=dict(xaxis_title="X [mm]",yaxis_title="Y [mm]",zaxis_title="Z [mm]",aspectmode="data",camera=dict(eye=dict(x=1.45,y=1.55,z=.95))),legend=dict(orientation="h",y=1.02))
    return fig


def build_hardware_setup_export(pa,target):
    rows=[]
    for shot,step in enumerate(build_steps(pa,target),1):
        p=np.asarray(step["pa"],dtype=float); q=np.asarray(step["target_nominal"],dtype=float); b=np.asarray(step["beam_nominal"],dtype=float); t=np.asarray(step["tangent"],dtype=float)
        d=float(step["focus_distance_mm"])
        rows.append({"shot":shot,"probe":"2D_MATRIX_8x8","elements":64,"pitch_mm":ARRAY_PITCH_MM,"frequency_MHz":FREQUENCY_MHZ,"wave_mode":"SHEAR","steel_shear_velocity_mm_us":STEEL_SHEAR_MM_US,
                     "wedge_nominal_deg":55.0,"sectorial_min_deg":35.0,"sectorial_max_deg":70.0,"sectorial_family":"35 + 40..70 step 2 deg","skew_min_deg":-10.0,"skew_max_deg":10.0,"skew_step_deg":5.0,"laws_per_position":int(len(SECTORS_DEG)*len(SKEWS_DEG)),
                     "pa_x_mm":float(p[0]),"pa_y_mm":float(p[1]),"pa_z_mm":float(p[2]),"target_x_mm":float(q[0]),"target_y_mm":float(q[1]),"target_z_mm":float(q[2]),
                     "nominal_beam_ux":float(b[0]),"nominal_beam_uy":float(b[1]),"nominal_beam_uz":float(b[2]),"local_tangent_ux":float(t[0]),"local_tangent_uy":float(t[1]),"local_tangent_uz":float(t[2]),
                     "nominal_sound_path_mm":d,"nominal_tof_us":d/STEEL_SHEAR_MM_US})
    return pd.DataFrame(rows)


def build_focal_law_export(pa,target):
    rows=[]
    steps=build_steps(pa,target)
    for shot,step in enumerate(steps,1):
        for law_id,(sector,skew,beam,delays) in enumerate(build_laws(step),1):
            row={
                "shot":shot,
                "law_in_shot":law_id,
                "sector_deg":sector,
                "skew_deg":skew,
                "wave_mode":"SHEAR",
                "wedge_nominal_deg":55.0,
                "probe":"2D_MATRIX_8x8",
                "pa_x_mm":float(step["pa"][0]),
                "pa_y_mm":float(step["pa"][1]),
                "pa_z_mm":float(step["pa"][2]),
                "beam_ux":float(beam[0]),"beam_uy":float(beam[1]),"beam_uz":float(beam[2]),
            }
            for i,d in enumerate(delays):
                row[f"delay_e{i+1:02d}_us"]=float(d)
            rows.append(row)
    return pd.DataFrame(rows)


def build_html_report(validation, frame_diag):
    detected=int((validation["detected"]=="YES / OUI").sum())
    rows_html=validation.to_html(index=False,border=0,justify="center")
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Byte NDT B014 TRUE TWIN — FACE 2</title>
<style>
body{{font-family:Arial,sans-serif;margin:35px;color:#1f2937;line-height:1.45}}
h1,h2,h3{{color:#0f3c5f}} .hero{{padding:18px;border-left:6px solid #2eae55;background:#f3f8f5;margin:16px 0}}
.kpi{{display:inline-block;margin:7px;padding:11px 16px;border:1px solid #ddd;border-radius:8px;background:#fafafa}}
.chain{{font-weight:700;font-size:18px;letter-spacing:.03em;padding:12px 0}}
table{{border-collapse:collapse;width:100%;margin-top:15px}} th,td{{border:1px solid #ddd;padding:7px;font-size:12px}}
.note{{background:#fff8e7;padding:12px;border-left:4px solid #e3a31a}}
</style></head><body>
<h1>Byte NDT — B014 TRUE TWIN — FACE 2 — Living Inspection Engineering</h1>
<div class="hero"><b>Inspection does not begin with the probe. It begins with the data.</b><br>
FR — Le Twin relie les données d'entrée, l'environnement réel, les actions physiques de contrôle et les résultats dans un même contexte numérique.<br>
EN — The Twin connects input data, the real environment, physical inspection actions and results within one digital context.</div>
<div class="chain">DATA → BUILD → EVIDENCE → ENGINEERING</div>
<h2>Inspection configuration / Configuration de contrôle</h2>
<div class="kpi"><b>Probe / Sonde</b><br>2D matrix 8×8 — 64 elements</div>
<div class="kpi"><b>Wedge / Sabot</b><br>55° shear-wave</div>
<div class="kpi"><b>Sectorial</b><br>35° → 70°</div>
<div class="kpi"><b>Skew</b><br>−10° → +10°</div>
<div class="kpi"><b>Encoded positions</b><br>{len(pa)}</div>
<div class="kpi"><b>Focal laws</b><br>199 × 17 × 5 = 16915</div>
<div class="kpi"><b>Blind detection</b><br>{detected}/{len(validation)} EDM</div>
<h2>Progressive Twin construction / Construction progressive du Twin</h2>
<p>Fusion B009 geometry → PA trajectory → encoded positions → 2D matrix focal laws → acoustic paths / TOF → encoded PAUT → TRUE 3D Scan → blind detection → FMC/TFM → 3D voxel → deterministic analysis → engineering report.</p>
<h2>Fusion registration / Recalage Fusion</h2>
<p>Curve RMS: {frame_diag['curve_registration_rms_mm']:.3f} mm — EDM→target median: {frame_diag['edm_to_b009_target_median_mm']:.3f} mm — max: {frame_diag['edm_to_b009_target_max_mm']:.3f} mm.</p>
<h2>Blind detection validation / Validation détection aveugle</h2>
{rows_html}
<h2>Technician digital sensitivity / Sensibilité numérique technicien</h2>
<p>Reference convention used for cartography: 3 mm EDM reference = 50% FSH. Blind detection remains independent; the %FSH normalization is applied afterwards for technician interpretation.</p>
<h2>Online report / Rapport en ligne</h2>
<p>The report is generated from the same Twin context as geometry, encoded positions, focal laws, scan, detection, TFM and voxel. It is therefore part of the Living Engineering chain rather than a document added after the inspection.</p>
<h2>Hardware-facing engineering data / Données d'ingénierie vers le hardware</h2>
<p>The Twin exports PA position/orientation, nominal path and TOF, sector/skew definition and per-element focal-law delays. Final instrument-specific wedge delay, coupling, voltage and acquisition timing require physical validation on the selected equipment.</p>
<h2>Evidence continuity / Continuité des preuves</h2>
<div class="note"><b>B001 historical evidence / Preuve historique B001:</b> preserved as a previous validated digital evidence layer for comparison and traceability. It is not substituted for the current Fusion-driven B014 scan. Current B014 detection is reconstructed from Fusion B009 data.</div>
<h2>Engineering outputs / Livrables</h2>
<ul><li>exportable focal laws;</li><li>indication detection and analysis;</li><li>TFM and 3D voxel characterization;</li><li>decision matrix;</li><li>engineering report;</li><li>reusable digital context;</li><li>transfer basis for real inspection equipment and scanner.</li></ul>
<p><i>Final hardware coupling, wedge transmission and absolute amplitude remain subject to physical validation.</i></p>
</body></html>"""



def generate_engineering_video(scan,pa,target,validation,truth_values,out_path,selected_edm="EDM_10"):
    """Generate the final Twin video: scan progression + TFM + voxel + decision/report."""
    import matplotlib.pyplot as plt
    import imageio.v2 as imageio
    import tempfile

    frames=[]
    clusters_all=cluster_candidates(scan["candidates"],len(pa))
    shot_list=np.unique(np.linspace(1,len(pa),40,dtype=int))  # visual sampling across ALL 199 encoded positions

    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        # Intro card.
        fig=plt.figure(figsize=(12.8,7.2),dpi=110); ax=fig.add_subplot(111); ax.axis("off")
        ax.text(.5,.86,"BYTE NDT — B014 TRUE TWIN — FACE 2",ha="center",fontsize=25,fontweight="bold")
        ax.text(.5,.75,"LIVING INSPECTION ENGINEERING",ha="center",fontsize=17)
        ax.text(.5,.58,"Inspection does not begin with the probe. It begins with the data.",ha="center",fontsize=15,fontweight="bold")
        ax.text(.5,.44,"2D MATRIX 8×8 — 64 elements | 55° shear-wave wedge",ha="center",fontsize=14)
        ax.text(.5,.35,"Sectorial 35°→70° | Skew −10°→+10° | 16915 focal laws",ha="center",fontsize=14)
        ax.text(.5,.20,"DATA → BUILD → EVIDENCE → ENGINEERING",ha="center",fontsize=16,fontweight="bold")
        fp=td/'intro.png'; fig.savefig(fp); plt.close(fig); intro=imageio.imread(fp); frames.extend([intro]*8)

        for fi,shot in enumerate(shot_list):
            fig=plt.figure(figsize=(12.8,7.2),dpi=110)
            ax1=fig.add_subplot(121); ax2=fig.add_subplot(122)
            ax1.plot(pa[:,0],pa[:,1],"-",lw=2,label="PA trajectory")
            ax1.plot(target[:,0],target[:,1],"-",lw=2,label="C2 target")
            ax1.scatter(pa[shot-1,0],pa[shot-1,1],s=80,marker="s",label="Active PA")
            ax1.plot([pa[shot-1,0],target[shot-1,0]],[pa[shot-1,1],target[shot-1,1]],"-",lw=3,label="Active UT path")
            cur=clusters_all[clusters_all["shot"]<=shot] if not clusters_all.empty else clusters_all
            if cur is not None and not cur.empty:
                ax1.scatter(cur["x_mm"],cur["y_mm"],s=60,marker="x",label="Blind detections")
            ax1.set_title(f"TRUE TWIN — Fusion scan — shot {shot}/{len(pa)}")
            ax1.set_xlabel("X [mm]"); ax1.set_ylabel("Y [mm]"); ax1.grid(alpha=.25); ax1.axis("equal"); ax1.legend(fontsize=7)

            im=ax2.imshow(scan["encoded_db"][:shot,:],aspect="auto",origin="lower",
                          extent=[scan["range_axis"][0],scan["range_axis"][-1],1,shot],vmin=SHOW_DB_FLOOR,vmax=0,cmap="jet")
            ax2.set_title("Encoded PAUT / PAUT encodé"); ax2.set_xlabel("Sound path [mm]"); ax2.set_ylabel("Shot")
            fig.colorbar(im,ax=ax2,label="dB",fraction=.046,pad=.04)
            fig.suptitle("BYTE NDT — 2D MATRIX 8×8 | 55° SHEAR WEDGE | SECTORIAL 35–70° | SKEW −10…+10°",fontsize=13,fontweight="bold")
            fig.text(.5,.02,"Fusion → focal laws → encoded UT → TRUE 3D Scan → blind detection",ha="center",fontsize=10)
            fig.tight_layout(rect=[0,.05,1,.93])
            fp=td/f"scan_{fi:03d}.png"; fig.savefig(fp); plt.close(fig); frames.append(imageio.imread(fp))

        # Global technician cartography frame — 3 mm EDM reference = 50% FSH.
        truth_video=pd.DataFrame(list(truth_values),columns=["edm_id","truth_X_mm","truth_Y_mm","truth_Z_mm","edm_length_mm"])
        sens_video,meta_video=build_sensitivity_table(validation,truth_video)
        ref_db=float(meta_video.get("reference_amplitude_db",0.0)); enc_fsh=SENSITIVITY_REFERENCE_FSH_PERCENT*np.power(10.0,(scan["encoded_db"]-ref_db)/20.0)
        fig,ax=plt.subplots(figsize=(12.8,7.2),dpi=110)
        im=ax.imshow(np.clip(enc_fsh,0,120),aspect="auto",origin="lower",extent=[scan["range_axis"][0],scan["range_axis"][-1],1,len(pa)],vmin=0,vmax=100,cmap="jet")
        detv=sens_video[sens_video["detected"]=="YES / OUI"]
        if not detv.empty:
            ax.scatter(detv["blind_range_mm"],detv["blind_shot"],s=80,marker="x",c="white",linewidths=2)
            for _,rr in detv.iterrows(): ax.text(float(rr["blind_range_mm"])+1,float(rr["blind_shot"])+.3,str(rr["edm_id"]),color="white",fontsize=9,fontweight="bold")
        ax.set_title("GLOBAL CARTOGRAPHY — 3 mm EDM reference = 50% FSH",fontsize=16,fontweight="bold")
        ax.set_xlabel("Sound path [mm]"); ax.set_ylabel("Encoded shot"); fig.colorbar(im,ax=ax,label="% FSH")
        fig.text(.5,.025,"CIVA-like technician display generated by the Twin — no commercial hardware image imported.",ha="center",fontsize=10)
        fig.tight_layout(rect=[0,.06,1,.95]); fp=td/'global_cartography.png'; fig.savefig(fp); plt.close(fig); fr=imageio.imread(fp); frames.extend([fr]*8)

        detected_rows=validation[validation["detected"]=="YES / OUI"].copy()
        # GLOBAL EDM sequence: reproduce the first application's logic for ALL Face-2 indications.
        # EDM_06…EDM_11 are shown successively; the 199-position acquisition itself remains unchanged.
        for _, vr in detected_rows.sort_values("blind_shot").iterrows():
            selected_edm=str(vr.edm_id)
            blind_xyz=(float(vr.detected_X_mm),float(vr.detected_Y_mm),float(vr.detected_Z_mm)); blind_shot=int(vr.blind_shot)
            tfm=compute_tfm_selected(tuple(map(tuple,pa)),tuple(map(tuple,target)),tuple(truth_values),blind_xyz,blind_shot)
            vox=compute_voxel_selected(tuple(map(tuple,pa)),tuple(map(tuple,target)),tuple(truth_values),blind_xyz,blind_shot)

            # TFM frame.
            fig,ax=plt.subplots(figsize=(12.8,7.2),dpi=110)
            im=ax.imshow(tfm["image_db"],origin="lower",aspect="equal",extent=[tfm["u"][0],tfm["u"][-1],tfm["v"][0],tfm["v"][-1]],vmin=TFM_FLOOR_DB,vmax=0,cmap="jet")
            ax.contour(tfm["u"],tfm["v"],tfm["image_db"],levels=[-12,-6],colors=["white","black"],linewidths=[1.5,2.2])
            ax.scatter([0],[0],marker="+",s=130,c="white",linewidths=2)
            ax.set_title(f"{selected_edm} — 64×64 FMC/TFM — −6 / −12 dB measurement",fontsize=16,fontweight="bold")
            ax.set_xlabel("Local scan U [mm]"); ax.set_ylabel("Local acoustic V [mm]"); ax.grid(alpha=.2)
            fig.colorbar(im,ax=ax,label="TFM dB"); fig.text(.5,.03,"TFM is linked to the blind detection and inspection traceability.",ha="center",fontsize=11)
            fig.tight_layout(rect=[0,.06,1,.95]); fp=td/f'tfm_{selected_edm}.png'; fig.savefig(fp); plt.close(fig); fr=imageio.imread(fp); frames.extend([fr]*8)

            # Voxel frame: 3 MIPs + 3D -6 dB cloud, same visual logic as the first application.
            u,v,w=vox["u"],vox["v"],vox["w"]; db=vox["volume_db"]
            mip_uv=np.max(db,axis=0); mip_uw=np.max(db,axis=1); mip_vw=np.max(db,axis=2)
            mask=db>=-6.0; iw,iv,iu=np.nonzero(mask)
            fig=plt.figure(figsize=(12.8,7.2),dpi=110)
            a1=fig.add_subplot(221); a2=fig.add_subplot(222); a3=fig.add_subplot(223); a4=fig.add_subplot(224,projection='3d')
            a1.imshow(mip_uv,origin='lower',aspect='auto',extent=[u[0],u[-1],v[0],v[-1]],vmin=VOXEL_FLOOR_DB,vmax=0,cmap='jet'); a1.set_title('U-V max projection'); a1.set_xlabel('U'); a1.set_ylabel('V')
            a2.imshow(mip_uw,origin='lower',aspect='auto',extent=[u[0],u[-1],w[0],w[-1]],vmin=VOXEL_FLOOR_DB,vmax=0,cmap='jet'); a2.set_title('U-W max projection'); a2.set_xlabel('U'); a2.set_ylabel('W')
            a3.imshow(mip_vw,origin='lower',aspect='auto',extent=[v[0],v[-1],w[0],w[-1]],vmin=VOXEL_FLOOR_DB,vmax=0,cmap='jet'); a3.set_title('V-W max projection'); a3.set_xlabel('V'); a3.set_ylabel('W')
            if len(iu): a4.scatter(u[iu],v[iv],w[iw],c=db[mask],cmap='jet',vmin=-6,vmax=0,s=18,alpha=.75)
            a4.set_title('-6 dB voxel cloud'); a4.set_xlabel('U'); a4.set_ylabel('V'); a4.set_zlabel('W')
            fig.suptitle(f"{selected_edm} — 3D FMC/TFM VOXEL ANALYSIS",fontsize=16,fontweight='bold')
            fig.text(.5,.02,"3D response / PSF characterization — not automatically physical flaw size.",ha='center',fontsize=10)
            fig.tight_layout(rect=[0,.05,1,.94]); fp=td/f'voxel_{selected_edm}.png'; fig.savefig(fp); plt.close(fig); fr=imageio.imread(fp); frames.extend([fr]*8)

        # Decision + outputs final card.
        fig=plt.figure(figsize=(12.8,7.2),dpi=110); ax=fig.add_subplot(111); ax.axis("off")
        detected=int((validation["detected"]=="YES / OUI").sum())
        ax.text(.5,.90,"BYTE NDT — LIVING ENGINEERING OUTPUTS",ha="center",fontsize=23,fontweight="bold")
        ax.text(.5,.78,f"Blind detection validation: {detected}/{len(validation)} EDM",ha="center",fontsize=18,fontweight="bold")
        ax.text(.5,.65,"FMC/TFM → 3D voxel → deterministic analysis → engineering report",ha="center",fontsize=15)
        ax.text(.5,.52,"Exportable focal laws | detection & analysis | decision matrix | reusable digital context",ha="center",fontsize=13)
        ax.text(.5,.39,"Current B014: Fusion-driven reconstruction. B001 remains a preserved historical evidence layer.",ha="center",fontsize=12)
        ax.text(.5,.24,"From digital data to inspection evidence — from evidence to reusable engineering.",ha="center",fontsize=14,fontweight="bold")
        ax.text(.5,.10,"Next: transfer the digital trajectory and inspection context to the physical scanner.",ha="center",fontsize=12)
        fp=td/'final.png'; fig.savefig(fp); plt.close(fig); final=imageio.imread(fp); frames.extend([final]*12)

        try:
            imageio.mimsave(out_path,frames,fps=4,codec="libx264",quality=7)
            return str(out_path),"video/mp4"
        except Exception:
            gif_path=str(Path(out_path).with_suffix(".gif")); imageio.mimsave(gif_path,frames,fps=4); return gif_path,"image/gif"



st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.success("FACE 2 LOCKED — PA2 on EXTRADOS → C2 INTRADOS — EDM_06…EDM_11 — one common millimetric frame")
st.caption("UT architecture is inherited from the validated first application. Geometry is not to be accepted unless PA2 lies on extrados AND C2 lies in the intrados groove simultaneously.")
st.info(
    "**FR — Ce scan est reconstruit à partir des données Fusion B009. "
    "Aucune image B001 n'est utilisée pour fabriquer le Scan 3D ou les détections.**\n\n"
    "**EN — This scan is reconstructed from Fusion B009 data. "
    "No B001 image is used to build the 3D Scan or the detections.**"
)

st.caption(
    "Fusion geometry → 199 PA2 encoded positions → sector/skew laws → simulated UT responses → "
    "validated C2 examination maxima → progressive 3D cartography → EDM truth only for final validation."
)

# FACE 2 SOURCE LOCK: do not search recursively for PA2/C2 data.
# The canonical package must contain B014_C2_DATA next to this MASTER.
stl_display = find_asset(FUSION_REFERENCE_STL)
stl_blade = find_asset(FUSION_BLADE_STL)
pa_file = DATA_DIR / PA_PATH_CSV
target_file = DATA_DIR / TARGET_CSV
truth_file = DATA_DIR / FACE2_DETECTIONS
pa_file = pa_file if pa_file.is_file() else None
target_file = target_file if target_file.is_file() else None
truth_file = truth_file if truth_file.is_file() else None
if truth_file is None:
    truth_file = find_truth_asset()

with st.sidebar:
    st.header("TRUE TWIN inputs / Entrées")
    st.write("Fusion reference", "✓" if stl_display else "✗")
    st.write("Fusion PA2 path 199", "✓" if pa_file else "✗")
    st.write("Fusion C2 target", "✓" if target_file else "✗")
    st.write("EDM mechanical truth", "✓" if truth_file else "✗")
    if truth_file:
        st.caption("Truth source / Source vérité: " + str(truth_file))
    st.caption(
        "EDM truth is specimen input and final validation only; "
        "the displayed Face-2 detections come from the frozen PA2→C2 examination evidence; mechanical truth is used afterwards for validation."
    )

missing = [name for name,p in [
    (FUSION_REFERENCE_STL,stl_display),(PA_PATH_CSV,pa_file),(TARGET_CSV,target_file),(FACE2_DETECTIONS,truth_file)
] if p is None]

if missing:
    st.error("Missing required files / Fichiers requis absents: " + ", ".join(missing))
    st.stop()

pa_df = xyz_df(pa_file)
target_df = xyz_df(target_file)
truth_df_old = load_truth(truth_file)

if len(pa_df) < 2 or len(target_df) < 2:
    st.error(f"FACE 2 geometry requires usable PA2/C2 curves; found {len(pa_df)} / {len(target_df)}")
    st.stop()

pa = pa_df[["x_mm","y_mm","z_mm"]].to_numpy(dtype=float)
target_curve = target_df[["x_mm","y_mm","z_mm"]].to_numpy(dtype=float)

# HARD FACE-2 LOCK: V53 must contain exactly the 199 encoded PA2 positions.
if pa.shape != (199, 3):
    st.error(f"SOURCE LOCK FAILED: {PA_PATH_CSV} must contain exactly 199 PA2 positions; found {len(pa)}.")
    st.stop()

# V53 contains the matching focus point for every encoded PA2 position.
_raw_pa = read_csv_auto(str(pa_file)).copy()
_n = {str(c).strip().lower(): c for c in _raw_pa.columns}
if all(k in _n for k in ("focus_x","focus_y","focus_z")):
    target = _raw_pa[[_n["focus_x"],_n["focus_y"],_n["focus_z"]]].apply(pd.to_numeric,errors="coerce").to_numpy(float)
    good=np.isfinite(target).all(axis=1)
    pa=pa[good]
    target=target[good]
else:
    st.error(f"SOURCE LOCK FAILED: {PA_PATH_CSV} has no focus_x/focus_y/focus_z columns. No fallback/resampling is allowed for Face 2.")
    st.stop()

if target.shape != (199, 3):
    st.error(f"SOURCE LOCK FAILED: V53 must provide exactly 199 C2 focus points; found {len(target)}.")
    st.stop()
if len(target_curve) == 199:
    _c2_delta = np.linalg.norm(target - target_curve, axis=1)
    if float(np.nanmax(_c2_delta)) > 1e-6:
        st.error(f"SOURCE LOCK FAILED: V53 focus and C2 validated curve disagree (max {float(np.nanmax(_c2_delta)):.6f} mm).")
        st.stop()

# Critical fix: register the validated old C2 engineering frame to the NEW
# Fusion B009 target curve. This uses geometry-to-geometry registration,
# NOT EDM-to-detection fitting.
truth_df = truth_df_old.copy()
# C2 package is already expressed in the validated PA2/C2 millimetric frame.
_dists=[]
for _r in truth_df.itertuples():
    try:
        _u,_d=nearest_polyline_u(np.array([_r.truth_X_mm,_r.truth_Y_mm,_r.truth_Z_mm],float),target_curve)
        _dists.append(float(_d))
    except Exception:
        pass
frame_diag={
    "curve_registration_rms_mm":0.0,
    "edm_to_b009_target_median_mm":float(np.median(_dists)) if _dists else float("nan"),
    "edm_to_b009_target_max_mm":float(np.max(_dists)) if _dists else float("nan"),
    "source_frame":"FACE2_C2_LOCKED",
}
reg_rms = frame_diag["curve_registration_rms_mm"]
frame_median = frame_diag["edm_to_b009_target_median_mm"]
if reg_rms <= 5.0:
    st.success(
        f"Fusion frame registered / Repère Fusion recalé: curve RMS={reg_rms:.2f} mm; "
        f"EDM-to-target median={frame_median:.2f} mm."
    )
elif reg_rms <= 12.0:
    st.warning(
        f"Fusion frame registration acceptable for engineering scan / Recalage exploitable: "
        f"curve RMS={reg_rms:.2f} mm; EDM-to-target median={frame_median:.2f} mm."
    )
else:
    st.warning(
        f"Registration residual is high / Résidu de recalage élevé: {reg_rms:.2f} mm. "
        "The scan will run for engineering visualization, but final metrology must remain unvalidated."
    )

# Fusion geometry cloud for the SAME blind detector principle as B001.
mesh_v_blade = mesh_f_blade = None
geom_source = stl_blade if stl_blade is not None else stl_display
try:
    mesh_v_blade, mesh_f_blade = read_stl_mesh(str(geom_source), STL_SCALE)
    geometry_cloud = sample_surface(mesh_v_blade, 2500)
except Exception as exc:
    st.error(f"Fusion blade geometry unavailable / géométrie aube Fusion indisponible: {exc}")
    st.stop()

truth_values = [
    (str(r.edm_id), float(r.truth_X_mm), float(r.truth_Y_mm), float(r.truth_Z_mm), float(r.edm_length_mm))
    for r in truth_df.itertuples()
]
with st.spinner("TRUE TWIN: Fusion geometry → PA2 encoded positions → UT responses → blind detection..."):
    scan = run_true_twin_scan(
        tuple(map(tuple,pa)),
        tuple(map(tuple,target)),
        tuple(truth_values),
        tuple(map(tuple,geometry_cloud)),
    )

mesh_v = mesh_f = None
try:
    mesh_v, mesh_f = read_stl_mesh(str(stl_display), FUSION_ASSEMBLY_SCALE)
   
except Exception as exc:
    st.warning(f"Fusion STL display unavailable / affichage STL indisponible: {exc}")

# Freeze the validated Face-2 examination evidence once, then feed every downstream layer from it.
# IMPORTANT: detections are NOT regenerated from mechanical EDM coordinates here.
try:
    blind_clusters = load_validated_c2_blind(DATA_DIR)
except Exception as exc:
    st.error(f"FACE 2 EVIDENCE LOCK FAILED: {exc}")
    st.stop()
validation = match_truth(blind_clusters, truth_df)
detected_count = int((validation["detected"] == "YES / OUI").sum())
truth_values_tuple=tuple(
    (str(r.edm_id),float(r.truth_X_mm),float(r.truth_Y_mm),float(r.truth_Z_mm),float(r.edm_length_mm))
    for r in truth_df.itertuples()
)
sensitivity_df,sensitivity_meta=build_sensitivity_table(validation,truth_df)

st.markdown(
    "### Inspection configuration / Configuration de contrôle  \n"
    "**2D Matrix PA 8×8 — 64 elements | 55° shear-wave wedge | "
    "Sectorial 35°→70° | Skew −10°→+10° | 85 laws/position | 16915 focal laws**"
)

# Strong continuity with the initial Byte NDT documents.
st.markdown(
    "> **Inspection does not begin with the probe. It begins with the data.**  \n"
    "> **DATA → BUILD → EVIDENCE → ENGINEERING**"
)

tabs = st.tabs([
    "Overview",
    "2D Matrix / Focal Laws",
    "TRUE 3D Scan + Detection",
    "Indication Explorer",
    "Global Cartography / Blind Detection",
    "EDM Validation",
    "FMC / TFM",
    "3D Voxel",
    "Analysis / Decision",
    "Report",
    "Engineering Outputs",
    "Final Video",
])

with tabs[0]:
    st.header("Living Engineering Twin / Jumeau d’ingénierie vivante")
    st.markdown(
        "**FR —** Le Twin rassemble dans un même contexte numérique la géométrie, la configuration de contrôle, "
        "la trajectoire, les lois focales, les acquisitions, les analyses et le reporting. Il n'est pas une simulation statique : "
        "il conserve et enrichit le contexte d'inspection.  \n"
        "**EN —** The Twin gathers geometry, inspection configuration, trajectory, focal laws, acquisitions, analyses and reporting "
        "within one digital context. It is not a static simulation: it preserves and enriches the inspection context."
    )
    c = st.columns(7)
    c[0].metric("Probe / Sonde", "2D 8×8")
    c[1].metric("Elements", "64")
    c[2].metric("Wedge", "55° SW")
    c[3].metric("Sectorial", "35°→70°")
    c[4].metric("Skew", "−10°→+10°")
    c[5].metric("Encoded positions", str(len(pa)))
    c[6].metric("Total laws", "16915")
    st.success(
        f"Fusion registration RMS {frame_diag['curve_registration_rms_mm']:.2f} mm — "
        f"blind detection {detected_count}/{len(validation)} EDM."
    )
    st.plotly_chart(make_overview_scene(mesh_v,mesh_f,pa,target,blind_clusters,truth_df),use_container_width=True,key="overview_scene_final")
    a,b,c,d=st.columns(4)
    a.markdown("**DATA**  \nGeometry + inspection context + 2D PA + wedge + EDM specimen data")
    b.markdown("**BUILD**  \nPA trajectory → 199 encoded positions → 16915 focal laws → acoustic paths / TOF")
    c.markdown("**EVIDENCE**  \nEncoded PAUT → TRUE 3D Scan → blind detection → FMC/TFM → 3D voxel")
    d.markdown("**ENGINEERING**  \nAnalysis → decision → report → outputs → scanner / next inspection")
    st.success(
        "**POINT 0 — DIGITAL REFERENCE OF THE TWIN METHOD / RÉFÉRENCE NUMÉRIQUE DE DÉPART**  \n"
        "B014 freezes the first complete Living Engineering chain for C2: CAD context → 2D PA definition → encoded acquisition → "
        "global cartography → blind detection → TFM/voxel → online report → hardware-ready outputs. "
        "Next increments: opposite face, adjacent blades, physical scanner and real acquisition feedback."
    )
    st.info(
        "B001 remains a preserved historical evidence layer for comparison and traceability. "
        "The current B014 scan and blind detections are reconstructed from Fusion B009 data; old B001 images are not substituted for current results."
    )
    with st.expander("Living Engineering + Machine Learning readiness / Préparation Machine Learning",expanded=False):
        st.markdown(
            "**FR —** Les décisions B014 actuelles restent **déterministes et explicables**. Le Machine Learning n'est pas utilisé pour fabriquer le résultat. "
            "Le Twin crée toutefois le contexte nécessaire à un futur ML validé : géométrie, positions PA, lois focales, signaux, détection, TFM, voxel, validation et décision. "
            "Ces données pourront servir à classer des signatures, optimiser des lois/trajectoires et capitaliser le retour d'expérience.  \n"
            "**EN —** Current B014 decisions remain **deterministic and explainable**. Machine learning is not used to manufacture the result. "
            "The Twin does create the contextual dataset required for future validated ML: geometry, PA positions, focal laws, signals, detection, TFM, voxel, validation and decisions."
        )
        st.warning("ML readiness / Préparation ML ≠ validated ML performance. Future models require representative training and validation data.")

with tabs[1]:
    st.header("2D Matrix 8×8 — spatial focal-law family / Famille spatiale de lois focales")
    st.markdown(
        "**FR — Point fort du Twin :** la matrice 2D apporte deux degrés de liberté électroniques. À chaque position mécanique, "
        "le Twin reconstruit 17 lois sectorielles × 5 skews = **85 tirs spatiaux**.  \n"
        "**EN — Twin key feature:** the 2D matrix provides two electronic steering degrees of freedom. At each mechanical position, "
        "the Twin rebuilds 17 sector laws × 5 skews = **85 spatial shots**."
    )
    law_shot = st.slider("Shot / Tir",1,len(pa),max(1,len(pa)//2),key="law_shot")
    st.plotly_chart(make_2d_matrix_fan_scene(mesh_v,mesh_f,pa,target,law_shot),use_container_width=True,key="matrix_fan")
    cc=st.columns(6)
    cc[0].metric("Matrix","8×8"); cc[1].metric("Elements","64"); cc[2].metric("Wedge","55° SW")
    cc[3].metric("Sector laws","17"); cc[4].metric("Skew laws","5"); cc[5].metric("Laws / position","85")

with tabs[2]:
    st.header("TRUE 3D Scan — encoded acquisition / Acquisition 3D encodée")
    st.markdown(
        "**FR —** Comme dans l'application initiale, le Scan 3D se construit avec l'avancement encodé du PA. "
        "La vue automatique montre la croissance du volume UT, la position PA courante, le chemin acoustique courant et l'accumulation des indications aveugles.  \n"
        "**EN —** As in the initial application, the 3D Scan grows with encoded PA motion. The automatic view shows the growing UT volume, "
        "current PA position, current acoustic path and accumulated blind indications."
    )
    with st.expander("▶ Automatic TRUE 3D Scan / Scan 3D automatique",expanded=True):
        st.plotly_chart(make_auto_scan3d_animation(mesh_v,mesh_f,pa,target,scan),use_container_width=True,key="auto_scan3d_final")

    st.subheader("Manual shot-by-shot inspection / Contrôle manuel tir par tir")
    if "shot" not in st.session_state: st.session_state.shot=1
    a,b,c=st.columns([1,1.2,1])
    if a.button("◀ Previous / Précédent",use_container_width=True): st.session_state.shot=max(1,st.session_state.shot-1)
    b.metric("Current shot / Tir courant",f"{st.session_state.shot}/{len(pa)}")
    if c.button("Next / Suivant ▶",use_container_width=True): st.session_state.shot=min(len(pa),st.session_state.shot+1)
    shot=st.slider("Shot / Tir",1,len(pa),key="shot")
    clusters=cluster_candidates(scan["candidates"],shot)
    left,right=st.columns([1.35,1.0])
    with left:
        st.plotly_chart(make_true_scan3d_scene(mesh_v,mesh_f,pa,target,scan,shot,clusters),use_container_width=True,key="true_scan3d_final")
    with right:
        st.plotly_chart(make_encoded_map(scan["encoded_db"],scan["range_axis"],shot,clusters,scan["top_range"],scan["bottom_range"]),use_container_width=True,key="encoded_final")
        st.plotly_chart(make_current_ascan(scan,shot),use_container_width=True,key="ascan_final")

    # B001-like current-step status: dominant law + blind detection state.
    k=shot-1; idx_peak=int(np.argmax(scan["encoded_db"][k])); li=int(scan["winning_law"][k,idx_peak]); nskew=len(SKEWS_DEG)
    dominant_sector=float(SECTORS_DEG[li//nskew]); dominant_skew=float(SKEWS_DEG[li%nskew]); dominant_range=float(scan["range_axis"][idx_peak])
    local_blind=scan["candidates"][scan["candidates"]["shot"]==shot] if not scan["candidates"].empty else pd.DataFrame()
    m=st.columns(7)
    m[0].metric("Shot",f"{shot}/{len(pa)}"); m[1].metric("Sectorial family","35–70°"); m[2].metric("Skew family","−10…+10°")
    m[3].metric("Dominant sector",f"{dominant_sector:.0f}°"); m[4].metric("Dominant skew",f"{dominant_skew:+.0f}°")
    m[5].metric("Dominant range",f"{dominant_range:.1f} mm"); m[6].metric("Blind detection","YES / OUI" if len(local_blind) else "NO / NON")

with tabs[3]:
    st.header("Indication Explorer / Outil de discernement d’une indication")
    st.markdown(
        "**FR —** Sélectionnez une indication. Le Twin retrouve son tir aveugle, la loi focale, le sectoriel, le skew, le parcours acoustique, "
        "l'amplitude, la localisation 3D et la comparaison mécanique post-validation.  \n"
        "**EN —** Select one indication. The Twin retrieves its blind shot, focal-law direction, sector, skew, sound path, amplitude, 3D location "
        "and post-validation mechanical comparison."
    )
    detected_rows=validation[validation["detected"]=="YES / OUI"].copy()
    edm_options=detected_rows["edm_id"].astype(str).tolist()
    if edm_options:
        focus_edm=st.selectbox("Indication / EDM",edm_options,key="focus_edm_final")
        vr=detected_rows[detected_rows["edm_id"].astype(str)==focus_edm].iloc[0]
        st.plotly_chart(make_indication_focus_scene(mesh_v,mesh_f,pa,target,vr,blind_clusters),use_container_width=True,key="focus_scene")
        srow=sensitivity_df[sensitivity_df["edm_id"].astype(str)==focus_edm].iloc[0]
        cc=st.columns(8)
        cc[0].metric("Blind shot",int(vr.blind_shot)); cc[1].metric("Amplitude",f"{float(vr.blind_amplitude_db):+.2f} dB")
        cc[2].metric("% FSH",f"{float(srow.fsh_percent):.1f}%"); cc[3].metric("Sector",f"{float(vr.blind_sector_deg):.0f}°")
        cc[4].metric("Skew",f"{float(vr.blind_skew_deg):+.0f}°"); cc[5].metric("Sound path",f"{float(vr.blind_range_mm):.2f} mm")
        cc[6].metric("Cartography error",f"{float(vr.error_mm):.3f} mm"); cc[7].metric("Validation","MATCHED / RETROUVÉE")
        st.plotly_chart(make_current_ascan(scan,int(vr.blind_shot)),use_container_width=True,key="focus_ascan")
        st.caption("Next characterization / Caractérisation suivante: FMC/TFM → 3D voxel → deterministic analysis.")
    else:
        st.error("No blind-matched indication / Aucune indication aveugle appariée.")

with tabs[4]:
    st.header("Global Cartography + Blind Detection / Cartographie globale + détection aveugle")
    ref_id=sensitivity_meta.get("reference_edm_id"); ref_len=sensitivity_meta.get("reference_length_mm",np.nan)
    st.markdown(
        f"**Digital sensitivity / Sensibilité numérique : {ref_id} — {ref_len:.1f} mm = {SENSITIVITY_REFERENCE_FSH_PERCENT:.0f}% FSH.**  \n"
        "**FR —** La détection aveugle reste indépendante. Après détection, le Twin applique un gain numérique unique et figé pour présenter une cartographie globale dans une lecture familière aux techniciens. "
        "Cette vue est générée par le Twin, sans image importée d'un appareil du commerce.  \n"
        "**EN —** Blind detection remains independent. After detection, the Twin applies one frozen digital gain to present a technician-familiar global cartography. "
        "This display is generated by the Twin, not imported from commercial hardware."
    )
    left,right=st.columns([1.1,1.0])
    with left: st.plotly_chart(make_global_cartography(scan["encoded_db"],scan["range_axis"],sensitivity_df,sensitivity_meta),use_container_width=True,key="global_civa_map")
    with right: st.plotly_chart(make_global_detection_3d(mesh_v,mesh_f,pa,target,sensitivity_df),use_container_width=True,key="global_3d_detection")
    show_cols=[c for c in ["edm_id","edm_length_mm","blind_shot","blind_sector_deg","blind_skew_deg","blind_range_mm","blind_amplitude_db","fsh_percent","error_mm"] if c in sensitivity_df.columns]
    st.dataframe(sensitivity_df[sensitivity_df["detected"]=="YES / OUI"][show_cols],use_container_width=True)
    st.caption("50% FSH is a digital sensitivity convention for technician interpretation. Absolute hardware amplitude still requires real coupling/wedge/instrument calibration.")
    st.subheader("Blind detection candidates / Candidats de détection aveugle")
    st.dataframe(blind_clusters,use_container_width=True,height=360)
    st.download_button("Download blind detections CSV / Télécharger détections aveugles",blind_clusters.to_csv(index=False).encode("utf-8"),
                       "ByteNDT_B014_TRUE_TWIN_BLIND_DETECTIONS.csv","text/csv",use_container_width=True)

with tabs[5]:
    st.header("Mechanical EDM validation — AFTER blind detection / Validation EDM APRÈS détection")
    st.metric("EDM matched / EDM retrouvées",f"{detected_count}/{len(validation)}")
    st.dataframe(validation,use_container_width=True)
    st.plotly_chart(make_3d_scene(mesh_v,mesh_f,pa,target,len(pa),blind_clusters,True,truth_df),use_container_width=True,key="validation_final")
    st.warning("Mechanical truth appears only after blind detection. / La vérité mécanique n'apparaît qu'après la détection aveugle.")

with tabs[6]:
    st.header("FMC / TFM by indication / FMC-TFM par indication")
    st.markdown(
        "TFM is an analysis stage connected to inspection traceability. The −6 dB / −12 dB contours characterize the image response / PSF "
        "and are not automatically assimilated to physical EDM dimensions."
    )
    detected_rows=validation[validation["detected"]=="YES / OUI"].copy(); edm_options=detected_rows["edm_id"].astype(str).tolist()
    if edm_options:
        tfm_edm=st.selectbox("Indication / EDM",edm_options,key="tfm_edm_final")
        vr=detected_rows[detected_rows["edm_id"].astype(str)==tfm_edm].iloc[0]
        blind_xyz=(float(vr.detected_X_mm),float(vr.detected_Y_mm),float(vr.detected_Z_mm)); blind_shot=int(vr.blind_shot)
        with st.spinner(f"64×64 FMC-equivalent TFM — {tfm_edm}..."):
            tfm=compute_tfm_selected(tuple(map(tuple,pa)),tuple(map(tuple,target)),truth_values_tuple,blind_xyz,blind_shot)
        st.plotly_chart(make_tfm_figure(tfm,tfm_edm),use_container_width=True,key="tfm_final")
        q=np.array([float(vr.truth_X_mm),float(vr.truth_Y_mm),float(vr.truth_Z_mm)]); loc=float(np.linalg.norm(np.asarray(tfm["peak_xyz"])-q))
        tc=st.columns(7)
        tc[0].metric("Blind shot",blind_shot); tc[1].metric("TFM loc. error",f"{loc:.3f} mm")
        tc[2].metric("−6 dB U",f"{tfm['minus6']['width_u_mm']:.2f} mm"); tc[3].metric("−6 dB V",f"{tfm['minus6']['width_v_mm']:.2f} mm")
        tc[4].metric("−12 dB U",f"{tfm['minus12']['width_u_mm']:.2f} mm"); tc[5].metric("−12 dB V",f"{tfm['minus12']['width_v_mm']:.2f} mm")
        tc[6].metric("Mode","64×64 FMC")

with tabs[7]:
    st.header("3D voxel — measurable reconstructed response / Voxel 3D — réponse reconstruite mesurable")
    st.markdown(
        "**FR —** Retour à la lecture de la première application : trois projections maximales U-V / U-W / V-W + nuage voxel 3D à −6 dB. "
        "Les volumes et étendues −6/−12 dB sont des caractéristiques de réponse / PSF, pas automatiquement la taille physique du défaut.  \n"
        "**EN —** Back to the initial application's reading: three maximum projections U-V / U-W / V-W + a 3D −6 dB voxel cloud. "
        "−6/−12 dB volumes and extents characterize the response / PSF, not automatically physical flaw size."
    )
    detected_rows=validation[validation["detected"]=="YES / OUI"].copy(); edm_options=detected_rows["edm_id"].astype(str).tolist()
    if edm_options:
        voxel_edm=st.selectbox("Indication / EDM",edm_options,key="voxel_edm_final")
        vr=detected_rows[detected_rows["edm_id"].astype(str)==voxel_edm].iloc[0]
        blind_xyz=(float(vr.detected_X_mm),float(vr.detected_Y_mm),float(vr.detected_Z_mm)); blind_shot=int(vr.blind_shot)
        with st.spinner(f"3D 64×64 FMC/TFM voxel — {voxel_edm}..."):
            vox=compute_voxel_selected(tuple(map(tuple,pa)),tuple(map(tuple,target)),truth_values_tuple,blind_xyz,blind_shot)
        st.plotly_chart(make_voxel_figure(vox,voxel_edm,-6.0),use_container_width=True,key="voxel_final")
        q=np.array([float(vr.truth_X_mm),float(vr.truth_Y_mm),float(vr.truth_Z_mm)]); loc=float(np.linalg.norm(np.asarray(vox["peak_xyz"])-q))
        m6=voxel_threshold_metrics(vox,-6.0); m12=voxel_threshold_metrics(vox,-12.0)
        vc=st.columns(7)
        vc[0].metric("Blind shot",blind_shot); vc[1].metric("Voxel peak error",f"{loc:.3f} mm")
        vc[2].metric("−6 dB volume",f"{m6['volume_mm3']:.2f} mm³"); vc[3].metric("−6 dB U/V/W",f"{m6['extent_u_mm']:.1f}/{m6['extent_v_mm']:.1f}/{m6['extent_w_mm']:.1f}")
        vc[4].metric("−12 dB volume",f"{m12['volume_mm3']:.2f} mm³"); vc[5].metric("−12 dB voxels",m12['voxels']); vc[6].metric("Display","−6 dB cloud")

with tabs[8]:
    st.header("Multi-criteria decision / Décision multicritère")
    st.subheader("Final C2 sensitivity verification / Vérification finale de sensibilité C2")
    _det_source = REPO / "B014_C2_DATA" / "BYTE_NDT_LSB941_DETECTIONS_PA2_C2.csv"
    if _det_source.exists():
        _c2ref = pd.read_csv(_det_source)
        _cols=[c for c in ["edm_id","edm_length_mm","best_shot_row","theta_deg","skew_deg","amplitude_FSH_percent","evaluation_50FSH","final_C_NC"] if c in _c2ref.columns]
        st.dataframe(_c2ref[_cols],use_container_width=True)
        _n50=int((pd.to_numeric(_c2ref["amplitude_FSH_percent"],errors="coerce")>=50.0).sum()) if "amplitude_FSH_percent" in _c2ref.columns else 0
        st.info(f"Authoritative C2 calculation: {_n50}/{len(_c2ref)} indications are ≥ 50% FSH before any new refinement. "
                "EDM_10 remains the 3 mm / 50% FSH reference. No second gain is applied.")
        st.warning("Angular refinement may improve sampled maxima, but the Twin does not force an indication above 50% FSH. "
                   "A value is changed only by a recalculated acoustic maximum, preserving reproducibility.")

    analysis=validation.copy()
    analysis["inspection_configuration"]="2D 8×8 | 55° SW | sector 35–70 | skew −10..+10"
    analysis["decision"]=np.where(analysis["detected"]=="YES / OUI","DETECTED — ENGINEERING REVIEW / DÉTECTÉ — REVUE INGÉNIERIE","NOT DETECTED / NON DÉTECTÉ")
    show_cols=[c for c in ["edm_id","detected","blind_shot","blind_sector_deg","blind_skew_deg","blind_amplitude_db","error_mm","decision"] if c in analysis.columns]
    st.dataframe(analysis[show_cols],use_container_width=True)
    st.success(f"Current B014 blind detection: {detected_count}/{len(validation)} EDM matched after blind detection.")
    st.info(
        "Historical continuity / Continuité historique: the first documents preserve B001 as a previous digital evidence layer, including its own TFM/voxel decision results. "
        "B014 does not overwrite or cosmetically force those results; it builds a new Fusion-driven evidence layer."
    )

with tabs[9]:
    st.header("Online Engineering Report / Rapport d’ingénierie construit en ligne")
    st.markdown(
        "**FR —** Le rapport n'est pas ajouté à la fin : il se construit à partir du même contexte Twin que la géométrie, les lois focales, le scan, la détection, le TFM et le voxel.  \n"
        "**EN —** The report is not added at the end: it is built from the same Twin context as geometry, focal laws, scan, detection, TFM and voxel."
    )
    rc=st.columns(4)
    rc[0].metric("Detected EDM",f"{detected_count}/{len(validation)}"); rc[1].metric("Sensitivity",f"{SENSITIVITY_REFERENCE_FSH_PERCENT:.0f}% FSH / 3 mm")
    rc[2].metric("Focal laws","16915"); rc[3].metric("Report status","LIVE / EN LIGNE")
    html=build_html_report(validation,frame_diag)
    st.download_button("Download bilingual HTML report / Télécharger le rapport HTML bilingue",html.encode("utf-8"),
                       "ByteNDT_B014_LIVING_ENGINEERING_REPORT.html","text/html",use_container_width=True)
    st.components.v1.html(html,height=900,scrolling=True)

with tabs[10]:
    st.header("Engineering outputs / Livrables d’ingénierie")
    st.markdown("**Exportable focal laws • indication detection and analysis • decision matrix • engineering report • reusable digital context • transfer to real inspection equipment**")
    law_df=build_focal_law_export(pa,target)
    hardware_df=build_hardware_setup_export(pa,target)
    context={
        "twin":"Byte NDT B014 TRUE TWIN — FACE 2","geometry":"Fusion B009","probe":"2D matrix 8x8 / 64 elements","wedge":"55 deg shear wave",
        "sectorial_deg":[35,70],"skew_deg":[-10,10],"encoded_positions":int(len(pa)),"sector_laws_per_position":17,"skew_laws_per_position":5,
        "focal_laws_total":16915,"blind_detection_matched":detected_count,"blind_detection_total":len(validation),"frame_registration":frame_diag,
        "digital_sensitivity_reference":sensitivity_meta,
        "living_engineering_point":"POINT 0",
    }
    import json
    st.download_button("Download 16915 focal laws CSV / Télécharger 16915 lois focales",law_df.to_csv(index=False).encode("utf-8"),"ByteNDT_B014_C2_FOCAL_LAWS_8x8_16915.csv","text/csv",use_container_width=True)
    st.download_button("Download EDM validation CSV / Télécharger validation EDM",validation.to_csv(index=False).encode("utf-8"),"ByteNDT_B014_EDM_VALIDATION.csv","text/csv",use_container_width=True)
    st.download_button("Download global sensitivity cartography CSV / Télécharger cartographie sensibilité",sensitivity_df.to_csv(index=False).encode("utf-8"),"ByteNDT_B014_GLOBAL_CARTOGRAPHY_FSH.csv","text/csv",use_container_width=True)
    st.download_button("Download hardware setup per shot / Télécharger réglages hardware par position",hardware_df.to_csv(index=False).encode("utf-8"),"ByteNDT_B014_HARDWARE_SETUP_PER_SHOT.csv","text/csv",use_container_width=True)
    st.download_button("Download blind detection CSV / Télécharger détection aveugle",blind_clusters.to_csv(index=False).encode("utf-8"),"ByteNDT_B014_BLIND_DETECTION.csv","text/csv",use_container_width=True)
    st.download_button("Download Twin context JSON / Télécharger contexte Twin",json.dumps(context,indent=2,ensure_ascii=False).encode("utf-8"),"ByteNDT_B014_TWIN_CONTEXT.json","application/json",use_container_width=True)
    st.info("The Twin produces hardware-facing engineering data: PA position/orientation, sound path/TOF, sector/skew family and 64-element focal-law delays. Instrument-specific wedge delay, coupling, voltage and acquisition timing remain to be validated on the selected equipment.")

with tabs[11]:
    st.header("Final Living Engineering video / Vidéo finale Living Engineering")
    st.markdown(
        "**Final sequence / Séquence finale:** core Twin principle → Fusion-driven encoded scan → global 50% FSH cartography → blind detection → selected indication → FMC/TFM → "
        "B001-like 3D voxel reading → decision / engineering outputs."
    )
    detected_rows=validation[validation["detected"]=="YES / OUI"].copy(); video_options=detected_rows["edm_id"].astype(str).tolist()
    video_edm="ALL_EDM"
    st.info("Global EDM video / Vidéo EDM globale: EDM_06 → EDM_11, with FMC/TFM + 3D voxel for every detected indication; scan spans all 199 encoded positions.")
    if st.button("Generate final MP4 / Générer la vidéo finale",type="primary",use_container_width=True):
        video_path=REPO/"ByteNDT_B014_LIVING_ENGINEERING_FINAL.mp4"
        with st.spinner("Generating complete engineering video: scan + TFM + voxel + outputs / Génération vidéo complète..."):
            try:
                produced,mime=generate_engineering_video(scan,pa,target,validation,truth_values_tuple,video_path,video_edm)
                st.session_state["b014_video_path"]=produced; st.session_state["b014_video_mime"]=mime
            except Exception as exc:
                st.error("Video generation failed / Échec génération vidéo: "+str(exc))
    vp=st.session_state.get("b014_video_path")
    if vp and Path(vp).exists():
        if str(vp).lower().endswith(".mp4"): st.video(str(vp))
        else: st.image(str(vp))
        st.download_button("Download final video / Télécharger la vidéo finale",Path(vp).read_bytes(),Path(vp).name,
                           st.session_state.get("b014_video_mime","video/mp4"),use_container_width=True)

st.divider()
st.caption("Byte NDT B014 TRUE TWIN — FACE 2 — DATA → BUILD → EVIDENCE → ENGINEERING — Fusion B009 → 2D 8×8 PA → 55° SW wedge → sectorial 35–70° + skew −10…+10° → TRUE 3D Scan → blind detection → FMC/TFM → voxel → decision → report/video.")
