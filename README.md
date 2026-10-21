<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/doydl-technologies/azauthlib/main/assets/png/azauthlib-endorsed-lockup-light-989x308.png">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/doydl-technologies/azauthlib/main/assets/png/azauthlib-endorsed-lockup-dark-989x308.png">
    <img src="https://raw.githubusercontent.com/doydl-technologies/azauthlib/main/assets/png/azauthlib-endorsed-lockup-dark-989x308.png" alt="azauthlib — powered by DOYDL Technologies" width="700">
  </picture>
</p>

<p align="center">
  Secure Microsoft identity platform authentication helpers built on
  <a href="https://github.com/AzureAD/microsoft-authentication-library-for-python">MSAL for Python</a>.
</p>

<p align="center">
  <a href="https://pypi.org/project/azauthlib/"><img src="https://img.shields.io/pypi/v/azauthlib" alt="PyPI version"></a>
  <a href="https://pypi.org/project/azauthlib/"><img src="https://img.shields.io/pypi/pyversions/azauthlib" alt="Supported Python versions"></a>
  <a href="https://pepy.tech/project/azauthlib"><img src="https://static.pepy.tech/badge/azauthlib" alt="Downloads"></a>
  <a href="https://github.com/doydl-technologies/azauthlib/actions/workflows/ci.yml"><img src="https://github.com/doydl-technologies/azauthlib/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/doydl-technologies/azauthlib" alt="License"></a>
  <a href="https://doydl.studio"><img src="https://img.shields.io/badge/Powered%20by-DOYDL%20Technologies-blue" alt="Powered by DOYDL Technologies"></a>
