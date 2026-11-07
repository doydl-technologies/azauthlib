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

"""Guard runtime modules and shared libraries against overly broad Qt pruning."""

# ruff: noqa: S101 -- Assertions are intentional in tests.
import json

import pytest
import qt_resources as resources


@pytest.fixture
def plan():
    retained = {
        "QtQuick": "QtQuick",
        "QtQuick.Controls": "QtQuick/Controls",
        "QtQuick.Controls.Basic": "QtQuick/Controls/Basic",
        "QtQuick.Dialogs.quickimpl": "QtQuick/Dialogs/quickimpl",
        "QtQuick.Effects": "QtQuick/Effects",
    }
    return {
        "direct_imports": ["QtQuick", "QtQuick.Controls"],
        "retained_modules": retained,
        "module_directories": [*retained.values(), "QtQuick3D", "QtQuick/Controls/Material"],
    }


@pytest.mark.parametrize(
    "file",
    [
        "PySide6/qml/QtQuick/Controls/Basic/Button.qml",
        "PySide6/qml/QtQuick/Effects/effectsplugin.dll",
        "PySide6/Qt/qml/QtQuick/Dialogs/quickimpl/qml/FileDialog.qml",
        "PySide6/Qt6Quick3D.dll",
        "PySide6/plugins/platforms/qwindows.dll",
        "PySide6/translations/qt_de.qm",
        "azauthlib/assets/logo/png/mascot-garden.png",
    ],
)
def test_runtime_and_non_qml_assets_are_preserved(plan, file):
    assert resources.exclusion_reason(file, plan) is None


@pytest.mark.parametrize(
    "file",
    [
        "PySide6/qml/QtQuick3D/qtquick3dplugin.dll",
        "PySide6/Qt/qml/QtQuick/Controls/Material/Button.qml",
        "PySide6/qml/QtQuick/Controls/Basic/designer/ButtonSpecifics.qml",
        "PySide6/qml/QtQuick/Dialogs/quickimpl/qml/+Fusion/FileDialog.qml",
        r"PySide6\qml\QtQuick3D\designer\MaterialEditor.qml",
    ],
)
def test_unused_modules_styles_and_designer_resources_are_removed(plan, file):
    assert resources.exclusion_reason(file, plan) is not None


def test_analysis_filters_plugin_binaries_and_records_removals(plan, tmp_path):
    source = tmp_path / "data"
    source.write_bytes(b"test")
    data = [("PySide6/qml/QtQuick/Controls/Basic/Button.qml", str(source), "DATA")]
    binaries = [("PySide6/qml/QtQuick3D/plugin.dll", str(source), "BINARY")]
    report = tmp_path / "report.json"
    selected_data, selected_binaries = resources.trim_analysis(data, binaries, plan, report)
    assert selected_data == data
    assert selected_binaries == []
    assert json.loads(report.read_text())["removed_bytes"] == 4


def test_future_explicit_style_import_fails_instead_of_silently_pruning(tmp_path):
    pytest.importorskip("PySide6")
    (tmp_path / "Main.qml").write_text("import QtQuick.Controls.Material\n")
    with pytest.raises(RuntimeError, match="non-Basic style"):
        resources.import_plan(tmp_path)
