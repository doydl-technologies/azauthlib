pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.VectorImage
import QtQuick.Effects
import "../theme"

Button {
    id: root
    property bool expanded: false
    property string accentFamily: AccentTheme.preset
    visible: AccentTheme.showInfoButtons
    readonly property bool sunken: down || expanded
    enabled: !expanded && AccentTheme.showInfoButtons
    focusPolicy: visible && enabled ? Qt.StrongFocus : Qt.NoFocus
    opacity: enabled ? 1 : 0.4
    width: 21; height: 21
    implicitWidth: 21; implicitHeight: 21
    padding: 4
    leftPadding: 4; rightPadding: 4; topPadding: 4; bottomPadding: 4
    hoverEnabled: enabled
    Accessible.name: text
    Accessible.checked: expanded
    Accessible.description: expanded ? "Help shelf is open" : "Open contextual help shelf"
    Keys.onReturnPressed: if (enabled) clicked()
    HoverHandler { enabled: root.enabled; cursorShape: Qt.PointingHandCursor }
    // Keep the click target and crisp SVG; the PNG supplies the raised surface.
    contentItem: Item {
        transform: Translate {
            // Move both layers together without shifting the click target.
            y: root.enabled && root.hovered && !root.sunken ? -1 : 0
            Behavior on y { NumberAnimation { duration: 120 } }
        }
        Image {
            objectName: root.objectName + "SurfaceImage"
            anchors.centerIn: parent
            anchors.alignWhenCentered: true
            width: root.width + 5
            height: root.height + 5

            source: root.accentFamily !== "blue" ? AccentTheme.artwork(root.sunken ?
                "surface-head-icon--sunken-circle.png" : "surface-head-icon--raised-circle.png", root.accentFamily) : root.sunken
                ? Qt.resolvedUrl("../../../assets/controls/surface-head-icon--sunken-circle.png")
                : Qt.resolvedUrl("../../../assets/controls/surface-head-icon--raised-circle.png")
            sourceSize: root.sunken ? Qt.size(66, 66) : Qt.size(69, 70)
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true
        }
        VectorImage {
            objectName: root.objectName + "SvgImage"
            anchors.centerIn: parent
            anchors.alignWhenCentered: true

            anchors.horizontalCenterOffset: -1
            anchors.verticalCenterOffset: -1

            width: 12
            height: 12

            source: Qt.resolvedUrl("../../../assets/icons/svg/status/information-alerts/info-borderless.svg")
            fillMode: VectorImage.PreserveAspectFit
            // Render curves at the final screen scale, not through a tiny mipmap.
            preferredRendererType: VectorImage.CurveRenderer
            
        }



    }
    background: Rectangle {
        objectName: root.objectName + "Background"
        radius: 4
        color: "transparent"
        border.width: root.enabled && root.visualFocus ? 1 : 0
        border.color: AccentTheme.paletteFor(root.accentFamily).accent
    }
}
