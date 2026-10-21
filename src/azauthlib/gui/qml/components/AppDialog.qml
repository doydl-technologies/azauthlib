pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import "../theme"

Popup {
    id: root

    property string dialogTitle: ""
    property string message: ""
    property string variant: "information"
    property bool closeAfter: false
    readonly property color statusAccent: variant === "success" ? "#57e5ae" :
                                         variant === "information" ? "#65caff" : "#ff8a99"
    signal acknowledged

    parent: Overlay.overlay
    anchors.centerIn: parent
    width: 470
    height: 228
    modal: true
    focus: true
    padding: 0
    closePolicy: Popup.NoAutoClose

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic }
        NumberAnimation { property: "scale"; from: 0.98; to: 1; duration: 260; easing.type: Easing.OutCubic }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: 150; easing.type: Easing.InOutCubic }
    }

    function showDialog(title, body, kind, shouldClose) {
        const wasVisible = visible
        dialogTitle = title
        message = body
        variant = kind
        closeAfter = shouldClose
        open()
        // Also restart if a new result replaces an already visible dialog.
        if (wasVisible)
            startStatusAnimation()
    }

    function startStatusAnimation() {
        if (variant === "success")
            animatedSuccessIcon.play()
        else
            animatedSuccessIcon.reset()
    }

    function acceptDialog() {
        close()
        acknowledged()
    }

    onOpened: okButton.forceActiveFocus()
    onAboutToShow: startStatusAnimation()
    onAboutToHide: animatedSuccessIcon.stop()
    onClosed: animatedSuccessIcon.reset()
    onVariantChanged: {
        if (variant !== "success")
            animatedSuccessIcon.reset()
    }

    Shortcut {
        sequence: "Return"
        enabled: root.visible
        onActivated: root.acceptDialog()
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.visible
        onActivated: root.acceptDialog()
    }

    Overlay.modal: Rectangle {
        color: Theme.darkMode ? "#99050b13" : "#668393a3"
    }

    background: Rectangle {
        radius: 16
        gradient: Gradient {
            GradientStop { position: 0; color: Theme.darkMode ? "#183b5c" : "#ffffff" }
            GradientStop { position: 0.46; color: Theme.darkMode ? "#112d49" : "#f4f9ff" }
            GradientStop { position: 1; color: Theme.darkMode ? "#091b2e" : "#e9f3ff" }
        }
        border.width: 1
        border.color: Theme.darkMode ? "#4387b6" : Theme.borderStrong
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.shadow
            shadowOpacity: 0.72
            shadowBlur: 0.60
            shadowVerticalOffset: 8
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 2
            radius: 14
            color: "transparent"
            border.width: 1
            border.color: Theme.darkMode ? "#244d6c" : "#ffffff"
        }

        // Subtle blue edge light and footer divider tie into the main cards.
        Rectangle {
            anchors.top: parent.top
            anchors.topMargin: 1
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 40
            height: 1
            color: Theme.darkMode ? "#79caff" : "#b5d9fa"
            opacity: 0.65
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            y: parent.height - 82
            height: 1
            color: Theme.darkMode ? "#376285" : "#c4dcef"
            opacity: 0.65
        }
    }

    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 18

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            Item {
                Layout.alignment: Qt.AlignTop
                Layout.preferredWidth: 44
                Layout.preferredHeight: 44
                AnimatedSuccessIcon {
                    id: animatedSuccessIcon
                    objectName: "dialogSuccessIcon"
                    anchors.fill: parent
                    visible: root.variant === "success"
                    accent: Theme.darkMode ? root.statusAccent : Theme.success
                    checkColor: Theme.darkMode ? "#8dffd1" : Theme.success
                    surfaceTop: Theme.darkMode ? "#205c53" : "#eaf7f0"
                    surfaceBottom: Theme.darkMode ? "#0a2637" : "#ffffff"
                }

                // Use static rendering for info/error results.
                Rectangle {
                    objectName: "dialogStaticStatusIcon"
                    anchors.fill: parent
                    visible: root.variant !== "success"
                    radius: 22
                    gradient: Gradient {
                        GradientStop {
                            position: 0
                            color: Theme.darkMode ? "#314b68" : "#f9edef"
                        }
                        GradientStop {
                            position: 1
                            color: Theme.darkMode ? "#0a2637" : "#ffffff"
                        }
                    }
                    border.width: 1
                    border.color: Theme.darkMode ? root.statusAccent : Theme.error
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: root.statusAccent
                        shadowOpacity: Theme.darkMode ? 0.24 : 0.10
                        shadowBlur: 0.4
                        shadowVerticalOffset: 0
                    }

                    Text {
                        anchors.centerIn: parent
                        text: root.variant === "information" ? "i" : "!"
                        color: Theme.darkMode ? root.statusAccent : Theme.error
                        font.family: Theme.fontFamily
                        font.pixelSize: 23
                        font.weight: Font.Bold
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: root.dialogTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                }

                Text {
                    Layout.fillWidth: true
                    text: root.message
                    color: Theme.darkMode ? "#c1ddf3" : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: 13
                    lineHeight: 1.25
                    wrapMode: Text.Wrap
                }

                Item { Layout.fillHeight: true }
            }
        }

        PrimaryButton {
            id: okButton
            objectName: "dialogOkButton"
            Layout.alignment: Qt.AlignRight
            Layout.preferredWidth: 112
            Layout.preferredHeight: 42
            text: "OK"
            iconSource: ""
            visualStyle: FormTheme.current.saveButton
            onClicked: root.acceptDialog()
        }
    }
}
