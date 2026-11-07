# Optional standalone desktop setup

The Python package and the standalone desktop application are separate distributions.
Installing or importing the Python package never downloads, starts or installs a desktop
bundle automatically. Existing `azauthlib-app` and `python -m azauthlib.gui.launch` behavior
is unchanged.

## Install an available desktop release

After installing the library, explicitly run:

```bash
azauthlib-install-desktop
```

The command detects the operating system and processor architecture and asks for permission
before downloading. It verifies the matching release download before opening setup. Keep
the terminal open until setup finishes. Normal library installation never runs this command.

### Automatic Windows setup

The normal Windows download is `azauthlib-desktop-VERSION-windows-x86_64-setup.exe`.
It can be opened directly without Python, or downloaded by `azauthlib-install-desktop`.
Opening this executable starts installation immediately:

1. A fixed-size white branded window appears and starts a background installation worker.
   The endorsed azauthlib logo sits at the top left; the transparent garden mascot appears
   in the center. Neither image is recolored or flattened onto a background.
2. The embedded MSI is extracted, verified and installed with Windows Installer's own
   wizard suppressed. The thin green bar shows activity during unpacking, then follows
   Windows Installer's progress estimates, including reverse movement during rollback.
3. Windows Installer installs the app for the current user in
   `%LOCALAPPDATA%\azauthlib\desktop\app` and creates a **Start Menu entry only**.
4. Setup reports completion and closes. The app does **not** open automatically.

Closing the active setup window asks whether to cancel. Setup waits for Windows Installer
to complete cancellation and rollback; it does not terminate the installation worker.
The cancelled result remains visible with an **Aborted** status until the window is closed.
Successful setup still closes automatically without opening the app. The window can be
dragged or minimized, but cannot be resized or maximized.
It opens centered in the usable work area of the monitor under the mouse pointer,
accounting for display scaling and the taskbar. The local `test_uninstall.cmd` likewise
centers the Windows Installer removal dialog when it appears. Positioning happens once
per window, so dragging it afterward does not cause it to snap back.
Failed or cancelled upgrades restore the previous managed application files. Close the
running app before upgrading; files in use cause setup to cancel rather than force-close it.
Successful installation can be removed through Windows **Installed apps**. Installation,
upgrade and removal do not remove profiles, credentials or certificates outside the managed
application directory.

The temporary extraction folder is removed after the transaction. A verified source MSI is
retained under `%LOCALAPPDATA%\azauthlib\installer-cache\SHA256\azauthlib.msi` for later
repair, upgrade and rollback. Leave this cache in place while the app is installed. Cache
packages are retained after removal and can then be deleted manually; they contain the
application distribution, not saved profiles or credentials.

This flow requests no administrator elevation and does not create a Desktop shortcut.
Windows may still show security warnings or enforce machine policy. The download includes
the entire application and its runtime; it is not a small online bootstrap download.

### Options-based setup

The existing wizard remains available on Windows with `azauthlib-install-desktop --wizard`.
It is the default graphical flow on macOS and Linux. It uses the verified archive's own
runtime; the command does not import Qt to display it. This is a Qt wizard, not an NSIS
installer, and the existing Windows ZIP remains its separate download.

In this setup window:

1. Choose a new installation folder. **Browse** selects a parent folder and proposes a
   versioned subfolder; nothing is installed until **Install** is clicked.
2. Optionally select a shortcut: Desktop on Windows; a Desktop launcher that can be added
   to the Dock on macOS; applications-menu entry and a Desktop copy if available on Linux.
3. Click **Install**. Verification and extraction run in a background worker so setup stays
   responsive. Closing/cancelling is disabled while files are being installed.
4. Optionally select **Launch azauthlib when I click Finish**, then click **Finish**.

Both shortcut creation and launching are unchecked by default. Cancel before **Install**
leaves no installation or shortcut. An existing shortcut is preserved; a shortcut failure
is explained on the result page without removing a successfully installed app. Temporary
download/runtime files are removed after the setup window exits.

