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

"""Explicit, per-user installation of verified standalone desktop release bundles.

Nothing runs during pip installation or import. Downloads are restricted to the
official GitHub repository and its release-asset hosts. SHA-256 detects damaged
or substituted downloads; it is not a replacement for platform code signing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import posixpath
import re
import shutil
import stat
import subprocess  # nosec B404 # Only verified local executables are launched without a shell.
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile

import requests
from platformdirs import user_data_path

REPOSITORY = "doydl-technologies/azauthlib"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
CHECKSUMS_NAME = "SHA256SUMS-desktop.txt"
MAX_DOWNLOAD = 1024 * 1024 * 1024
MAX_UNPACKED = 3 * 1024 * 1024 * 1024
MAX_MEMBERS = 30_000
SETUP_MANIFEST = "desktop-setup.json"
ALLOWED_HOSTS = frozenset(
    {
        "api.github.com",
        "github.com",
        "release-assets.githubusercontent.com",
        "objects.githubusercontent.com",
    }
)


class DesktopInstallError(RuntimeError):
    """The requested standalone app cannot be installed safely."""


@dataclass(frozen=True)
class DesktopTarget:
    system: str
    architecture: str

    @property
    def label(self):
        return f"{self.system}-{self.architecture}"

    @property
    def root_name(self):
        return "azauthlib.app" if self.system == "macos" else "azauthlib"

    @property
    def executable(self):
        if self.system == "macos":
            return "Contents/MacOS/azauthlib"
        return "azauthlib.exe" if self.system == "windows" else "azauthlib"

    @property
    def setup_manifest(self):
        return "Contents/Resources/" + SETUP_MANIFEST if self.system == "macos" else SETUP_MANIFEST

    def asset_name(self, version):
        extension = "zip" if self.system == "windows" else "tar.gz"
        return f"azauthlib-desktop-{version}-{self.label}.{extension}"

    def installer_name(self, version):
        return f"azauthlib-desktop-{version}-{self.label}-setup.exe"


@dataclass(frozen=True)
class DesktopRelease:
    version: str
    target: DesktopTarget
    download_url: str
    checksum: str
    size: int


def release_version(value):
    """Accept stable release numbers only; never interpolate arbitrary URL paths."""
    if not re.fullmatch(r"v?\d{1,6}\.\d{1,6}\.\d{1,6}", value):
        raise DesktopInstallError("Use a stable release number such as 5.0.1.")
    return ".".join(str(int(part)) for part in value.removeprefix("v").split("."))


def current_version():
    from .. import __version__

    return release_version(__version__)


def default_destination(version, target):
    return user_data_path("azauthlib", appauthor=False) / "desktop" / version / target.label


def detect_target(*, system=None, machine=None, libc=None):
    system = system or sys.platform
    machine = (machine or platform.machine()).lower()
    architecture = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(machine)
    if system == "win32" and architecture == "x86_64":
        return DesktopTarget("windows", architecture)
    if system == "darwin" and architecture in {"x86_64", "arm64"}:
        return DesktopTarget("macos", architecture)
    if system.startswith("linux") and architecture == "x86_64":
        name, version = libc if libc is not None else platform.libc_ver()
        numbers = tuple(int(part) for part in version.split(".") if part.isdigit())
        if name != "glibc" or numbers < (2, 35):
            raise DesktopInstallError(
                "The Linux desktop bundle requires x86-64 Linux with glibc 2.35 or newer."
            )
        return DesktopTarget("linux", architecture)
    raise DesktopInstallError(
        f"No standalone bundle is supported for {system}/{machine}. "
        "The Python-based azauthlib-app command remains available."
    )


def _trusted_url(url):
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
    ):
        raise DesktopInstallError("The release points to an untrusted download location.")


def _download(url, stream, *, limit, expected_size=None):
    """Validate each redirect before following it; never send credentials or tokens."""
    with requests.Session() as session:
        session.trust_env = False
        for _ in range(6):
            _trusted_url(url)
            with session.get(
                url,
                headers={
                    "User-Agent": "azauthlib-desktop-installer",
                    "Accept-Encoding": "identity",
                },
                timeout=(15, 60),
                allow_redirects=False,
                stream=True,
            ) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    url = requests.compat.urljoin(url, response.headers.get("Location", ""))
                    continue
                if response.status_code == 404:
                    raise DesktopInstallError(
                        "This release has no published desktop bundle for your machine. "
                        f"Check {RELEASES_URL} or use azauthlib-app."
                    )
                response.raise_for_status()
                total = 0
                digest = hashlib.sha256()
                for block in response.iter_content(1024 * 1024):
                    total += len(block)
                    if total > limit:
                        raise DesktopInstallError("The download exceeds its permitted size.")
                    stream.write(block)
                    digest.update(block)
                if expected_size is not None and total != expected_size:
                    raise DesktopInstallError("The desktop download is incomplete or has changed.")
                return digest.hexdigest()
    raise DesktopInstallError("Too many redirects while downloading the desktop release.")


def _read_url(url, limit):
    import io

    stream = io.BytesIO()
    _download(url, stream, limit=limit)
    return stream.getvalue()


def resolve_release(version, target, *, native_installer=False):
    version = release_version(version)
    metadata = json.loads(
        _read_url(
            f"https://api.github.com/repos/{REPOSITORY}/releases/tags/v{version}", 1024 * 1024
        )
    )
    if (
        not isinstance(metadata, dict)
        or metadata.get("tag_name") != f"v{version}"
        or metadata.get("draft") is not False
        or metadata.get("prerelease") is not False
    ):
        raise DesktopInstallError(
            "The requested desktop release is not a stable published release."
        )
    raw_assets = metadata.get("assets")
    if not isinstance(raw_assets, list) or any(
        not isinstance(asset, dict) or not isinstance(asset.get("name"), str)
        for asset in raw_assets
    ):
        raise DesktopInstallError("The release asset metadata is invalid.")
    assets = {asset["name"]: asset for asset in raw_assets}
    if len(assets) != len(raw_assets):
        raise DesktopInstallError("The release contains duplicate asset names.")
    name = target.installer_name(version) if native_installer else target.asset_name(version)
    if name not in assets or CHECKSUMS_NAME not in assets:
        raise DesktopInstallError(
            f"Desktop bundle {name} is not published yet. See {RELEASES_URL}; "
            "the existing azauthlib-app launcher still works."
        )
    # Pin the repository, tag and filenames instead of accepting arbitrary asset URLs.
    base = f"{RELEASES_URL}/download/v{version}/"
    for filename in (name, CHECKSUMS_NAME):
        if assets[filename].get("browser_download_url") != base + filename:
            raise DesktopInstallError("Unexpected release asset URL.")
    matches = []
    for line in _read_url(base + CHECKSUMS_NAME, 64 * 1024).decode("utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](\S+)", line)
        if match and match[2] == name:
            matches.append(match[1].lower())
    if len(matches) != 1:
        raise DesktopInstallError("The desktop checksum is missing or ambiguous.")
    size = assets[name].get("size")
    if type(size) is not int or not 0 < size <= MAX_DOWNLOAD:
        raise DesktopInstallError("The release asset has an invalid size.")
    return DesktopRelease(version, target, base + name, matches[0], size)


def _archive_path(name, root):
    path = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or any(ord(char) < 32 for char in name)
        or path.is_absolute()
        or not path.parts
        or path.parts[0] != root
        or any(
            part in {".", ".."} or ":" in part or part.endswith((".", " ")) for part in path.parts
        )
        or any(
            re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", part.split(".")[0], re.IGNORECASE)
            for part in path.parts
        )
    ):
        raise DesktopInstallError("The desktop archive contains an unsafe path.")
    return path


def filesystem_path(path):
    """Use extended Win32 paths internally, without changing displayed launch paths."""
    path = Path(os.path.abspath(Path(path).expanduser()))
    if os.name != "nt":
        return path
    value = str(path)
    if value.startswith("\\\\?\\"):
        return path
    if value.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + value[2:])
    return Path("\\\\?\\" + value)


def extract_bundle(archive, directory, target):
    """Extract regular files first, then bounded POSIX links; never use extractall."""
    result = Path(directory) / target.root_name
    archive, directory = filesystem_path(archive), filesystem_path(directory)
    entries, links, total, names = [], [], 0, set()
    is_zip = target.system == "windows"
    with ZipFile(archive) if is_zip else tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.infolist() if is_zip else bundle:
            name = member.filename if is_zip else member.name
            path = _archive_path(name.rstrip("/"), target.root_name)
            key = str(path).casefold() if target.system in {"windows", "macos"} else str(path)
            if key in names or len(names) >= MAX_MEMBERS:
                raise DesktopInstallError(
                    "The desktop archive has duplicate paths or too many files."
                )
            names.add(key)
            size = member.file_size if is_zip else member.size
            total += size
            if size < 0 or total > MAX_UNPACKED:
                raise DesktopInstallError("The expanded desktop bundle exceeds its permitted size.")
            mode = member.external_attr >> 16 if is_zip else member.mode
            is_directory = member.is_dir() if is_zip else member.isdir()
            if not is_zip and member.issym():
                linked = member.linkname
                if "\\" in linked or ":" in linked or any(ord(c) < 32 for c in linked):
                    raise DesktopInstallError("Unsafe desktop symbolic link.")
                resolved = posixpath.normpath(posixpath.join(str(path.parent), linked))
                _archive_path(resolved, target.root_name)
                links.append((path, linked))
            elif not is_directory and (
                (is_zip and stat.S_IFMT(mode) not in {0, stat.S_IFREG})
                or (not is_zip and not member.isfile())
            ):
                raise DesktopInstallError("The desktop archive contains an unsupported file type.")
            else:
                entries.append((path, member, is_directory, mode))

        def path_key(path):
            return str(path).casefold() if target.system == "macos" else str(path)

        link_paths = {path_key(path) for path, _ in links}
        for path in [entry[0] for entry in entries] + [link[0] for link in links]:
            parents = path.parents if path_key(path) in link_paths else (path, *path.parents)
            if any(path_key(parent) in link_paths for parent in parents):
                raise DesktopInstallError("Desktop archive files overlap a symbolic link.")
        for path, member, is_directory, mode in entries:
            destination = directory.joinpath(*path.parts)
            if is_directory:
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.open(member) if is_zip else bundle.extractfile(member)
            with source, destination.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            destination.chmod(0o755 if mode & 0o111 else 0o644)
        for path, linked in links:
            destination = directory.joinpath(*path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(linked)
        for path, _ in links:
            try:
                resolved = directory.joinpath(*path.parts).resolve(strict=True)
            except (OSError, RuntimeError) as error:
                raise DesktopInstallError(
                    "An invalid or cyclic symbolic link was found."
                ) from error
            if not resolved.is_relative_to(directory / target.root_name):
                raise DesktopInstallError("A desktop symbolic link leaves its bundle.")
    executable = directory / target.root_name / target.executable
    if not executable.is_file() or executable.is_symlink():
        raise DesktopInstallError("The desktop executable is missing or is not a regular file.")
    return result


def validate_destination(destination):
    """Reject existing destinations and paths through links before creating any files."""
    destination = Path(destination).expanduser().absolute()
    checked = filesystem_path(destination)
    if checked.exists() or checked.is_symlink():
        raise DesktopInstallError(f"{destination} already exists. Nothing was overwritten.")
    for path in (checked, *checked.parents):
        try:
            details = path.lstat()
        except FileNotFoundError:
            continue
        # st_file_attributes is available on Python 3.10 Windows too, where
        # pathlib has no is_junction() method yet.
        reparse = getattr(details, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
        )
        if stat.S_ISLNK(details.st_mode) or reparse:
            raise DesktopInstallError(
                "The installation path must not traverse symbolic links or junctions."
            )
    return destination


def verify_archive(archive, release):
    with filesystem_path(archive).open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != release.checksum:
        raise DesktopInstallError("Desktop checksum verification failed. Nothing was installed.")


def install_archive(archive, release, destination):
    """Install into a new versioned directory; never replace an existing installation."""
    requested = validate_destination(destination)
    destination = filesystem_path(requested)
    verify_archive(archive, release)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".azauthlib-desktop-", dir=destination.parent
    ) as staging:
        payload = extract_bundle(archive, Path(staging), release.target)
        destination.mkdir(mode=0o700)
        try:
            (Path(staging) / "desktop-install.json").write_text(
                json.dumps(
                    {
                        "version": release.version,
                        "platform": release.target.label,
                        "sha256": release.checksum,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            # The private staging folder becomes the installed app in one move.
            payload.rename(destination / payload.name)
            (Path(staging) / "desktop-install.json").rename(destination / "desktop-install.json")
        except OSError:
            # Remove only this request's payload, never an existing user directory.
            owned = destination / release.target.root_name
            if owned.is_dir() and not owned.is_symlink():
                shutil.rmtree(owned)
            destination.rmdir()
            raise
    return requested / release.target.root_name / release.target.executable


def create_shortcut(executable):
    from importlib.resources import as_file, files

    from PySide6.QtCore import QStandardPaths

    from .shortcuts import create_app_shortcut

    with as_file(files("azauthlib").joinpath("assets", "azauthlib-taskbar.ico")) as icon:
        return create_app_shortcut(
            desktop_dir=QStandardPaths.writableLocation(QStandardPaths.DesktopLocation),
            icon_path=icon,
            executable=executable,
            standalone=True,
        )


def standalone_environment():
    """Keep a child bundle independent of the caller's Python and Qt paths."""
    env = dict(os.environ)
    for name in (
        "PYTHONHOME",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QML2_IMPORT_PATH",
        "QML_IMPORT_PATH",
    ):
        env.pop(name, None)
    # A finished wizard must not leave its new app dependent on temporary files.
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    if getattr(sys, "frozen", False) and sys.platform.startswith("linux"):
        if "LD_LIBRARY_PATH_ORIG" in env:
            env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
        else:
            env.pop("LD_LIBRARY_PATH", None)
    return env


