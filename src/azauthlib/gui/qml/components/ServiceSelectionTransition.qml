pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "../theme"

// Only a native copy of the selected emblem/name moves. The full card and
// description are never captured, reparented, scaled or carried across pages.
FocusScope {
    id: root
    property bool active: false
    property real cornerRadius: 25
    property var subject: ({x: 0, y: 0, width: 1, height: 1, unit: 1, circleSize: 108,
        logoSize: 66, labelGap: 11, labelHeight: 27.6, fontSize: 20, name: "", logo: ""})
    property string mode: "group"
    property bool ready: false
    property real actualProgress: 0
    property string loadingMessage: "Initializing runtime context…"
    property string failureText: ""
    property bool minimumElapsed: false
    property bool settled: false
    property bool progressRevealed: false
    property real moveAmount: 0
    property real subjectZoom: 1
    property real glowOpacity: 0
    property real glowZoom: 0.5
    property real messageOpacity: 0
    property real messageOffset: 15
    readonly property real targetZoom: mode === "group" ? 1.66 : mode === "badge" ? 2.1 : 3.1
    readonly property real destinationX: width * 0.5
    readonly property real destinationY: height * 0.43
    readonly property real dx: destinationX - (subject.x + subject.width / 2)
    readonly property real dy: destinationY - (subject.y + subject.height / 2)
    property real progressValue: progressRevealed ? Math.max(0, Math.min(1, actualProgress / 100)) : 0
    Behavior on progressValue { NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 930; easing.type: Easing.Linear } }
    signal finished()
    signal cancelled()
    signal retryRequested()
    visible: active
    enabled: active
    clip: true

    function begin(data, style) {
        if (active || !data) return false
        stopMotion()
        subject = data
        mode = ["group", "badge", "mark"].includes(style) ? style : "group"
        moveAmount = 0; subjectZoom = 1; glowOpacity = 0; glowZoom = 0.5
        messageOpacity = 0; messageOffset = 15; progressRevealed = false
        minimumElapsed = false; settled = false
        for (let i = 0; i < ripples.count; ++i) {
            ripples.itemAt(i).opacity = 0
            ripples.itemAt(i).scale = 0.5
        }
        active = true
        forceActiveFocus()
        if (ConnectionTheme.reducedMotion) finishMotion()
        else {
            pop.start(); glow.start(); message.start()
            progressDelay.start(); minimumTimer.start()
        }
        return true
    }
    function stopMotion() {
        pop.stop(); glow.stop(); message.stop(); progressDelay.stop(); minimumTimer.stop()
    }
    function finishMotion() {
        stopMotion()
        moveAmount = 1; subjectZoom = targetZoom
        glowOpacity = 0.9; glowZoom = 1.35
        messageOpacity = 1; messageOffset = 0
        progressRevealed = true; minimumElapsed = true; settled = true
        tryFinish()
    }
    function reset() { stopMotion(); active = false }
    function tryFinish() {
        if (active && ready && !failureText.length && settled && minimumElapsed && progressValue >= 0.999) {
            reset()
            finished()
        }
    }
    function cancel() { if (active) { reset(); cancelled() } }
    onReadyChanged: tryFinish()
    onProgressValueChanged: tryFinish()
    onFailureTextChanged: if (active && failureText.length) {
        message.stop()
        messageOpacity = 1; messageOffset = 0
    }
    Keys.onEscapePressed: event => { event.accepted = true; cancel() }
    Connections {
        target: ConnectionTheme
        function onReducedMotionChanged() { if (root.active && ConnectionTheme.reducedMotion) root.finishMotion() }
    }

    SpotlightGradient {
        objectName: "serviceSelectionCurtain"
        anchors.fill: parent
        cornerRadius: root.cornerRadius; gradientCenter: Qt.vector2d(0.5, 0.45)
        colorCenter: ServiceSelectionTheme.curtainCenter
        colorMiddle: ServiceSelectionTheme.curtainMiddle
        colorEdge: ServiceSelectionTheme.curtainEdge
        middleStop: 0.46; edgeStop: 1
    }
    MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons }
    SpotlightGradient {
        objectName: "serviceSelectionGlow"
        x: root.destinationX - width / 2; y: root.destinationY - height / 2
        width: 390; height: 390
        colorCenter: AccentTheme.withAlpha(ServiceSelectionTheme.glowCore, 0.4)
        colorMiddle: AccentTheme.withAlpha(ServiceSelectionTheme.glowOuter, 0.157)
        colorEdge: "transparent"
        opacity: root.glowOpacity; scale: root.glowZoom
        enabled: false
    }
    Repeater {
        id: ripples
        model: 2
        Rectangle {
            id: ripple
            required property int index
            objectName: "serviceSelectionRipple" + index
            x: root.destinationX - width / 2; y: root.destinationY - height / 2
            width: 140; height: 140; radius: width / 2
            color: "transparent"; border.width: 2; border.color: ServiceSelectionTheme.ripple
            opacity: 0; scale: 0.5
            visible: root.active && !ConnectionTheme.reducedMotion
            enabled: false
            SequentialAnimation {
                running: root.active && !ConnectionTheme.reducedMotion
                PauseAnimation { duration: 520 + ripple.index * 170 }
                ParallelAnimation {
                    NumberAnimation { target: ripple; property: "scale"; from: 0.5; to: 3.2; duration: 1100; easing.type: Easing.OutCubic }
                    SequentialAnimation {
                        NumberAnimation { target: ripple; property: "opacity"; from: 0; to: 0.65; duration: 330 }
                        NumberAnimation { target: ripple; property: "opacity"; to: 0; duration: 770 }
                    }
                }
            }
        }
    }
    Item {
        objectName: "serviceSelectionSubject"
        x: root.subject.x + root.dx * root.moveAmount
        y: root.subject.y + root.dy * root.moveAmount
        width: root.subject.width; height: root.subject.height
        scale: root.subjectZoom
        enabled: false
        Item {
            x: (parent.width - root.subject.circleSize) / 2
            width: root.subject.circleSize; height: width
            visible: root.mode !== "mark"
            ProviderEmblem {
                objectName: "serviceSelectionEmblem"
                providerObjectName: "serviceSelection"
                logoSource: root.subject.logo
                logoSize: root.subject.logoSize
                asynchronousLogo: false
                scale: root.subject.unit; transformOrigin: Item.TopLeft
                selected: true
            }
        }
        Text {
            objectName: "serviceSelectionMovingName"
            visible: root.mode === "group"
            y: root.subject.circleSize + root.subject.labelGap
            width: parent.width; height: root.subject.labelHeight
            text: root.subject.name; color: "#f3f7ff"
            font.family: ConnectionTheme.heading; font.pixelSize: root.subject.fontSize
            font.weight: 780; font.letterSpacing: -0.55 * root.subject.unit
            horizontalAlignment: Text.AlignHCenter
        }
        Item {
            width: root.subject.logoSize; height: width
            scale: root.subject.unit; transformOrigin: Item.TopLeft
            visible: root.mode === "mark"
            Image {
                id: mark
                objectName: "serviceSelectionBareLogo"
                anchors.fill: parent
                source: root.subject.logo.length ? "image://providerlogos/" + root.subject.logo : ""
                sourceSize: Qt.size(384, 384)
                fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
                asynchronous: false
                // Keep the enlarged, bare logo sharp and its shadow free of
                // the small-card shader's texture-boundary artifacts.
                layer.enabled: root.active && root.mode === "mark"
                layer.textureSize: Qt.size(384, 384)
                layer.smooth: true
                layer.effect: MultiEffect {
                    shadowEnabled: true; shadowColor: "#03101e"; shadowOpacity: 0.6
                    shadowHorizontalOffset: 1; shadowVerticalOffset: 2
                    shadowBlur: 0.125; blurMax: 16
                }
            }
        }
    }
    Column {
        objectName: "serviceSelectionLoadingMessage"
        anchors.left: parent.left; anchors.right: parent.right
        y: parent.height - 175 + root.messageOffset
        spacing: 9
        opacity: root.messageOpacity
        Text {
            width: parent.width
            text: root.mode === "group" && !root.failureText.length ? "" : root.subject.name
            visible: text.length > 0
            color: ConnectionTheme.text; font.family: ConnectionTheme.heading
            font.pixelSize: 22; font.weight: Font.ExtraBold
            horizontalAlignment: Text.AlignHCenter
        }
        Text {
            objectName: "serviceSelectionStatus"
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(540, parent.width - 60)
            text: root.failureText.length ? root.failureText : root.loadingMessage
            color: root.failureText.length ? "#ff94a2" : ServiceSelectionTheme.loadingText
            font.family: ConnectionTheme.body; font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
            Accessible.role: Accessible.StaticText; Accessible.name: text
        }
        Rectangle {
            objectName: "serviceSelectionProgressTrack"
            anchors.horizontalCenter: parent.horizontalCenter
            width: 180; height: 3; radius: 1.5
            visible: !root.failureText.length
            color: ServiceSelectionTheme.progressTrack; clip: true
            Rectangle {
                objectName: "serviceSelectionProgressFill"
                width: parent.width * root.progressValue; height: parent.height
                radius: parent.radius; color: ServiceSelectionTheme.progressFill
            }
        }
    }
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom; anchors.bottomMargin: 24
        spacing: 12
        ConnectionButton {
            objectName: "serviceSelectionRetry"
            text: "Retry"; variant: "primary"
            visible: root.failureText.length > 0
            onClicked: { root.progressRevealed = true; root.retryRequested() }
        }
        ConnectionButton {
            objectName: "serviceSelectionCancel"
            text: root.failureText.length ? "Return to Main Menu" : "Cancel"
            variant: "cancel"
            onClicked: root.cancel()
        }
    }
    SequentialAnimation {
        id: pop
        ParallelAnimation {
            NumberAnimation { target: root; property: "moveAmount"; from: 0; to: 0.65; duration: ServiceSelectionTheme.popDuration * 0.46; easing.type: Easing.OutCubic }
            NumberAnimation { target: root; property: "subjectZoom"; from: 1; to: root.targetZoom * 1.15; duration: ServiceSelectionTheme.popDuration * 0.46; easing.type: Easing.OutCubic }
        }
        ParallelAnimation {
            NumberAnimation { target: root; property: "moveAmount"; to: 1; duration: ServiceSelectionTheme.popDuration * 0.26; easing.type: Easing.OutCubic }
            NumberAnimation { target: root; property: "subjectZoom"; to: root.targetZoom * 0.91; duration: ServiceSelectionTheme.popDuration * 0.26; easing.type: Easing.OutCubic }
        }
        NumberAnimation { target: root; property: "subjectZoom"; to: root.targetZoom; duration: ServiceSelectionTheme.popDuration * 0.28; easing.type: Easing.OutCubic }
        onFinished: { root.settled = true; root.tryFinish() }
    }
    SequentialAnimation {
        id: glow
        PauseAnimation { duration: 220 }
        ParallelAnimation {
            NumberAnimation { target: root; property: "glowOpacity"; from: 0; to: 0.9; duration: 1000; easing.type: Easing.OutCubic }
            NumberAnimation { target: root; property: "glowZoom"; from: 0.5; to: 1.35; duration: 1000; easing.type: Easing.OutCubic }
        }
    }
    SequentialAnimation {
        id: message
        PauseAnimation { duration: 850 }
        ParallelAnimation {
            NumberAnimation { target: root; property: "messageOpacity"; from: 0; to: 1; duration: 490; easing.type: Easing.OutCubic }
            NumberAnimation { target: root; property: "messageOffset"; from: 15; to: 0; duration: 490; easing.type: Easing.OutCubic }
        }
    }
    Timer { id: progressDelay; interval: 1110; onTriggered: root.progressRevealed = true }
    Timer { id: minimumTimer; interval: ServiceSelectionTheme.minimumDuration; onTriggered: { root.minimumElapsed = true; root.tryFinish() } }
}