When launch is selected, **Finish** starts the installed executable as an independent
process and closes setup without waiting for the app to exit. It does not reuse the
temporary setup runtime. Close an older running instance before testing a newly built app;
single-instance activation otherwise restores that existing instance.

The standalone application includes its Python runtime and dependencies. Removing the
Python environment that ran the setup command does not remove or disable that application.
The existing Python-based GUI still requires its Python environment.

Check availability without installing or creating shortcuts:

```bash
azauthlib-install-desktop --check
```

For explicitly approved unattended setup:

```bash
azauthlib-install-desktop --yes --shortcut
```

`--yes` approves installation only; without `--shortcut`, unattended setup does not create
shortcuts. `--release 5.0.1` selects a specific stable release. By default the command uses
the installed library's version. `--install-dir PATH` selects a **new** destination;
existing directories and existing shortcuts are never overwritten.

For terminal-only questions, use `azauthlib-install-desktop --terminal`. To approve the
download without a terminal prompt but keep the graphical installation choices, use
`azauthlib-install-desktop --yes --wizard`. `--shortcut` preselects that option in the wizard;
it can still be unchecked before **Install**. Unattended/terminal mode never launches the app.

The options-based and terminal setup's default installation folder is a versioned `desktop` subdirectory of the current
user's application-data directory for `azauthlib`, without a vendor directory. On Windows
this is `%LOCALAPPDATA%\azauthlib\desktop\VERSION\windows-x86_64`. No administrator access
is requested. Existing installations in other folders are not moved or removed automatically.
Profiles, credentials, certificate files and their existing storage locations are not
changed by the installer. A subsequently launched app uses the normal azauthlib profile
and credential-store behavior.

### Availability

The setup command requires matching desktop assets on the official GitHub release.
Previously published releases, including `v5.0.0`, do not currently include those assets.
Until a new command/package and its corresponding desktop bundles are released, use a
source checkout to test the command and the existing `azauthlib-app` to open the GUI.
An unavailable asset produces an explanation, not a partial installation or a fallback
that pretends to be standalone.

The graphical wizard requires a compatible `desktop-setup.json` marker inside the verified
archive. Older bundles without this marker are not executed as installers; `--terminal`
remains available for compatible archive-only releases.

Build targets are Windows x86-64, macOS Apple Silicon and Intel, and x86-64 Linux with
glibc 2.35 or later. Support for older operating systems is not implied. Linux still needs native graphics
libraries and a working desktop session. Musl-based Linux and ARM Windows/Linux bundles
are not provided by this build matrix.

## Safety and updates

- Downloads are restricted to the official repository's release assets over verified HTTPS.
  Environment-provided proxy/authentication settings are not consumed by this downloader.
- Each archive or native installer must match its release's SHA-256 checksum and declared
  download size. The Windows host also verifies its embedded MSI before invoking it.
- Archive expansion is bounded. Absolute paths, traversal, duplicate paths, special files
  and escaping symbolic links are rejected. Valid POSIX bundle links stay inside the app.
- Checksums protect download integrity, **not publisher identity** if a release account
  is compromised. They do not replace Windows signing or macOS signing/notarization.
- Operating-system security warnings and approval requirements remain in place; the
  command does not disable Gatekeeper, SmartScreen or other security protections.
- There is no background updater. The Windows MSI upgrades its stable managed application
  directory; archive-based setup uses new versioned directories. Existing archive-based
  installations are not migrated or removed by the MSI. When moving to a different app
  location, disable its launch-at-login setting first and recreate its shortcut explicitly.
- A manually selected standalone version must support the user's existing profile data;
  the setup command does not promise compatibility with older application versions.

The Windows automatic setup uses MSI and registers an OS uninstaller. The archive-based
wizard does not register one; macOS Installer packages and Linux package-manager integration
are not provided. To remove an archive installation, close the app, disable its login
startup option if enabled, remove its explicitly created shortcut, and remove that version's
installation folder. User profiles and credential-store entries are separate and retained.
Production signing/notarization is still required before distributing these development builds.
