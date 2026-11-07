# -*- coding: utf-8 -*-

#
# DOYDL's Microsoft Identity Authentication Library — azauthlib
#
# Copyright 2024 DOYDL Technologies.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Build and verify a native standalone app; never publish or modify user storage.

Each platform builds its own bundle. Archives retain macOS framework symlinks
and Linux executable permissions. Code signing/notarization must be completed
before distributing production desktop releases.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]


def native_build_environment():
    env = dict(os.environ)
    if sys.platform == "win32":
        # Qt uses Windows' ICU API. Unrelated tools on PATH may ship a DLL
        # with the same name but incompatible exports; do not freeze that DLL.
        windows = Path(env.get("SystemRoot", r"C:\Windows"))
        env["PATH"] = os.pathsep.join(
            map(
                str,
                (
                    Path(sys.executable).parent,
                    Path(sys.base_prefix),
                    Path(sys.base_prefix) / "DLLs",
                    windows / "System32",
                    windows,
                ),
            )
        )
    for name in (
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QML2_IMPORT_PATH",
        "QML_IMPORT_PATH",
    ):
        env.pop(name, None)
    return env


def verification_environment():
    env = native_build_environment()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.pop("VIRTUAL_ENV", None)
    env.pop("QT_QUICK_BACKEND", None)
    if sys.platform == "win32":
        windows = Path(env.get("SystemRoot", r"C:\Windows"))
        env["PATH"] = os.pathsep.join(map(str, (windows / "System32", windows)))
    return env


def verify_standalone(executable, report):
    subprocess.run(
        [str(executable), "--desktop-self-check", str(report)],
        env=verification_environment(),
        timeout=180,
        check=True,
    )
    if json.loads((report / "smoke-report.json").read_text())["status"] != "passed":
        raise RuntimeError("The installed standalone native GUI check failed.")


def build(output, *, self_check=True):
    from ci_prepare import excluded
    from PyInstaller.utils.hooks import collect_submodules, copy_metadata
    from qt_resources import import_plan

    from azauthlib.gui.desktop_install import (
        DesktopRelease,
        current_version,
        detect_target,
    )

    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output / "work"
    work.mkdir(exist_ok=True)
    target, version = detect_target(), current_version()
    icon = ROOT / "src/azauthlib/assets/azauthlib-taskbar.ico"
    if target.system == "macos":
        from azauthlib.gui.shortcuts import _icns, _png_icons

        icon = work / "azauthlib.icns"
        icon.write_bytes(
            _icns(_png_icons((ROOT / "src/azauthlib/assets/azauthlib-taskbar.ico").read_bytes()))
        )
    # Build data from the installed wheel's RECORD, not a recursive copy of a
    # developer checkout that might contain dormant assets or local tools.
    distribution = importlib.metadata.distribution("azauthlib")
    origin = json.loads(distribution.read_text("direct_url.json") or "{}")
    if origin.get("dir_info", {}).get("editable"):
        raise RuntimeError("Build from a regular installed wheel, not an editable checkout.")
    plan = import_plan(
        Path(distribution.locate_file("azauthlib/gui/qml")).resolve(),
        env=native_build_environment(),
    )
    data = []
    for item in distribution.files or []:
        relative = item.as_posix()
        if relative.startswith("azauthlib/"):
            part = relative.removeprefix("azauthlib/")
            if not excluded(part) and not relative.endswith((".py", ".pyc")):
                data.append((str(distribution.locate_file(item)), str(Path(relative).parent)))
    data.extend(copy_metadata("azauthlib", recursive=True))
    data.append((str(ROOT / "LICENSE"), "licenses/azauthlib"))
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        data.append((str(python_license), "licenses/Python"))
    smoke = work / "_azauthlib_desktop_smoke.py"
    shutil.copy2(ROOT / ".github/desktop/gui_smoke.py", smoke)
    shutil.copy2(ROOT / ".github/desktop/setup_smoke.py", work / "_azauthlib_setup_smoke.py")
    hidden = collect_submodules("keyring.backends")
    spec = work / "azauthlib.spec"
    specification = (
        "import sys\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(ROOT / '.github/desktop')!r})\n"
        "from qt_resources import trim_analysis\n"
        f"a = Analysis([{str(ROOT / '.github/desktop/frozen_entry.py')!r}], "
        f"pathex=[{str(work)!r}], datas={data!r}, hiddenimports={hidden!r}, "
        "excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineQuick', "
        "'PySide6.QtWebEngineWidgets', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets'])\n"
        f"a.datas, a.binaries = trim_analysis(a.datas, a.binaries, {plan!r}, "
        f"Path({str(output / 'qt-resource-report.json')!r}))\n"
        "pyz = PYZ(a.pure)\n"
        f"exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='azauthlib', "
        f"console={target.system == 'linux'!r}, icon={str(icon)!r}, upx=False)\n"
        "bundle = COLLECT(exe, a.binaries, a.datas, name='azauthlib', upx=False)\n"
    )
    if target.system == "macos":
        specification += (
            f"app = BUNDLE(bundle, name='azauthlib.app', icon={str(icon)!r}, "
            "bundle_identifier='doydl-technologies.azauthlib', "
            f"version={version!r}, info_plist={{'NSHighResolutionCapable': True}})\n"
        )
    spec.write_text(specification, encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--distpath",
            str(output / "dist"),
            "--workpath",
            str(work / "pyinstaller"),
            str(spec),
        ],
        env=native_build_environment(),
        check=True,
    )
    payload = output / "dist" / target.root_name
    (payload / target.setup_manifest).write_text(
        json.dumps({"schema": 1, "version": version, "target": target.label}) + "\n",
        encoding="utf-8",
    )
    archive = output / target.asset_name(version)
    if target.system == "windows":
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
            for path in sorted(payload.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(payload.parent).as_posix())
    else:
        with tarfile.open(archive, "w:gz", dereference=False) as bundle:
            bundle.add(payload, arcname=payload.name)
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    (output / (archive.name + ".sha256")).write_text(
        f"{digest.hexdigest()}  {archive.name}\n", encoding="utf-8"
    )
    if self_check:
        release = DesktopRelease(version, target, "", digest.hexdigest(), archive.stat().st_size)
        subprocess.run(
            [
                str(payload / target.executable),
                "--desktop-setup-self-check",
                "--archive",
                str(archive),
                "--sha256",
                release.checksum,
                "--artifacts",
                str(output / "setup-check"),
            ],
            env=verification_environment(),
            timeout=600,
            check=True,
        )
        executable = output / "setup-check/installation" / target.root_name / target.executable
        verify_standalone(executable, output / "frozen-check")
    print(f"Standalone bundle: {archive}")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--skip-self-check", action="store_true", help="Build only; not release-ready"
    )
    args = parser.parse_args()
    build(args.output, self_check=not args.skip_self_check)


if __name__ == "__main__":
    main()
