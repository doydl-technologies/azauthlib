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

"""Build, inspect, and install distributions in an isolated directory.

The installed target is used by gui_smoke.py in a separate process. No
GitHub credentials, publishing, authentication, or user storage are involved.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
LOCAL_NAMES = {
    "_Search-Qml.cmd-",
    "_Search-Qml.ps1-",
    "Search-Qml.cmd",
    "Search-Qml.ps1",
    "Search-Qml.settings.json",
    ".repoSearch.settings.json",
    "repoSearch",
    "repoSearch.cmd",
}
PREVIEW_FILES = {
    "gui/preview_add_connection_animation.py",
    "gui/qml/AddConnectionAnimationPreview.qml",
    "gui/qml/ConnectionAnimationSimulation.qml",
    "gui/qml/components/ConnectionAnimationInspector.qml",
}
AVATAR_DIRECTORY = "assets/icons/svg/third-party/profile-avatar/"


def excluded(relative):
    path = Path(relative)
    return (
        bool(set(path.parts) & {".dormant", ".docs", ".scripts", "__pycache__"})
        or (
            path.as_posix().startswith("assets/icons/svg/third-party/")
            and not path.as_posix().startswith(AVATAR_DIRECTORY)
        )
        or path.as_posix() in PREVIEW_FILES
        or path.as_posix() == "UI_IMPLEMENTATION_NOTES.md"
        or (path.parent.as_posix() == "gui/qml" and path.name in LOCAL_NAMES)
    )


def verify_archives(root, wheel, sdist):
    package = root / "src/azauthlib"
    expected = set()
    for path in package.rglob("*"):
        relative = path.relative_to(package)
        if not path.is_file() or excluded(relative):
            continue
        if (
            path.suffix in {".png", ".svg", ".ico", ".ttf", ".qml", ".qsb", ".frag"}
            or path.name == "qmldir"
            or path.name.endswith("-OFL.txt")
            or path.name == ".TERMS-OF-USE.md"
            or path.parent == package / "assets/docs/legal"
            or (path.suffix == ".py" and path.parent in (package, package / "gui"))
        ):
            expected.add(relative.as_posix())
    with ZipFile(wheel) as archive:
        wheel_names = set(archive.namelist())
        packaged = {
            name.removeprefix("azauthlib/") for name in wheel_names if name.startswith("azauthlib/")
        }
        for name in wheel_names:
            if not name.endswith(".qml"):
                continue
            text = "\n".join(
                line
                for line in archive.read(name).decode("utf-8").splitlines()
                if not line.lstrip().startswith("//")
            )
            for reference in re.findall(r'["\']([^"\'\n]+\.(?:svg|png|ico|ttf|qsb))["\']', text):
                if reference.startswith("."):
                    resolved = posixpath.normpath(
                        posixpath.join(posixpath.dirname(name), reference)
                    )
                    if resolved not in wheel_names:
                        raise ValueError(
                            f"Missing/case-mismatched QML resource: {name}: {reference}"
                        )
    with tarfile.open(sdist) as archive:
        source_files = {
            item.name.split("/", 1)[1]
            for item in archive.getmembers()
            if item.isfile() and "/" in item.name
        }
        source_names = {
            item.name.split("/src/azauthlib/", 1)[1]
            for item in archive.getmembers()
            if item.isfile() and "/src/azauthlib/" in item.name
        }
    validation_files = {path.relative_to(root).as_posix() for path in (root / "tests").glob("*.py")}
    if (root / "CHANGELOG.md").is_file():
        validation_files.add("CHANGELOG.md")
    if missing := validation_files - source_files:
        raise ValueError(f"sdist missing validation files: {sorted(missing)}")
    for label, contents in (("wheel", packaged), ("sdist", source_names)):
        if missing := expected - contents:
            raise ValueError(f"{label} missing runtime files: {sorted(missing)}")
        if unwanted := sorted(name for name in contents if excluded(name)):
            raise ValueError(f"{label} contains excluded development files: {unwanted}")
    return {"runtime_files_checked": len(expected), "wheel": wheel.name, "sdist": sdist.name}


def run_logged(command, cwd, log):
    print("Running:", " ".join(map(str, command)), flush=True)
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run(
            command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, timeout=900, check=False
        )
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    print("\n".join(lines[-80:] if result.returncode else lines[-8:]), flush=True)
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=Path("ci-artifacts"))
    args = parser.parse_args(argv)
    artifacts = args.artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    dist = artifacts / "dist"
    target = artifacts / "installed"
    if target.exists() or (dist.exists() and any(dist.iterdir())):
        parser.error("Use a fresh artifact directory; existing builds/installs are not overwritten")
    run_logged(
        [sys.executable, "-m", "build", "--outdir", str(dist)], ROOT, artifacts / "build.log"
    )
    wheels, sdists = list(dist.glob("*.whl")), list(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("Expected exactly one wheel and source archive")
    report = verify_archives(ROOT, wheels[0], sdists[0])
    (artifacts / "package-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    run_logged(
        [sys.executable, "-m", "twine", "check", str(wheels[0]), str(sdists[0])],
        ROOT,
        artifacts / "twine.log",
    )
    run_logged(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-warn-script-location",
            "--target",
            str(target),
            str(wheels[0]),
        ],
        ROOT,
        artifacts / "install.log",
    )
    print("Distribution checks passed; installed target:", target, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
