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

"""Standalone setup validation, with no live downloads or real desktop installation."""

import hashlib
import io
import json
import os
import stat
import tarfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile, ZipInfo

import pytest

from azauthlib.gui import desktop_install as setup


@pytest.mark.parametrize(
    "system,machine,libc,label",
    [
        ("win32", "AMD64", None, "windows-x86_64"),
        ("darwin", "arm64", None, "macos-arm64"),
        ("darwin", "x86_64", None, "macos-x86_64"),
        ("linux", "x86_64", ("glibc", "2.35"), "linux-x86_64"),
    ],
)
def test_supported_targets(system, machine, libc, label):
    assert setup.detect_target(system=system, machine=machine, libc=libc).label == label


@pytest.mark.parametrize(
    "system,machine,libc",
    [
        ("win32", "ARM64", None),
        ("linux", "aarch64", ("glibc", "2.39")),
        ("linux", "x86_64", ("musl", "1.2")),
        ("linux", "x86_64", ("glibc", "2.31")),
        ("freebsd", "x86_64", None),
    ],
)
def test_unsupported_targets_do_not_silently_use_another_binary(system, machine, libc):
    with pytest.raises(setup.DesktopInstallError):
        setup.detect_target(system=system, machine=machine, libc=libc)


@pytest.mark.parametrize("value", ["latest", "../5.0.0", "5.0.0b1", "https://example.com", "5.0"])
def test_version_is_not_a_url_or_prerelease(value):
    with pytest.raises(setup.DesktopInstallError):
        setup.release_version(value)


def test_padded_project_version_normalizes():
    assert setup.release_version("v005.000.001") == "5.0.1"


def test_default_installation_uses_app_root_without_vendor(monkeypatch, tmp_path):
    calls = []

    def data_path(name, **kwargs):
        calls.append((name, kwargs))
        return tmp_path / name

    monkeypatch.setattr(setup, "user_data_path", data_path)
    target = setup.DesktopTarget("windows", "x86_64")
    assert (
        setup.default_destination("5.0.0", target)
        == tmp_path / "azauthlib/desktop/5.0.0/windows-x86_64"
    )
    assert calls == [("azauthlib", {"appauthor": False})]


def test_launch_starts_independent_app_without_waiting(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        setup.subprocess, "Popen", lambda *args, **kwargs: calls.append((args, kwargs)) or object()
    )
    executable = tmp_path / "azauthlib.exe"
    setup.launch_application(executable, ["--desktop-self-check", "temporary-report"])
    args, kwargs = calls[0]
    assert args[0] == [str(executable), "--desktop-self-check", "temporary-report"]
    assert kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"
    assert kwargs["cwd"] == executable.parent
    assert kwargs["stdin"] == setup.subprocess.DEVNULL


@pytest.fixture
def bundle(tmp_path):
    target = setup.DesktopTarget("windows", "x86_64")
    archive = tmp_path / target.asset_name("5.0.1")
    with ZipFile(archive, "w") as data:
        data.writestr("azauthlib/azauthlib.exe", b"MZ test executable")
        data.writestr("azauthlib/_internal/resource.txt", b"bundled resource")
    release = setup.DesktopRelease(
        "5.0.1",
        target,
        f"{setup.RELEASES_URL}/download/v5.0.1/{archive.name}",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
        archive.stat().st_size,
    )
    return archive, release


def test_install_verified_bundle_in_new_directory(bundle, tmp_path):
    archive, release = bundle
    destination = tmp_path / "installed" / "5.0.1"
    executable = setup.install_archive(archive, release, destination)
    assert executable.read_bytes() == b"MZ test executable"
    assert (destination / "azauthlib/_internal/resource.txt").read_bytes() == b"bundled resource"
    assert (
        json.loads((destination / "desktop-install.json").read_text())["sha256"] == release.checksum
    )
    assert not list(destination.parent.glob(".azauthlib-desktop-*"))


def test_failed_checksum_creates_no_installation(bundle, tmp_path):
    archive, release = bundle
    destination = tmp_path / "not-created" / "app"
    with pytest.raises(setup.DesktopInstallError, match="checksum"):
        setup.install_archive(archive, replace(release, checksum="0" * 64), destination)
    assert not destination.parent.exists()


def test_existing_directory_is_preserved(bundle, tmp_path):
    archive, release = bundle
    destination = tmp_path / "existing"
    destination.mkdir()
    unrelated = destination / "keep.txt"
    unrelated.write_text("user file")
    with pytest.raises(setup.DesktopInstallError, match="Nothing was overwritten"):
        setup.install_archive(archive, release, destination)
    assert unrelated.read_text() == "user file"


