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

"""Test distribution inspection and build safeguards without Qt or a display."""
# ruff: noqa: S101 -- assertions are intentional in this test module

from io import BytesIO
from tarfile import TarInfo
from zipfile import ZipFile

import ci_prepare
import pytest


@pytest.mark.parametrize(
    "relative",
    [
        "gui/qml/repoSearch",
        "gui/qml/Search-Qml.ps1",
        "UI_IMPLEMENTATION_NOTES.md",
        "assets/logo/svg/.dormant/old.svg",
        "assets/icons/svg/.docs/guide.md",
        "assets/icons/svg/.scripts/utility.py",
        "assets/icons/svg/third-party/reference.svg",
        "assets/icons/svg/third-party/profile-avatar/.dormant/old.svg",
        "gui/preview_add_connection_animation.py",
        "gui/qml/AddConnectionAnimationPreview.qml",
        "gui/qml/ConnectionAnimationSimulation.qml",
        "gui/qml/components/ConnectionAnimationInspector.qml",
    ],
)
def test_local_only_files_are_excluded(relative):
    assert ci_prepare.excluded(relative)


@pytest.mark.parametrize(
    "relative",
    [
        "assets/logo/svg/mark.svg",
        "assets/logo/third-party/graph.svg",
        "assets/logo/svg/third-party/.TERMS-OF-USE.md",
        "gui/platform_integration.py",
        "assets/docs/legal/PRIVACY.html",
        "assets/icons/svg/third-party/profile-avatar/app-services.svg",
        "assets/icons/svg/third-party/profile-avatar/.TERMS-OF-USE.md",
    ],
)
def test_runtime_files_are_not_excluded(relative):
    assert not ci_prepare.excluded(relative)


def archives(tmp_path, *, extra=None, reference="mark.svg", omit_source=False):
    root = tmp_path / "checkout"
    entries = {
        "assets/logo/mark.svg": b"<svg/>",
        "gui/qml/components/Test.qml": (
            'Image { source: "../../../assets/logo/' + reference + '" }'
        ).encode(),
    }
    for name, data in entries.items():
        target = root / "src/azauthlib" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    wheel = tmp_path / "test.whl"
    sdist = tmp_path / "test.tar.gz"
    with ZipFile(wheel, "w") as archive:
        for name, data in entries.items():
            archive.writestr("azauthlib/" + name, data)
        if extra:
            archive.writestr("azauthlib/" + extra, b"excluded")
    with ci_prepare.tarfile.open(sdist, "w:gz") as archive:
        for name, data in entries.items():
            if omit_source and name.endswith(".svg"):
                continue
            info = TarInfo("test/src/azauthlib/" + name)
            info.size = len(data)
            archive.addfile(info, BytesIO(data))
    return root, wheel, sdist


def test_archive_check_accepts_complete_distributions(tmp_path):
    report = ci_prepare.verify_archives(*archives(tmp_path))
    assert report["runtime_files_checked"] == 2


def test_archive_check_rejects_missing_source_assets(tmp_path):
    with pytest.raises(ValueError, match="sdist missing runtime files"):
        ci_prepare.verify_archives(*archives(tmp_path, omit_source=True))


def test_archive_check_requires_test_isolation_fixture(tmp_path):
    root, wheel, sdist = archives(tmp_path)
    tests = root / "tests"
    tests.mkdir()
    (tests / "conftest.py").write_text('"""Isolated user storage."""', encoding="utf-8")
    with pytest.raises(ValueError, match="sdist missing validation files"):
        ci_prepare.verify_archives(root, wheel, sdist)


def test_archive_check_rejects_excluded_files(tmp_path):
    with pytest.raises(ValueError, match="excluded development files"):
        ci_prepare.verify_archives(*archives(tmp_path, extra="assets/logo/.dormant/old.svg"))


def test_archive_check_detects_case_sensitive_qml_resource_failures(tmp_path):
    with pytest.raises(ValueError, match="case-mismatched QML resource"):
        ci_prepare.verify_archives(*archives(tmp_path, reference="Mark.svg"))


def test_archive_check_requires_avatar_attribution_in_both_distributions(tmp_path):
    root, wheel, sdist = archives(tmp_path)
    terms = root / "src/azauthlib" / ci_prepare.AVATAR_DIRECTORY / ".TERMS-OF-USE.md"
    terms.parent.mkdir(parents=True)
    terms.write_text("Third-party attribution", encoding="utf-8")
    with pytest.raises(ValueError, match="wheel missing runtime files"):
        ci_prepare.verify_archives(root, wheel, sdist)
    with ZipFile(wheel, "a") as archive:
        archive.writestr(
            "azauthlib/" + ci_prepare.AVATAR_DIRECTORY + terms.name, terms.read_bytes()
        )
    with pytest.raises(ValueError, match="sdist missing runtime files"):
        ci_prepare.verify_archives(root, wheel, sdist)


def test_prepare_refuses_to_overwrite_an_existing_install(tmp_path, monkeypatch):
    (tmp_path / "installed").mkdir()

    def unexpected_run(*args, **kwargs):
        pytest.fail("Existing artifact directories must not launch any build/install command")

    monkeypatch.setattr(ci_prepare, "run_logged", unexpected_run)
    with pytest.raises(SystemExit) as error:
        ci_prepare.main(["--artifacts", str(tmp_path)])
    assert error.value.code == 2
