pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import "../theme"

// Preview-only transport/camera. AnimationController seeks the same native
// timeline used by production; no parallel hand-coded pose calculations.
Item {
    id: root
    property real positionMs: 0
    property real playbackRate: 1
    property real zoomFactor: 1
    property bool paused: false
    property bool pendingPlay: false
    readonly property real durationMs: controlledTimeline.baseDuration
    readonly property bool playing: playback.running
    readonly property bool atEnd: positionMs >= durationMs
    readonly property real frameDuration: 1000 / 60
    readonly property int totalFrames: Math.ceil(durationMs / frameDuration)
    readonly property int currentFrame: atEnd ? totalFrames : Math.round(positionMs / frameDuration)
    readonly property bool ready: icon.ready
    readonly property real effectiveRate: Math.max(0.1, Math.min(2,
        Number.isFinite(playbackRate) ? playbackRate : 1))
    readonly property string phase: atEnd ? "Connected - final outer glow" :
        positionMs < controlledTimeline.insertionStart ? "Disconnected" :
        positionMs < controlledTimeline.contactTime ? "Plug insertion" :
        positionMs < controlledTimeline.innerGlowStart ? "Contact - cyan burst" :
        positionMs < controlledTimeline.outerGlowStart ? "Inner glow and burst" : "Outer glow"

    function pause() {
        pendingPlay = false
        playback.stop()
        paused = true
    }
    function resume() {
        playback.stop()
        paused = false
        if (!ready) { pendingPlay = true; return }
        pendingPlay = false
        if (ConnectionTheme.reducedMotion) {
            positionMs = durationMs
            return
        }
        if (atEnd) positionMs = 0
        playback.from = positionMs
        playback.to = durationMs
        playback.duration = Math.max(1, Math.round((durationMs - positionMs) / effectiveRate))
        playback.start()
    }
    function replay() { seek(0); resume() }
    function togglePlayback() { if (playing || pendingPlay) pause(); else resume() }
    function seek(milliseconds) {
        pause()
        let destination = Math.max(0, Math.min(durationMs,
            Number.isFinite(milliseconds) ? milliseconds : 0))
        // Qt seeks only active jobs. Restore the shared initial state and
        // reload atomically so later glows cannot leak into a backward scrub.
        icon.reset()
        positionMs = destination
        manualController.reload()
    }
    function stepFrame(direction) {
        seek(Math.max(0, Math.min(totalFrames, currentFrame + direction)) * frameDuration)
    }
    function centerView() {
        viewport.contentX = Math.max(0, (viewport.contentWidth - viewport.width) / 2)
        viewport.contentY = Math.max(0, (viewport.contentHeight - viewport.height) / 2)
    }
    onReadyChanged: if (ready && pendingPlay) resume()
    onPlaybackRateChanged: if (playback && playback.running && !atEnd) resume()
    onZoomFactorChanged: Qt.callLater(centerView)

    Flickable {
        id: viewport
        objectName: "previewAnimationViewport"
        anchors.fill: parent
        clip: true
        contentWidth: Math.max(width, icon.width + 96)
        contentHeight: Math.max(height, icon.height + 96)
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.HorizontalAndVerticalFlick
        onWidthChanged: Qt.callLater(root.centerView)
        onHeightChanged: Qt.callLater(root.centerView)
        ScrollBar.horizontal: ScrollBar { }
        ScrollBar.vertical: ScrollBar { }
        AnimatedConnectionIcon {
            id: icon
            objectName: "newConnectionSuccessIcon"
            x: (viewport.contentWidth - width) / 2
            y: (viewport.contentHeight - height) / 2
            width: 180 * root.zoomFactor; height: 128 * root.zoomFactor
            inspectionMode: true
            outlinePlaybackEnabled: !root.paused
        }
    }
    AnimationController {
        id: manualController
        objectName: "previewTimelineController"
        progress: root.positionMs / root.durationMs
        animation: ConnectionAnimationTimeline {
            id: controlledTimeline
            objectName: "previewControlledTimeline"
            targetItem: icon
        }
    }
    NumberAnimation {
        id: playback
        objectName: "previewPlaybackClock"
        target: root; property: "positionMs"
        easing.type: Easing.Linear
    }
    Connections {
        target: ConnectionTheme
        function onReducedMotionChanged() {
            if (ConnectionTheme.reducedMotion && (root.playing || root.pendingPlay)) {
                root.pause()
                root.positionMs = root.durationMs
            }
        }
    }
    Component.onDestruction: playback.stop()
}
