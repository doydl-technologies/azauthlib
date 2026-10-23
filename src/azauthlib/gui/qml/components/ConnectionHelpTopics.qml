import QtQuick

// Fixed explanatory text only: no profile values, secrets, or network content.
QtObject {
    readonly property var topics: ({
        terms: {
            title: "Terms of Use", subtitle: "azauthlib desktop application terms", icon: "info"
        },
        privacy: {
            title: "Privacy Policy", subtitle: "Desktop privacy and information handling", icon: "info"
        },
        about: {
            title: "About azauthlib", subtitle: "Independence and third-party notices", icon: "info"
        },
        shortcut: {
            title: "Create app shortcut", subtitle: "An easier way to open azauthlib", icon: "info",
            description: "Use this button to add an azauthlib shortcut to your Desktop. Next time, open the app from that shortcut instead of starting it from a terminal. On Linux, it also adds azauthlib to your application menu.",
            noteTitle: "Your connections stay the same",
            note: "Creating a shortcut does not change your saved connections or install another copy of the app. You can delete the shortcut at any time without deleting azauthlib or your connections.",
            section: "Using the shortcut",
            steps: ["Click the shortcut button once and wait for a message confirming it was created.", "Look for <b>azauthlib</b> on your Desktop, then double-click it to open the app. If azauthlib is already open, its window is brought to the front.", "If a shortcut with the same name already exists, you will see a message instead. Nothing is replaced; you can keep using the existing shortcut.", "On Linux, you can also open azauthlib from your application menu. Your computer may ask you to allow the Desktop shortcut before you can use it."]
        },
        profiles: {
            title: "Saved connections", subtitle: "Select the profile you want to work with", icon: "plug",
            description: "Each connection stores the authentication settings for one application or environment. Selecting a profile shows its details; it does not automatically make it active.",
            noteTitle: "Selected vs. active",
            note: "The highlighted profile is the one you are viewing. Choose <b>Set Active</b> to change the default connection used by azauthlib.",
            section: "Working with profiles",
            steps: ["Select a saved connection to inspect its settings.", "Use <b>Add connection</b> to create a separate profile without overwriting another.", "Choose <b>Edit</b> to change a profile, or <b>Set Active</b> to activate it."]
        },
        name: {
            title: "Connection name", subtitle: "A friendly label for this saved profile", icon: "edit",
            description: "This name identifies the saved connection inside azauthlib. Use it to distinguish applications, tenants, or environments.",
            noteTitle: "Naming tip", note: "This label is for your own organization. It is not a Microsoft Entra identifier and does not change the app registration.",
            section: "Good naming practices",
            steps: ["Choose a short, unique name you will recognize later.", "Include an application or environment, such as <b>Operations – Production</b>.", "Edit the name when the connection’s purpose changes."]
        },
        auth: {
            title: "Authentication method", subtitle: "How the application signs in", icon: "lock",
            description: "Choose a sign-in flow that matches your Microsoft Entra app registration. The application can sign in a user or obtain a token for itself.",
            noteTitle: "Know the difference",
            note: "<b>Interactive</b> and <b>Device code</b> sign in a person and use delegated permissions. <b>Client credentials</b> signs in the app and requires administrator-consented application permissions.",
            section: "Available sign-in flows",
            steps: ["<b>Interactive</b> — sign in as a user in a browser. No client secret.", "<b>Device code</b> — enter the displayed code at the sign-in page, on this or another device. No client secret.", "<b>Client credentials — Secret</b> — app-only sign-in with a specific tenant, Application (client) ID, and client secret.", "<b>Client credentials — Certificate</b> — app-only sign-in using a PFX/P12 or a PEM private key and matching public certificate. Upload only the public certificate to Entra. Private files stay on this computer; optionally remember their password in OS secure storage. Use your own app registration, not a shared private key distributed to users."]
        },
        tenant: {
            title: "Tenant ID", subtitle: "Microsoft Entra directory identifier", icon: "info",
            description: "Tenant ID is also known as Directory ID. Microsoft Entra labels it Directory (tenant) ID. It identifies the directory used for sign-in, not the app itself.",
            noteTitle: "Sign-in audience",
            note: "Client credentials requires a <b>specific tenant</b>. For supported interactive/device-code apps, a verified domain, <b>common</b>, <b>organizations</b>, or <b>consumers</b> can select the audience.",
            section: "Where to find it",
            steps: ["Open the <b>Microsoft Entra admin center</b>.", "Go to <b>App registrations</b>, select your app, then open <b>Overview</b>.", "Copy <b>Directory (tenant) ID</b> from your app registration into the Tenant ID field."]
        },
        client: {
            title: "Client ID", subtitle: "Application registration identifier", icon: "info",
            description: "Client ID is also known as Application ID (App ID). Microsoft Entra labels it Application (client) ID. It uniquely identifies your app registration.",
            noteTitle: "Use the correct identifier",
            note: "Use the <b>Application (client) ID</b>, not the Object ID, Secret ID, or app display name. This is different from the Tenant ID.",
            section: "Where to find it",
            steps: ["Open <b>Microsoft Entra</b> and go to <b>App registrations</b>.", "Select your app and open its <b>Overview</b> page.", "Copy <b>Application (client) ID</b> into the Client ID field."]
        },
        secret: {
            title: "Client secret", subtitle: "Credential for app-only authentication", icon: "lock",
            description: "A client secret is an application password, not your Microsoft account password. Only the client credentials flow uses it; interactive and device-code sign-in do not.",
            noteTitle: "Handle carefully",
            note: "Copy the secret’s <b>Value</b>, not its Secret ID. Secrets stay in the OS credential manager, not in .env. Leave the field blank to keep a saved secret for the same Client ID. Replace secrets before expiry and keep their values private.",
            section: "Where to find it",
            steps: ["In <b>App registrations</b>, select your application.", "Open <b>Certificates &amp; secrets</b> → <b>Client secrets</b> → <b>New client secret</b>.", "Copy the <b>Value</b> immediately; it cannot be viewed again later."]
        },
        certificateFormat: {
            title: "Certificate format", subtitle: "Choose how your existing credential is stored", icon: "lock",
            description: "Select the format of your certificate files, or choose Create certificate to generate a new encrypted credential. Creation defaults to 90 days and offers preset or custom validity in days. Importing an existing certificate does not change its expiration.",
            noteTitle: "One file or two",
            note: "<b>PFX / P12</b> packages the private key and public certificate together. <b>PEM</b> uses a private-key file and a separate matching public certificate. File extensions alone do not prove what a file contains.",
            section: "Choosing a format",
            steps: ["Choose <b>PFX / P12</b> for a PKCS#12 bundle containing both the private key and certificate, or <b>PEM</b> for a private key and matching public certificate in separate files.", "Use <b>Create certificate</b> to choose a name, output format, password and expiration timeframe (90 days by default). Creation uses a new output folder and fills the import fields automatically.", "Upload only the generated public certificate to your own Entra app registration. Save the connection and test; local validation does not register the certificate or grant permissions."]
        },
        certificateFile: {
            title: "Certificate file", subtitle: "PFX / P12 bundle containing your private key", icon: "lock",
            description: "Select a local .pfx or .p12 file containing the certificate and its matching private key. A public .cer file alone cannot authenticate your application.",
            noteTitle: "Keep this file private",
            note: "A PFX/P12 bundle contains sensitive private-key material. Never upload it to Entra, commit it to a repository, or share it. azauthlib references this file in place; it does not copy it or import it into a certificate store.",
            section: "Selecting the bundle",
            steps: ["Use <b>Browse</b> to select your existing PFX/P12 file from a protected local folder.", "Enter the password used when exporting or creating it. Validation checks the private key, certificate match, dates and signing suitability.", "Upload only the separate <b>public certificate</b> to the intended Entra app registration, save the connection, then use <b>Test connection</b>."]
        },
        privateKeyFile: {
            title: "Private key file", subtitle: "PEM signing key that stays on this computer", icon: "lock",
            description: "Select the PEM file containing your RSA private key. The corresponding public certificate is selected in the next field. The key must match that certificate.",
            noteTitle: "Never upload the private key",
            note: "Private-key PEM files may contain a PRIVATE KEY, ENCRYPTED PRIVATE KEY, or RSA PRIVATE KEY block. Their .pem extension does not make them public. Protect the file and never upload it to Entra or include it in source control.",
            section: "Selecting the key",
            steps: ["Choose the <b>private</b> PEM created by your certificate tool, not its public-certificate output.", "Select its matching public certificate and enter the private-key password when encrypted. The importer supports RSA keys of at least 2048 bits.", "Keep the referenced file in a stable, protected local location. If you move or replace it, edit and validate this connection again."]
        },
        publicCertificate: {
            title: "Public certificate", subtitle: "The public half of your certificate credential", icon: "info",
            description: "Select the public certificate that matches your PEM private key. The importer accepts PEM-encoded certificates and DER-encoded certificates, commonly saved as .pem, .cer or .crt.",
            noteTitle: "Check the contents, not just the extension",
            note: "A public PEM certificate normally contains a <b>BEGIN CERTIFICATE</b> block. Do not upload a PEM containing a private-key block. A public certificate alone is not sufficient for azauthlib to authenticate.",
            section: "Registering the public half",
            steps: ["Choose the public certificate produced alongside your private key. Local validation confirms the pair matches and checks its validity dates.", "In your own Entra app registration, open <b>Certificates &amp; secrets → Certificates → Upload certificate</b> and upload only the public certificate.", "Confirm the Tenant ID and Client ID identify that app registration, save, then test. Successful authentication does not establish permission for every Graph operation."]
        },
        certificateDetails: {
            title: "Certificate details", subtitle: "Public identity, expiration and fingerprint", icon: "info",
            description: "This card shows public metadata from the certificate validated locally, or the metadata recorded when the connection was saved. Saved details do not mean the file or Entra registration has been rechecked.",
            noteTitle: "Keep the private key private",
            note: "Upload only the <b>public certificate</b> to your Entra app registration. The private key stays on this computer. Choose <b>Edit</b> to replace certificate files or unlock an encrypted key.",
            section: "Reading the details",
            steps: ["<b>Common name (CN)</b> is the certificate's descriptive subject name. It is not the Application (client) ID or evidence of who owns an app registration.", "<b>Expires</b> shows the certificate's recorded expiration timestamp and a locally calculated number of days remaining. Renew it and register the replacement public certificate before it expires.", "<b>SHA-256 fingerprint</b> identifies the public certificate. It is not a password or a private key, and may differ from a SHA-1 thumbprint shown by another tool.", "Local validation does not register the certificate with Microsoft or verify Graph permissions. Save the connection and use <b>Test connection</b> to check authentication."]
        },
        certificatePassword: {
            title: "Private-key password", subtitle: "Unlock your existing local certificate credential", icon: "lock",
            description: "Enter the password protecting your PFX/P12 bundle or encrypted PEM private key. This is not your Microsoft account password, a client secret, or a password assigned by Entra.",
            noteTitle: "Secure storage and reuse",
            note: "<b>Remember password securely</b> stores it in the OS credential manager for this connection. Otherwise, saving unlocks it only for the current desktop session. Passwords are not written to profile configuration, and private keys are not sent to Microsoft.",
            section: "Using the password field",
            steps: ["Enter the password chosen when the private key or PFX was created/exported. If it is incorrect, correct the field and wait for validation again.", "Leave blank to retain an available saved/session password for the same files and application. Select <b>This file has no password</b> to explicitly stop reusing a retained password for an unencrypted replacement.", "Without a remembered password, after restarting the app choose <b>Edit</b>, enter the password, validate and save again. Changing this field does not change the password encrypting the original file."]
        },
        test: {
            title: "Test connection", subtitle: "Check saved authentication settings", icon: "bolt",
            description: "The optional test uses the saved credentials and may request Microsoft sign-in or consent. Unsaved changes are not tested.",
            noteTitle: "What success means",
            note: "A pass means Microsoft’s token endpoint returned <b>HTTP 200</b> and issued an access token. It checks authentication, <b>not every Microsoft Graph permission or operation</b>. The test does not persist a token cache.",
            section: "Before testing",
            steps: ["Confirm the Tenant ID and Client ID belong to your intended Entra app registration.", "Choose a supported flow and supply a client secret when required.", "<b>Save</b> your changes, then test. For device code, use <b>Copy code</b> and <b>Open sign-in page</b>; you can cancel the test."]
        }
    })
}
