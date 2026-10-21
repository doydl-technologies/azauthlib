import QtQuick
import QtQuick.Controls
import "../theme"

Button {
    id: root
    property url destination: ""
    property bool active: false
    property bool openExternally: true
    property color linkColor: "#91aac5"
    property bool visualEnabled: enabled
    font.family: ConnectionTheme.body; font.pixelSize: 11; font.weight: Font.Bold
    font.underline: true
    implicitWidth: label.implicitWidth + 2 * padding
    implicitHeight: 26
    padding: 5
    hoverEnabled: enabled
    opacity: visualEnabled || active ? 1 : 0.37
    focusPolicy: enabled ? Qt.StrongFocus : Qt.NoFocus
    Accessible.role: Accessible.Link
    Accessible.name: text
    Accessible.checked: active
    Accessible.description: destination.toString() || "Open the About azauthlib drawer"
    HoverHandler { enabled: root.enabled; cursorShape: Qt.PointingHandCursor }
    Keys.onReturnPressed: if (enabled) clicked()
    onClicked: if (root.openExternally && destination.toString().length) Qt.openUrlExternally(destination)
    contentItem: Text {
        id: label
        text: root.text
        color: root.active ? "#6891b5" : root.enabled && (root.hovered || root.down) ? "#bfe5ff" : root.linkColor
        font: root.font
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        style: Text.Raised; styleColor: "#03101e"
    }
    background: Rectangle {
        radius: 4; color: "transparent"
        border.width: root.enabled && root.visualFocus ? 1 : 0
        border.color: ConnectionTheme.accent
    }
}