def test_deep_installation_paths_preserve_files_and_refuse_replacement(bundle, tmp_path):
    archive, release = bundle
    destination = tmp_path / ("nested-" * 12) / ("application-" * 9) / "installation"
    executable = setup.install_archive(archive, release, destination)
    assert setup.filesystem_path(executable).read_bytes() == b"MZ test executable"
    assert str(executable) == str(
        destination / release.target.root_name / release.target.executable
    )
    with pytest.raises(setup.DesktopInstallError, match="already exists"):
        setup.install_archive(archive, release, destination)


@pytest.mark.parametrize(
    "path",
    [
        "../outside",
        "/absolute",
        "azauthlib/../../outside",
        "other/app.exe",
        "azauthlib/C:evil",
        "azauthlib\\evil",
        "azauthlib/NUL.txt",
        "azauthlib/name.",
    ],
)
def test_archive_paths_cannot_escape_or_use_windows_special_files(tmp_path, path):
    archive = tmp_path / "unsafe.zip"
    with ZipFile(archive, "w") as data:
        data.writestr(path, b"unsafe")
    with pytest.raises(setup.DesktopInstallError):
        setup.extract_bundle(archive, tmp_path / "stage", setup.DesktopTarget("windows", "x86_64"))
    assert not (tmp_path / "outside").exists()


def test_duplicate_case_insensitive_archive_paths_are_rejected(tmp_path):
    archive = tmp_path / "duplicate.zip"
    with ZipFile(archive, "w") as data:
        data.writestr("azauthlib/file", b"first")
        data.writestr("azauthlib/FILE", b"second")
    with pytest.raises(setup.DesktopInstallError, match="duplicate"):
        setup.extract_bundle(archive, tmp_path / "stage", setup.DesktopTarget("windows", "x86_64"))


def test_zip_symlinks_are_rejected(tmp_path):
    archive = tmp_path / "link.zip"
    link = ZipInfo("azauthlib/link")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(archive, "w") as data:
        data.writestr(link, "../../outside")
    with pytest.raises(setup.DesktopInstallError, match="file type"):
        setup.extract_bundle(archive, tmp_path / "stage", setup.DesktopTarget("windows", "x86_64"))


def test_archive_expansion_is_bounded(bundle, tmp_path, monkeypatch):
    archive, release = bundle
    monkeypatch.setattr(setup, "MAX_UNPACKED", 1)
    with pytest.raises(setup.DesktopInstallError, match="size"):
        setup.extract_bundle(archive, tmp_path / "stage", release.target)


def tar_bundle(path, link=None):
    with tarfile.open(path, "w:gz") as data:
        executable = tarfile.TarInfo("azauthlib/azauthlib")
        executable.mode, executable.size = 0o755, 4
        data.addfile(executable, io.BytesIO(b"ELF!"))
        if link is not None:
            member = tarfile.TarInfo("azauthlib/link")
            member.type, member.linkname = tarfile.SYMTYPE, link
            data.addfile(member)


def test_tar_rejects_external_symlink_before_writing(tmp_path):
    archive = tmp_path / "link.tar.gz"
    tar_bundle(archive, "../../outside")
    with pytest.raises(setup.DesktopInstallError, match="unsafe path"):
        setup.extract_bundle(archive, tmp_path / "stage", setup.DesktopTarget("linux", "x86_64"))
    assert not (tmp_path / "stage").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable permissions and symbolic links")
def test_tar_preserves_internal_links_and_executable_permission(tmp_path):
    archive = tmp_path / "valid.tar.gz"
    tar_bundle(archive, "azauthlib")
    root = setup.extract_bundle(archive, tmp_path / "stage", setup.DesktopTarget("linux", "x86_64"))
    assert (root / "azauthlib").stat().st_mode & 0o111
    assert (root / "link").is_symlink()
    assert (root / "link").read_bytes() == b"ELF!"


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/file",
        "https://evil.example/file",
        "file:///tmp/a",
        "https://user:password@github.com/a",
        "https://github.com:8443/a",
    ],
)
def test_untrusted_download_urls_rejected(url):
    with pytest.raises(setup.DesktopInstallError, match="untrusted"):
        setup._trusted_url(url)


def release_metadata(release):
    base = f"{setup.RELEASES_URL}/download/v{release.version}/"
    return {
        "tag_name": "v" + release.version,
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": release.target.asset_name(release.version),
                "size": release.size,
                "browser_download_url": release.download_url,
            },
            {"name": setup.CHECKSUMS_NAME, "browser_download_url": base + setup.CHECKSUMS_NAME},
        ],
    }


