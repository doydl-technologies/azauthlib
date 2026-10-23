import QtQuick
import "../theme"
import QtQuick.Window

// Keep layout spacing unchanged, but blend thin edges during fractional scroll.
// Rounding contentY would trade shimmer for stepping and is wrong at fractional
// zoom/DPI. The stroke stays at least one physical pixel without snapping motion.
Item {
    id: root
    property real contentScale: 1
    property color color: AccentTheme.color("#315673")
    readonly property real deviceRatio: Screen.devicePixelRatio
    readonly property real physicalScale: Math.max(0.01, contentScale * deviceRatio)
    // Quantize the weight, not its position, to whole physical pixels.
    readonly property real physicalStroke: Math.max(1, Math.round(physicalScale))
    readonly property real strokeHeight: physicalStroke / physicalScale
    implicitHeight: 1
    Rectangle {
        id: stroke
        objectName: root.objectName + "Stroke"
        anchors.verticalCenter: parent.verticalCenter
        anchors.alignWhenCentered: false
        width: parent.width; height: root.physicalStroke + 1
        // Cancel vertical zoom/DPI for the tiny coverage ramp, keeping
        // its center and the full rule width attached to the scrolling content.
        // Otherwise Qt's software gradient cache rounds its height before zoom.
        transform: Scale { origin.y: stroke.height / 2; yScale: 1 / root.physicalScale }
        // Exact one-device-pixel edge ramps, not binary rectangle coverage.
        // This works in the software renderer too, where Rectangle's AA flag
        // alone still rounds a moving hairline between one and two bright rows.
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.rgba(root.color.r, root.color.g, root.color.b, 0) }
            GradientStop { position: 1 / (root.physicalStroke + 1); color: root.color }
            GradientStop { position: root.physicalStroke / (root.physicalStroke + 1); color: root.color }
            GradientStop { position: 1; color: Qt.rgba(root.color.r, root.color.g, root.color.b, 0) }
        }
    }
}
