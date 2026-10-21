pragma ComponentBehavior: Bound
import QtQuick

// Animation only: no modal backdrop, input handling, text or acknowledgement.
Item {
    id: root
    visible: false
    enabled: false
    z: 100

    function play() {
        dismiss()
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
    }

    AnimatedSuccessIcon {
        id: successIcon
        objectName: "actionSuccessIcon"
        anchors.centerIn: parent
        width: 96; height: 96
        onCompleteChanged: if (root.visible && complete)
            holdTimer.restart()
    }
    Timer {
        id: startDelay
        interval: 140
        onTriggered: successIcon.play()
    }
    Timer {
        id: holdTimer
        interval: 350
        onTriggered: fadeOut.start()
    }
    NumberAnimation {
        id: fadeOut
        target: root; property: "opacity"; to: 0
        duration: 180; easing.type: Easing.InOutCubic
        onFinished: root.dismiss()
    }
    Component.onDestruction: dismiss()
}
