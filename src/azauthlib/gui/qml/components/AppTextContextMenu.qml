pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import "../theme"

Menu {
    id: root
    required property TextField target
    readonly property bool hasSelection: target.selectionStart !== target.selectionEnd
    readonly property bool canCopySelection: hasSelection && target.echoMode === TextInput.Normal
    popupType: Popup.Item
    width: 238
    padding: 6
    margins: 8
    overlap: 0
    font.family: Theme.fontFamily
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 100 } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 80 } }
    background: Rectangle {
        radius: 11
        color: "#102a43"
        border.color: AccentTheme.color("#4387b6")
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: "#020a14"
            shadowOpacity: 0.55
            shadowBlur: 0.35
            shadowVerticalOffset: 4
        }
    }
    component EditItem: MenuItem {
        id: item
        property string keyHint: ""
        implicitHeight: 33
        implicitWidth: 226
        leftPadding: 12
        rightPadding: 12
        hoverEnabled: true
        HoverHandler { cursorShape: item.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }
        contentItem: RowLayout {
            spacing: 22
            Text {
                Layout.fillWidth: true
                text: item.text
                color: item.enabled ? "#e2eaf3" : AccentTheme.color("#647e96")
                font.family: Theme.fontFamily
                font.pixelSize: 13
            }
            Text {
                text: item.keyHint
                color: item.enabled ? AccentTheme.color("#8fb6d6") : AccentTheme.color("#536b81")
                font.family: Theme.fontFamily
                font.pixelSize: 11
            }
        }
        background: Rectangle {
            radius: 6
            color: item.enabled && item.highlighted ? AccentTheme.color("#24557b") : "transparent"
            border.color: item.enabled && item.highlighted ? AccentTheme.color("#397da9") : "transparent"
        }
    }
    component Divider: MenuSeparator {
        padding: 4
        contentItem: Rectangle { implicitWidth: 218; implicitHeight: 1; color: AccentTheme.color("#31516e") }
    }
    EditItem {
        text: "Undo"; keyHint: "Ctrl+Z"
        enabled: !root.target.readOnly && root.target.canUndo
        onTriggered: root.target.undo()
    }
    EditItem {
        text: "Redo"; keyHint: "Ctrl+Y"
        enabled: !root.target.readOnly && root.target.canRedo
        onTriggered: root.target.redo()
    }
    Divider {}
    EditItem {
        text: "Cut"; keyHint: "Ctrl+X"
        enabled: !root.target.readOnly && root.canCopySelection
        onTriggered: root.target.cut()
    }
    EditItem {
        text: "Copy"; keyHint: "Ctrl+C"
        enabled: root.canCopySelection
        onTriggered: root.target.copy()
    }
    EditItem {
        text: "Paste"; keyHint: "Ctrl+V"
        enabled: !root.target.readOnly && root.target.canPaste
        onTriggered: root.target.paste()
    }
    EditItem {
        text: "Delete"; keyHint: "Del"
        enabled: !root.target.readOnly && root.hasSelection
        onTriggered: root.target.remove(root.target.selectionStart, root.target.selectionEnd)
    }
    Divider {}
    EditItem {
        text: "Select all"; keyHint: "Ctrl+A"
        enabled: root.target.length > 0
        onTriggered: root.target.selectAll()
    }
}
