pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import "../theme"

// One rigid shell and cable, taken from the final artwork, for the whole slide.
// Once seated, only decorative rays and glows change. Source SVGs stay intact.
Item {
    id: root
    implicitWidth: 180; implicitHeight: 128
    readonly property bool circularBackground: true
    readonly property string sourcePalette: "white-circle"
    property bool outlinePlaybackEnabled: true
    property int outlineFrame: 0
    readonly property int outlineFrameInterval: Math.max(16,
        Math.round(ConnectionTheme.newConnectionOutlineFrameInterval * durationScale))
    readonly property bool spinning: circularBackground && outlinePlaybackEnabled && ready &&
        outerGlowProgress >= 1 && (complete || inspectionMode) &&
        visible && Window.window !== null && Window.window.visible && !ConnectionTheme.reducedMotion
    property int frameRevision: 0
    // Optional preview override. Production callers retain the original 1x timing.
    property real playbackRate: 1
    // Extra glow-only contribution for local previews; zero changes nothing.
    property real outerGlowBoost: 0
    // A paused/scrubbed preview keeps its artwork visible even at time zero.
    property bool inspectionMode: false
    readonly property real durationScale: 1 / Math.max(0.1, Math.min(2,
        Number.isFinite(playbackRate) ? playbackRate : 1))
    readonly property string palette: "white"
    property real insertionProgress: 0
    property real glowProgress: 0
    property real outerGlowProgress: 0
    property real burstProgress: 0
    property real badgeOpacity: 0
    readonly property real badgeScale: 1
    property bool complete: false
    property bool pendingStart: false
    readonly property bool running: motion.running || pendingStart
    readonly property real viewBoxX: 0
    readonly property real viewBoxY: 0
    readonly property real viewBoxWidth: 1254
    readonly property real viewBoxHeight: 1254
    readonly property real paintWidth: Math.min(width, height * viewBoxWidth / viewBoxHeight)
    readonly property real paintLeft: (width - paintWidth) / 2
    readonly property real travel: paintWidth * 226 / viewBoxWidth
    readonly property var artwork: {
        const revision = frameRevision
        let layers = [socket, slots, pins, plug, lip, badgeBase,
            badgePlus, glowPlus, outerAura, outerEdge, finalArtwork]
        if (circularBackground) {
            layers = layers.concat([surface, surfaceAura, surfaceEdge])
            for (let i = 0; i < spinFrames.count; ++i) layers.push(spinFrames.itemAt(i))
        }
        return layers
    }
    readonly property bool ready: artwork.every(layer => layer && layer.status === Image.Ready)
    readonly property bool assetError: artwork.some(layer => layer && layer.status === Image.Error)
    signal loadFailed()

    function reset() {
        motion.stop()
        outlineFrame = 0
        pendingStart = false
        insertionProgress = 0; glowProgress = 0; outerGlowProgress = 0; burstProgress = 0
        badgeOpacity = 0; complete = false
    }
    function begin() {
        pendingStart = false
        if (ConnectionTheme.reducedMotion) {
            insertionProgress = 1; glowProgress = 1; outerGlowProgress = 1; burstProgress = 1
            badgeOpacity = 1; complete = true
        } else motion.start()
    }
    function play() {
        reset()
        pendingStart = true
        settleArtwork()
    }
    function settleArtwork() {
        if (!pendingStart) return
        if (assetError) {
            reset()
            loadFailed()
        } else if (ready) begin()
    }
    onReadyChanged: if (ready) settleArtwork()
    onAssetErrorChanged: if (assetError) settleArtwork()
    onVisibleChanged: if (!visible) reset()

    component ArtworkLayer: Image {
        required property string part
        width: root.width; height: root.height
        source: "image://connectionanimation/" + root.sourcePalette + "/" + part +
            (AccentTheme.customAccent ? "/" + AccentTheme.preset : "")
        // Inspectors reuse one high-resolution texture set: changing camera
        // zoom must not rerasterize every filtered SVG on the UI thread.
        sourceSize.width: root.inspectionMode ? 1024 : Math.ceil(root.paintWidth * Screen.devicePixelRatio * 2)
        sourceSize.height: root.inspectionMode ? Math.round(1024 * root.viewBoxHeight / root.viewBoxWidth) :
            Math.ceil(root.paintWidth * root.viewBoxHeight / root.viewBoxWidth * Screen.devicePixelRatio * 2)
        fillMode: Image.PreserveAspectFit
        smooth: true; mipmap: true
        asynchronous: false
    }
    Item {
        anchors.fill: parent
        opacity: root.inspectionMode ? 1 : root.badgeOpacity
        Item {
            objectName: "newConnectionCompositeLayers"
            anchors.fill: parent
            visible: root.outerGlowProgress < 1
            ArtworkLayer {
                id: surface; part: "surface"
                objectName: "newConnectionBackgroundDisc"
                source: root.circularBackground ? "image://connectionanimation/" + root.sourcePalette + "/surface" +
                    (AccentTheme.customAccent ? "/" + AccentTheme.preset : "") : ""
                visible: root.circularBackground
            }
            ArtworkLayer {
                id: surfaceAura; part: "surface-aura"
                source: root.circularBackground ? "image://connectionanimation/" + root.sourcePalette + "/surface-aura" +
                    (AccentTheme.customAccent ? "/" + AccentTheme.preset : "") : ""
                opacity: root.outerGlowProgress
                visible: root.circularBackground
            }
            ArtworkLayer {
                id: surfaceEdge; part: "surface-edge"
                source: root.circularBackground ? "image://connectionanimation/" + root.sourcePalette + "/surface-edge" +
                    (AccentTheme.customAccent ? "/" + AccentTheme.preset : "") : ""
                opacity: root.outerGlowProgress
                visible: root.circularBackground
            }
            // Surround the whole disc, not the off-center socket. Convert the
            // original SVG's rim radius to burst units and leave a clear gap.
            ConnectionSuccessBurst {
                objectName: "newConnectionSuccessBurst"
                anchors.fill: parent
                progress: root.burstProgress
                unit: root.paintWidth / 180
                startRadius: 470 * 180 / root.viewBoxWidth + 7
                centerX: root.paintLeft + root.paintWidth *
                    (620 - root.viewBoxX) / root.viewBoxWidth
                centerY: (root.height - root.paintWidth * root.viewBoxHeight / root.viewBoxWidth) / 2
                    + root.paintWidth * (627 - root.viewBoxY) / root.viewBoxWidth
            }
            ArtworkLayer { id: socket; part: "socket"; objectName: "newConnectionSocketLayer" }
            ArtworkLayer {
                id: slots; part: "slots"
                // The plug occludes the slots before their layer is hidden.
                visible: root.insertionProgress < 1
            }
            Item {
                objectName: "newConnectionPinClip"
                // The source mouth at x=740 lives inside centered-content's
                // translate(-100 0). Clip in that same final coordinate space;
                // the unshifted boundary leaves pin tips beyond the housing.
                width: root.paintLeft + root.paintWidth * (740 - 100 - root.viewBoxX) / root.viewBoxWidth
                height: root.height; clip: true
                ArtworkLayer {
                    id: pins; part: "pins"
                    objectName: "newConnectionPinsLayer"
                    // Attach the original pins to the rounded connected shell.
                    // The socket mouth clips them as the rigid plug advances.
                    visible: root.insertionProgress < 1
                    transform: Translate {
                        x: root.travel * root.insertionProgress - root.paintWidth * 28 / root.viewBoxWidth
                    }
                }
            }
            ArtworkLayer {
                id: plug; part: "plug"
                objectName: "newConnectionRigidPlug"
                transform: Translate {
                    objectName: "newConnectionPlugTranslation"
                    x: -root.travel * (1 - root.insertionProgress)
                }
            }
            ArtworkLayer { id: lip; part: "lip" }
            ArtworkLayer { id: outerAura; part: "outer-aura"; opacity: root.outerGlowProgress }
            ArtworkLayer { id: badgeBase; part: "badge-base" }
            ArtworkLayer { id: badgePlus; part: "badge-plus"; opacity: 1 - root.glowProgress }
            ArtworkLayer { id: glowPlus; part: "glow-plus"; opacity: root.glowProgress }
            ArtworkLayer { id: outerEdge; part: "outer-edge"; opacity: root.outerGlowProgress }
        }
        // Static layers share the final artwork's geometry and definitions.
        ArtworkLayer {
            id: finalArtwork; part: "outer"
            objectName: "newConnectionFinalArtwork"
            visible: root.outerGlowProgress >= 1
        }
        Loader {
            objectName: "newConnectionExtraGlow"
            anchors.fill: parent
            active: root.outerGlowBoost > 0
            opacity: Math.max(0, Math.min(1, root.outerGlowBoost)) * root.outerGlowProgress
            // Reuse only the original filtered auras, not the plug, disc or
            // edge strokes. This preserves their gradients, colors and motion
            // on both sides of the final-artwork handoff.
            sourceComponent: Item {
                ArtworkLayer {
                    part: "surface-aura"
                    source: root.circularBackground ? "image://connectionanimation/" + root.sourcePalette +
                        "/surface-aura" + (AccentTheme.customAccent ? "/" + AccentTheme.preset : "") : ""
                    visible: root.circularBackground
                }
                ArtworkLayer { part: "outer-aura" }
            }
        }
        Repeater {
            id: spinFrames
            model: root.circularBackground ? 16 : 0
            onItemAdded: root.frameRevision++
            onItemRemoved: root.frameRevision++
            delegate: ArtworkLayer {
                required property int index
                objectName: "newConnectionOutlineFrame" + index
                part: "spin-" + String(index + 1).padStart(2, "0")
                // Only the original rim-rotating-shine group is rendered.
                // No duplicate disc, plug, badge, or shadow is composited.
                visible: root.outerGlowProgress >= 1 && index === root.outlineFrame &&
                    !ConnectionTheme.reducedMotion
                sourceSize: Qt.size(root.inspectionMode ? 512 :
                    Math.ceil(root.paintWidth * Screen.devicePixelRatio * 2),
                    root.inspectionMode ? 512 : Math.ceil(root.paintWidth * Screen.devicePixelRatio * 2))
            }
        }
    }
    Timer {
        objectName: "newConnectionOutlineTimer"
        interval: root.outlineFrameInterval
        running: root.spinning
        repeat: true
        onTriggered: root.outlineFrame = (root.outlineFrame + 1) % 16
    }
    ConnectionAnimationTimeline {
        id: motion
        targetItem: root
        durationScale: root.durationScale
        onFinished: root.complete = true
    }
    Connections {
        target: ConnectionTheme
        function onReducedMotionChanged() {
            if (ConnectionTheme.reducedMotion && root.running) {
                root.reset()
                if (root.ready) root.begin()
                else if (!root.assetError) root.pendingStart = true
                else root.loadFailed()
            }
        }
    }
}
