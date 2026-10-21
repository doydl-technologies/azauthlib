pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects
import QtQuick.Shapes

// Native, one-shot confirmation mark. No image frames or video playback.
Item {
    id: root

    implicitWidth: 44
    implicitHeight: 44
    property color accent: "#57e5ae"
    property color checkColor: "#8dffd1"
    property color surfaceTop: "#205c53"
    property color surfaceBottom: "#0a2637"
    property real badgeOpacity: 0
    property real badgeScale: 0.12
    property real shortProgress: 0
    property real longProgress: 0
    property real glowStrength: 0.24
    property real haloOpacity: 0
    property real haloScale: 1
    readonly property bool running: successAnimation.running
    readonly property bool complete: shortProgress === 1 && longProgress === 1 && !running

    function stop() {
        successAnimation.stop()
    }

    function reset() {
        stop()
        badgeOpacity = 0
        badgeScale = 0.12
        shortProgress = 0
        longProgress = 0
        glowStrength = 0.24
        haloOpacity = 0
        haloScale = 1
    }

    function play() {
        reset()
        successAnimation.start()
    }

    onVisibleChanged: {
        if (!visible)
            reset()
    }

    // The check, disc and glow share one transform, including the single heartbeat.
    Item {
        id: mark
        anchors.fill: parent
        opacity: root.badgeOpacity
        scale: root.badgeScale

        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: root.accent
            opacity: root.haloOpacity
            scale: root.haloScale
        }

        Rectangle {
            anchors.fill: parent
            radius: width / 2
            border.width: 1.25
            border.color: root.accent
            gradient: Gradient {
                GradientStop { position: 0; color: root.surfaceTop }
                GradientStop { position: 1; color: root.surfaceBottom }
            }
            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.accent
                shadowOpacity: root.glowStrength
                shadowBlur: 0.4
                shadowVerticalOffset: 0
            }
        }

        Shape {
            id: check
            objectName: root.objectName + "Check"
            anchors.fill: parent
            visible: root.shortProgress > 0
            // Native edge smoothing stays clean while the mark draws and pulses.
            preferredRendererType: Shape.CurveRenderer
            antialiasing: true
            ShapePath {
                fillColor: "transparent"
                strokeColor: root.checkColor
                strokeWidth: check.width * 0.086
                capStyle: ShapePath.RoundCap
                joinStyle: ShapePath.RoundJoin
                startX: check.width * 0.27
                startY: check.height * 0.52
                PathLine {
                    x: check.width * (0.27 + 0.16 * root.shortProgress)
                    y: check.height * (0.52 + 0.16 * root.shortProgress)
                }
                PathLine {
                    x: check.width * (0.27 + 0.16 * root.shortProgress + 0.33 * root.longProgress)
                    y: check.height * (0.52 + 0.16 * root.shortProgress - 0.36 * root.longProgress)
                }
            }
        }
    }

    // 960 ms total: draw completely, breathe for 60 ms, then beat exactly once.
    SequentialAnimation {
        id: successAnimation
        PauseAnimation { duration: 80 }
        ParallelAnimation {
            NumberAnimation {
                target: root; property: "badgeOpacity"; to: 1
                duration: 110; easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: root; property: "badgeScale"; to: 1.06
                duration: 180; easing.type: Easing.OutCubic
            }
        }
        NumberAnimation {
            target: root; property: "badgeScale"; to: 1
            duration: 80; easing.type: Easing.InOutCubic
        }
        NumberAnimation {
            target: root; property: "shortProgress"; to: 1
            duration: 80; easing.type: Easing.InOutCubic
        }
        NumberAnimation {
            target: root; property: "longProgress"; to: 1
            duration: 140; easing.type: Easing.OutCubic
        }
        PauseAnimation { duration: 60 }
        ParallelAnimation {
            SequentialAnimation {
                NumberAnimation {
                    target: root; property: "badgeScale"; to: 1.12
                    duration: 100; easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    target: root; property: "badgeScale"; to: 0.985
                    duration: 160; easing.type: Easing.InOutCubic
                }
                NumberAnimation {
                    target: root; property: "badgeScale"; to: 1
                    duration: 80; easing.type: Easing.OutCubic
                }
            }
            SequentialAnimation {
                NumberAnimation {
                    target: root; property: "glowStrength"; to: 0.42
                    duration: 100; easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    target: root; property: "glowStrength"; to: 0.24
                    duration: 240; easing.type: Easing.InOutCubic
                }
            }
            SequentialAnimation {
                NumberAnimation {
                    target: root; property: "haloOpacity"; to: 0.28
                    duration: 80; easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    target: root; property: "haloOpacity"; to: 0
                    duration: 260; easing.type: Easing.InOutCubic
                }
            }
            NumberAnimation {
                target: root; property: "haloScale"; to: 1.3
                duration: 340; easing.type: Easing.OutCubic
            }
        }
    }
}
