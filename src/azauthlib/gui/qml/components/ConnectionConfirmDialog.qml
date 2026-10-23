import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Dialog {
    id: root
    property string message: ""
    property string confirmText: "Continue"
    property string cancelText: "Cancel"
    property bool destructive: false
    property bool discardAction: false
    property bool dismissing: false
    parent: Overlay.overlay; anchors.centerIn: parent
    width: Math.min(390, parent ? parent.width - 40 : 390)
    padding: 23; modal: true; focus: true; popupType: Popup.Item
    closePolicy: Popup.CloseOnEscape
    standardButtons: Dialog.NoButton
    header: Item {}
    footer: Item {}
    onOpened: cancelButton.forceActiveFocus()
    onAboutToShow: dismissing = false
    onAboutToHide: dismissing = true
    Overlay.modal: Rectangle { color: "#bd020b15" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 180 } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: ConnectionTheme.popupExitDuration; easing.type: Easing.InOutCubic } }
    background: DialogSurface { objectName: root.objectName + "Surface" }
    contentItem: ColumnLayout {
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            Rectangle {
                objectName: root.objectName + "IconRegion"
                Layout.alignment: Qt.AlignTop
                Layout.preferredWidth: 42; Layout.preferredHeight: 42
                radius: 11; color: root.destructive ? "#5c5d2538" : "#153b5b"; border.color: root.destructive ? "#9b5065" : AccentTheme.color("#345b85")
                ConnectionIcon {
                    objectName: root.objectName + "Icon"
                    anchors.centerIn: parent; width: 22; height: 22
                    name: root.destructive ? "trash" : "plug"
                    // Use the same compatible artwork renderer as the Remove tile.
                    sourceOverride: root.destructive ? Qt.resolvedUrl("../../../assets/icons/svg/" + assetPath) : ""
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 8
                Text {
                    objectName: root.objectName + "Title"
                    Layout.fillWidth: true
                    text: root.title; color: "#edf4ff"; font.family: ConnectionTheme.heading; font.pixelSize: 17; font.weight: Font.ExtraBold; wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }
                Text {
                    objectName: root.objectName + "Message"
                    Layout.fillWidth: true
                    text: root.message; color: "#adc7da"; font.family: ConnectionTheme.body; font.pixelSize: 12; lineHeight: 1.5; wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }
            }
        }
        DialogDivider { objectName: root.objectName + "Divider"; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true; spacing: 9
            Item { Layout.fillWidth: true }
            ConnectionButton {
                id: cancelButton; objectName: root.objectName + "CancelButton"
                text: root.cancelText; variant: "cancel"; font.pixelSize: 11
                onClicked: if (!root.dismissing) root.reject()
            }
            ConnectionButton {
                objectName: root.objectName + "ConfirmButton"
                text: root.confirmText; variant: root.destructive ? "destructive" : "primary"; font.pixelSize: 11
                onClicked: {
                    if (root.dismissing) return
                    root.dismissing = true
                    if (root.discardAction) { root.discarded(); root.close() }
                    else root.accept()
                }
            }
        }
    }
}
