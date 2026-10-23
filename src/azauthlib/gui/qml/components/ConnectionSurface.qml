import QtQuick
import "../theme"

// Render the fill, border, and shadows in one pass to preserve the rounded
// boundary and avoid the hard inset edges of chained InnerShadow textures.
Item {
    id: root
    property real radius: 10
    property bool sunken: false
    property bool recessedFill: false
    property bool diagonal: !recessedFill
    property bool radial: false
    property real angle: 135
    property color topColor: recessedFill ? "#071626" : "#1a3550"
    property color middleColor: recessedFill ? "#0c2137" : "#142d4e"
    property color bottomColor: recessedFill ? "#102b48" : "#0d2238"
    property real middleStop: recessedFill ? 0.5 : 0.55
    property color borderColor: AccentTheme.color("#345b85")
    property real borderWidth: 1
    property real depth: 3
    property real blur: 7
    property real lightBlur: blur * 0.85
    property point shadowOffset: Qt.point(depth, depth)
    property point lightOffset: Qt.point(-depth * 0.7, -depth * 0.7)
    property color shadowColor: "#03101e"
    property color lightColor: AccentTheme.color("#72345b85")
    property bool shadows: true
    property color rimColor: "transparent"
    // Opt in for circular plug holders without changing other controls/dots.
    property bool smoothCircleOutline: false
    // Native stroke stays above inset shading/child shadows at fractional scales.
    property bool crispOutline: false
    property real outlineWidth: 1.25

    ShaderEffect {
        objectName: root.objectName + "Shader"
        readonly property real padding: root.sunken || !root.shadows ? 0 : Math.ceil(Math.max(
            root.blur * 1.75 + Math.max(Math.abs(root.shadowOffset.x), Math.abs(root.shadowOffset.y)),
            root.lightBlur * 1.75 + Math.max(Math.abs(root.lightOffset.x), Math.abs(root.lightOffset.y)))) + 1
        x: -padding; y: -padding
        width: root.width + padding * 2; height: root.height + padding * 2
        readonly property vector2d surfaceSize: Qt.vector2d(root.width, root.height)
        readonly property real cornerRadius: Math.min(root.radius, root.width / 2, root.height / 2)
        readonly property real lineWidth: root.crispOutline ? 0 : root.borderWidth
        readonly property real shadowBlur: root.blur
        readonly property real highlightBlur: root.lightBlur
        readonly property vector2d darkOffset: Qt.vector2d(root.shadowOffset.x, root.shadowOffset.y)
        readonly property vector2d brightOffset: Qt.vector2d(root.lightOffset.x, root.lightOffset.y)
        readonly property real inset: root.sunken ? 1 : 0
        readonly property real hasShadows: root.shadows ? 1 : 0
        readonly property real gradientAngle: root.diagonal ? root.angle : 180
        readonly property real radialFill: root.radial ? 1 : 0
        readonly property real centerStop: root.middleStop
        readonly property real circleOutline: root.smoothCircleOutline ? 1 : 0
        readonly property color colorTop: root.topColor
        readonly property color colorMiddle: root.middleColor
        readonly property color colorBottom: root.bottomColor
        readonly property color colorBorder: root.borderColor
        readonly property color colorShadow: root.shadowColor
        readonly property color colorLight: root.lightColor
        readonly property color colorRim: root.rimColor
        fragmentShader: Qt.resolvedUrl("../shaders/connection-surface.frag.qsb")
    }
    Rectangle {
        objectName: root.objectName + "Outline"
        anchors.fill: parent
        visible: root.crispOutline
        z: 100
        color: "transparent"
        radius: root.radius
        antialiasing: true
        border.width: root.outlineWidth
        border.color: root.borderColor
    }
}
