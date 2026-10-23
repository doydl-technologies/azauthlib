pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../theme"

ColumnLayout {
    id: root
    required property var manager
    property bool editing: false
    property real contentScale: 1
    property string clientId: ""
    property string tenantId: ""
    property string connectionName: ""
    property bool synchronizing: false
    property string helpTopic: ""
    property var generatedFiles: ({})
    readonly property var validation: manager.certificateImport.state
    readonly property bool changed: validation.changed === true
    readonly property var summary: editing ? validation : manager.editor.certificate || ({})
    readonly property bool summaryVisible: !!summary.fingerprint
    readonly property bool modalOpen: creationDialog.visible || fileDialog.visible || formatBox.popup.visible ||
        keyField.menuVisible || publicField.menuVisible || passwordField.menuVisible
    signal edited()
    signal helpRequested(string topic, var trigger)
    signal helpDismissRequested()
    spacing: 10

    function validate() {
        if (synchronizing || !visible || !editing) return
        manager.certificateImport.updateDraft(formatBox.currentIndex === 0 ? "pfx" : "pem",
            keyField.text, publicField.text, passwordField.text, rememberBox.checked, clientId, tenantId, noPasswordBox.checked)
        edited()
    }
    function synchronize(spec) {
        if (spec.key_path !== generatedFiles.key_path) generatedFiles = ({})
        synchronizing = true
        formatBox.currentIndex = spec.format === "pem" ? 1 : 0
        keyField.text = spec.key_path || ""
        publicField.text = spec.certificate_path || ""
        passwordField.text = ""
        passwordField.passwordVisible = false
        rememberBox.checked = !!spec.password_ref
        noPasswordBox.checked = false
        synchronizing = false
        if (editing && visible) validate()
    }
    function dismissInteractions() {
        formatBox.popup.close()
        keyField.dismissInteractions(); publicField.dismissInteractions(); passwordField.dismissInteractions()
        fileDialog.close()
        creationDialog.close()
    }
    onClientIdChanged: validate()
    onTenantIdChanged: validate()
    onVisibleChanged: {
        if (!visible) { dismissInteractions(); passwordField.text = "" }
        else if (editing) validate()
    }
    onEnabledChanged: if (!enabled) dismissInteractions()
    RowLayout {
        Layout.fillWidth: true
        Text {
            text: "Certificate format"; color: "#c1d5ec"
            font.family: ConnectionTheme.body; font.pixelSize: 11; font.weight: Font.ExtraBold
        }
        ConnectionHelpButton {
            objectName: "managerCertificateFormatInfoButton"
            text: "About certificate formats"
            expanded: root.helpTopic === "certificateFormat"
            onClicked: root.helpRequested("certificateFormat", this)
        }
        Item { Layout.fillWidth: true }
        ConnectionCombo {
            id: formatBox
            objectName: "managerCertificateFormat"
            Layout.preferredWidth: 210; Layout.preferredHeight: 37
            model: ["PFX / P12 (recommended)", "PEM key + public certificate"]
            enabled: root.editing
            onActivated: root.validate()
            onCurrentIndexChanged: {
                if (!root.synchronizing &&
                    ((currentIndex !== 0 && root.helpTopic === "certificateFile") ||
                     (currentIndex !== 1 && ["privateKeyFile", "publicCertificate"].includes(root.helpTopic))))
                    root.helpDismissRequested()
            }
        }
    }
    ConnectionButton {
        objectName: "managerCreateCertificateButton"
        visible: root.editing
        text: "Create certificate..."; variant: "secondary"
        enabled: root.editing && !root.manager.testing
        onClicked: creationDialog.open()
    }
    RowLayout {
        Layout.fillWidth: true; spacing: 8
        ConnectionField {
            id: keyField
            objectName: "managerCertificateKeyField"
            Layout.fillWidth: true
            label: formatBox.currentIndex === 0 ? "Certificate file (.pfx / .p12)" : "Private key file (.pem)"
            helpTopic: formatBox.currentIndex === 0 ? "certificateFile" : "privateKeyFile"
            helpExpanded: root.helpTopic === helpTopic
            onHelpRequested: trigger => root.helpRequested(keyField.helpTopic, trigger)
            readOnly: !root.editing
            placeholderText: "Select a local file; it will not be copied"
            onEdited: root.validate()
        }
        ConnectionButton {
            objectName: "managerCertificateBrowseButton"
            text: "Browse"; enabled: root.editing
            Layout.alignment: Qt.AlignBottom
            onClicked: { fileDialog.publicFile = false; fileDialog.open() }
        }
    }
    RowLayout {
        Layout.fillWidth: true; spacing: 8; visible: formatBox.currentIndex === 1
        ConnectionField {
            id: publicField
            objectName: "managerCertificatePublicField"
            Layout.fillWidth: true
            label: "Public certificate (.pem / .cer / .crt)"; readOnly: !root.editing
            helpTopic: "publicCertificate"
            helpExpanded: root.helpTopic === helpTopic
            onHelpRequested: trigger => root.helpRequested(publicField.helpTopic, trigger)
            onEdited: root.validate()
        }
        ConnectionButton {
            objectName: "managerCertificatePublicBrowseButton"
            text: "Browse"; enabled: root.editing; Layout.alignment: Qt.AlignBottom
            onClicked: { fileDialog.publicFile = true; fileDialog.open() }
        }
    }
    ConnectionField {
        id: passwordField
        objectName: "managerCertificatePasswordField"
        Layout.fillWidth: true; visible: root.editing
        label: "Private-key password"; password: true; readOnly: !root.editing || noPasswordBox.checked
        placeholderText: root.manager.editor.certificate && root.manager.editor.certificate.password_ref ?
            "Leave blank to retain the saved password for the same files and app" : "Enter password, or leave blank for an unencrypted key"
        helpTopic: "certificatePassword"
        helpExpanded: root.helpTopic === helpTopic
        onHelpRequested: trigger => root.helpRequested(passwordField.helpTopic, trigger)
        onEdited: root.validate()
    }
    CheckBox {
        id: rememberBox
        Layout.fillWidth: true
        objectName: "managerRememberCertificatePassword"
        visible: root.editing
        enabled: !noPasswordBox.checked
        text: "Remember password securely for this connection"
        palette.windowText: ConnectionTheme.text
        font.family: ConnectionTheme.body; font.pixelSize: 11
        spacing: 8
        leftPadding: 0
        indicator: ConnectionSurface {
            x: 0; y: (rememberBox.height - height) / 2
            width: 20; height: 20; radius: 5
            sunken: !rememberBox.checked
            borderColor: rememberBox.visualFocus ? AccentTheme.focus : AccentTheme.color("#345b85")
            ConnectionIcon { anchors.centerIn: parent; width: 14; height: 14; name: "check"; visible: rememberBox.checked }
        }
        contentItem: Text {
            text: rememberBox.text
            leftPadding: 28; verticalAlignment: Text.AlignVCenter
            color: ConnectionTheme.text; font: rememberBox.font
            wrapMode: Text.Wrap
        }
        HoverHandler { cursorShape: Qt.PointingHandCursor }
        onClicked: root.validate()
    }
    CheckBox {
        id: noPasswordBox
        Layout.fillWidth: true
        objectName: "managerCertificateNoPassword"
        visible: root.editing
        text: "This file has no password (do not reuse a saved password)"
        font.family: ConnectionTheme.body; font.pixelSize: 11
        spacing: 8; leftPadding: 0
        indicator: ConnectionSurface {
            x: 0; y: (noPasswordBox.height - height) / 2
            width: 20; height: 20; radius: 5; sunken: !noPasswordBox.checked
            borderColor: noPasswordBox.visualFocus ? AccentTheme.focus : AccentTheme.color("#345b85")
            ConnectionIcon { anchors.centerIn: parent; width: 14; height: 14; name: "check"; visible: noPasswordBox.checked }
        }
        contentItem: Text {
            text: noPasswordBox.text; leftPadding: 28; verticalAlignment: Text.AlignVCenter
            color: ConnectionTheme.text; font: noPasswordBox.font; wrapMode: Text.Wrap
        }
        HoverHandler { cursorShape: Qt.PointingHandCursor }
        onClicked: { if (checked) { passwordField.text = ""; rememberBox.checked = false }; root.validate() }
    }
    Text {
        objectName: "managerCertificateValidation"
        Layout.fillWidth: true
        visible: !root.summaryVisible || (root.editing && (!root.validation.valid || root.validation.busy))
        text: root.editing ? root.validation.message || "Choose certificate files to validate." :
            "Certificate files are referenced locally. Choose Edit to replace or unlock them."
        textFormat: Text.PlainText; wrapMode: Text.Wrap
        color: root.editing && !root.validation.valid && !root.validation.busy ? "#ff889e" : ConnectionTheme.muted
        font.family: ConnectionTheme.body; font.pixelSize: 11
        Accessible.name: text
    }
    Text {
        objectName: "managerGeneratedCertificateFiles"
        Layout.fillWidth: true
        visible: !!root.generatedFiles.public_cer
        text: "Created files in: " + (root.generatedFiles.folder || "") +
            "\nUpload only this public certificate to Entra: " + (root.generatedFiles.public_cer || "")
        textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere
        color: ConnectionTheme.muted; font.family: ConnectionTheme.body; font.pixelSize: 11
    }
    CertificateDetailsCard {
        objectName: "managerCertificateSummary"
        Layout.fillWidth: true
        visible: root.summaryVisible
        summary: root.summary
        contentScale: root.contentScale
        commonName: root.manager.certificateCommonName(root.summary.subject || "")
        helpExpanded: root.helpTopic === "certificateDetails"
        onHelpRequested: trigger => root.helpRequested("certificateDetails", trigger)
    }
    FileDialog {
        id: fileDialog
        property bool publicFile: false
        title: publicFile ? "Select the public certificate" : "Select the private certificate/key file"
        fileMode: FileDialog.OpenFile
        nameFilters: publicFile ? ["Public certificates (*.pem *.cer *.crt)", "All files (*)"] :
            formatBox.currentIndex === 0 ? ["PKCS#12 certificates (*.pfx *.p12)", "All files (*)"] :
            ["PEM private keys (*.pem *.key)", "All files (*)"]
        onAccepted: {
            const path = root.manager.localCertificatePath(selectedFile)
            if (!path.length) return
            if (publicFile) publicField.text = path
            else keyField.text = path
            root.validate()
        }
    }
    CreateCertificateDialog {
        id: creationDialog
        objectName: "managerCreateCertificateDialog"
        manager: root.manager
        initialName: root.connectionName || "azauthlib-certificate"
        initialFormat: formatBox.currentIndex === 0 ? "pfx" : "pem"
        onCreated: files => {
            if (!root.editing || root.manager.testing) return
            root.synchronizing = true
            formatBox.currentIndex = files.format === "pem" ? 1 : 0
            keyField.text = files.key_path
            publicField.text = files.certificate_path || ""
            passwordField.text = creationDialog.password
            passwordField.passwordVisible = false
            noPasswordBox.checked = false
            root.generatedFiles = files
            root.synchronizing = false
            root.validate()
        }
    }
}
