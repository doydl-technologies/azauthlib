# Startup preferences

Settings → Advanced offers three independent, opt-in switches. All default to off.
General and Accessibility remain unavailable. Save preferences commits drafts from
both enabled tabs together; Cancel discards them. Reset to default resets only the
current tab's draft and still requires Save.

## Faster repeat launches

Reuses prepared bundled Terms, Privacy Policy and About content, plus rendered
service-logo thumbnails, across application launches. Preferences are always read
fresh. Connections, certificates, credentials, tokens, test history and profile
avatars are never stored in these disk startup caches. Unvisited services remain
deferred until opened; returning services may prepare in memory as described below.

The content cache is invalidated by source/loader changes. Logo cache keys include
the source path, file size and modification time, render dimensions and renderer
code revision. Missing, corrupt or unwritable caches fall back to the normal
load/render path. The logo cache is limited to 64 thumbnails. These files live in
the current user's application cache, not in the installation. Disabling this
option stops using them; it does not require deleting any user data.

Saving with this option enabled starts background preparation immediately, reusing
already-rendered logos from the current session when available. Advanced settings
shows preparation, completion or fallback status. Let preparation finish before
closing if you want the next launch to reuse it. Cache preparation failure does
not undo a successful preference save; the normal startup path remains available.

This is a disk-backed warm start, not a resident helper: closing the app still exits
normally. Startup time can still vary; Python, Qt, fonts and the UI must still
initialize, and a changed display/asset revision may need additional preparation.
Qt continues to manage its own compiled-QML cache. This option prepares shared app
content. After Main Menu has painted and is idle, it also prepares the Connections
page in memory for a supported service that has been successfully opened before.

### Previously visited services

Only a completed Open records a visit; selecting a card, cancelling loading,
existing saved profiles, and unsupported/unavailable services do not qualify.
Visit history stores only an allowlisted service ID in UI preferences. Existing
users need to open a service once after this feature is installed to establish
that history. Microsoft Graph is currently the only supported Connections service.

Background service preparation loads public profile/certificate settings and
avatar thumbnails, then asynchronously builds the hidden Connections controls.
It never signs in, tests a connection, accesses secrets/private certificate material,
or restores keyring-protected test outcomes. It does not activate a different
profile, open a browser or display prompts. Profiles are not added to the disk
startup cache. Main Menu and Settings remain usable during preparation.

Open supersedes any in-flight background worker and refreshes current profile,
secure-storage presence and saved result state through the normal foreground path.
The already-built interface and avatar cache are reused. Generation guards reject
late background results, including queued manager-opening callbacks. This avoids
stale public settings/active-profile selections and never overwrites edits or tests.
Background failures are quiet, tried at most once per service per session, and
leave the normal Open/Retry path available. Turning warm starts off cancels and
discards an unused background page; foreground-loaded pages retain normal behavior.

## Skip splash on fast launches

Starts preparing shared content immediately, without waiting for a splash frame.
If Main Menu readiness completes before the grace timer is serviced, no splash is
created and there is no artificial minimum splash delay. A 350 ms grace timer
covers shared preparation; it is paused during synchronous QML construction and
rearmed for asynchronous menu readiness. A queued preparation result wins over a
due splash timer, preventing a last-moment splash during the QML handoff. On slower
launches the existing splash is shown with the latest progress. If shown, it stays
for at least 400 ms after its first frame (with a 2 s render-backend failsafe), and
remains in place until the main window paints its first frame. Startup failures
always show the retry/abort interface, even when the splash was initially skipped.
The main window remains hidden until its required assets and interface are ready.
Single-instance locking and activation still run before startup work.

With this switch off, the original splash-first startup and minimum display timing
are preserved. Warm-start caching and splash suppression can be used separately.

## Open at login

Only an explicit changed preference followed by Save creates/removes the app's
current-user login registration. It opens the normal app, does not authenticate,
and does not create a hidden background process or require administrator rights.

- Windows: the app's named value in the current-user `Run` registry key.
- macOS: an app-managed per-user LaunchAgent with `RunAtLoad`, without `KeepAlive`.
- Linux: an app-managed `.desktop` entry in the user's XDG autostart directory.

Other startup apps and unrelated files are not changed. The current executable
and absolute app launcher path are used, so the installation and its runtime must
remain available. Turn the option off before moving/removing the installation;
enable it again from the new location if needed. Operating-system policy may
delay or block startup applications. An existing azauthlib instance is activated
instead of creating a second manager.

If login registration succeeds but preferences cannot be saved, the previous
registration is restored. Any rollback failure is shown in Settings rather than
reporting a successful save. Importing the module or launching the app never
silently registers/re-registers login startup.

Integration references: [Windows Run keys](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys),
[Apple per-user agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html),
[XDG autostart](https://specifications.freedesktop.org/autostart/latest/).
