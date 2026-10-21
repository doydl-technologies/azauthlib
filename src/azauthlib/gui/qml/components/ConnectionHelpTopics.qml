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
        profiles: {
            title: "Saved connections", subtitle: "Select the profile you want to work with", icon: "plug",
            description: "Each connection stores the authentication settings for one application or environment. Selecting a profile shows its details; it does not automatically make it active.",
            noteTitle: "Selected vs. active",
            // note: "The highlighted profile is the one you are viewing. Choose <b>Set as active</b> to change the default connection used by azauthlib.",
            note: "The highlighted profile is the one you are viewing. Choose <b>Activate connection</b> to change the default connection used by azauthlib.",            
            section: "Working with profiles",
            // steps: ["Select a saved connection to inspect its settings.", "Use <b>Add a connection</b> to create a separate profile without overwriting another.", "Choose <b>Edit</b> to change a profile, or <b>Set as active</b> to activate it."]
            steps: ["Select a saved connection to inspect its settings.", "Use <b>Add a connection</b> to create a separate profile without overwriting another.", "Choose <b>Edit</b> to change a profile, or <b>Activate connection</b> to activate it."]            
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
            steps: ["<b>Interactive</b> — sign in as a user in a browser. No client secret.", "<b>Device code</b> — enter the displayed code at the sign-in page, on this or another device. No client secret.", "<b>Client credentials</b> — sign in without a user, using a specific tenant, Application (client) ID, and client secret."]
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
