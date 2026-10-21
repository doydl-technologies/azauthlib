import QtQuick
import QtQuick.Window

// Transient in-memory outgoing frame. Incoming controls remain live QML.
// Capturing completes before any model mutation; nothing is saved to disk.
Item {
    id: root
    required property Item sourceItem
    property Item overlayParent: sourceItem.parent
    objectName: sourceItem.objectName + "OutgoingFrame"
    property bool revealing: false
    property real progress: 1
    property real direction: 1
    property real movementScale: 1
    property var grabResult: null
    property real capturedOpacity: 1
    property int generation: 0
    property rect capturedRect: Qt.rect(0, 0, 0, 0)
    property rect sourceRect: Qt.rect(0, 0, 0, 0)
    readonly property real captureDensity: Math.max(2, Screen.devicePixelRatio)
    signal captured(bool success)
    parent: overlayParent
    x: capturedRect.x; y: capturedRect.y
    width: capturedRect.width; height: capturedRect.height
    z: 20
    clip: true // A moving control must not paint over its stationary labels.
    enabled: false
    visible: revealing && grabResult !== null
    function capture() {
        const token = ++generation
        grabResult = null
        // Hidden incoming controls have no outgoing frame. Keep the coordinator
        // asynchronous without asking Qt to grab an invisible/zero-sized item.
        if (!sourceItem.visible || sourceItem.width <= 0 || sourceItem.height <= 0) {
            Qt.callLater(() => { if (generation === token) root.captured(true) })
            return
        }
        // A text-only grab excludes ancestor opacity (e.g. the disabled Active
        // connection button). Preserve it when moving the grab into the overlay.
        let alpha = 1
        for (let item = sourceItem.parent; item && item !== overlayParent; item = item.parent)
            alpha *= item.opacity
        capturedOpacity = alpha
        const start = sourceItem.mapToItem(overlayParent, 0, 0)
        const end = sourceItem.mapToItem(overlayParent, sourceItem.width, sourceItem.height)
        sourceRect = Qt.rect(start.x, start.y, end.x - start.x, end.y - start.y)
        let left = start.x; let top = start.y; let right = end.x; let bottom = end.y
        // The frame has a stable overlay parent, so preserve the source's
        // ancestor clipping explicitly (including nested/scrolling form views).
        for (let item = sourceItem.parent; item && item !== overlayParent; item = item.parent) {
            if (!item.clip) continue
            const a = item.mapToItem(overlayParent, 0, 0)
            const b = item.mapToItem(overlayParent, item.width, item.height)
            left = Math.max(left, a.x); top = Math.max(top, a.y)
            right = Math.min(right, b.x); bottom = Math.min(bottom, b.y)
        }
        capturedRect = Qt.rect(left, top, Math.max(0, right - left), Math.max(0, bottom - top))
        if (capturedRect.width <= 0 || capturedRect.height <= 0) {
            Qt.callLater(() => { if (generation === token) root.captured(true) })
            return
        }
        const accepted = sourceItem.grabToImage(result => {
            if (generation !== token) return
            grabResult = result
            root.captured(true)
        }, Qt.size(Math.max(1, Math.ceil(sourceItem.width * captureDensity)),
                   Math.max(1, Math.ceil(sourceItem.height * captureDensity))))
        if (!accepted) Qt.callLater(() => { if (generation === token) root.captured(false) })
    }
    function release() {
        generation += 1
        grabResult = null
    }
    Image {
        x: root.sourceRect.x - root.capturedRect.x
        y: root.sourceRect.y - root.capturedRect.y
        width: root.sourceRect.width; height: root.sourceRect.height
        source: root.grabResult ? root.grabResult.url : ""
        opacity: (1 - root.progress) * root.capturedOpacity
        smooth: true
        transform: Translate { y: -14 * root.direction * root.progress * root.movementScale }
    }
}
