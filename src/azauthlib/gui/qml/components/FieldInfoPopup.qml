pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "../theme"

Popup {
    id: root

    property string title: ""
    property string description: ""
    property string guidance: ""
    property string storageNote: ""
    property url iconSource

    parent: Overlay.overlay
    width: Math.min(390, parent ? parent.width - 24 : 390)
    padding: 18
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    function openBeside(anchor: Item) {
        const point = anchor.mapToItem(root.parent, 0, anchor.height)
        x = Math.max(12, Math.min(point.x - 18, root.parent.width - width - 12))
        y = point.y + 8
        open()
        if (y + height > root.parent.height - 12)
            y = Math.max(12, point.y - anchor.height - height - 8)
    }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 90 }
    }

    background: Rectangle {
        radius: 14
        border.width: 1
        border.color: Theme.darkMode ? "#36b5ef" : "#90bfe9"
        gradient: Gradient {
            GradientStop { position: 0; color: Theme.darkMode ? "#142f4d" : "#ffffff" }
            GradientStop { position: 1; color: Theme.darkMode ? "#091c30" : "#edf5fc" }
        }
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.shadow
            shadowOpacity: 0.28
            shadowBlur: 0.4
            shadowVerticalOffset: 4
        }
    }

    contentItem: Item {
        implicitHeight: textColumn.implicitHeight
        Accessible.name: root.title + ". " + root.description + " " +
                         root.guidance + " " + root.storageNote

        Image {
            x: 0
            y: 1
            width: 28
            height: 28
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true
        }

        Column {
            id: textColumn
            x: 42
            width: parent.width - x
            spacing: 10

            Text {
                width: parent.width - 24
                text: root.title
                color: Theme.textPrimary
                font.family: Theme.fontFamily
                font.pixelSize: 16
                wrapMode: Text.Wrap
            }
            Text {
                width: parent.width
                text: root.description
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: 12
                lineHeight: 1.3
                wrapMode: Text.Wrap
            }
            Rectangle {
                width: parent.width
                height: 1
                color: Theme.border
            }
            Text {
                width: parent.width
                text: root.guidance
                color: Theme.icon
                font.family: Theme.fontFamily
                font.pixelSize: 11
                lineHeight: 1.3
                wrapMode: Text.Wrap
            }
            Text {
                visible: root.storageNote.length > 0
                width: parent.width
                text: root.storageNote
                color: Theme.textSecondary
                font.family: Theme.fontFamily
                font.pixelSize: 11
                lineHeight: 1.3
                wrapMode: Text.Wrap
            }
        }

        Button {
            id: closeButton
            objectName: root.objectName + "CloseButton"
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: -8
            anchors.topMargin: -8
            width: 26
            height: 26
            padding: 2
            hoverEnabled: true
            focusPolicy: Qt.StrongFocus
            Accessible.name: "Close information"
            onClicked: root.close()
            contentItem: Image {
                source: Qt.resolvedUrl("../../../assets/icons/svg/actions/Monocolor-Filled-Ice-Blue-close.svg")
                fillMode: Image.PreserveAspectFit
                smooth: true
                mipmap: true
            }
            background: Rectangle {
                radius: 5
                color: closeButton.pressed ?
                           (Theme.darkMode ? "#254866" : "#c4ddf4") :
                       closeButton.hovered ?
                           (Theme.darkMode ? Theme.surfaceHover : "#d8e9f8") :
                           "transparent"
                border.width: closeButton.visualFocus ? 1 : 0
                border.color: Theme.focus
            }
            HoverHandler {
                acceptedDevices: PointerDevice.Mouse
                cursorShape: Qt.PointingHandCursor
            }
        }
    }
}
