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
    property bool acknowledgementPending: false
    readonly property color statusAccent: variant === "success" ? "#57e5ae" :
                                         variant === "information" ? AccentTheme.color("#65caff") : "#ff8a99"
    signal acknowledged

    parent: Overlay.overlay
    anchors.centerIn: parent
    width: 470
    height: Math.max(228, contentItem.implicitHeight + topPadding + bottomPadding)
    modal: true
    focus: true
    padding: 24
    closePolicy: Popup.NoAutoClose

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic }
        NumberAnimation { property: "scale"; from: 0.98; to: 1; duration: 260; easing.type: Easing.OutCubic }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: ConnectionTheme.popupExitDuration; easing.type: Easing.InOutCubic }
    }

    function showDialog(title, body, kind, shouldClose) {
        const wasVisible = visible
        dialogTitle = title
        message = body
        variant = kind
        closeAfter = shouldClose
        acknowledgementPending = false
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
        if (!visible || acknowledgementPending) return
        acknowledgementPending = true
        close()
    }

    onOpened: okButton.forceActiveFocus()
    onAboutToShow: startStatusAnimation()
    onAboutToHide: animatedSuccessIcon.stop()
    onClosed: {
        animatedSuccessIcon.reset()
        // A fatal message may close the application: let its fade finish first.
        if (acknowledgementPending) {
            acknowledgementPending = false
            acknowledged()
        }
    }
    onVariantChanged: {
        if (variant !== "success")
            animatedSuccessIcon.reset()
    }

    Shortcut {
        sequence: "Return"
        enabled: root.visible && !root.acknowledgementPending
        onActivated: root.acceptDialog()
    }

    Shortcut {
        sequence: "Escape"
        enabled: root.visible && !root.acknowledgementPending
        onActivated: root.acceptDialog()
    }

    Overlay.modal: Rectangle {
        color: Theme.darkMode ? "#99050b13" : "#668393a3"
    }

    background: DialogSurface { objectName: "appDialogSurface" }

    contentItem: ColumnLayout {
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            Item {
                objectName: "appDialogIconRegion"
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
                            color: Theme.darkMode ? AccentTheme.color("#314b68") : "#f9edef"
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
                Layout.alignment: Qt.AlignTop
                spacing: 8

                Text {
                    objectName: "appDialogTitle"
                    Layout.fillWidth: true
                    text: root.dialogTitle
                    color: Theme.textPrimary
                    font.family: Theme.fontFamily
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }

                Text {
                    objectName: "appDialogMessage"
                    Layout.fillWidth: true
                    text: root.message
                    color: Theme.darkMode ? "#c1ddf3" : Theme.textSecondary
                    font.family: Theme.fontFamily
                    font.pixelSize: 13
                    lineHeight: 1.25
                    wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }
            }
        }

        DialogDivider {
            objectName: "appDialogDivider"
            Layout.fillWidth: true
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
