pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

ConnectionSurface {
    id: root
    property var summary: ({})
    property string commonName: summary.subject || "Not provided"
    property bool helpExpanded: false
    property real contentScale: 1
    property bool expanded: true
    property bool useProfileAvatar: true
    property double nowMilliseconds: Date.now()
    readonly property string fingerprint: summary.fingerprint || ""
    readonly property double expirationMilliseconds: Date.parse(summary.not_after || "")
    readonly property bool expirationKnown: Number.isFinite(expirationMilliseconds)
    readonly property bool expired: expirationKnown && expirationMilliseconds <= nowMilliseconds
    readonly property int daysRemaining: expirationKnown ?
        Math.ceil((expirationMilliseconds - nowMilliseconds) / 86400000) : 0
    readonly property string expirationStatus: !expirationKnown ? "" : expired ? "Expired" :
        "in " + daysRemaining + (daysRemaining === 1 ? " day" : " days")
    readonly property color expirationColor: expired ? "#ff889e" : daysRemaining <= 30 ? "#ffc36e" : AccentTheme.color("#68caff")
    property real revealProgress: expanded ? 1 : 0
    signal helpRequested(var trigger)

    implicitHeight: cardContent.implicitHeight + 24
    radius: 13; borderColor: AccentTheme.color("#32bada"); crispOutline: true
    topColor: "#143650"; middleColor: "#102c45"; bottomColor: "#0b2337"
    depth: 4; blur: 11; lightBlur: 9
    lightColor: AccentTheme.color("#45345b85"); shadowColor: "#aa03101e"
    onFingerprintChanged: { expanded = true; nowMilliseconds = Date.now() }
    Behavior on revealProgress {
        NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 200; easing.type: Easing.InOutCubic }
    }
    Timer {
        interval: 60000; repeat: true; running: root.visible
        onTriggered: root.nowMilliseconds = Date.now()
    }
    function escaped(value) {
        return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
    }

    component DetailRow: ColumnLayout {
        id: detailRow
        required property string label
        required property string value
        property bool richValue: false
        property bool monospace: false
        readonly property bool stacked: root.width < 470
        Layout.fillWidth: true
        spacing: 0
        ConnectionDivider {
            objectName: "certificateDetailsDivider_" + detailRow.label
            Layout.fillWidth: true; contentScale: root.contentScale
        }
        GridLayout {
            Layout.fillWidth: true; Layout.topMargin: 6; Layout.bottomMargin: 6
            columns: detailRow.stacked ? 1 : 2; columnSpacing: 14; rowSpacing: 4
            Text {
                Layout.preferredWidth: detailRow.stacked ? -1 : 160
                Layout.fillWidth: detailRow.stacked
                text: detailRow.label; textFormat: Text.PlainText
                color: AccentTheme.color("#83cff4"); font.family: ConnectionTheme.body
                font.pixelSize: 11; font.weight: Font.DemiBold
                wrapMode: Text.Wrap
            }
            TextEdit {
                objectName: "certificateDetailValue_" + detailRow.label
                Layout.fillWidth: true; Layout.minimumWidth: 0
                text: detailRow.value
                textFormat: detailRow.richValue ? TextEdit.RichText : TextEdit.PlainText
                readOnly: true; selectByMouse: true
                wrapMode: TextEdit.WrapAnywhere
                color: ConnectionTheme.text
                font.family: detailRow.monospace ? ConnectionTheme.mono : ConnectionTheme.body
                font.pixelSize: detailRow.monospace ? 10 : 11
                Accessible.name: detailRow.label + ": " + getText(0, length)
            }
        }
    }

    ColumnLayout {
        id: cardContent
        x: 14; y: 12; width: parent.width - 28
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            spacing: root.width < 300 ? 6 : 10

            ProfileAvatar {
                objectName: "managerCertificateDetailsProfileIcon"
                visible: root.useProfileAvatar
                Layout.preferredWidth: root.width < 300 ? 24 : 32
                Layout.preferredHeight: 36
                avatarId: "app-service-certificates.svg"
            }

            ConnectionIcon {
                objectName: "managerCertificateDetailsSvgIcon"
                visible: !root.useProfileAvatar
                Layout.preferredWidth: root.width < 300 ? 24 : 32
                Layout.preferredHeight: 36
                sourceOverride: Qt.resolvedUrl(
                    "../../../assets/icons/svg/technology/Monocolor-Filled-White-Certificate-Diploma-Degree.svg"
                )
            }
            Text {
                objectName: "managerCertificateDetailsTitle"
                text: "Certificate details"; color: ConnectionTheme.text
                font.family: ConnectionTheme.heading; font.pixelSize: root.width < 300 ? 12 : 14; font.weight: Font.ExtraBold
                Layout.maximumWidth: Math.max(40, root.width - 134); wrapMode: Text.Wrap
            }
            ConnectionHelpButton {
                objectName: "managerCertificateDetailsInfoButton"
                text: "About certificate details"; expanded: root.helpExpanded
                onClicked: root.helpRequested(this)
            }
            Item { Layout.fillWidth: true }
            AbstractButton {
                id: toggle
                objectName: "managerCertificateDetailsToggle"
                implicitWidth: 28; implicitHeight: 28
                hoverEnabled: enabled; focusPolicy: enabled ? Qt.StrongFocus : Qt.NoFocus
                Accessible.name: root.expanded ? "Collapse certificate details" : "Expand certificate details"
                checkable: true; checked: root.expanded
                onClicked: root.expanded = !root.expanded
                Keys.onReturnPressed: if (enabled) clicked()
                HoverHandler { enabled: toggle.enabled; cursorShape: Qt.PointingHandCursor }
                background: Rectangle {
                    radius: 6; color: toggle.hovered ? AccentTheme.color("#253f6384") : "transparent"
                    border.width: toggle.visualFocus ? 1 : 0; border.color: AccentTheme.focus
                }
                contentItem: Item {
                    ConnectionIcon {
                        anchors.centerIn: parent; width: 18; height: 18
                        name: "down"; rotation: root.expanded ? 180 : 0
                        Behavior on rotation {
                            NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 200; easing.type: Easing.InOutCubic }
                        }
                    }
                }
            }
        }
        Item {
            objectName: "managerCertificateDetailsBody"
            Layout.fillWidth: true
            Layout.preferredHeight: body.implicitHeight * root.revealProgress
            visible: root.revealProgress > 0
            enabled: root.expanded
            clip: true; opacity: root.revealProgress
            ColumnLayout {
                id: body
                x: root.width < 470 ? 0 : 42
                width: parent.width - x; spacing: 0
                DetailRow { label: "Common name (CN)"; value: root.commonName }
                DetailRow {
                    label: "Expires"; richValue: true
                    value: root.escaped(root.summary.not_after || "Not available") +
                        (root.expirationStatus.length ? " &nbsp; <font color='" + root.expirationColor + "'>(" +
                            root.expirationStatus + ")</font>" : "")
                }
                DetailRow { label: "SHA-256 fingerprint"; value: root.fingerprint; monospace: true }
                ConnectionDivider {
                    objectName: "certificateDetailsFooterDivider"
                    Layout.fillWidth: true; contentScale: root.contentScale
                }
                RowLayout {
                    Layout.fillWidth: true; Layout.topMargin: 8; spacing: 8
                    ConnectionIcon {
                        Layout.preferredWidth: 20; Layout.preferredHeight: 20
                        Layout.alignment: Qt.AlignTop; name: "info"
                    }
                    Text {
                        objectName: "managerCertificateDetailsGuidance"
                        Layout.fillWidth: true
                        text: "Only upload the public certificate to Entra. The private key stays on this computer."
                        textFormat: Text.PlainText; wrapMode: Text.Wrap
                        color: "#bed3e8"; font.family: ConnectionTheme.body; font.pixelSize: 11
                        lineHeight: 1.3
                    }
                }
            }
        }
    }
}
