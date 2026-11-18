# Certificate authentication

azauthlib supports certificate-based, app-only authentication using an RSA private key
and its matching certificate. Existing interactive, device-code and client-secret
connections remain available.

## Before you begin

- Use a tenant-specific Microsoft Entra application registration and its application
  (client) ID. Certificate authentication does not support `common`, `organizations`
  or `consumers` as the tenant.
- Register the public certificate with that application and configure the required
  application permissions and administrator consent.
- Keep the matching private key locally. A public `.cer` file alone cannot authenticate.
  Imported RSA keys must be at least 2048 bits, and the certificate must be currently
  valid and allow digital signatures when a key-usage extension is present.

## Configure a connection in the desktop application

1. Run `azauthlib-app`, choose Microsoft Graph and open Connections.
2. Add a connection or edit an existing one. Choose the certificate authentication method.
3. Enter the application and tenant identifiers, then select a certificate format:
   - **PFX/P12:** select the bundle containing the certificate and private key.
   - **PEM:** select the private-key file and a separate public certificate in PEM or DER format.
   - **Windows certificate store:** select **Current User** or **Local Machine** and paste the
     certificate's Windows thumbprint. See the Windows requirements below.
4. For certificate files, supply the private-key password or indicate that the file has no
   password. You can optionally remember the password in the operating system's credential
   manager. Windows store certificates use Windows key permissions.
5. Wait for local validation and save the connection. Use **Test connection** to check whether
   Microsoft Entra accepts the certificate.

The application checks that the key matches the certificate and displays the subject,
expiration and SHA-256 fingerprint. A changed certificate must be validated again.

## Use a certificate from the Windows Personal store

Use **Certificates – Current User** (`certmgr.msc`) or **Certificates – Local Computer**
(`certlm.msc`). Open **Personal → Certificates**, select the certificate, and copy
**Thumbprint** on the **Details** tab. This 40-digit Windows thumbprint selects the store
entry. azauthlib separately computes the SHA-256 fingerprint for authentication.

The certificate must have a Windows CNG RSA key of at least 2048 bits. The key's provider
must support RSA-PSS signing without an interactive prompt, and the Windows account running
azauthlib must have permission to use it. Compatible non-exportable keys work. Keys that
require a PIN dialog or use only a legacy CryptoAPI provider are unsupported. Register the
public certificate with your Microsoft Entra application.

From Python:

```python
from azauthlib import Authentication

auth = Authentication()
auth.Build.WithWindowsCertificate(
    client_id="00000000-0000-0000-0000-000000000001",
    tenant_id="00000000-0000-0000-0000-000000000002",
    thumbprint="0123456789ABCDEF0123456789ABCDEF01234567",
    store_location="CurrentUser",  # Or "LocalMachine"
)
result = auth.ClientCredentials()
```

Windows signs a fresh assertion when MSAL needs a token request. The private key stays in
Windows, and the connection stores the location, thumbprint and public certificate metadata.
Renew by registering the new public certificate in Entra and updating the saved thumbprint.

## Create a certificate in the app

The certificate editor can create an encrypted, self-signed RSA-3072 certificate.
The default validity is 90 days; choose a lifetime allowed by your organization.
Set and confirm a password and choose an output folder.

Creation uses a new subfolder and does not overwrite existing files. The output
includes the encrypted private PFX or PEM file, a public PEM certificate and a public
DER `.cer` certificate. Upload only the public certificate to Microsoft Entra.
Cancelling the connection editor after creation does not delete these files.

## Use a certificate from Python

For a PFX/P12 bundle:

```python
from getpass import getpass

from azauthlib import Authentication

auth = Authentication()
auth.Build.WithCertificate(
    client_id="00000000-0000-0000-0000-000000000001",
    tenant_id="00000000-0000-0000-0000-000000000002",
    key_path="/secure/path/application.pfx",
    password=getpass("Certificate password: "),
)
result = auth.ClientCredentials()
# Default resource scope: https://graph.microsoft.com/.default
```

For PEM files, set `format="pem"`, supply the private key as `key_path`, and pass
the matching public certificate as `certificate_path`. Omit `password` only when
the imported private key is not encrypted. Paths are local to the machine running Python.

`Build.WithCertificate(...)` validates the files but does not persist the supplied
password. A saved desktop certificate profile can instead be loaded with
`auth.Build.Default()`; use `Authentication(profile="profile-id")` to select a specific
profile. Unattended use of a password-protected saved profile requires its password
to be available through the operating system's credential manager.

## Storage and renewal

Profiles store certificate file paths or Windows store selectors, along with public metadata.
Remembered passwords are scoped to the profile and application in the operating
system's credential manager. Keep that credential backend available when using them.

Keep the private-key files at their configured locations with restricted permissions.
Never add private keys, PFX/P12 bundles, passwords or access tokens to source control.
Before a certificate expires, register its replacement in Microsoft Entra and update
and validate the connection. Removing a local profile does not revoke credentials
registered with Microsoft Entra.

See the [README](../README.md) for installation, profiles and token-cache security.
