pragma ComponentBehavior: Bound
import QtQuick
import "../theme"

// Decorative native strokes only. The parent coordinates timing and reduced
// motion; the plug itself never scales, bounces or changes its seated pose.
Item {
    id: root
    property real progress: 0
    property real unit: 1
    property real startRadius: 35
    property real centerX: width / 2
    property real centerY: height / 2
    property color color: AccentTheme.color("#56d7ef")
    readonly property real clampedProgress: Math.max(0, Math.min(1, progress))
    readonly property real outwardProgress: Math.min(1, clampedProgress / 0.72)
    // A restrained OutBack curve: overshoot affects ray travel, never the icon.
    readonly property real spring: 1 + 2.3 * Math.pow(outwardProgress - 1, 3)
        + 1.3 * Math.pow(outwardProgress - 1, 2)
    readonly property real rayRadius: (startRadius + 18 * spring) * unit
    readonly property real rayLength: 11 * Math.min(1, clampedProgress / 0.16)
        * Math.min(1, (1 - clampedProgress) / 0.38) * unit
    opacity: Math.min(1, clampedProgress / 0.1)
        * Math.min(1, (1 - clampedProgress) / 0.45)
    visible: progress > 0 && progress < 1
    enabled: false
    Accessible.ignored: true

    Repeater {
        model: 8
        delegate: Item {
            id: ray
            required property int index
            objectName: "connectionSuccessRay" + index
            x: root.centerX; y: root.centerY
            width: 0; height: 0
            rotation: index * 45 - 90
            Rectangle {
                objectName: "connectionSuccessStroke" + ray.index
                x: root.rayRadius; y: -height / 2
                width: root.rayLength; height: 2 * root.unit
                radius: height / 2
                color: root.color; antialiasing: true
            }
        }
    }
}
