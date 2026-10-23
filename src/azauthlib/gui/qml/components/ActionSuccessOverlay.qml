pragma ComponentBehavior: Bound
import QtQuick
import "../theme"

// Animation only: no modal backdrop, input handling, text or acknowledgement.
Item {
    id: root
    visible: false
    enabled: false
    z: 100
    property bool connectionAction: false
    property bool connectionFallback: false
    // Local to the preview instance; the app never sets this override.
    property real playbackRate: 1
    // Per-instance geometry and timing overrides for animation previews.
    property size connectionIconSize: Qt.size(180, 128)
    property point connectionIconOffset: Qt.point(0, 0)
    property int connectionHoldDuration: ConnectionTheme.newConnectionSuccessHold
    property real connectionGlowBoost: 0
    readonly property bool useConnection: connectionAction && !connectionFallback
    readonly property real durationScale: useConnection ? connectionIcon.durationScale : 1

    function play(action) {
        dismiss()
        connectionAction = action === "created"
        connectionFallback = false
        opacity = 1
        visible = true
        // Let an activation/removal confirmation finish fading before drawing.
        startDelay.restart()
    }
    function dismiss() {
        visible = false
        startDelay.stop()
        holdTimer.stop()
        fadeOut.stop()
        successIcon.reset()
        connectionIcon.reset()
    }

    AnimatedSuccessIcon {
        id: successIcon
        objectName: "actionSuccessIcon"
        anchors.centerIn: parent
        width: 96; height: 96
        visible: !root.useConnection
        onCompleteChanged: if (root.visible && !root.useConnection && complete)
            holdTimer.restart()
    }
    AnimatedConnectionIcon {
        id: connectionIcon
        objectName: "newConnectionSuccessIcon"
        anchors.centerIn: parent
        anchors.horizontalCenterOffset: root.connectionIconOffset.x
        anchors.verticalCenterOffset: root.connectionIconOffset.y
        width: root.connectionIconSize.width; height: root.connectionIconSize.height
        visible: root.useConnection
        playbackRate: root.playbackRate
        outerGlowBoost: root.connectionGlowBoost
        onCompleteChanged: if (root.visible && root.useConnection && complete)
            holdTimer.restart()
        onLoadFailed: {
            if (!root.visible || !root.useConnection) return
            root.connectionFallback = true
            successIcon.play()
        }
    }
    Timer {
        id: startDelay
        interval: ConnectionTheme.reducedMotion ? 0 : Math.round(140 * root.durationScale)
        onTriggered: if (root.useConnection) connectionIcon.play(); else successIcon.play()
    }
    Timer {
        id: holdTimer
        objectName: "connectionSuccessHoldTimer"
        interval: Math.round((root.useConnection && connectionIcon.circularBackground ?
            root.connectionHoldDuration : 350) * root.durationScale)
        onTriggered: fadeOut.start()
    }
    NumberAnimation {
        id: fadeOut
        target: root; property: "opacity"; to: 0
        duration: ConnectionTheme.reducedMotion ? 0 : Math.round(180 * root.durationScale); easing.type: Easing.InOutCubic
        onFinished: root.dismiss()
    }
    Component.onDestruction: dismiss()
}