@contextmanager
def _child_library_search():
    """Do not let a frozen Windows parent's DLL directory leak into the new app."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        yield
        return
    import ctypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetDllDirectoryW.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p]
    kernel.GetDllDirectoryW.restype = ctypes.c_uint32
    kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
    kernel.SetDllDirectoryW.restype = ctypes.c_int
    size = kernel.GetDllDirectoryW(0, None)
    previous = ctypes.create_unicode_buffer(size + 1)
    kernel.GetDllDirectoryW(len(previous), previous)
    if not kernel.SetDllDirectoryW(None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        kernel.SetDllDirectoryW(previous.value or None)


def launch_application(executable, arguments=()):
    """Start an independent installed app; never wait for its lifetime or invoke a shell."""
    executable = Path(executable).absolute()
    options = (
        {"start_new_session": True}
        if os.name != "nt"
        else {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
    )
    with _child_library_search():
        return subprocess.Popen(  # nosec B603 # Explicit installed binary and argument list; no shell.
            [str(executable), *map(str, arguments)],
            cwd=executable.parent,
            env=standalone_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **options,
        )


def run_graphical_setup(archive, release, destination, *, shortcut=False):
    """Run the verified bundle's wizard, keeping its private runtime until it exits."""
    verify_archive(archive, release)
    with tempfile.TemporaryDirectory(prefix="azauthlib-setup-runtime-") as temporary:
        root = extract_bundle(archive, Path(temporary), release.target)
        marker = root / release.target.setup_manifest
        expected = {"schema": 1, "version": release.version, "target": release.target.label}
        if (
            not marker.is_file()
            or marker.is_symlink()
            or marker.stat().st_size > 4096
            or json.loads(marker.read_text(encoding="utf-8")) != expected
        ):
            raise DesktopInstallError(
                "This bundle does not provide a compatible graphical setup wizard. "
                "Use --terminal for the archive installer instead."
            )
        command = [
            str(root / release.target.executable),
            "--desktop-setup",
            "--archive",
            str(Path(archive).resolve()),
            "--sha256",
            release.checksum,
            "--release",
            release.version,
            "--install-dir",
            str(Path(destination).absolute()),
        ]
        if shortcut:
            command.append("--shortcut")
        print("Opening graphical setup. Finish or cancel in that window.", flush=True)
        with subprocess.Popen(command, env=standalone_environment()) as process:  # nosec B603
            while True:
                try:
                    code = process.wait()
                    break
                except KeyboardInterrupt:
                    # Deleting a running frozen runtime can corrupt setup on POSIX
                    # and leave locked temporary files on Windows.
                    print("Please finish or cancel in the setup window.", file=sys.stderr)
        if code == 2:
            print("Setup cancelled. Nothing was installed.")
            return 0
        if code:
            raise DesktopInstallError(f"Graphical setup exited with status {code}.")
        return 0


