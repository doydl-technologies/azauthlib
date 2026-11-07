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

"""Select standalone QML resources using Qt's import/dependency scanner.

Only the standalone bundle is filtered. The installed Python package and shared
Qt libraries/plugins outside the QML import tree remain unchanged.
"""

import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

UNUSED_STYLES = frozenset(
    {"Fusion", "Imagine", "Material", "Universal", "FluentWinUI3", "Windows", "macOS", "iOS"}
)


def unused_style(module):
    return any(
        module == "QtQuick.Controls." + style
        or module.startswith("QtQuick.Controls." + style + ".")
        for style in UNUSED_STYLES
    )


def import_plan(source, *, env=None):
    from PySide6.QtCore import QLibraryInfo

    qml = Path(QLibraryInfo.path(QLibraryInfo.QmlImportsPath)).resolve()
    tools = Path(QLibraryInfo.path(QLibraryInfo.LibraryExecutablesPath))
    scanner = tools / ("qmlimportscanner.exe" if sys.platform == "win32" else "qmlimportscanner")
    if not scanner.is_file():
        raise RuntimeError("Qt's qmlimportscanner is required to validate standalone resources")
    direct = set()
    for file in source.rglob("*.qml"):
        direct.update(re.findall(r"^\s*import\s+([\w.]+)", file.read_text(encoding="utf-8"), re.M))
    if any(unused_style(name) for name in direct):
        raise RuntimeError("A QML file imports a non-Basic style; review the standalone Qt policy")
    result = subprocess.run(
        [str(scanner), "-rootPath", str(source), "-importPath", str(qml)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    modules = {}
    for item in json.loads(result.stdout):
        if item.get("type") != "module" or not item.get("path"):
            continue
        path = Path(item["path"]).resolve()
        if path.is_relative_to(qml) and not unused_style(item["name"]):
            modules[item["name"]] = path.relative_to(qml).as_posix()
    if direct - modules.keys() - {"QML"}:
        raise RuntimeError(
            "Qt did not resolve all direct QML imports: " + str(direct - modules.keys())
        )
    if "QtQuick.Controls.Basic" not in modules:
        raise RuntimeError("Qt's Basic style is missing from the import dependency closure")
    return {
        "direct_imports": sorted(direct),
        "retained_modules": modules,
        "module_directories": sorted(
            p.parent.relative_to(qml).as_posix() for p in qml.rglob("qmldir")
        ),
    }


def exclusion_reason(destination, plan):
    parts = PurePosixPath(destination.replace("\\", "/")).parts
    if not parts or parts[0] != "PySide6" or "qml" not in parts:
        return None
    relative = PurePosixPath(*parts[parts.index("qml") + 1 :])
    if "designer" in relative.parts:
        return "Qt Designer resources"
    if any(part.startswith("+") and part[1:] in UNUSED_STYLES for part in relative.parts):
        return "Unused style selector"
    module_directories = set(plan["module_directories"])
    retained = set(plan["retained_modules"].values())
    for parent in relative.parents:
        directory = parent.as_posix()
        if directory in module_directories:
            return None if directory in retained else "Unreferenced QML module/style"
    # Root-level Qt metadata is not assigned to any individual import module.
    return None


def trim_analysis(data, binaries, plan, report_path):
    removed = []

    def select(entries):
        kept = []
        for entry in entries:
            reason = exclusion_reason(entry[0], plan)
            if reason:
                removed.append(
                    {
                        "destination": entry[0],
                        "bytes": Path(entry[1]).stat().st_size if Path(entry[1]).is_file() else 0,
                        "reason": reason,
                    }
                )
            else:
                kept.append(entry)
        return kept

    selected_data, selected_binaries = select(data), select(binaries)
    report_path.write_text(
        json.dumps(
            {
                "direct_imports": plan["direct_imports"],
                "retained_modules": sorted(plan["retained_modules"]),
                "removed_files": len(removed),
                "removed_bytes": sum(item["bytes"] for item in removed),
                "removed": removed,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return selected_data, selected_binaries
