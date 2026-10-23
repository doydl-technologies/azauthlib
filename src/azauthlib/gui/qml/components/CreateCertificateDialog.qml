pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../theme"

Dialog {
    id: root
    required property var manager
    property string initialName: ""
    property string initialFormat: "pfx"
    readonly property var creator: manager.certificateCreator
    readonly property bool busy: creator.state.busy === true
    readonly property string password: passwordField.text
    readonly property string selectedFormat: formatBox.currentIndex === 0 ? "pfx" : "pem"
    readonly property string selectedDays: timeframe.currentIndex === 4 ? customDays.text :
        ["30", "90", "180", "365"][timeframe.currentIndex] || "90"
    readonly property var validation: creator.validate(nameField.text, selectedFormat, selectedDays,
        passwordField.text, confirmationField.text, outputField.text)
    signal created(var files)
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(620, parent ? parent.width - 32 : 620)
    height: Math.min(710, parent ? parent.height - 32 : 710)
    padding: 24; modal: true; focus: true; popupType: Popup.Item
    closePolicy: busy ? Popup.NoAutoClose : Popup.CloseOnEscape
    standardButtons: Dialog.NoButton
    header: Item {}
    footer: Item {}
    background: DialogSurface {}
    Overlay.modal: Rectangle { color: "#bd020b15" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: ConnectionTheme.reducedMotion ? 0 : 150 } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: ConnectionTheme.reducedMotion ? 0 : 150 } }

    function clearSecrets() {
        passwordField.text = ""; confirmationField.text = ""
        passwordField.passwordVisible = false; confirmationField.passwordVisible = false
    }
    onAboutToShow: {
        creator.clear()
        nameField.text = initialName || "azauthlib-certificate"
        formatBox.currentIndex = initialFormat === "pem" ? 1 : 0
        timeframe.currentIndex = 1
        customDays.text = "90"
        outputField.text = creator.defaultFolder
        clearSecrets()
        for (const field of [nameField, customDays, passwordField, confirmationField, outputField])
            field.validationTouched = false
    }
    onOpened: nameField.focusInput()
    onAboutToHide: {
        folderDialog.close()
        formatBox.popup.close(); timeframe.popup.close()
        if (busy) creator.cancel()
        clearSecrets()
    }
    Connections {
        target: root.creator
        function onCreated(files) {
            if (!root.visible) return
            // The parent copies the existing password input before it is cleared.
            // Only public file paths/metadata travel in the created signal.
            root.created(files)
            root.clearSecrets()
            root.accept()
        }
    }
    contentItem: ColumnLayout {
        spacing: 12
        Text {
            Layout.fillWidth: true
            text: "Create certificate"; color: ConnectionTheme.text
            font.family: ConnectionTheme.heading; font.pixelSize: 20; font.weight: Font.ExtraBold
        }
        Text {
            Layout.fillWidth: true
            text: "Create an encrypted, self-signed credential for your own Entra app. A new folder is used; existing files are never overwritten."
            color: ConnectionTheme.muted; font.family: ConnectionTheme.body; font.pixelSize: 11
            wrapMode: Text.Wrap
        }
        DialogDivider { Layout.fillWidth: true }
        ScrollView {
            id: fieldsScroll
            objectName: "certificateCreationScroll"
            Layout.fillWidth: true; Layout.fillHeight: true
            contentWidth: availableWidth; clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                width: fieldsScroll.availableWidth
                spacing: 12
                enabled: !root.busy
                ConnectionField {
                    id: nameField
                    objectName: "certificateCreationName"
                    Layout.fillWidth: true
                    label: "Certificate name (Common Name)"
                    validationFeedbackEnabled: true
                    validationError: validationTouched ? root.validation.name || "" : ""
                }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Output format"; color: "#c1d5ec"; font.family: ConnectionTheme.body; font.pixelSize: 11; font.weight: Font.ExtraBold }
                    Item { Layout.fillWidth: true }
                    ConnectionCombo {
                        id: formatBox
                        objectName: "certificateCreationFormat"
                        Layout.preferredWidth: 240
                        Accessible.name: "Certificate output format"
                        model: ["PFX / P12 (recommended)", "PEM key + public certificate"]
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Expiration timeframe"; color: "#c1d5ec"; font.family: ConnectionTheme.body; font.pixelSize: 11; font.weight: Font.ExtraBold }
                    Item { Layout.fillWidth: true }
                    ConnectionCombo {
                        id: timeframe
                        objectName: "certificateCreationTimeframe"
                        Layout.preferredWidth: 240
                        Accessible.name: "Certificate expiration timeframe"
                        model: ["30 days", "90 days (default)", "180 days", "365 days", "Custom days"]
                        currentIndex: 1
                    }
                }
                ConnectionField {
                    id: customDays
                    objectName: "certificateCreationDays"
                    Layout.fillWidth: true; visible: timeframe.currentIndex === 4
                    label: "Validity in days"; text: "90"
                    validationFeedbackEnabled: true
                    validationError: validationTouched ? root.validation.days || "" : ""
                }
                Text {
                    Layout.fillWidth: true
                    text: root.validation.expires ? "Expires: " + root.validation.expires.replace("T", " ").replace("+00:00", " UTC") : root.validation.days || ""
                    color: root.validation.expires ? ConnectionTheme.muted : "#ff889e"
                    font.family: ConnectionTheme.body; font.pixelSize: 11; wrapMode: Text.Wrap
                }
                ConnectionField {
                    id: passwordField
                    objectName: "certificateCreationPassword"
                    Layout.fillWidth: true; label: "Private-key password"; password: true
                    placeholderText: "4-511 characters; 16 or more recommended"
                    validationFeedbackEnabled: true
                    validationError: validationTouched ? root.validation.password || "" : ""
                }
                ConnectionField {
                    id: confirmationField
                    objectName: "certificateCreationConfirmation"
                    Layout.fillWidth: true; label: "Confirm private-key password"; password: true
                    validationFeedbackEnabled: true
                    validationError: validationTouched ? root.validation.confirmation || "" : ""
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    ConnectionField {
                        id: outputField
                        objectName: "certificateCreationOutputFolder"
                        Layout.fillWidth: true; label: "Output folder"
                        validationFeedbackEnabled: true
                        validationError: validationTouched ? root.validation.folder || "" : ""
                    }
                    ConnectionButton {
                        objectName: "certificateCreationBrowseFolder"
                        text: "Browse"; Layout.alignment: Qt.AlignBottom
                        onClicked: folderDialog.open()
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: "Upload only the generated public .cer to Entra. Keep the private PFX/PEM and its password protected. Your tenant may impose its own certificate-lifetime policy. Cancelling the connection later will not delete files created here."
                    color: ConnectionTheme.muted; font.family: ConnectionTheme.body; font.pixelSize: 11
                    wrapMode: Text.Wrap
                }
            }
        }
        Text {
            objectName: "certificateCreationStatus"
            Layout.fillWidth: true
            visible: text.length > 0
            text: root.creator.state.message || ""
            color: root.busy ? ConnectionTheme.muted : "#ffb4bb"
            font.family: ConnectionTheme.body; font.pixelSize: 11; wrapMode: Text.Wrap
            textFormat: Text.PlainText
            Accessible.name: text
        }
        DialogDivider { Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            Item { Layout.fillWidth: true }
            ConnectionButton {
                objectName: "certificateCreationCancel"
                text: root.creator.state.cancelling ? "Cancelling..." : "Cancel"
                enabled: !root.creator.state.cancelling
                variant: "cancel"
                onClicked: if (root.busy) root.creator.cancel(); else root.reject()
            }
            ConnectionButton {
                objectName: "certificateCreationConfirm"
                text: root.busy ? "Creating..." : "Create certificate"
                variant: "primary"
                enabled: !root.busy && root.validation.valid
                onClicked: if (enabled) root.creator.create(nameField.text, root.selectedFormat, root.selectedDays,
                    passwordField.text, confirmationField.text, outputField.text)
            }
        }
    }
    FolderDialog {
        id: folderDialog
        title: "Choose the parent folder for the new certificate files"
        onAccepted: outputField.text = root.manager.localCertificatePath(selectedFolder)
    }
}