def run_native_setup(executable, release):
    """Opening the verified native Windows host starts its MSI transaction immediately."""
    verify_archive(executable, release)
    print(
        "Opening automatic setup. Installation starts in that window; the app will not launch.",
        flush=True,
    )
    with subprocess.Popen([str(executable)], env=standalone_environment()) as process:  # nosec B603
        while True:
            try:
                code = process.wait()
                break
            except KeyboardInterrupt:
                print(
                    "Cancel in the setup window so Windows Installer can roll back safely.",
                    file=sys.stderr,
                )
    if code == 1602:
        print("Setup cancelled.")
        return 0
    if code:
        raise DesktopInstallError(f"Windows Installer returned setup code {code}.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Optionally install the standalone azauthlib desktop app."
    )
    parser.add_argument(
        "--release",
        default=current_version(),
        help="Stable release (default: installed library version)",
    )
    parser.add_argument(
        "--install-dir",
        type=Path,
        help="New installation directory; existing files are never replaced",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check availability without installing or creating files",
    )
    parser.add_argument(
        "--yes", action="store_true", help="Explicitly approve installation without prompting"
    )
    parser.add_argument(
        "--shortcut",
        action="store_true",
        help="Select the optional shortcut (never replaces an existing one)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--terminal", action="store_true", help="Use terminal questions instead of the wizard"
    )
    mode.add_argument(
        "--wizard", action="store_true", help="Open graphical setup, including with --yes"
    )
    args = parser.parse_args(argv)
    try:
        target, version = detect_target(), release_version(args.release)
        graphical = args.wizard or not (args.yes or args.terminal)
        native = (
            target.system == "windows"
            and graphical
            and not (args.wizard or args.install_dir or args.shortcut)
        )
        destination = (
            user_data_path("azauthlib", appauthor=False) / "desktop/app"
            if native
            else args.install_dir or default_destination(version, target)
        )
        print(
            f"Standalone azauthlib {version} for {target.label}\nInstallation folder: {destination}"
        )
        if not args.check and not args.yes:
            if not sys.stdin.isatty():
                raise DesktopInstallError(
                    "Run interactively to confirm installation, or explicitly supply --yes."
                )
            question = (
                "Download and open setup? Installation starts when it opens. [y/N] "
                if native
                else "Download and open the setup wizard? [y/N] "
                if graphical
                else "Download and install the standalone desktop app? [y/N] "
            )
            if input(question).strip().lower() not in {"y", "yes"}:
                print("Cancelled. Nothing was installed.")
                return 0
        release = (
            resolve_release(version, target, native_installer=True)
            if native
            else resolve_release(version, target)
        )
        if args.check:
            name = target.installer_name(version) if native else target.asset_name(version)
            print(f"Available: {name} ({release.size / 1024**2:.1f} MiB)")
            return 0
        if not graphical:
            validate_destination(destination)
        with tempfile.TemporaryDirectory(prefix="azauthlib-desktop-download-") as temporary:
            archive = Path(temporary) / (
                target.installer_name(version) if native else target.asset_name(version)
            )
            with archive.open("xb") as stream:
                print("Downloading and verifying the standalone bundle...", flush=True)
                _download(
                    release.download_url, stream, limit=release.size, expected_size=release.size
                )
            if native:
                return run_native_setup(archive, release)
            if graphical:
                return run_graphical_setup(archive, release, destination, shortcut=args.shortcut)
            executable = install_archive(archive, release, destination)
        open_path = executable.parents[2] if target.system == "macos" else executable
        print(
            f"Desktop app installed. Open:\n{open_path}\n"
            "This app does not need your Python environment to remain installed."
        )
        shortcut = args.shortcut
        if not shortcut and not args.yes and sys.stdin.isatty():
            shortcut = input("Create an app shortcut? [y/N] ").strip().lower() in {"y", "yes"}
        if shortcut:
            try:
                print(create_shortcut(executable).message)
            except (OSError, RuntimeError) as error:
                print(
                    f"The app was installed, but its shortcut could not be created: {error}",
                    file=sys.stderr,
                )
        if target.system in {"windows", "macos"}:
            print(
                "Your operating system may require publisher approval. "
                "This command does not bypass security checks."
            )
        return 0
    except (KeyboardInterrupt, EOFError):
        print("Cancelled.", file=sys.stderr)
        return 130
    except (
        DesktopInstallError,
        BadZipFile,
        requests.RequestException,
        OSError,
        ValueError,
        KeyError,
        tarfile.TarError,
    ) as error:
        print(f"Desktop setup: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
