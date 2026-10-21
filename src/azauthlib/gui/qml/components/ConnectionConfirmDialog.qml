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
    parent: Overlay.overlay; anchors.centerIn: parent
    width: Math.min(390, parent ? parent.width - 40 : 390)
    padding: 23; modal: true; focus: true; popupType: Popup.Item
    closePolicy: Popup.CloseOnEscape
    standardButtons: Dialog.NoButton
    header: Item {}
    footer: Item {}
    onOpened: cancelButton.forceActiveFocus()
    Overlay.modal: Rectangle { color: "#bd020b15" }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 180 } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 120 } }
    background: ConnectionSurface { radius: 15; borderColor: "#5684b8"; depth: 14; blur: 32; shadowColor: "#bb000000"; lightColor: "transparent" }
    contentItem: ColumnLayout {
        spacing: 0
        Rectangle {
            Layout.preferredWidth: 42; Layout.preferredHeight: 42; Layout.bottomMargin: 13
            radius: 11; color: root.destructive ? "#5c5d2538" : "#153b5b"; border.color: root.destructive ? "#9b5065" : "#345b85"
            ConnectionIcon { anchors.centerIn: parent; width: 22; height: 22; name: root.destructive ? "trash" : "plug" }
        }
        Text {
            Layout.fillWidth: true; Layout.bottomMargin: 8
            text: root.title; color: "#edf4ff"; font.family: ConnectionTheme.heading; font.pixelSize: 17; font.weight: Font.ExtraBold; wrapMode: Text.Wrap
        }
        Text {
            Layout.fillWidth: true; Layout.bottomMargin: 19
            text: root.message; color: "#adc7da"; font.family: ConnectionTheme.body; font.pixelSize: 12; lineHeight: 1.65; wrapMode: Text.Wrap
            textFormat: Text.PlainText
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 9
            Item { Layout.fillWidth: true }
            ConnectionButton {
                id: cancelButton; objectName: root.objectName + "CancelButton"
                text: root.cancelText; variant: "warning"; font.pixelSize: 11
                onClicked: root.reject()
            }
            ConnectionButton {
                objectName: root.objectName + "ConfirmButton"
                text: root.confirmText; variant: root.destructive ? "destructive" : "primary"; font.pixelSize: 11
                onClicked: {
                    if (root.discardAction) { root.discarded(); root.close() }
                    else root.accept()
                }
            }
        }
    }
}
