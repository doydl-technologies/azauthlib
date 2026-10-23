pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.VectorImage
import "../theme"

Item {
    id: root
    // Four preloaded vector frames: 0 -> 1 -> 2 -> 3 -> 0, without crossfading.
    property int frameInterval: 220
    property int frameIndex: 0
    property bool running: visible
    implicitWidth: 17; implicitHeight: 17

    Repeater {
        model: 4
        VectorImage {
            required property int index
            objectName: "connectionTestSignalFrame" + index
            anchors.fill: parent
            visible: index === root.frameIndex && !AccentTheme.customAccent
            source: Qt.resolvedUrl("../../../assets/animate/Multicolor-blue-white-podcast-line-" + index + ".svg")
            fillMode: VectorImage.PreserveAspectFit
            preferredRendererType: VectorImage.CurveRenderer
        }
    }
    Repeater {
        model: 4
        Image {
            required property int index
            objectName: "connectionThemedSignalFrame" + index
            anchors.fill: parent
            visible: AccentTheme.customAccent && index === root.frameIndex
            source: AccentTheme.customAccent ? AccentTheme.artwork("Multicolor-blue-white-podcast-line-" + index + ".svg") : ""
            sourceSize: Qt.size(96, 96)
            fillMode: Image.PreserveAspectFit
            smooth: true; mipmap: true
        }
    }
    Timer {
        objectName: "connectionTestSignalTimer"
        interval: Math.max(16, root.frameInterval)
        repeat: true
        // A busy button is disabled to clicks, but its progress must still animate.
        running: root.running && root.visible
        onRunningChanged: root.frameIndex = 0
        onTriggered: root.frameIndex = (root.frameIndex + 1) % 4
    }
}
