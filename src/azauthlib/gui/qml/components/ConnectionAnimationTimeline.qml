pragma ComponentBehavior: Bound
import QtQuick

// One definition for production playback and the preview's seek controller.
SequentialAnimation {
    id: root
    required property Item targetItem
    property real durationScale: 1
    readonly property int entryDuration: 120
    readonly property int initialHold: 80
    readonly property int insertionDuration: 620
    readonly property int burstDuration: 500
    readonly property int glowDelay: 60
    readonly property int innerGlowDuration: 260
    readonly property int outerGlowDuration: 300
    readonly property int insertionStart: entryDuration + initialHold
    readonly property int contactTime: insertionStart + insertionDuration
    readonly property int innerGlowStart: contactTime + glowDelay
    readonly property int outerGlowStart: innerGlowStart + innerGlowDuration
    readonly property int baseDuration: contactTime + Math.max(burstDuration,
        glowDelay + innerGlowDuration + outerGlowDuration)

    NumberAnimation {
        target: root.targetItem; property: "badgeOpacity"; from: 0; to: 1
        duration: Math.round(root.entryDuration * root.durationScale)
    }
    PauseAnimation { duration: Math.round(root.initialHold * root.durationScale) }
    NumberAnimation {
        objectName: "newConnectionInsertionAnimation"
        target: root.targetItem; property: "insertionProgress"; from: 0; to: 1
        duration: Math.round(root.insertionDuration * root.durationScale)
        easing.type: Easing.InOutCubic
    }
    ParallelAnimation {
        NumberAnimation {
            target: root.targetItem; property: "burstProgress"; from: 0; to: 1
            duration: Math.round(root.burstDuration * root.durationScale)
        }
        SequentialAnimation {
            PauseAnimation { duration: Math.round(root.glowDelay * root.durationScale) }
            NumberAnimation {
                target: root.targetItem; property: "glowProgress"; from: 0; to: 1
                duration: Math.round(root.innerGlowDuration * root.durationScale)
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: root.targetItem; property: "outerGlowProgress"; from: 0; to: 1
                duration: Math.round(root.outerGlowDuration * root.durationScale)
                easing.type: Easing.OutCubic
            }
        }
    }
}
