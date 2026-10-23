pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import "../theme"

ComboBox {
    id: root
    property bool visualEnabled: enabled
    property real transitionOpacity: 1
    property real transitionOffset: 0
    readonly property Item transitionItem: label
    implicitHeight: 37; leftPadding: 12; rightPadding: 34
    hoverEnabled: true
    Accessible.name: "Authentication method"
    HoverHandler { cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }
    contentItem: Text {
        id: label
        objectName: root.objectName + "TransitionText"
        opacity: root.transitionOpacity
        transform: Translate { y: root.transitionOffset }
        text: root.displayText; color: root.visualEnabled ? "#edf4ff" : "#b9d3e9"
        font.family: ConnectionTheme.body; font.pixelSize: 12; font.weight: Font.DemiBold
        verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
    }
    indicator: ConnectionIcon { x: root.width - 28; y: (root.height - height) / 2; width: 16; height: 16; name: "down" }
    background: ConnectionFieldBackground { control: root }
    delegate: ItemDelegate {
        id: option
        required property string modelData
        required property int index
        width: root.width - 10; height: 34
        text: modelData; highlighted: root.highlightedIndex === index
        HoverHandler { cursorShape: Qt.PointingHandCursor }
        contentItem: Text { text: option.text; color: "#edf4ff"; font.family: ConnectionTheme.body; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { radius: 6; color: option.highlighted ? AccentTheme.color("#24557b") : "transparent" }
    }
    popup: Popup {
        y: root.height + 5; width: root.width; padding: 5
        implicitHeight: contentItem.implicitHeight + 10
        popupType: Popup.Item
        background: ConnectionSurface { depth: 4; blur: 10 }
        contentItem: ListView {
            clip: true; implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
        }
    }
}
