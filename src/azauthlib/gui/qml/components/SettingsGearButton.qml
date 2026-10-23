pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import "../theme"

Button {
    id: root
    property bool visualEnabled: enabled
    // Give a quick click enough time to show the complete press before opening.
    property int hoverInDuration: 450
    property int hoverOutDuration: 550
    property int pressDuration: 450
    property int releaseDuration: 550
    property int pressHoldDuration: 120
    property bool activationPending: false
    signal activationRequested()
    function requestActivation() {
        if (!enabled || !visible || activationPending) return
        if (ConnectionTheme.reducedMotion) {
            activationRequested()
            return
        }
        activationPending = true
        pressVisualRequested = true
        if (pressProgress >= 1) releaseHold.restart()
    }
    onClicked: requestActivation()
    property real hoverProgress: enabled && hovered ? 1 : 0
    Behavior on hoverProgress {
        NumberAnimation {
            duration: ConnectionTheme.reducedMotion ? 0 :
                (root.enabled && root.hovered ? root.hoverInDuration : root.hoverOutDuration)
            easing.type: Easing.InOutCubic
        }
    }
    property bool pressVisualRequested: false
    property real pressProgress: pressVisualRequested ? 1 : 0
    Behavior on pressProgress {
        NumberAnimation {
            duration: ConnectionTheme.reducedMotion ? 0 :
                (root.pressVisualRequested ? root.pressDuration : root.releaseDuration)
            easing.type: Easing.InOutCubic
        }
    }
    onPressProgressChanged: {
        if (pressProgress >= 1 && pressVisualRequested && !down)
            releaseHold.restart()
    }
    onDownChanged: {
        if (down) {
            releaseHold.stop()
            pressVisualRequested = true
        } else if (ConnectionTheme.reducedMotion) {
            pressVisualRequested = false
        } else if (pressProgress >= 1) {
            releaseHold.restart()
        }
    }
    onEnabledChanged: if (!enabled) {
        releaseHold.stop()
        activationPending = false
        pressVisualRequested = false
    }
    onVisibleChanged: if (!visible) {
        releaseHold.stop()
        activationPending = false
        pressVisualRequested = false
    }
    Timer {
        id: releaseHold
        interval: root.pressHoldDuration
        onTriggered: if (!root.down) {
            root.pressVisualRequested = false
            if (root.activationPending) {
                root.activationPending = false
                root.activationRequested()
            }
        }
    }
    Connections {
        target: ConnectionTheme
        function onReducedMotionChanged() {
            if (ConnectionTheme.reducedMotion) {
                releaseHold.stop()
                root.pressVisualRequested = root.down
                if (root.activationPending) {
                    root.activationPending = false
                    root.activationRequested()
                }
            }
        }
    }
    readonly property string artworkState: enabled && pressVisualRequested ? "sunken" :
        enabled && hovered ? "hover" : "raised"
    readonly property string artworkName: "settings-gear-" + artworkState + ".svg"
    implicitWidth: 40
    implicitHeight: 40
    padding: 0
    text: "Settings"
    Accessible.name: text
    hoverEnabled: enabled
    focusPolicy: enabled ? Qt.StrongFocus : Qt.NoFocus
    opacity: visualEnabled ? 1 : 0.37
    Keys.onReturnPressed: if (enabled) clicked()
    HoverHandler { enabled: root.enabled; cursorShape: Qt.PointingHandCursor }
    background: Rectangle {
        radius: 8
        color: "transparent"
        border.width: root.enabled && root.visualFocus ? 1 : 0
        border.color: ConnectionTheme.accent
    }
    // Exactly one Image: family-aware SVG layers, instant state selection,
    // no crossfade or additional shadow drawn over the original artwork.
    contentItem: Image {
        objectName: "settingsGearImage"
        readonly property url originalSvgSource: Qt.resolvedUrl(
            "../../../assets/icons/svg/actions/relief/" + root.artworkName)
        source: AccentTheme.customAccent ? AccentTheme.artwork(root.artworkName) :
            "image://actionicons/" + root.artworkName
        sourceSize: Qt.size(192, 192)
        asynchronous: false
        retainWhileLoading: true
        cache: true
        smooth: true
        mipmap: true
        fillMode: Image.PreserveAspectFit
        transform: Translate {
            objectName: "settingsGearMovement"
            y: ConnectionTheme.reducedMotion ? 0 :
                -2 * root.hoverProgress * (1 - root.pressProgress) + 1.5 * root.pressProgress
        }
    }
}
