"""
Read and write parameters in prm.prm.
All 12 slip-system values are set to the same scalar.
"""

import re
import shutil
from pathlib import Path


def write_params(prm_path, param_values, n_slip=12, refine_factor=None):
    """
    Update slip parameters in prm.prm in-place.
    param_values: {prm_key: scalar_value}
    Auto-backs up original to prm.prm.bak on first call.
    """
    backup = Path(prm_path).with_suffix(".prm.bak")
    if not backup.exists():
        shutil.copy(prm_path, str(backup))

    with open(prm_path) as f:
        lines = f.readlines()

    updated = set()
    new_lines = []
    for line in lines:
        replaced = False

        for key, value in param_values.items():
            pattern = re.compile(
                r"^(\s*set\s+" + re.escape(key) + r"\s*=\s*)(.+)$", re.IGNORECASE
            )
            m = pattern.match(line)
            if m:
                vals_str = ", ".join(str(value) for _ in range(n_slip))
                new_lines.append("{}{}\n".format(m.group(1), vals_str))
                updated.add(key)
                replaced = True
                break

        if not replaced and refine_factor is not None:
            rf_pat = re.compile(r"^(\s*set\s+Refine factor\s*=\s*)(.+)$", re.IGNORECASE)
            m = rf_pat.match(line)
            if m:
                new_lines.append("{}{}\n".format(m.group(1), refine_factor))
                replaced = True

        if not replaced:
            new_lines.append(line)

    missing = set(param_values) - updated
    if missing:
        raise KeyError("Keys not found in prm file: {}".format(missing))

    with open(prm_path, "w") as f:
        f.writelines(new_lines)


def restore_backup(prm_path):
    backup = Path(prm_path).with_suffix(".prm.bak")
    if backup.exists():
        shutil.copy(str(backup), prm_path)
