pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Dialog {
    id: root
    required property var manager
    property string pendingAvatar: ""
    property string errorText: ""
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(620, parent ? parent.width - 32 : 620)
    height: Math.min(590, parent ? parent.height - 32 : 590)
    padding: 24
    modal: true
    focus: true
    popupType: Popup.Item
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    standardButtons: Dialog.NoButton
    header: Item {}
    footer: Item {}
    background: DialogSurface {}
    Overlay.modal: Rectangle { color: "#b8020b15" }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: ConnectionTheme.reducedMotion ? 0 : 150 }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: ConnectionTheme.reducedMotion ? 0 : 150 }
    }
    onAboutToShow: {
        pendingAvatar = manager.avatar
        errorText = ""
        gallery.currentIndex = Math.max(0, manager.avatarChoices.indexOf(pendingAvatar))
    }
    onOpened: {
        gallery.positionViewAtIndex(gallery.currentIndex, GridView.Contain)
        gallery.forceActiveFocus()
    }
    function chooseAvatar(index) {
        if (index < 0 || index >= manager.avatarChoices.length) return
        gallery.currentIndex = index
        pendingAvatar = manager.avatarChoices[index]
        errorText = ""
    }
    contentItem: ColumnLayout {
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: "Choose an avatar"
                color: ConnectionTheme.text
                font.family: ConnectionTheme.heading
                font.pixelSize: 20
                font.weight: Font.ExtraBold
            }
            ConnectionButton {
                objectName: "avatarPickerClose"
                Accessible.name: "Close avatar picker"
                symbol: "x"; implicitWidth: 28; implicitHeight: 28
                padding: 6
                onClicked: root.reject()
            }
        }
        Text {
            Layout.fillWidth: true
            text: "Pick an image for “" + (root.manager.editor.name || "this connection") + "”."
            textFormat: Text.PlainText
            color: ConnectionTheme.muted
            font.family: ConnectionTheme.body
            font.pixelSize: 12
            wrapMode: Text.Wrap
        }
        DialogDivider { Layout.fillWidth: true }
        GridView {
            id: gallery
            objectName: "profileAvatarGallery"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 84
            clip: true
            readonly property int columns: Math.max(1, Math.floor((width - 12) / 82))
            cellWidth: (width - 12) / columns
            cellHeight: 84
            cacheBuffer: cellHeight * 2
            model: root.manager.avatarChoices
            keyNavigationEnabled: true
            boundsBehavior: Flickable.StopAtBounds
            Keys.onReturnPressed: root.chooseAvatar(currentIndex)
            Keys.onSpacePressed: root.chooseAvatar(currentIndex)
            ScrollBar.vertical: ScrollBar {
                width: 6
                policy: ScrollBar.AsNeeded
            }
            delegate: AbstractButton {
                id: choice
                required property string modelData
                required property int index
                objectName: "profileAvatarChoice" + index
                readonly property bool selected: root.pendingAvatar === modelData
                width: gallery.cellWidth
                height: gallery.cellHeight
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                Accessible.name: index === 0 ? "Default plug avatar" : "Avatar " + index
                Accessible.role: Accessible.RadioButton
                Accessible.checked: selected
                onClicked: root.chooseAvatar(index)
                Keys.onReturnPressed: clicked()
                HoverHandler { cursorShape: Qt.PointingHandCursor }
                background: Item {}
                contentItem: Item {
                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.min(68, choice.width - 12)
                        height: width
                        radius: width / 2
                        readonly property var circleColors: ["#cfe1f3", "#c9e7de", "#e4daf2", "#f4e4bd", "#f2d6df", "#d1def7"]
                        color: choice.index === 0 ? "#163650" : circleColors[(choice.index - 1) % circleColors.length]
                        readonly property bool keyboardFocus: choice.visualFocus || (gallery.activeFocus && gallery.currentIndex === choice.index)
                        border.color: choice.selected || keyboardFocus ? AccentTheme.accent : choice.hovered ? AccentTheme.focus : AccentTheme.color("#355c7b")
                        border.width: choice.selected || keyboardFocus ? 3 : 1
                        scale: choice.down ? 0.95 : 1
                        Behavior on scale { NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 100 } }
                        ProfileAvatar {
                            objectName: "profileAvatarArtwork" + choice.index
                            anchors.centerIn: parent
                            width: parent.width * 0.62; height: width
                            avatarId: choice.modelData
                        }
                        Rectangle {
                            visible: choice.selected
                            anchors.right: parent.right; anchors.top: parent.top
                            anchors.rightMargin: -1; anchors.topMargin: -1
                            width: 20; height: 20; radius: 10
                            color: AccentTheme.color("#157fce"); border.color: AccentTheme.color("#9ed6ff")
                            ConnectionIcon { anchors.centerIn: parent; width: 11; height: 11; name: "check" }
                        }
                    }
                }
            }
        }
        Text {
            Layout.fillWidth: true
            visible: root.errorText.length > 0
            text: root.errorText
            color: "#ffb4bb"
            font.family: ConnectionTheme.body
            font.pixelSize: 12
            wrapMode: Text.Wrap
        }
        DialogDivider { Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            spacing: 9
            Text {
                Layout.fillWidth: true
                color: ConnectionTheme.muted
                font.family: ConnectionTheme.body
                font.pixelSize: 11
                wrapMode: Text.Wrap
            }
            ConnectionButton {
                objectName: "avatarPickerCancel"
                text: "Cancel"
                variant: "cancel"
                onClicked: root.reject()
            }
            ConnectionButton {
                objectName: "avatarPickerApply"
                text: "Use avatar"
                variant: "primary"
                onClicked: {
                    if (root.manager.setAvatar(root.pendingAvatar)) root.accept()
                    else root.errorText = root.manager.status
                }
            }
        }
    }
}
