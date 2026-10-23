pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "components" as Components
import "theme" as Theme

// Deliberately no appController/connectionManager: every value here is sample
// presentation data. Shared visual components and the production overlay keep
// this preview faithful without accessing profiles, keyring or authentication.
Window {
    id: window
    objectName: "connectionAnimationSimulation"
    title: "azauthlib - Simulated Connections screen"
    width: 1293; height: 836
    minimumWidth: 960; minimumHeight: 650
    color: "#071626"
    property bool autoPlay: false
    property real playbackRate: 1
    property bool loopPlayback: false
    property bool playing: false
    readonly property bool animationVisible: confirmation.visible
    readonly property real sceneScale: Math.min(viewport.width / 1293, viewport.height / 776)

    function replay() {
        stop()
        confirmation.play("created")
        playing = true
    }
    function stop() {
        playing = false
        confirmation.dismiss()
    }
    onClosing: stop()
    onVisibleChanged: if (!visible) stop()
    onLoopPlaybackChanged: if (!loopPlayback && !confirmation.visible) playing = false
    Component.onCompleted: {
        if (autoPlay) Qt.callLater(replay)
    }

    RowLayout {
        id: toolbar
        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
        anchors.margins: 12
        height: 36; spacing: 12
        Text {
            Layout.fillWidth: true
            text: "SIMULATION ONLY · Nothing is saved or tested"
            color: Theme.ConnectionTheme.muted
            font.family: Theme.ConnectionTheme.body; font.pixelSize: 12
            elide: Text.ElideRight
        }
        Components.ConnectionCombo {
            objectName: "simulationSpeedSelector"
            Layout.preferredWidth: 100
            Accessible.name: "Simulation playback speed"
            model: ["0.10×", "0.25×", "0.50×", "0.75×", "1.00×", "2.00×"]
            currentIndex: Math.max(0, [0.1, 0.25, 0.5, 0.75, 1, 2].indexOf(window.playbackRate))
            onActivated: index => window.playbackRate = [0.1, 0.25, 0.5, 0.75, 1, 2][index]
        }
        Components.ConnectionButton {
            objectName: "simulationPlayButton"
            text: "Play"; variant: "primary"; enabled: !window.playing
            onClicked: window.replay()
        }
        Components.ConnectionButton {
            objectName: "simulationStopButton"
            text: "Stop"; enabled: window.playing
            onClicked: window.stop()
        }
        Components.ConnectionButton {
            objectName: "simulationReplayButton"
            text: "Restart"; symbol: "save"
            onClicked: window.replay()
        }
        Components.ConnectionButton {
            objectName: "simulationLoopButton"
            text: window.loopPlayback ? "Loop: On" : "Loop: Off"
            selected: window.loopPlayback
            onClicked: window.loopPlayback = !window.loopPlayback
        }
        Components.ConnectionButton { text: "Close simulation"; onClicked: window.close() }
    }
    Item {
        id: viewport
        anchors.left: parent.left; anchors.right: parent.right
        anchors.top: toolbar.bottom; anchors.topMargin: 12
        anchors.bottom: parent.bottom
        clip: true
        Item {
            id: scene
            objectName: "simulationGuiCanvas"
            width: 1293; height: 776
            x: (viewport.width - width * window.sceneScale) / 2
            y: (viewport.height - height * window.sceneScale) / 2
            scale: window.sceneScale; transformOrigin: Item.TopLeft
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop { position: 0; color: "#112d4d" }
                    GradientStop { position: 1; color: "#071626" }
                }
            }
            Image {
                x: 24; y: 12; width: 205; height: 43
                source: Qt.resolvedUrl("../../assets/logo/svg/azauthlib-wordmark-qt.svg")
                fillMode: Image.PreserveAspectFit; horizontalAlignment: Image.AlignLeft
            }
            Components.ConnectionButton {
                x: 1151; y: 15; width: 112
                text: "Main Menu"; symbol: "menu"
                // Static app chrome, not a navigation action in the simulation.
                enabled: false; visualEnabled: true
            }
            Components.ConnectionPageSurface {
                x: 30; y: 70; width: 1233; height: 658
                Item {
                    width: parent.width / 1.08; height: parent.height / 1.08
                    scale: 1.08; transformOrigin: Item.TopLeft
                    Text {
                        x: 29; y: 23; text: "Connections"
                        color: Theme.ConnectionTheme.text
                        font.family: Theme.ConnectionTheme.heading; font.pixelSize: 23; font.bold: true
                    }
                    Text {
                        x: 29; y: 58; text: "Your Microsoft Graph connection profiles, organized."
                        color: Theme.ConnectionTheme.muted
                        font.family: Theme.ConnectionTheme.body; font.pixelSize: 12
                    }
                    Components.ConnectionIcon {
                        x: parent.width - 65; y: 31; width: 26; height: 26; name: "plug"
                    }
                    Components.ConnectionSurface {
                        x: 26; y: 93; width: 288; height: 204
                        radius: 19; sunken: true; depth: 7; blur: 16; crispOutline: true
                        Components.ConnectionTestHalo {
                            anchors.horizontalCenter: parent.horizontalCenter; y: 20
                            width: 82; height: 82; idleFaceSize: 82; idleIconSize: 31
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter; y: 116
                            text: "Sample connection"; color: Theme.ConnectionTheme.text
                            font.family: Theme.ConnectionTheme.body; font.pixelSize: 15; font.bold: true
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter; y: 143
                            text: "Saved authentication profile"; color: Theme.ConnectionTheme.muted
                            font.family: Theme.ConnectionTheme.body; font.pixelSize: 11
                        }
                        Components.ConnectionButton {
                            anchors.horizontalCenter: parent.horizontalCenter; y: 165
                            text: "Interactive"; symbol: "lock"
                            height: 26; enabled: false; visualEnabled: true
                            font.pixelSize: 10
                        }
                    }
                    Text {
                        x: 26; y: 314; text: "MY CONNECTIONS  01"
                        color: Theme.ConnectionTheme.muted
                        font.family: Theme.ConnectionTheme.mono; font.pixelSize: 10; font.letterSpacing: 1
                    }
                    GridLayout {
                        x: 54; y: 337; width: 232
                        columns: 2; rowSpacing: 8; columnSpacing: 8
                        Repeater {
                            model: ["Add connection", "Edit", "Remove", "Set Active"]
                            Components.ConnectionButton {
                                required property int index
                                required property string modelData
                                Layout.fillWidth: true
                                text: modelData; tileLayout: true
                                symbol: ["add", "edit", "trash", "checkActive"][index]
                                enabled: false; visualEnabled: true
                            }
                        }
                    }
                    Components.ConnectionButton {
                        x: 26; y: 445; width: 288
                        text: "Sample connection"; symbol: "checkProfile"; alignLeft: true
                        selected: true; enabled: false; visualEnabled: true
                    }
                    Components.ConnectionSurface {
                        x: 336; y: 93; width: parent.width - x - 26; height: 437
                        radius: 19; sunken: true; depth: 7; blur: 16; crispOutline: true
                        Text {
                            x: 20; y: 20; text: "AUTHENTICATION PROFILE"
                            color: Theme.ConnectionTheme.muted
                            font.family: Theme.ConnectionTheme.mono; font.pixelSize: 10; font.letterSpacing: 1
                        }
                        Text {
                            x: 20; y: 37; text: "Connection details"
                            color: Theme.ConnectionTheme.text
                            font.family: Theme.ConnectionTheme.body; font.pixelSize: 16; font.bold: true
                        }
                        Components.ConnectionButton {
                            anchors.right: parent.right; anchors.rightMargin: 20; y: 20
                            text: "Test connection"; symbol: "bolt"
                            enabled: false; visualEnabled: true
                        }
                        GridLayout {
                            x: 20; y: 77; width: parent.width - 40
                            columns: 2; rowSpacing: 14; columnSpacing: 14
                            Repeater {
                                model: [
                                    {label: "Connection name", value: "Sample connection"},
                                    {label: "Authentication method", value: "Interactive"},
                                    {label: "Tenant ID / Directory ID", value: "11111111-2222-3333-4444-555555555555"},
                                    {label: "Client ID / Application ID", value: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}
                                ]
                                Components.ConnectionField {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    label: modelData.label; text: modelData.value; readOnly: true
                                }
                            }
                        }
                        Text {
                            x: 20; y: 230
                            text: "Saved identifiers are shown for reference. These are sample values."
                            color: Theme.ConnectionTheme.muted
                            font.family: Theme.ConnectionTheme.body; font.pixelSize: 11
                        }
                    }
                    Components.ConnectionSurface {
                        x: 26; y: parent.height - 63; width: parent.width - 52; height: 41
                        radius: 12; sunken: true
                        Components.ConnectionIcon { x: 14; anchors.verticalCenter: parent.verticalCenter; name: "checkSuccess" }
                        Text {
                            x: 42; anchors.verticalCenter: parent.verticalCenter
                            text: "“Sample connection” saved securely. You can test it, or set it as the active connection."
                            color: Theme.ConnectionTheme.text
                            font.family: Theme.ConnectionTheme.body; font.pixelSize: 11; font.bold: true
                        }
                    }
                }
            }
            Components.ConnectionIcon {
                x: 8; y: 741; width: 28; height: 28
                sourceOverride: Qt.resolvedUrl("../../assets/icons/svg/actions/settings-gear.svg")
            }
            Text {
                anchors.right: parent.right; anchors.rightMargin: 30; y: 752
                text: "Terms of Use     |     Privacy Policy     |     About azauthlib"
                color: "#91aac5"; font.family: Theme.ConnectionTheme.body; font.pixelSize: 11
            }
            Components.ActionSuccessOverlay {
                id: confirmation
                objectName: "simulationActionSuccessOverlay"
                anchors.fill: parent
                playbackRate: window.playbackRate
                // Match application geometry; hold and glow overrides are preview-only.
                connectionIconSize: Theme.ConnectionTheme.newConnectionSuccessIconSize
                connectionIconOffset: Theme.ConnectionTheme.newConnectionSuccessIconOffset
                connectionHoldDuration: 2000
                connectionGlowBoost: 0.25
                onVisibleChanged: {
                    if (!visible && window.playing && !window.loopPlayback)
                        window.playing = false
                }
            }
        }
    }
    Timer {
        objectName: "simulationLoopTimer"
        interval: 400
        running: window.visible && window.playing && window.loopPlayback && !confirmation.visible
        onTriggered: window.replay()
    }
    Shortcut { sequence: "Space"; onActivated: if (window.playing) window.stop(); else window.replay() }
    Shortcut { sequence: "R"; onActivated: window.replay() }
    Shortcut { sequence: "L"; onActivated: window.loopPlayback = !window.loopPlayback }
    Shortcut { sequence: "Escape"; onActivated: window.close() }
}
