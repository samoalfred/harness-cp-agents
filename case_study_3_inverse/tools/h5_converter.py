# -*- coding: utf-8 -*-
"""
h5_converter.py
Converts the HDF5 output from microstructure_gen.m into PRISMS-Plasticity
input files: grainID.txt and orientations.txt.
Also updates the voxel dimensions in prm.prm to match the generated grid.
"""

import os
import re
import numpy as np

try:
    import h5py
except ImportError:
    raise ImportError("h5py is required: pip install h5py")

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATLAB_DIR    = os.path.join(BASE_DIR, "matlab")
H5_FILE       = os.path.join(MATLAB_DIR, "input_structure_poly.h5")
GRAIN_ID_FILE = os.path.join(BASE_DIR, "grainID.txt")
ORI_FILE      = os.path.join(BASE_DIR, "orientations.txt")
PRM_FILE      = os.path.join(BASE_DIR, "prm.prm")


def convert_h5_to_prisms(h5_path=H5_FILE):
    """
    Read input_structure_poly.h5 and write grainID.txt + orientations.txt.
    Returns (success, message, info_dict).
    """
    if not os.path.isfile(h5_path):
        return False, "HDF5 file not found: {}".format(h5_path), {}

    print("[H5] Reading: {}".format(h5_path))

    with h5py.File(h5_path, "r") as f:
        pix       = f["/pix"][:]          # shape (Nx*Ny*Nz, 1), int32
        ori_vec   = f["/orientation"][:]  # shape (3*N_grains, 1), float64
        dims      = f["/pix"].attrs["dimensions"]  # [Nx, Ny, Nz]

    Nx, Ny, Nz = int(dims[0]), int(dims[1]), int(dims[2])
    pix = pix.flatten().astype(np.int32)

    N_grains = len(ori_vec.flatten()) // 3
    print("[H5] Grid: {}x{}x{} | Grains: {}".format(Nx, Ny, Nz, N_grains))

    # ── Write grainID.txt ──────────────────────────────────────────
    # PRISMS format: reshape pix (Fortran/column-major from MATLAB) to
    # [Nx, Ny, Nz], then write as (Nx*Ny) x Nz 2D integer array.
    phase_3d = pix.reshape((Nx, Ny, Nz), order="F")   # MATLAB column-major
    phase_2d = phase_3d.reshape((Nx * Ny, Nz), order="C")

    print("[H5] Writing grainID.txt ...")
    with open(GRAIN_ID_FILE, "w") as f:
        f.write("**Total header lines = 5\n")
        f.write("**Grain ID File\n")
        f.write("**3D Volume has dimensions [{} x{} x {}] voxels\n".format(Nx, Ny, Nz))
        f.write("**Data arranged in a 2D array of {} x {} integer values\n".format(Nx * Ny, Nz))
        f.write("**\n")
        for row in phase_2d:
            f.write(" ".join(str(v) for v in row) + "\n")
    print("[H5] grainID.txt written ({} rows x {} cols).".format(Nx * Ny, Nz))

    # ── Write orientations.txt ─────────────────────────────────────
    # Format: grain_id  rx  ry  rz
    ori_flat = ori_vec.flatten()
    ori_mat  = ori_flat.reshape((N_grains, 3), order="C")  # row = [rx, ry, rz]

    print("[H5] Writing orientations.txt ...")
    with open(ORI_FILE, "w") as f:
        f.write("**Grain ID, Rodrigues vector r_x, r_y, r_z\n")
        for i in range(N_grains):
            f.write("{}\t{:.15f}\t{:.15f}\t{:.15f}\n".format(
                i + 1, ori_mat[i, 0], ori_mat[i, 1], ori_mat[i, 2]))
    print("[H5] orientations.txt written ({} grains).".format(N_grains))

    # ── Update prm.prm voxel dimensions ───────────────────────────
    _update_prm(Nx, Ny, Nz)

    info = {"Nx": Nx, "Ny": Ny, "Nz": Nz, "N_grains": N_grains}
    msg  = "Conversion complete: {}x{}x{} grid, {} grains.".format(Nx, Ny, Nz, N_grains)
    return True, msg, info


def _update_prm(Nx, Ny, Nz):
    """Update Voxels in X/Y/Z direction in prm.prm to match the HDF5 grid."""
    if not os.path.isfile(PRM_FILE):
        print("[H5] prm.prm not found — skipping dimension update.")
        return

    with open(PRM_FILE) as f:
        content = f.read()

    def _replace(text, key, value):
        pattern = r"(set {}\s*=\s*)\d+".format(re.escape(key))
        return re.sub(pattern, r"\g<1>{}".format(value), text)

    content = _replace(content, "Voxels in X direction", Nx)
    content = _replace(content, "Voxels in Y direction", Ny)
    content = _replace(content, "Voxels in Z direction", Nz)

    with open(PRM_FILE, "w") as f:
        f.write(content)

    print("[H5] prm.prm updated: Voxels = {}x{}x{}".format(Nx, Ny, Nz))


if __name__ == "__main__":
    ok, msg, info = convert_h5_to_prisms()
    print(msg)