def mock_release(monkeypatch, release, *, metadata=None, checksum=None):
    metadata = release_metadata(release) if metadata is None else metadata

    def read(url, limit):
        if url.startswith("https://api.github.com/"):
            return json.dumps(metadata).encode()
        return (
            checksum
            if checksum is not None
            else (f"{release.checksum}  {release.target.asset_name(release.version)}\n".encode())
        )

    monkeypatch.setattr(setup, "_read_url", read)


def test_resolve_exact_version_and_platform_checksum(bundle, monkeypatch):
    _, release = bundle
    mock_release(monkeypatch, release)
    assert setup.resolve_release("005.000.001", release.target) == release


def test_missing_desktop_assets_are_actionable(bundle, monkeypatch):
    _, release = bundle
    mock_release(
        monkeypatch,
        release,
        metadata={
            "tag_name": "v5.0.1",
            "assets": [],
            "draft": False,
            "prerelease": False,
        },
    )
    with pytest.raises(setup.DesktopInstallError, match="not published yet"):
        setup.resolve_release(release.version, release.target)


def test_duplicate_checksum_rejected(bundle, monkeypatch):
    _, release = bundle
    line = f"{release.checksum}  {release.target.asset_name(release.version)}\n"
    mock_release(monkeypatch, release, checksum=(line + line).encode())
    with pytest.raises(setup.DesktopInstallError, match="ambiguous"):
        setup.resolve_release(release.version, release.target)


