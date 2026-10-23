pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Window
import "../theme"

Button {
    id: root
    required property string providerId
    required property string providerName
    required property string summary
    required property url logoSource
    property real logoSize: 66
    property bool selected: false
    signal logoSettled(string providerId, bool success)
    function spotlightSubject(mode, target) {
        const item = mode === "mark" ? emblem.logoItem : emblem
        const origin = item.mapToItem(target, 0, 0)
        const end = item.mapToItem(target, item.width, item.height)
        const unit = (end.x - origin.x) / item.width
        const groupWidth = Math.max(emblem.width, serviceName.implicitWidth) * unit
        return {
            x: mode === "group" ? origin.x + (end.x - origin.x - groupWidth) / 2 : origin.x,
            y: origin.y,
            width: mode === "group" ? groupWidth : end.x - origin.x,
            height: mode === "group" ? (emblem.height + 11 + serviceName.height) * unit : end.y - origin.y,
            unit: unit, circleSize: emblem.width * unit, logoSize: root.logoSize,
            labelGap: 11 * unit, labelHeight: serviceName.height * unit,
            fontSize: serviceName.font.pixelSize * unit,
            name: root.providerName, logo: root.logoSource.toString().split("/").pop()
        }
    }
    padding: 0
    hoverEnabled: enabled
    focusPolicy: Qt.StrongFocus
    Accessible.name: providerName
    Accessible.description: summary.replace(/\n/g, " ")
    Accessible.role: Accessible.CheckBox
    Accessible.checked: selected
    Keys.onReturnPressed: clicked()
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    background: ProviderSurface {
        objectName: root.objectName + "Well"
        kind: 2; radius: 23
        selected: root.selected; hovered: root.hovered; focused: root.visualFocus
    }
    contentItem: Item {
        Column {
            id: copy
            anchors.horizontalCenter: parent.horizontalCenter
            y: (parent.height - height) / 2 + 1
            width: parent.width - 36
            spacing: 0
            ProviderEmblem {
                id: emblem
                objectName: root.objectName + "Halo"
                anchors.horizontalCenter: parent.horizontalCenter
                width: 108; height: 108; radius: 54; kind: 3
                selected: root.selected; hovered: root.hovered
                providerObjectName: root.objectName
                logoSource: root.logoSource
                logoSize: root.logoSize
                onLogoSettled: success => root.logoSettled(root.providerId, success)
            }
            Item { width: 1; height: 11 }
            Text {
                id: serviceName
                objectName: root.objectName + "Name"
                width: parent.width; height: 27.6
                text: root.providerName; color: "#f3f7ff"
                horizontalAlignment: Text.AlignHCenter
                font.family: ConnectionTheme.heading; font.pixelSize: 20; font.weight: 780
                font.letterSpacing: -0.55
                lineHeightMode: Text.FixedHeight; lineHeight: 27.6
            }
            Item { width: 1; height: 7 }
            Text {
                objectName: root.objectName + "Summary"
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(345, parent.width); height: 48.67
                text: root.summary; color: AccentTheme.color("#99b7d8")
                horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
                font.family: ConnectionTheme.body; font.pointSize: 11.775; font.weight: Font.Normal
                lineHeightMode: Text.FixedHeight; lineHeight: 24.335
            }
        }
        ProviderSurface {
            objectName: root.objectName + "Check"
            x: parent.width - width - 16; y: 16
            width: 40; height: 40; radius: 20; kind: 5
            opacity: root.selected ? 1 : 0
            scale: root.selected ? 1 : 0.8
            Behavior on opacity { NumberAnimation { duration: 180 } }
            Behavior on scale { NumberAnimation { duration: 180 } }
            Shape {
                anchors.centerIn: parent
                width: 24; height: 24; scale: 21 / 24
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    fillColor: "transparent"; strokeColor: "white"; strokeWidth: 2.6
                    capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                    PathSvg { path: "m4.5 12.5 4.9 4.7L19.7 6.9" }
                }
            }
        }
    }
}