</p>

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Desktop application](#desktop-application)
- [Public-client authentication](#public-client-authentication)
- [Device-code authentication](#device-code-authentication)
- [Client-credentials authentication](#client-credentials-authentication)
- [Configuration](#configuration)
- [Upgrading from 1.4.0b1](#upgrading-from-140b1)
- [Token-cache security](#token-cache-security)
- [Error handling](#error-handling)
- [Development](#development)
- [License](#license)

## Features

- Interactive, silent, device-code, and client-credentials authentication.
- Encrypted, cross-process-safe token persistence through MSAL Extensions.
- Client secrets stored in the operating-system credential manager.
- Exact-path `.env` loading; no upward directory search.
- Delegated and application scope handling kept separate.
- No filesystem writes or global logging configuration during import.

## Installation

```bash
python -m pip install azauthlib
```

**Optional first-time setup:** To configure your connections using a graphical interface,
run the following command in the environment where azauthlib is installed:

```bash
azauthlib-app
```

The GUI is optional. You can instead configure credentials through Python or environment
variables, as shown below. See [Desktop application](#desktop-application) for more details.

From a source checkout:

```bash
git clone git@github.com:doydl-technologies/azauthlib.git
cd azauthlib
python -m pip install .
```

Python 3.10 or newer is required.

## Desktop application

Open the Connections Manager from a terminal in the environment where azauthlib is installed:

```bash
azauthlib-app
```

Alternatively, run `python -m azauthlib.gui.launch` with that environment's Python.
No Python code is needed to use the application.

Choose **Create app shortcut** in the top-right corner of Home or Connections to create
a launcher for your user account:

- **Windows:** an `azauthlib.lnk` Desktop shortcut with the application icon.
- **macOS:** an `azauthlib.app` Desktop launcher that can also be added to the Dock.
- **Linux:** an applications-menu entry and a Desktop copy when a Desktop folder is available.
  The desktop environment may require approval before launching the Desktop copy.

Shortcut creation is optional and does not run during installation, import, or startup.
Existing files with the same name are not overwritten. These launchers use the current
Python environment, rather than bundling Python; keep that environment installed at the
same location. If it moves, remove the old launcher and create another from the new environment.

## Public-client authentication

```python
from azauthlib import Authentication, InteractionRequiredError

auth = Authentication(scopes=["User.Read"])
auth.Build.WithEntry(
    client_id="00000000-0000-0000-0000-000000000000",
    tenant_id="organizations",
)

try:
    result = auth.Silent()
except InteractionRequiredError:
    result = auth.Interactive()

print(result["token_source"])
# Use auth.access_token only where an Authorization header is required.
```

Silent authentication does not unexpectedly launch a browser. Pass
`fallback_to_interactive=True` if that behavior is explicitly desired.

## Device-code authentication

```python
auth = Authentication(scopes=["Files.Read"])
auth.Build.WithEntry(client_id="...", tenant_id="organizations")
result = auth.DeviceCodeFlow(webbrowser_enabled=True)
```

MSAL controls polling and expiration. The method blocks until authentication completes or fails.

## Client-credentials authentication

Microsoft requires the `/.default` resource scope for client credentials:

```python
auth = Authentication()
auth.Build.WithEntry(
    client_id="...",
    tenant_id="...",
    client_secret="...",
)
result = auth.ClientCredentials()
# Default scope: https://graph.microsoft.com/.default
```

For production workloads, prefer a certificate or workload identity federation over a shared
secret when your deployment architecture supports it.

## Configuration

Environment variables are supported:

```bash
export CLIENT_ID="..."
export TENANT_ID="..."
export CLIENT_SECRET="..." # confidential clients only
```

```python
auth = Authentication(scopes=["User.Read"])
auth.Build.WithOSEnv()
```

`WithOSEnv()` treats mapping values strictly as environment-variable names. Use `WithEntry()` for
literal values.

The optional configuration application stores the client ID and tenant ID in azauthlib's platform
configuration directory. Client secrets go to the operating-system keyring, never the `.env` file:

```bash
azauthlib-app
```

The application supports named profiles for multiple Microsoft Entra app registrations.
After the splash screen, choose Microsoft Graph on the Home page to open the Connections
Manager. Add, edit, optionally test, remove, and set the active connection there. Other service
cards are previews and cannot continue yet. Information buttons open a contextual-help shelf that
pushes the workspace aside. It explains profiles, authentication methods, connection testing,
and where to find your Entra app registration's Tenant/Directory ID, Client/Application ID,
and client secret. The active info button is dimmed and disabled while its topic is open.
Close the shelf with its close button, Got it, or Escape, or select another topic.

The Test connection icon is blue for untested saved credentials, green for the last successful
test, and red for the last failed test. Changing credentials resets the indicator; renaming a
connection does not. Canceling a retest preserves the previous completed result. This is test
history, not a guarantee that authentication or every Microsoft Graph operation will work now.
History stores only outcomes and signed, opaque credential fingerprints, with its signing key
in the OS credential manager. Tests do not persist tokens or client secrets. When history storage
is unavailable, results are kept for the current session only.
The `Default` profile uses `.env` and `msal-cache.bin` directly in the current configuration
and cache directories. Every additional profile receives its own public configuration file
and encrypted MSAL token cache; client secrets
remain in the operating-system keyring. Create and select profiles in the configuration app, or
manage the active profile in Python:

```python
from azauthlib import Authentication, create_profile, select_profile
from azauthlib.credentials import save_configuration

profile = create_profile("Accounting")
save_configuration(
    profile=profile,
    client_id="00000000-0000-0000-0000-000000000000",
    tenant_id="organizations",
    auth_method="interactive",
)
select_profile("Accounting")

# Explicit profile selection is recommended when several applications share a process.
auth = Authentication(profile="Accounting", scopes=["User.Read"])
auth.Build.Default()
```

Passing `profile=` avoids depending on whichever profile is currently selected in the GUI.

## Upgrading from 1.4.0b1

On Windows, the default configuration and cache directories no longer include the additional
vendor directory. Existing settings are not automatically migrated. To upgrade safely:

1. Close azauthlib and any applications using its token cache.
2. Back up the existing configuration and cache directories. The previous Windows configuration
   directory is normally `%LOCALAPPDATA%\DOYDL Technologies\azauthlib`; its cache is normally
   the `Cache` subdirectory. Keep these backups private because they contain authentication data.
3. Install the update, run `azauthlib-app`, and recreate the required connections using the saved
   tenant ID, client ID, and authentication method. The new configuration directory is normally
   `%LOCALAPPDATA%\azauthlib`, with its cache in the `Cache` subdirectory. Do not delete the old
   files until the new connections have been verified.
4. Test each connection and sign in again where required. Client secrets remain in the operating
   system's keyring, keyed by client ID. If a secret cannot be retrieved, enter it again through
   the application; never put it in a public configuration file.

macOS and Linux keep their platform-specific configuration/cache roots. The Default profile
uses the existing root-level files there; additional profiles use separate files. An explicitly
supplied environment-file or token-cache path remains under the caller's control.

New authentication instances use the active profile unless `profile=` is supplied. Select an
explicit profile for applications that must not follow desktop selection changes. After all
profiles have been removed, create a profile before constructing an authentication instance.
Removing a profile archives its known local files; it does not revoke issued tokens or erase
shared client secrets from the keyring.

## Token-cache security

Encrypted persistence is the default and fails closed when the OS encryption provider is
unavailable. On Linux, ensure an appropriate Secret Service/LibSecret backend is configured.

Plaintext fallback requires an explicit opt-in:

```python
auth = Authentication(allow_plaintext_cache=True)
```

Only use that option when file permissions and the threat model have been independently reviewed.

## Error handling

Authentication methods return the successful MSAL result dictionary. Failures raise:

- `AuthenticationError` for identity platform or protocol errors.
- `InteractionRequiredError` when silent authentication cannot continue.
- `TokenCacheSecurityError` when secure persistence cannot be established.

Error logs include error codes and correlation IDs, not full response dictionaries or tokens.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
bandit -c pyproject.toml -r src
pip-audit --skip-editable
pytest
python -m build
twine check dist/*
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[CHANGELOG.md](CHANGELOG.md). Maintainers should also follow [RELEASING.md](RELEASING.md).

## License

Apache License 2.0. Microsoft, Azure, Entra, and Microsoft Graph are trademarks of Microsoft and
are not affiliated with or endorsed by this project.
