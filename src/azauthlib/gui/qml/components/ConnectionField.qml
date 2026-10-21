pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root
    property alias text: input.text
    property alias readOnly: input.readOnly
    property alias placeholderText: input.placeholderText
    property string label: ""
    property bool password: false
    property bool passwordVisible: false
    property string infoDescription: ""
    property string infoGuidance: ""
    property string infoStorageNote: ""
    property string helpTopic: ""
    property bool helpExpanded: false
    property bool validationFeedbackEnabled: false
    property string validationError: ""
    property bool validationTouched: false
    readonly property Item transitionItem: transitionText
    readonly property string transitionValue: input.text.length ? input.displayText : input.placeholderText
    property bool transitionBusy: false
    property real transitionOpacity: 1
    property real transitionOffset: 0
    property real presenceOpacity: 1
    property real presenceOffset: 0
    readonly property FieldInfoPopup helpPopup: helpLoader.item as FieldInfoPopup
    readonly property bool helpVisible: helpExpanded || (helpPopup ? helpPopup.visible : false)
    readonly property bool menuVisible: fieldContextMenu.visible
    signal edited()
    signal helpRequested(var trigger)
    function dismissHelp() { if (helpPopup) helpPopup.close() }
    function dismissInteractions() { fieldContextMenu.close(); dismissHelp() }
    function focusInput() { input.forceActiveFocus() }
    opacity: (enabled || transitionBusy ? 1 : 0.45) * presenceOpacity
    transform: Translate { y: root.presenceOffset }
    onEnabledChanged: if (!enabled) dismissInteractions()
    // Grid spacing reserves room for feedback so errors do not resize the field.
    implicitHeight: info.visible ? 64 : 57
    implicitWidth: 240
    Row {
        objectName: root.objectName + "LabelRow"
        height: info.visible ? 21 : 14
        spacing: 6
        Text { objectName: root.objectName + "Label"; anchors.verticalCenter: parent.verticalCenter; text: root.label; color: "#c1d5ec"; font.family: ConnectionTheme.body; font.pixelSize: 11; font.weight: Font.ExtraBold }
        ConnectionHelpButton {
            id: info
            objectName: root.objectName + "InfoButton"
            visible: root.helpTopic.length > 0 || root.infoDescription.length > 0
            text: "About " + root.label
            expanded: root.helpExpanded
            opacity: (enabled || root.transitionBusy) && !expanded ? 1 : 0.4
            onClicked: {
                if (root.helpTopic.length > 0) root.helpRequested(info)
                else if (root.helpPopup) root.helpPopup.openBeside(info)
            }
        }
    }
    // Entry chrome stays outside the text layer, so neither its surface nor
    // its outline is captured/moved when only the displayed value changes.
    ConnectionFieldBackground {
        objectName: root.objectName + "Chrome"
        control: input
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: 37
    }
    Item {
        id: transitionText
        objectName: root.objectName + "TransitionText"
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: 37
        opacity: root.transitionOpacity
        transform: Translate { y: root.transitionOffset }
        clip: true
        TextField {
            id: input
            objectName: root.objectName + "Input"
            anchors.fill: parent
            readonly property string validationError: root.validationError
            readonly property bool visualEnabled: root.enabled || root.transitionBusy
            height: 37; leftPadding: 12; rightPadding: eye.visible ? 40 : 12
            font.family: ConnectionTheme.body; font.pixelSize: 12; font.weight: Font.DemiBold
            color: readOnly ? "#b9d3e9" : "#edf4ff"
            placeholderTextColor: "#809bb2ce"
            selectionColor: "#196fd3"; selectedTextColor: "white"
            selectByMouse: true; hoverEnabled: true
            echoMode: root.password && !root.passwordVisible ? TextInput.Password : TextInput.Normal
            inputMethodHints: root.password ? Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase : Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
            Accessible.name: root.label
            Accessible.description: root.validationError || root.placeholderText
            // Give editing a high-contrast caret without implying saved details are writable.
            // Qt positions this delegate at the insertion point, including masked secrets.
            cursorDelegate: Item {
                id: caret
                objectName: input.objectName + "Caret"
                width: 2
                readonly property bool editing: input.enabled && input.activeFocus && !input.readOnly &&
                                               input.selectionStart === input.selectionEnd
                property bool blinkOn: true
                // StyleHints is exposed as QObject in QML's static type metadata.
                property var systemStyleHints: Qt.styleHints
                function resetBlink() {
                    blinkOn = true
                    if (blinkTimer.running) blinkTimer.restart()
                }
                onEditingChanged: resetBlink()
                Rectangle {
                    objectName: input.objectName + "CaretStroke"
                    anchors.fill: parent
                    color: "#d5f0ff"
                    visible: caret.editing && caret.blinkOn
                }
                Timer {
                    id: blinkTimer
                    interval: Math.max(150, caret.systemStyleHints.cursorFlashTime / 2)
                    repeat: true
                    // A zero flash time is the OS accessibility preference for a steady caret.
                    running: caret.editing && caret.systemStyleHints.cursorFlashTime > 0
                    onRunningChanged: if (!running) caret.blinkOn = true
                    onTriggered: caret.blinkOn = !caret.blinkOn
                }
                Connections {
                    target: input
                    function onCursorPositionChanged() { caret.resetBlink() }
                }
            }
            onTextEdited: { root.validationTouched = true; root.edited() }
            onEditingFinished: root.validationTouched = true
            // Passive saved identifiers keep their beginning visible as the shelf opens.
            onWidthChanged: if (readOnly && !activeFocus) cursorPosition = 0
            onTextChanged: if (readOnly && !activeFocus) cursorPosition = 0
            background: null
            ContextMenu.menu: AppTextContextMenu { id: fieldContextMenu; objectName: root.objectName + "ContextMenu"; target: input; enabled: root.enabled }
            Keys.onPressed: event => {
                if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))) {
                    fieldContextMenu.popup(input, Qt.point(input.leftPadding, input.height)); event.accepted = true
                }
            }
        }
    }
    Button {
        id: eye
        objectName: root.objectName + "VisibilityButton"
        visible: root.password && !input.readOnly
        anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: transitionText.verticalCenter
        width: 24; height: 24; padding: 4; hoverEnabled: true
        Accessible.name: root.passwordVisible ? "Hide client secret" : "Show client secret"
        contentItem: ConnectionIcon { name: root.passwordVisible ? "eyeOff" : "eye" }
        background: Rectangle { radius: 5; color: eye.hovered ? "#244c70" : "transparent"; border.color: eye.visualFocus ? "#38a8ff" : "transparent" }
        HoverHandler { cursorShape: Qt.PointingHandCursor }
        onClicked: root.passwordVisible = !root.passwordVisible
    }
    Text {
        objectName: root.objectName + "ValidationError"
        anchors.left: parent.left; anchors.right: parent.right
        anchors.top: transitionText.bottom
        height: 10
        visible: root.validationFeedbackEnabled
        text: root.validationError
        textFormat: Text.PlainText
        color: "#ff889e"
        font.family: ConnectionTheme.body; font.pixelSize: 9
        elide: Text.ElideRight
        Accessible.name: text
        ToolTip.visible: errorHover.hovered && text.length > 0
        ToolTip.text: text
        HoverHandler { id: errorHover }
    }
    Loader {
        id: helpLoader
        active: root.helpTopic.length === 0 && root.infoDescription.length > 0
        sourceComponent: FieldInfoPopup {
            objectName: root.objectName + "InfoPopup"
            title: root.label; description: root.infoDescription; guidance: root.infoGuidance; storageNote: root.infoStorageNote
            iconSource: Qt.resolvedUrl("../../../assets/icons/svg/status/information-alerts/info-thick.svg")
        }
    }
    onVisibleChanged: if (!visible) dismissInteractions()
}
