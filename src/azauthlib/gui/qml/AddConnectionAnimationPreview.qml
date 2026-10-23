pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "components" as Components
import "theme" as Theme

Window {
    id: window
    objectName: "addConnectionAnimationPreview"
    title: "azauthlib - Add connection animation preview"
    width: 840; height: 760
    minimumWidth: 700; minimumHeight: 650
    color: "#0b2035"
    property bool loopPlayback: false
    property bool initialGuiSimulation: false
    property var guiSimulation: null
    readonly property real playbackRate: [0.1, 0.25, 0.5, 0.75, 1, 2][speedSelector.currentIndex] || 1
    readonly property real zoomFactor: [0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4][zoomSelector.currentIndex] || 1

    function replay() {
        initialPlay.stop()
        inspector.replay()
    }
    function simulateInGui() {
        initialPlay.stop()
        inspector.pause()
        if (!guiSimulation) guiSimulation = simulatedGui.createObject(window)
        if (guiSimulation) {
            guiSimulation.show()
            guiSimulation.raise()
            guiSimulation.requestActivate()
            guiSimulation.replay()
        }
    }
    function toggleLoop() {
        loopPlayback = !loopPlayback
    }
    function togglePlayback() { initialPlay.stop(); inspector.togglePlayback() }
    function scrubToMs(value) { initialPlay.stop(); inspector.seek(value) }
    function stepFrame(direction) { initialPlay.stop(); inspector.stepFrame(direction) }
    function changeZoom(direction) {
        zoomSelector.currentIndex = Math.max(0, Math.min(zoomSelector.count - 1,
            zoomSelector.currentIndex + direction))
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20
        spacing: 12
        Text {
            text: "Add connection success"
            color: Theme.ConnectionTheme.text
            font.family: Theme.ConnectionTheme.heading
            font.pixelSize: 24; font.bold: true
        }
        Text {
            Layout.fillWidth: true
            text: "Inspect the real animation timeline. No connections or credentials are used."
            wrapMode: Text.WordWrap
            color: Theme.ConnectionTheme.muted
            font.family: Theme.ConnectionTheme.body; font.pixelSize: 13
        }
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.minimumHeight: 180
            radius: 24; color: "#102d49"; border.color: AccentTheme.color("#345b85")
            Components.ConnectionAnimationInspector {
                id: inspector
                objectName: "previewAnimationInspector"
                anchors.fill: parent; anchors.margins: 12
                playbackRate: window.playbackRate
                zoomFactor: window.zoomFactor
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Slider {
                id: scrubber
                objectName: "previewTimelineScrubber"
                Layout.fillWidth: true
                implicitHeight: 28
                from: 0; to: inspector.durationMs
                stepSize: inspector.frameDuration
                Accessible.name: "Animation timeline"
                onPressedChanged: if (pressed) window.scrubToMs(value)
                onMoved: window.scrubToMs(value)
                HoverHandler { cursorShape: Qt.PointingHandCursor }
                background: Rectangle {
                    x: scrubber.leftPadding; y: (scrubber.height - height) / 2
                    width: scrubber.availableWidth; height: 4; radius: 2; color: AccentTheme.color("#345b85")
                    Rectangle {
                        width: parent.width * scrubber.visualPosition; height: parent.height
                        radius: 2; color: AccentTheme.color("#56d7ef")
                    }
                }
                handle: Rectangle {
                    x: scrubber.leftPadding + scrubber.visualPosition * (scrubber.availableWidth - width)
                    y: (scrubber.height - height) / 2
                    width: 14; height: 14; radius: 7
                    color: scrubber.pressed ? "#ffffff" : AccentTheme.color("#56d7ef")
                    border.color: AccentTheme.color("#b6f4ff")
                }
            }
            Binding {
                target: scrubber; property: "value"
                value: inspector.positionMs
                when: !scrubber.pressed
                restoreMode: Binding.RestoreNone
            }
            Text {
                Layout.preferredWidth: 140
                text: (inspector.positionMs / 1000).toFixed(3) + " / "
                    + (inspector.durationMs / 1000).toFixed(3) + " s"
                color: Theme.ConnectionTheme.text
                font.family: Theme.ConnectionTheme.mono; font.pixelSize: 11
            }
        }
        Text {
            objectName: "previewFrameStatus"
            Layout.fillWidth: true
            text: "Frame " + inspector.currentFrame + " / " + inspector.totalFrames
                + " (60 fps)  -  " + inspector.phase
            horizontalAlignment: Text.AlignHCenter
            color: Theme.ConnectionTheme.muted
            font.family: Theme.ConnectionTheme.body; font.pixelSize: 12
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 12
            Components.ConnectionButton {
                objectName: "previewPreviousFrameButton"
                text: "Previous frame"; enabled: inspector.positionMs > 0
                onClicked: window.stepFrame(-1)
            }
            Components.ConnectionButton {
                objectName: "previewPauseButton"
                text: inspector.playing || inspector.pendingPlay ? "Pause" :
                    inspector.atEnd || inspector.positionMs === 0 ? "Play" : "Resume"
                variant: "primary"
                onClicked: window.togglePlayback()
            }
            Components.ConnectionButton {
                objectName: "previewNextFrameButton"
                text: "Next frame"; enabled: !inspector.atEnd
                onClicked: window.stepFrame(1)
            }
            Components.ConnectionButton {
                objectName: "previewReplayButton"
                text: "Replay"
                onClicked: window.replay()
            }
            Components.ConnectionButton {
                objectName: "previewGuiSimulationButton"
                text: "Simulate in GUI"
                onClicked: window.simulateInGui()
            }
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 12
            Components.ConnectionButton {
                objectName: "previewLoopButton"
                text: window.loopPlayback ? "Loop: On" : "Loop: Off"
                selected: window.loopPlayback
                onClicked: window.toggleLoop()
            }
            Text {
                text: "Speed"
                color: Theme.ConnectionTheme.text
                font.family: Theme.ConnectionTheme.body; font.pixelSize: 13
            }
            Components.ConnectionCombo {
                id: speedSelector
                objectName: "previewSpeedSelector"
                Layout.preferredWidth: 200
                Accessible.name: "Animation preview speed"
                model: ["0.10x - 10x slower", "0.25x - 4x slower", "0.50x - 2x slower",
                    "0.75x - Slightly slower", "1.00x - Normal", "2.00x - 2x faster"]
                currentIndex: 4
            }
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 12
            Text {
                text: "Zoom"
                color: Theme.ConnectionTheme.text
                font.family: Theme.ConnectionTheme.body; font.pixelSize: 13
            }
            Components.ConnectionButton {
                objectName: "previewZoomOutButton"
                text: "-"; enabled: zoomSelector.currentIndex > 0
                onClicked: window.changeZoom(-1)
            }
            Components.ConnectionCombo {
                id: zoomSelector
                objectName: "previewZoomSelector"
                Layout.preferredWidth: 110
                Accessible.name: "Animation preview zoom"
                model: ["25%", "50%", "75%", "100%", "150%", "200%", "300%", "400%"]
                currentIndex: 3
            }
            Components.ConnectionButton {
                objectName: "previewZoomInButton"
                text: "+"; enabled: zoomSelector.currentIndex < zoomSelector.count - 1
                onClicked: window.changeZoom(1)
            }
            Components.ConnectionButton {
                objectName: "previewResetViewButton"
                text: "Reset view"
                onClicked: { zoomSelector.currentIndex = 3; inspector.centerView() }
            }
        }
        Text {
            Layout.fillWidth: true
            text: "Space: pause/resume  |  Left/Right: one frame  |  R: replay  |  Esc: close\n"
                + "Drag to pan when zoomed. Speed and zoom changes keep your current frame."
            horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
            color: Theme.ConnectionTheme.muted
            font.family: Theme.ConnectionTheme.body; font.pixelSize: 11
        }
    }
    Shortcut { sequence: "Space"; onActivated: window.togglePlayback() }
    Shortcut { sequence: "Left"; onActivated: window.stepFrame(-1) }
    Shortcut { sequence: "Right"; onActivated: window.stepFrame(1) }
    Shortcut { sequence: "R"; onActivated: window.replay() }
    Shortcut { sequence: "Escape"; onActivated: window.close() }
    Component {
        id: simulatedGui
        ConnectionAnimationSimulation {
            playbackRate: window.playbackRate
            loopPlayback: window.loopPlayback
        }
    }
    Timer {
        id: initialPlay
        interval: 250
        onTriggered: window.replay()
    }
    Timer {
        id: loopTimer
        objectName: "previewLoopTimer"
        interval: 16 * Theme.ConnectionTheme.newConnectionOutlineFrameInterval + 200
        running: window.loopPlayback && inspector.atEnd && !inspector.paused
        // Pause/scrubbing holds even the final frame, including with Loop on.
        onTriggered: if (window.loopPlayback && inspector.atEnd && !inspector.paused)
            window.replay()
    }
    Component.onCompleted: {
        if (initialGuiSimulation) Qt.callLater(simulateInGui)
        else initialPlay.start()
    }
    onClosing: {
        initialPlay.stop()
        loopTimer.stop()
        inspector.pause()
        if (guiSimulation) guiSimulation.close()
    }
}
