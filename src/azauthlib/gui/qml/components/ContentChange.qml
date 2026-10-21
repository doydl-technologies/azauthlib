import QtQuick

// One semantic piece of a coordinated change, never a whole page/card.
Item {
    id: root
    required property var coordinator
    required property Item sourceItem
    required property Item overlayParent
    property string value: ""
    property bool compareValue: true
    property bool instant: false
    property bool suppressed: false
    property bool previousPresence: false
    property string previousValue: ""
    property bool changed: false
    readonly property real incomingOpacity: coordinator.revealing && changed ? coordinator.progress : 1
    readonly property real incomingOffset: coordinator.revealing && changed ?
        14 * coordinator.direction * (1 - coordinator.progress) : 0
    function capture() {
        changed = false
        previousPresence = sourceItem.visible
        previousValue = value
        frame.capture()
    }
    function resolve() {
        const present = sourceItem.visible
        changed = !instant && !suppressed && (previousPresence !== present ||
            (compareValue && previousPresence && present && previousValue !== value))
        if (!changed) frame.release()
    }
    function release() { changed = false; previousValue = ""; frame.release() }
    ContentCrossfade {
        id: frame
        sourceItem: root.sourceItem
        overlayParent: root.overlayParent
        revealing: root.coordinator.revealing && root.changed
        progress: root.coordinator.progress
        direction: root.coordinator.direction
        onCaptured: success => root.coordinator.captured(success)
    }
}
