pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Effects
import QtQuick.Window

// Shader geometry uses a 172-pixel orbit in CSS units; QML scales the
// complete drawing for the profile card and display DPI.
Item {
    id: root
    property bool testing: false
    property real idleFaceSize: 82
    property real idleIconSize: 31
    property int colorCycleDuration: 6000
    readonly property bool running: testing && visible && Window.window !== null && Window.window.visible
    property real activity: testing ? 1 : 0
    property real outerAngle: 0
    property real innerAngle: 0
    property real outerDotAngle: 0
    property real innerDotAngle: 0
    property color plugColor: "#2563eb"
    Behavior on activity { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    onRunningChanged: if (running) {
        outerAngle = 0; innerAngle = 0; outerDotAngle = 0; innerDotAngle = 0
        plugColor = "#2563eb"
    }
    NumberAnimation on outerAngle {
        objectName: root.objectName + "OuterAnimation"
        from: 0; to: 360; duration: 3500; loops: Animation.Infinite; running: root.running
    }
    NumberAnimation on innerAngle {
        objectName: root.objectName + "InnerAnimation"
        from: 0; to: -360; duration: 2700; loops: Animation.Infinite; running: root.running
    }
    NumberAnimation on outerDotAngle {
        objectName: root.objectName + "OuterDotAnimation"
        from: 0; to: 360; duration: 5500; loops: Animation.Infinite; running: root.running
    }
    NumberAnimation on innerDotAngle {
        objectName: root.objectName + "InnerDotAnimation"
        from: 0; to: -360; duration: 3000; loops: Animation.Infinite; running: root.running
    }
    SequentialAnimation on plugColor {
        objectName: root.objectName + "ColorAnimation"
        loops: Animation.Infinite; running: root.running
        ColorAnimation { from: "#2563eb"; to: "#38a8ff"; duration: root.colorCycleDuration / 16 }
        ColorAnimation { to: "#5abfff"; duration: root.colorCycleDuration / 16 }
        ColorAnimation { to: "#7ddcff"; duration: root.colorCycleDuration / 16 }
        ColorAnimation { to: "#00d4ff"; duration: root.colorCycleDuration / 16 }
        ColorAnimation { to: "#06b6d4"; duration: root.colorCycleDuration / 16 }
        ColorAnimation { to: "#6366f1"; duration: root.colorCycleDuration * 3 / 16 }
        ColorAnimation { to: "#8b5cf6"; duration: root.colorCycleDuration / 16 }
        ColorAnimation { to: "#a78bfa"; duration: root.colorCycleDuration / 16 }
        ColorAnimation { to: "#ffffff"; duration: root.colorCycleDuration * 5 / 16 }
        ColorAnimation { to: "#2563eb"; duration: root.colorCycleDuration / 16 }
    }
    ConnectionSurface {
        objectName: root.objectName + "IdleFace"
        anchors.centerIn: parent
        width: root.idleFaceSize; height: width; radius: width / 2
        smoothCircleOutline: true
        opacity: 1 - root.activity; visible: opacity > 0
        depth: 7; blur: 16; radial: true
        lightOffset: Qt.point(-5, -5); lightBlur: 14; lightColor: "#66345b85"
        topColor: "#1c456d"; middleColor: "#123152"; bottomColor: "#0d233c"
        borderColor: "#388bd0"; rimColor: "#3376b9ed"
        ConnectionIcon {
            anchors.centerIn: parent
            width: root.idleIconSize; height: width; name: "plug"
        }
    }
    Item {
        anchors.centerIn: parent
        width: 172; height: 172
        scale: Math.min(root.width, root.height) / 172
        opacity: root.activity; visible: opacity > 0
        ShaderEffect {
            objectName: root.objectName + "OrbitShader"
            // Include the dot/trail glow outside the orbit's nominal bounds.
            x: -20; y: -20; width: 212; height: 212
            readonly property real outerRotation: root.outerAngle
            readonly property real innerRotation: root.innerAngle
            readonly property real outerDotRotation: root.outerDotAngle
            readonly property real innerDotRotation: root.innerDotAngle
            fragmentShader: Qt.resolvedUrl("../shaders/connection-test-halo.frag.qsb")
        }
        ConnectionSurface {
            objectName: root.objectName + "TestingFace"
            anchors.centerIn: parent
            width: 69; height: 69; radius: 34.5
            smoothCircleOutline: true
            angle: 145; middleStop: 0.65
            topColor: "#204366"; middleColor: "#102a45"; bottomColor: "#10263f"
            borderColor: "#326394"
            depth: 5; shadowOffset: Qt.point(5, 7); blur: 14; shadowColor: "#03101f"
            lightOffset: Qt.point(-2, -2); lightBlur: 9; lightColor: "#2178bef1"
            rimColor: "#1cbfe6ff"
            ConnectionIcon {
                objectName: root.objectName + "TestingPlug"
                anchors.centerIn: parent
                width: 27; height: 27; name: "animatedPlug"
                // This animated plug is the only SVG recoloring exception.
                // Keep the shared icon renderer and all other artwork untinted.
                layer.enabled: true
                layer.textureSize: Qt.size(108, 108)
                layer.smooth: true
                layer.mipmap: true
                layer.effect: MultiEffect {
                    objectName: root.objectName + "TestingPlugColorEffect"
                    colorization: 1.0
                    colorizationColor: root.plugColor
                }
            }
        }
    }
}
