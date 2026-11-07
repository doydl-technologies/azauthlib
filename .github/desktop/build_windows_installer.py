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

"""Author a per-user MSI and embed it in an immediate, native Windows setup host.

Uses WiX candle/light-compatible tools supplied explicitly by WIX_BIN and MSYS2
UCRT64 g++/windres. No tools, installers or signing credentials are downloaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NS = "http://wixtoolset.org/schemas/v4/wxs"
UPGRADE_CODE = "{BA5DCD3A-9931-4B52-B1B2-4C2D753EC030}"
ET.register_namespace("", NS)


def node(parent, tag, **attrs):
    return ET.SubElement(parent, "{" + NS + "}" + tag, attrs)


def identity(prefix, value):
    return prefix + hashlib.sha256(value.encode()).hexdigest()[:28]


def author(payload, version, output, *, test_root=None, upgrade_code=UPGRADE_CODE):
    """Keep managed application files separate from all profile/cache/credential data."""
    parts = version.split(".")
    if len(parts) != 3 or any(not p.isdigit() for p in parts):
        raise ValueError("MSI version must contain three numeric fields")
    if any(int(p) > limit for p, limit in zip(parts, (255, 255, 65535), strict=True)):
        raise ValueError("Version exceeds Windows Installer limits")
    payload = payload.resolve()
    if not (payload / "azauthlib.exe").is_file():
        raise ValueError("Use a verified standalone Windows bundle directory")
    document = ET.Element("{" + NS + "}Wix")
    name = "azauthlib Desktop" if test_root is None else "azauthlib Installer Test " + output.name
    product_id = "{" + str(uuid.uuid4()).upper() + "}"
    product = node(
        document,
        "Product",
        Id=product_id,
        Name=name,
        Language="1033",
        Version=version,
        Manufacturer="DOYDL Technologies",
        UpgradeCode=upgrade_code,
    )
    node(
        product,
        "Package",
        InstallerVersion="500",
        Compressed="yes",
        InstallScope="perUser",
        Platform="x64",
        Description=name,
    )
    node(product, "MediaTemplate", EmbedCab="yes", CompressionLevel="high")
    node(
        product,
        "MajorUpgrade",
        Schedule="afterInstallExecute",
        AllowSameVersionUpgrades="yes",
        RemoveFeatures="ALL",
        DowngradeErrorMessage="A newer version of azauthlib Desktop is already installed.",
    )
    node(product, "Property", Id="ARPNOMODIFY", Value="1")
    # Only immutable app resources are managed here. Force their replacement
    # even after rollback changes an unversioned file's creation timestamp.
    node(product, "Property", Id="REINSTALLMODE", Value="amus")
    node(product, "Property", Id="MSIRESTARTMANAGERCONTROL", Value="Disable")
    node(product, "Property", Id="ARPURLINFOABOUT", Value="https://doydl.studio")
    node(product, "Property", Id="ARPPRODUCTICON", Value="AppIcon")
    node(
        product,
        "Icon",
        Id="AppIcon",
        SourceFile=str(ROOT / "src/azauthlib/assets/azauthlib-taskbar.ico"),
    )
    condition = node(
        product, "Condition", Message="azauthlib Desktop requires 64-bit Windows 10 or later."
    )
    build_number = node(product, "Property", Id="WINDOWS_BUILD")
    node(
        build_number,
        "RegistrySearch",
        Id="WindowsBuildNumber",
        Root="HKLM",
        Key=r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        Name="CurrentBuildNumber",
        Type="raw",
        Win64="yes",
    )
    condition.text = "Installed OR (VersionNT64 AND WINDOWS_BUILD >= 10240)"
    target = node(product, "Directory", Id="TARGETDIR", Name="SourceDir")
    if test_root is None:
        local = node(target, "Directory", Id="LocalAppDataFolder")
        app = node(local, "Directory", Id="AzauthlibRoot", Name="azauthlib")
        desktop = node(app, "Directory", Id="DesktopRoot", Name="desktop")
        install = node(desktop, "Directory", Id="INSTALLFOLDER", Name="app")
        program_menu = node(target, "Directory", Id="ProgramMenuFolder")
        menu = node(program_menu, "Directory", Id="AppMenu", Name="azauthlib")
    else:
        install = node(target, "Directory", Id="INSTALLFOLDER", Name="app")
        menu = node(target, "Directory", Id="AppMenu", Name="menu")
        node(product, "Property", Id="INSTALLFOLDER", Value=str(test_root / "app"))
        node(product, "Property", Id="AppMenu", Value=str(test_root / "menu"))
        sequence = node(product, "InstallExecuteSequence")
        node(
            product,
            "CustomAction",
            Id="InjectedFailure",
            Directory="INSTALLFOLDER",
            ExeCommand='"[SystemFolder]cmd.exe" /d /c exit 1',
            Execute="deferred",
            Impersonate="yes",
            Return="check",
        )
        custom = node(sequence, "Custom", Action="InjectedFailure", After="InstallFiles")
        custom.text = 'AZ_TEST_FAIL = "1"'
    feature = node(product, "Feature", Id="Desktop", Title=name, Level="1")
    directories = {Path("."): install}
    seen = set()
    registry = (
        r"Software\DOYDL Technologies\azauthlib\DesktopInstaller"
        if test_root is None
        else r"Software\DOYDL Technologies\azauthlib\InstallerTests" + "\\" + str(test_root.name)
    )
    for path in sorted(payload.rglob("*")):
        if path.is_symlink():
            raise ValueError("Windows MSI input must not contain symbolic links")
        if not path.is_file():
            continue
        relative = path.relative_to(payload)
        key = relative.as_posix().casefold()
        if key in seen:
            raise ValueError("Duplicate Windows file path")
        seen.add(key)
        chain = list(relative.parent.parents)[::-1] + [relative.parent]
        for folder in chain:
            if folder == Path(".") or folder in directories:
                continue
            directories[folder] = node(
                directories[folder.parent],
                "Directory",
                Id=identity("D", folder.as_posix()),
                Name=folder.name,
            )
        component_id = identity("C", key)
        component = node(
            directories[relative.parent],
            "Component",
            Id=component_id,
            Guid=str(uuid.uuid5(uuid.UUID(upgrade_code.strip("{}")), key)),
            Win64="yes",
        )
        node(
            component,
            "RegistryValue",
            Root="HKCU",
            Key=registry,
            Name=component_id,
            Type="integer",
            Value="1",
            KeyPath="yes",
        )
        node(component, "File", Id=identity("F", key), Source=str(path), Name=path.name)
        node(feature, "ComponentRef", Id=component_id)
    component = node(
        menu,
        "Component",
        Id="StartMenu",
        Guid=str(uuid.uuid5(uuid.UUID(upgrade_code.strip("{}")), "startmenu")),
        Win64="yes",
    )
    node(
        component,
        "Shortcut",
        Id="AppShortcut",
        Name=name,
        Target="[INSTALLFOLDER]azauthlib.exe",
        WorkingDirectory="INSTALLFOLDER",
        Icon="AppIcon",
        Advertise="no",
    )
    node(component, "RemoveFolder", Id="RemoveMenu", On="uninstall")
    node(
        component,
        "RegistryValue",
        Root="HKCU",
        Key=registry,
        Name="StartMenu",
        Type="integer",
        Value="1",
        KeyPath="yes",
    )
    node(feature, "ComponentRef", Id="StartMenu")
    cleanup = node(
        install,
        "Component",
        Id="DirectoryCleanup",
        Guid=str(uuid.uuid5(uuid.UUID(upgrade_code.strip("{}")), "directory-cleanup")),
        Win64="yes",
    )
    node(
        cleanup,
        "RegistryValue",
        Root="HKCU",
        Key=registry,
        Name="DirectoryCleanup",
        Type="integer",
        Value="1",
        KeyPath="yes",
    )
    owned = [directory.get("Id") for directory in directories.values()]
    if test_root is None:
        owned += ["AzauthlibRoot", "DesktopRoot"]
    for directory in owned:
        node(
            cleanup,
            "RemoveFolder",
            Id=identity("R", directory),
            Directory=directory,
            On="uninstall",
        )
    node(feature, "ComponentRef", Id="DirectoryCleanup")
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(document)
    ET.ElementTree(document).write(output, encoding="utf-8", xml_declaration=True)
    return product_id


def run(command, *, env=None):
    subprocess.run(list(map(str, command)), env=env, check=True)


def build(payload, output, version, *, wix_bin=None, test_root=None, upgrade_code=UPGRADE_CODE):
    if sys.platform != "win32":
        raise RuntimeError("Build native Windows installers on Windows")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    wix = Path(wix_bin or os.environ.get("WIX_BIN", ""))
    tools = [wix / "candle.exe", wix / "light.exe"]
    compiler = Path(os.environ.get("MSYS2_UCRT64_BIN", "C:/msys64/ucrt64/bin"))
    tools += [compiler / "g++.exe", compiler / "windres.exe"]
    if any(not tool.is_file() for tool in tools):
        raise RuntimeError(
            "Set WIX_BIN to candle/light-compatible WiX tools and provide MSYS2 UCRT64"
        )
    env = dict(os.environ)
    env["PATH"] = str(compiler) + os.pathsep + env.get("PATH", "")
    source = output / "desktop.wxs"
    product_id = author(payload, version, source, test_root=test_root, upgrade_code=upgrade_code)
    stem = f"azauthlib-desktop-{version}-windows-x86_64"
    msi = output / (stem + ".msi")
    run([tools[0], "-nologo", "-arch", "x64", "-out", output / "desktop.wixobj", source])
    run([tools[1], "-nologo", "-out", msi, output / "desktop.wixobj"])
    exe = build_host(msi, output, version, test_only=test_root is not None)
    (output / "build-report.json").write_text(
        json.dumps(
            {
                "version": version,
                "product_id": product_id,
                "upgrade_code": upgrade_code,
                "test_only": test_root is not None,
                "installer": str(exe),
                "msi": str(msi),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return exe, msi, product_id


def build_host(msi, output, version, *, test_only=False):
    """Rebuild the branded host independently of an unchanged, verified MSI payload."""
    if sys.platform != "win32":
        raise RuntimeError("Build native Windows installers on Windows")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    msi = msi.resolve()
    brand = ROOT / "assets/png/azauthlib-endorsed-lockup-dark-989x308.png"
    mascot = ROOT / "src/azauthlib/assets/logo/png/mascot-garden.png"
    compiler = Path(os.environ.get("MSYS2_UCRT64_BIN", "C:/msys64/ucrt64/bin"))
    if any(not path.is_file() for path in (msi, brand, mascot)):
        raise RuntimeError("The MSI payload, endorsed logo and transparent mascot PNG are required")
    if msi.parent != output:
        target = output / msi.name
        if target.exists():
            raise RuntimeError(
                "Use a fresh host output directory; existing MSI files are preserved"
            )
        shutil.copy2(msi, target)
        msi = target
    env = dict(os.environ)
    env["PATH"] = str(compiler) + os.pathsep + env.get("PATH", "")
    stem = f"azauthlib-desktop-{version}-windows-x86_64"
    digest = hashlib.sha256(msi.read_bytes()).digest()
    (output / "payload-digest.bin").write_bytes(digest)
    rc = output / "resources.rc"
    manifest = output / "setup.manifest"
    manifest.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">'
        '<trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges>'
        '<requestedExecutionLevel level="asInvoker" uiAccess="false"/>'
        "</requestedPrivileges></security></trustInfo>"
        '<application xmlns="urn:schemas-microsoft-com:asm.v3"><windowsSettings>'
        '<longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>'
        "</windowsSettings></application></assembly>",
        encoding="utf-8",
    )
    numeric_version = version.replace(".", ",") + ",0"

    def resource_path(path):
        return str(path).replace("\\", "/").replace('"', '\\"')

    rc.write_text(
        '#include <windows.h>\n1 ICON "'
        + resource_path(ROOT / "src/azauthlib/assets/azauthlib-taskbar.ico")
        + '"\n'
        '1 RT_MANIFEST "' + resource_path(manifest) + '"\n'
        '101 RCDATA "' + resource_path(msi) + '"\n102 RCDATA "' + resource_path(brand) + '"\n'
        '103 RCDATA "' + resource_path(output / "payload-digest.bin") + '"\n'
        '104 RCDATA "' + resource_path(mascot) + '"\n'
        f"1 VERSIONINFO\nFILEVERSION {numeric_version}\nPRODUCTVERSION {numeric_version}\n"
        'FILETYPE 1\nBEGIN\nBLOCK "StringFileInfo"\nBEGIN\nBLOCK "040904B0"\nBEGIN\n'
        'VALUE "CompanyName", "DOYDL Technologies"\n'
        'VALUE "FileDescription", "azauthlib Desktop Setup"\n'
        f'VALUE "FileVersion", "{version}"\nVALUE "ProductVersion", "{version}"\n'
        'VALUE "ProductName", "azauthlib Desktop"\nEND\nEND\n'
        'BLOCK "VarFileInfo"\nBEGIN\nVALUE "Translation", 0x409, 1200\nEND\nEND\n',
        encoding="utf-8",
    )
    resource = output / "resources.o"
    run([compiler / "windres.exe", "-i", rc, "-O", "coff", "-o", resource], env=env)
    exe = output / (stem + "-setup.exe")
    command = [
        compiler / "g++.exe",
        "-std=c++17",
        "-O2",
        "-municode",
        "-mwindows",
        "-static",
        "-static-libgcc",
        "-static-libstdc++",
        "-D_WIN32_WINNT=0x0A00",
    ]
    if test_only:
        command.append("-DAZAUTHLIB_INSTALLER_TEST")
    command += [
        ROOT / ".github/desktop/native/windows_setup.cpp",
        resource,
        "-o",
        exe,
        "-lgdiplus",
        "-lmsi",
        "-lbcrypt",
        "-lshell32",
        "-lole32",
        "-luuid",
        "-lgdi32",
        "-luser32",
    ]
    run(command, env=env)
    extracted = output / "verified-payload.msi"
    run([exe, "--verify-payload", extracted])
    if hashlib.sha256(extracted.read_bytes()).digest() != digest:
        raise RuntimeError("Embedded MSI does not match the authored payload")
    extracted.unlink()
    for state in ("", "-rollback", "-cancelled", "-complete"):
        run([exe, "--preview" + state, output / ("installer-preview" + state + ".png")])
    for artifact in (msi, exe):
        (output / (artifact.name + ".sha256")).write_text(
            hashlib.sha256(artifact.read_bytes()).hexdigest() + "  " + artifact.name + "\n",
            encoding="utf-8",
        )
    return exe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default=None)
    parser.add_argument("--wix-bin", type=Path)
    args = parser.parse_args()
    from azauthlib.gui.desktop_install import current_version

    build(args.payload, args.output, args.version or current_version(), wix_bin=args.wix_bin)


if __name__ == "__main__":
    main()