def test_cli_cancel_does_not_contact_network(monkeypatch, capsys):
    monkeypatch.setattr(setup, "detect_target", lambda: setup.DesktopTarget("windows", "x86_64"))
    monkeypatch.setattr(setup.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert setup.main([]) == 0
    assert "Nothing was installed" in capsys.readouterr().out


def test_cli_noninteractive_requires_explicit_approval(monkeypatch, capsys):
    monkeypatch.setattr(setup, "detect_target", lambda: setup.DesktopTarget("windows", "x86_64"))
    monkeypatch.setattr(setup.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert setup.main([]) == 1
    assert "--yes" in capsys.readouterr().err


def test_cli_check_has_no_install_side_effects(bundle, monkeypatch, tmp_path, capsys):
    _, release = bundle
    monkeypatch.setattr(setup, "detect_target", lambda: release.target)
    mock_release(monkeypatch, release)
    destination = tmp_path / "not-installed"
    assert setup.main(["--check", "--release", "5.0.1", "--install-dir", str(destination)]) == 0
    assert "Available" in capsys.readouterr().out
    assert not destination.exists()


def test_cli_installs_only_after_approval_without_automatic_launch(bundle, monkeypatch, tmp_path):
    archive, release = bundle
    monkeypatch.setattr(setup, "detect_target", lambda: release.target)
    mock_release(monkeypatch, release)

    def download(url, stream, **kwargs):
        stream.write(archive.read_bytes())

    monkeypatch.setattr(setup, "_download", download)
    destination = tmp_path / "installed"
    assert setup.main(["--yes", "--release", "5.0.1", "--install-dir", str(destination)]) == 0
    assert (destination / release.target.root_name / release.target.executable).is_file()


def test_default_interactive_command_opens_wizard_not_terminal_install(
    bundle, monkeypatch, tmp_path
):
    archive, release = bundle
    mock_release(monkeypatch, release)
    monkeypatch.setattr(setup, "detect_target", lambda: release.target)
    monkeypatch.setattr(setup.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    monkeypatch.setattr(
        setup, "_download", lambda url, stream, **kw: stream.write(archive.read_bytes())
    )
    calls = []
    destination = tmp_path / "chosen"

    def wizard(download, selected, folder, **kwargs):
        assert download.read_bytes() == archive.read_bytes()
        calls.append((selected, folder, kwargs))
        return 0

    monkeypatch.setattr(setup, "run_graphical_setup", wizard)
    assert setup.main(["--release", "5.0.1", "--install-dir", str(destination)]) == 0
    assert calls == [(release, destination, {"shortcut": False})]
    assert not destination.exists()


def test_wizard_can_be_explicit_with_approved_download(bundle, monkeypatch):
    archive, release = bundle
    mock_release(monkeypatch, release)
    monkeypatch.setattr(setup, "detect_target", lambda: release.target)
    monkeypatch.setattr(
        setup, "_download", lambda url, stream, **kw: stream.write(archive.read_bytes())
    )
    calls = []
    monkeypatch.setattr(setup, "run_graphical_setup", lambda *args, **kw: calls.append(kw) or 0)
    assert setup.main(["--yes", "--wizard", "--shortcut", "--release", "5.0.1"]) == 0
    assert calls == [{"shortcut": True}]


def wizard_bundle(bundle, *, marker=None):
    archive, release = bundle
    with ZipFile(archive, "a") as data:
        data.writestr(
            "azauthlib/" + setup.SETUP_MANIFEST,
            json.dumps(
                marker or {"schema": 1, "version": release.version, "target": release.target.label}
            ),
        )
    return archive, replace(release, checksum=hashlib.sha256(archive.read_bytes()).hexdigest())


@pytest.mark.parametrize("code", [0, 2])
def test_wizard_runtime_is_verified_and_retained_until_child_exit(
    bundle, monkeypatch, tmp_path, code
):
    archive, release = wizard_bundle(bundle)
    commands = []

    class Child:
        def __init__(self, command, **kwargs):
            commands.append(command)
            self.root = Path(command[0]).parent
            assert self.root.is_dir()
            assert kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"] == "1"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            assert self.root.is_dir()

        def wait(self):
            assert self.root.is_dir()
            return code

    monkeypatch.setattr(setup.subprocess, "Popen", Child)
    assert setup.run_graphical_setup(archive, release, tmp_path / "install", shortcut=True) == 0
    assert "--desktop-setup" in commands[0]
    assert "--shortcut" in commands[0]
    assert commands[0][commands[0].index("--sha256") + 1] == release.checksum
    assert not Path(commands[0][0]).parent.exists()


def test_wizard_rejects_bad_checksum_before_starting_any_executable(bundle, tmp_path):
    archive, release = bundle
    with pytest.raises(setup.DesktopInstallError, match="checksum"):
        setup.run_graphical_setup(
            archive, replace(release, checksum="0" * 64), tmp_path / "install"
        )


def test_wizard_requires_compatible_setup_marker(bundle, tmp_path):
    archive, release = bundle
    with pytest.raises(setup.DesktopInstallError, match="compatible graphical"):
        setup.run_graphical_setup(archive, release, tmp_path / "install")


def test_wizard_rejects_a_marker_for_another_release(bundle, tmp_path):
    archive, release = wizard_bundle(bundle, marker={"schema": 1, "version": "9.9.9"})
    with pytest.raises(setup.DesktopInstallError, match="compatible graphical"):
        setup.run_graphical_setup(archive, release, tmp_path / "install")


def test_child_environment_does_not_inherit_python_or_qt_overrides(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/unrelated/python")
    monkeypatch.setenv("QT_PLUGIN_PATH", "/unrelated/qt")
    env = setup.standalone_environment()
    assert "PYTHONPATH" not in env
    assert "QT_PLUGIN_PATH" not in env
    assert os.environ["PYTHONPATH"] == "/unrelated/python"


def test_new_command_is_registered():
    configuration = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    assert 'azauthlib-install-desktop = "azauthlib.gui.desktop_install:main"' in configuration


def native_release(bundle, monkeypatch):
    archive, release = bundle
    name = release.target.installer_name(release.version)
    url = f"{setup.RELEASES_URL}/download/v{release.version}/{name}"
    release = replace(release, download_url=url)
    metadata = release_metadata(release)
    metadata["assets"][0].update(name=name, browser_download_url=url)
    mock_release(
        monkeypatch, release, metadata=metadata, checksum=f"{release.checksum}  {name}\n".encode()
    )
    return archive, release


def test_native_release_resolves_only_pinned_setup_executable(bundle, monkeypatch):
    _, release = native_release(bundle, monkeypatch)
    assert setup.resolve_release(release.version, release.target, native_installer=True) == release


def test_windows_default_download_opens_native_installer(bundle, monkeypatch):
    archive, release = native_release(bundle, monkeypatch)
    monkeypatch.setattr(setup, "detect_target", lambda: release.target)
    monkeypatch.setattr(setup.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    monkeypatch.setattr(
        setup, "_download", lambda url, stream, **kw: stream.write(archive.read_bytes())
    )
    calls = []
    monkeypatch.setattr(
        setup, "run_native_setup", lambda path, rel: calls.append((path.suffix, rel)) or 0
    )
    assert setup.main(["--release", release.version]) == 0
    assert calls == [(".exe", release)]


def test_native_checksum_failure_never_starts_a_process(bundle, tmp_path):
    archive, release = bundle
    with pytest.raises(setup.DesktopInstallError, match="checksum"):
        setup.run_native_setup(archive, replace(release, checksum="0" * 64))


def test_download_validates_redirect_before_contacting_untrusted_host(monkeypatch):
    visited = []

    class Response:
        status_code = 302
        headers = {"Location": "https://evil.example/bundle"}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def get(self, url, **kwargs):
            visited.append(url)
            assert kwargs["allow_redirects"] is False
            return Response()

    monkeypatch.setattr(setup.requests, "Session", Session)
    with pytest.raises(setup.DesktopInstallError, match="untrusted"):
        setup._download("https://github.com/original", io.BytesIO(), limit=10)
    assert visited == ["https://github.com/original"]


@pytest.mark.parametrize(
    "change",
    [
        "draft",
        "prerelease",
        "wrong-tag",
        "bad-size",
        "bad-url",
        "duplicate-asset",
        "invalid-assets",
    ],
)
def test_release_metadata_must_be_stable_and_unambiguous(bundle, monkeypatch, change):
    _, release = bundle
    metadata = release_metadata(release)
    if change in {"draft", "prerelease"}:
        metadata[change] = True
    elif change == "wrong-tag":
        metadata["tag_name"] = "v9.9.9"
    elif change == "bad-size":
        metadata["assets"][0]["size"] = setup.MAX_DOWNLOAD + 1
    elif change == "bad-url":
        metadata["assets"][0]["browser_download_url"] = "https://evil.example/archive"
    elif change == "duplicate-asset":
        metadata["assets"].append(metadata["assets"][0])
    else:
        metadata["assets"] = [None]
    mock_release(monkeypatch, release, metadata=metadata)
    with pytest.raises(setup.DesktopInstallError):
        setup.resolve_release(release.version, release.target)


@pytest.mark.parametrize("limit,expected", [(3, None), (100, 99)])
def test_download_rejects_excessive_or_truncated_data(monkeypatch, limit, expected):
    class Response:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def raise_for_status(self):
            pass

        def iter_content(self, _):
            return iter([b"1234"])

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def get(self, *_, **__):
            return Response()

    monkeypatch.setattr(setup.requests, "Session", Session)
    with pytest.raises(setup.DesktopInstallError):
        setup._download(
            "https://github.com/archive", io.BytesIO(), limit=limit, expected_size=expected
        )


def test_nested_symlink_entries_rejected_before_any_link_is_created(tmp_path):
    archive = tmp_path / "links.tar.gz"
    with tarfile.open(archive, "w:gz") as data:
        for name, target in [("azauthlib/alias", "."), ("azauthlib/alias/other", "../escape")]:
            link = tarfile.TarInfo(name)
            link.type, link.linkname = tarfile.SYMTYPE, target
            data.addfile(link)
    with pytest.raises(setup.DesktopInstallError, match="overlap"):
        setup.extract_bundle(archive, tmp_path / "stage", setup.DesktopTarget("linux", "x86_64"))
    assert not (tmp_path / "stage").exists()


def test_missing_executable_is_not_an_installation(tmp_path):
    archive = tmp_path / "empty.zip"
    with ZipFile(archive, "w") as data:
        data.writestr("azauthlib/readme.txt", b"not an application")
    with pytest.raises(setup.DesktopInstallError, match="executable is missing"):
        setup.extract_bundle(archive, tmp_path / "stage", setup.DesktopTarget("windows", "x86_64"))


def test_frozen_cache_fingerprints_executable_instead_of_missing_source(monkeypatch, tmp_path):
    from azauthlib.gui import startup_cache

    executable = tmp_path / "standalone.exe"
    executable.write_bytes(b"MZ bundled code")
    monkeypatch.setattr(startup_cache.sys, "frozen", True, raising=False)
    monkeypatch.setattr(startup_cache.sys, "executable", str(executable))
    monkeypatch.setattr(startup_cache, "__file__", str(tmp_path / "no-source/startup_cache.py"))
    resource = tmp_path / "legal.html"
    resource.write_text("<p>Bundled public policy</p>")
    resources = SimpleNamespace(path=lambda *args: resource)
    identity = startup_cache._identity(resources)
    image_path = startup_cache._image_path(resource, ("logo", 128, 128))
    executable.write_bytes(b"MZ updated bundled code")
    assert startup_cache._identity(resources) != identity
    assert startup_cache._image_path(resource, ("logo", 128, 128)) != image_path
