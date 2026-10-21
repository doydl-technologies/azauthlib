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
            ProviderSurface {
                objectName: root.objectName + "Halo"
                anchors.horizontalCenter: parent.horizontalCenter
                width: 108; height: 108; radius: 54; kind: 3
                selected: root.selected; hovered: root.hovered
                SvgImageShadow {
                    objectName: root.objectName + "LogoShadow"
                    source: originalLogo
                }
                Image {
                    id: originalLogo
                    objectName: root.objectName + "Logo"
                    // Preserve the original source URL for inspection; the
                    // provider renders that exact SVG with mask/filter support.
                    readonly property url originalSvgSource: root.logoSource
                    readonly property int renderEdge: Math.max(384,
                        Math.ceil(root.logoSize * Screen.devicePixelRatio * 4))
                    anchors.centerIn: parent
                    width: root.logoSize; height: root.logoSize
                    source: "image://providerlogos/" + root.logoSource.toString().split("/").pop()
                    sourceSize: Qt.size(renderEdge, renderEdge)
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    retainWhileLoading: true
                    smooth: true; mipmap: true
                    onStatusChanged: {
                        if (status === Image.Ready || status === Image.Error)
                            root.logoSettled(root.providerId, status === Image.Ready)
                    }
                    Component.onCompleted: {
                        if (status === Image.Ready || status === Image.Error)
                            root.logoSettled(root.providerId, status === Image.Ready)
                    }
                    // No effect layer on the foreground: the separate shadow
                    // samples this texture and cannot blur or tint its colors.
                }
            }
            Item { width: 1; height: 11 }
            Text {
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
                text: root.summary; color: "#99b7d8"
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
