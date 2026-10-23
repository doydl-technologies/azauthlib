pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Popup {
    id: root
    required property var appController
    property string draftAccent: "blue"
    property bool draftShowInfo: true
    property string draftServiceAnimation: "group"
    property string activeTab: "appearance"
    property bool draftWarmStart: false
    property bool draftAdaptiveSplash: false
    property bool draftLaunchAtLogin: false
    readonly property var serviceStyles: ["group", "badge", "mark"]
    readonly property var serviceStyleLabels: [
        "Logo, circle and service name",
        "Logo inside a circle",
        "Logo without a circle"
    ]
    readonly property var serviceStyleDescriptions: [
        "The logo, circular frame and service name move together.",
        "The framed logo moves; the service name stays below.",
        "Only the logo moves, without a frame; the name stays below."
    ]
    property string saveError: ""
    property bool saveConfirmationPending: false
    signal preferencesSaved()
    property int openFadeDuration: 400
    property int openScaleDuration: 500
    property var returnFocusItem: null
    readonly property var draftPalette: AccentTheme.paletteFor(draftAccent)
    readonly property bool dirty: draftAccent !== appController.appearancePreferences.accent ||
        draftShowInfo !== appController.appearancePreferences.show_info_buttons ||
        draftServiceAnimation !== (appController.appearancePreferences.service_animation || "group") ||
        draftWarmStart !== appController.startupPreferences.warm_start ||
        draftAdaptiveSplash !== appController.startupPreferences.adaptive_splash ||
        draftLaunchAtLogin !== appController.startupPreferences.launch_at_login
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(1040, parent ? parent.width - 64 : 1040)
    height: Math.min(690, parent ? parent.height - 64 : 690)
    padding: 26
    modal: true
    focus: true
    popupType: Popup.Item
    closePolicy: Popup.CloseOnEscape
    function openSettings(trigger) { returnFocusItem = trigger || null; open() }
    onAboutToShow: {
        draftAccent = appController.appearancePreferences.accent
        draftShowInfo = appController.appearancePreferences.show_info_buttons
        draftServiceAnimation = appController.appearancePreferences.service_animation || "group"
        draftWarmStart = appController.startupPreferences.warm_start
        draftAdaptiveSplash = appController.startupPreferences.adaptive_splash
        draftLaunchAtLogin = appController.startupPreferences.launch_at_login
        activeTab = "appearance"
        saveError = ""
        saveConfirmationPending = false
    }
    onOpened: closeButton.forceActiveFocus()
    onClosed: {
        const saved = saveConfirmationPending
        saveConfirmationPending = false
        if (returnFocusItem && returnFocusItem.visible && returnFocusItem.enabled)
            returnFocusItem.forceActiveFocus()
        if (saved) preferencesSaved()
    }
    Overlay.modal: Rectangle { color: "#99050b13" }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: ConnectionTheme.reducedMotion ? 0 : root.openFadeDuration; easing.type: Easing.InOutCubic }
        NumberAnimation { property: "scale"; from: 0.98; to: 1; duration: ConnectionTheme.reducedMotion ? 0 : root.openScaleDuration; easing.type: Easing.InOutCubic }
    }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: ConnectionTheme.reducedMotion ? 0 : 160 } }
    background: DialogSurface { objectName: "settingsDialogSurface"; radius: 22 }

    component SettingsIcon: Image {
        property string filename: ""
        source: "image://actionicons/" + filename
        sourceSize: Qt.size(96, 96)
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
    }
    component BodyText: Text {
        color: "#a8c3df"
        font.family: ConnectionTheme.body
        font.pixelSize: 12
        wrapMode: Text.Wrap
    }
    component Heading: Text {
        color: ConnectionTheme.text
        font.family: ConnectionTheme.heading
        font.pixelSize: 18
        font.weight: Font.ExtraBold
        wrapMode: Text.Wrap
    }

    component StartupOption: RowLayout {
        id: option
        property string title: ""
        property string description: ""
        property string switchName: ""
        property alias checked: optionSwitch.checked
        signal toggled(bool checked)
        spacing: 24
        ColumnLayout {
            Layout.fillWidth: true; spacing: 6
            Heading { text: option.title; font.pixelSize: 16; Layout.fillWidth: true }
            BodyText { text: option.description; Layout.fillWidth: true }
        }
        Switch {
            id: optionSwitch
            objectName: option.switchName
            Accessible.name: option.title
            Accessible.description: option.description
            onToggled: option.toggled(checked)
            implicitWidth: 54; implicitHeight: 30
            padding: 0; hoverEnabled: enabled
            HoverHandler { cursorShape: Qt.PointingHandCursor }
            indicator: Rectangle {
                width: 52; height: 28; radius: 14
                color: optionSwitch.checked ? root.draftPalette.middle : "#0b2137"
                border.color: optionSwitch.visualFocus ? root.draftPalette.focus : optionSwitch.checked ? root.draftPalette.accent : AccentTheme.color("#477598")
                border.width: optionSwitch.visualFocus ? 2 : 1
                Rectangle {
                    x: optionSwitch.checked ? 26 : 4; y: 4
                    width: 20; height: 20; radius: 10; color: "#edf4ff"
                    Behavior on x { NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 140 } }
                }
            }
            contentItem: Item {}
        }
    }

    contentItem: ColumnLayout {
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            spacing: 18
            SettingsIcon { filename: "settings-gear.svg"; Layout.preferredWidth: 36; Layout.preferredHeight: 36 }
            Heading { text: "Settings"; font.pixelSize: 27; Layout.fillWidth: true }
            ConnectionButton {
                id: closeButton
                objectName: "settingsCloseButton"
                symbol: "x"; text: ""; padding: 10
                implicitWidth: 44; implicitHeight: 44
                Accessible.name: "Close settings without saving"
                onClicked: root.close()
            }
        }
        ConnectionSurface {
            Layout.fillWidth: true
            Layout.preferredHeight: 58
            radius: 14; sunken: true; recessedFill: true
            RowLayout {
                anchors.fill: parent; anchors.margins: 5
                spacing: 0
                Repeater {
                    model: [
                        {key: "general", label: "General", icon: "settings-gear.svg"},
                        {key: "appearance", label: "Appearance", icon: "paint-brush-solid.svg"},
                        {key: "accessibility", label: "Accessibility", icon: "accessibility.svg"},
                        {key: "advanced", label: "Advanced", icon: "settings-horizontal.svg"}
                    ]
                    Button {
                        id: tab
                        required property var modelData
                        objectName: "settingsTab_" + modelData.key
                        Layout.fillWidth: true; Layout.fillHeight: true
                        enabled: modelData.key === "appearance" || modelData.key === "advanced"
                        onClicked: root.activeTab = modelData.key
                        HoverHandler {
                            objectName: "settingsTabCursor_" + tab.modelData.key
                            enabled: tab.enabled
                            cursorShape: Qt.PointingHandCursor
                        }
                        hoverEnabled: enabled
                        focusPolicy: enabled ? Qt.StrongFocus : Qt.NoFocus
                        Accessible.name: modelData.label + (enabled ? "" : " — currently unavailable")
                        Accessible.role: Accessible.PageTab
                        Accessible.selected: root.activeTab === modelData.key
                        opacity: enabled ? 1 : 0.32
                        contentItem: Row {
                            spacing: 10
                            SettingsIcon { filename: tab.modelData.icon; width: 22; height: 22; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: tab.modelData.label; color: "#edf4ff"; font.family: ConnectionTheme.body; font.pixelSize: 14; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                        }
                        leftPadding: Math.max(10, (width - 130) / 2)
                        background: Item {
                            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 10; height: 2; color: root.draftPalette.accent; visible: root.activeTab === tab.modelData.key }
                        }
                    }
                }
            }
        }
        ConnectionSurface {
            Layout.fillWidth: true; Layout.fillHeight: true
            visible: root.activeTab === "appearance"
            radius: 17; sunken: true
            depth: 7; blur: 15
            RowLayout {
                anchors.fill: parent; anchors.margins: 24
                visible: root.activeTab === "appearance"
                spacing: 24
                ScrollView {
                    id: appearanceScroll
                    Layout.fillWidth: true; Layout.fillHeight: true
                    Layout.preferredWidth: 440
                    contentWidth: availableWidth
                    contentHeight: appearanceOptions.implicitHeight
                    rightPadding: ConnectionTheme.scrollBarGutter
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical: ScrollBar {
                        parent: appearanceScroll
                        x: appearanceScroll.width - width
                        width: ConnectionTheme.scrollBarWidth
                        height: appearanceScroll.height
                        policy: appearanceScroll.contentHeight > appearanceScroll.availableHeight ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                    }
                ColumnLayout {
                    id: appearanceOptions
                    width: appearanceScroll.availableWidth
                    spacing: 8
                    Heading { text: "Appearance"; font.pixelSize: 24; Layout.fillWidth: true }
                    Heading { text: "Accent color"; font.pixelSize: 16; Layout.fillWidth: true }
                    BodyText { text: "Choose a coordinated family for interface highlights, outlines, icons and glows."; Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        Repeater {
                            model: AccentTheme.presets
                            ColumnLayout {
                                id: swatchColumn
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 6
                                Button {
                                    id: swatch
                                    objectName: "settingsAccent_" + swatchColumn.modelData.key
                                    Layout.alignment: Qt.AlignHCenter
                                    implicitWidth: 42; implicitHeight: 42
                                    padding: 0; hoverEnabled: true
                                    Accessible.name: swatchColumn.modelData.label + " accent"
                                    Accessible.checked: root.draftAccent === swatchColumn.modelData.key
                                    onClicked: root.draftAccent = swatchColumn.modelData.key
                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                    background: ConnectionSurface {
                                        radius: width / 2; smoothCircleOutline: true
                                        topColor: Qt.lighter(swatchColumn.modelData.color, 1.15)
                                        middleColor: swatchColumn.modelData.color
                                        bottomColor: Qt.darker(swatchColumn.modelData.color, 1.25)
                                        borderColor: root.draftAccent === swatchColumn.modelData.key || swatch.visualFocus ? AccentTheme.color("#e9f7ff") : swatchColumn.modelData.color
                                        borderWidth: root.draftAccent === swatchColumn.modelData.key ? 2 : 1
                                        lightColor: "transparent"; depth: 3; blur: 7
                                        shadowColor: AccentTheme.withAlpha(swatchColumn.modelData.color, root.draftAccent === swatchColumn.modelData.key ? 0.5 : 0.12)
                                    }
                                    contentItem: Text { text: root.draftAccent === swatchColumn.modelData.key ? "✓" : ""; color: "#102039"; font.pixelSize: 25; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                }
                                BodyText { text: swatchColumn.modelData.label; font.pixelSize: 10; Layout.alignment: Qt.AlignHCenter }
                            }
                        }
                    }
                    DialogDivider { Layout.fillWidth: true; Layout.topMargin: 8; Layout.bottomMargin: 8 }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 16
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            Heading { text: "Show info buttons"; font.pixelSize: 16; Layout.fillWidth: true }
                            BodyText { text: "Show contextual help icons throughout the application, including connection and certificate fields."; Layout.fillWidth: true }
                        }
                        Switch {
                            id: infoSwitch
                            objectName: "settingsShowInfoSwitch"
                            checked: root.draftShowInfo
                            onToggled: root.draftShowInfo = checked
                            Accessible.name: "Show info buttons throughout the application"
                            implicitWidth: 54; implicitHeight: 30
                            padding: 0; hoverEnabled: true
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            indicator: Rectangle {
                                width: 52; height: 28; radius: 14
                                color: infoSwitch.checked ? root.draftPalette.middle : "#0b2137"
                                border.color: infoSwitch.visualFocus ? root.draftPalette.focus : infoSwitch.checked ? root.draftPalette.accent : AccentTheme.color("#477598")
                                border.width: infoSwitch.visualFocus ? 2 : 1
                                Rectangle {
                                    x: infoSwitch.checked ? 26 : 4; y: 4
                                    width: 20; height: 20; radius: 10; color: "#edf4ff"
                                    Behavior on x { NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 140 } }
                                }
                            }
                            contentItem: Item {}
                        }
                    }
                    DialogDivider { Layout.fillWidth: true; Layout.topMargin: 8; Layout.bottomMargin: 8 }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Heading { text: "Service selection animation"; font.pixelSize: 16; Layout.fillWidth: true }
                        BodyText { text: "Choose what moves into the center when opening a service."; Layout.fillWidth: true }
                        ConnectionCombo {
                            id: serviceAnimation
                            objectName: "settingsServiceAnimation"
                            popup.objectName: "settingsServiceAnimationPopup"
                            Layout.fillWidth: true
                            model: root.serviceStyleLabels
                            currentIndex: Math.max(0, root.serviceStyles.indexOf(root.draftServiceAnimation))
                            Accessible.name: "Service selection animation"
                            Accessible.description: root.serviceStyleDescriptions[currentIndex]
                            onActivated: index => root.draftServiceAnimation = root.serviceStyles[index]
                            delegate: ItemDelegate {
                                id: serviceOption
                                required property string modelData
                                required property int index
                                objectName: "settingsServiceAnimationOption" + index
                                width: serviceAnimation.width - 10
                                height: 70
                                leftPadding: 12; rightPadding: 34
                                topPadding: 10; bottomPadding: 10
                                text: modelData
                                highlighted: serviceAnimation.highlightedIndex === index
                                Accessible.name: modelData
                                Accessible.description: root.serviceStyleDescriptions[index]
                                Accessible.checked: serviceAnimation.currentIndex === index
                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                                contentItem: Column {
                                    spacing: 4
                                    Text {
                                        width: parent.width
                                        text: serviceOption.modelData
                                        color: ConnectionTheme.text
                                        font.family: ConnectionTheme.body
                                        font.pixelSize: 12; font.weight: Font.Bold
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        objectName: "settingsServiceAnimationDescription" + serviceOption.index
                                        width: parent.width
                                        text: root.serviceStyleDescriptions[serviceOption.index]
                                        color: "#a8c3df"
                                        font.family: ConnectionTheme.body
                                        font.pixelSize: 11
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2; elide: Text.ElideRight
                                    }
                                }
                                background: Rectangle {
                                    radius: 6
                                    color: serviceOption.highlighted ? AccentTheme.color("#24557b") : "transparent"
                                    Text {
                                        anchors.right: parent.right; anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "✓"; color: ConnectionTheme.accent; font.pixelSize: 16
                                        visible: serviceAnimation.currentIndex === serviceOption.index
                                    }
                                }
                            }
                        }
                    }
                }
                }
                Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 1; color: AccentTheme.color("#345b85") }
                ConnectionSurface {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    Layout.preferredWidth: 380
                    radius: 16; sunken: true; recessedFill: true; depth: 5; blur: 12
                    borderColor: AccentTheme.colorFor("#345b85", root.draftAccent)
                    lightColor: AccentTheme.colorFor("#72345b85", root.draftAccent)
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 22
                        spacing: 14
                        Heading { text: "Preview"; Layout.fillWidth: true }
                        BodyText { text: "See your appearance preferences before saving."; Layout.fillWidth: true }
                        RowLayout {
                            objectName: "settingsPreviewInputLabelRow"
                            Layout.fillWidth: true
                            Layout.minimumHeight: 21
                            BodyText { text: "Sample input (focused)"; Layout.fillWidth: true }
                            ConnectionHelpButton {
                                objectName: "settingsPreviewInfoIcon"
                                visible: root.draftShowInfo
                                // Show the real raised artwork, not a dimmed or
                                // interactive help control, in this sample.
                                enabled: false
                                opacity: 1
                                hoverEnabled: false
                                focusPolicy: Qt.NoFocus
                                accentFamily: root.draftAccent
                                Layout.preferredWidth: 21; Layout.preferredHeight: 21
                                text: "Example information icon"
                                Accessible.role: Accessible.Graphic
                                Accessible.description: "Display-only example of an information button"
                            }
                        }
                        ConnectionSurface {
                            objectName: "settingsPreviewInput"
                            Layout.fillWidth: true; Layout.preferredHeight: 44
                            radius: 8; sunken: true; recessedFill: true
                            borderColor: root.draftPalette.focus; borderWidth: 2
                            lightColor: AccentTheme.withAlpha(root.draftPalette.glow, 0.35)
                            Text { anchors.fill: parent; anchors.leftMargin: 13; verticalAlignment: Text.AlignVCenter; text: "Enter a value…"; color: "#b9d3e9"; font.family: ConnectionTheme.body; font.pixelSize: 12 }
                        }
                        ConnectionButton {
                            objectName: "settingsPreviewButton"
                            Layout.alignment: Qt.AlignHCenter
                            text: "Sample button"; symbol: "plug"; implicitWidth: 180; implicitHeight: 40
                            iconAccentFamily: root.draftAccent
                            focusPolicy: Qt.NoFocus
                            background: ConnectionSurface {
                                radius: 10; topColor: root.draftPalette.top; middleColor: root.draftPalette.middle; bottomColor: root.draftPalette.bottom
                                borderColor: root.draftPalette.border; lightColor: "transparent"
                                shadowColor: AccentTheme.withAlpha(root.draftPalette.glow, 0.35)
                            }
                        }
                        DialogDivider { Layout.fillWidth: true; color: AccentTheme.colorFor("#376285", root.draftAccent) }
                        BodyText { text: "Selected connection (sample)"; Layout.fillWidth: true }
                        ConnectionSurface {
                            objectName: "settingsPreviewProfile"
                            Layout.fillWidth: true; Layout.preferredHeight: 76
                            radius: 12; sunken: true; recessedFill: true
                            borderColor: root.draftPalette.accent; borderWidth: 1.5
                            lightColor: AccentTheme.colorFor("#72345b85", root.draftAccent)
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 14; spacing: 12
                                ConnectionIcon { objectName: "settingsPreviewPlug"; name: "plug"; accentFamily: root.draftAccent; Layout.preferredWidth: 26; Layout.preferredHeight: 26 }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 4
                                    Heading { text: "Sample profile"; font.pixelSize: 14; Layout.fillWidth: true }
                                    BodyText { text: "Currently active connection"; font.pixelSize: 10; Layout.fillWidth: true }
                                }
                                Text { text: "✓"; color: root.draftPalette.accent; font.pixelSize: 20 }
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }
        ConnectionSurface {
            objectName: "settingsAdvancedPanel"
            Layout.fillWidth: true; Layout.fillHeight: true
            visible: root.activeTab === "advanced"
            radius: 17; sunken: true; depth: 7; blur: 15
            ScrollView {
                id: advancedScroll
                anchors.fill: parent; anchors.margins: 24
                contentWidth: availableWidth
                contentHeight: advancedOptions.implicitHeight
                rightPadding: ConnectionTheme.scrollBarGutter
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical: ScrollBar {
                    parent: advancedScroll
                    x: advancedScroll.width - width
                    width: ConnectionTheme.scrollBarWidth
                    height: advancedScroll.height
                    policy: advancedScroll.contentHeight > advancedScroll.availableHeight ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                }
                ColumnLayout {
                    id: advancedOptions
                    width: advancedScroll.availableWidth
                    spacing: 16
                    Heading { text: "Advanced"; font.pixelSize: 24; Layout.fillWidth: true }
                    BodyText { text: "Choose how azauthlib starts. All options are off by default."; Layout.fillWidth: true }
                    StartupOption {
                        Layout.fillWidth: true
                        title: "Faster repeat launches"
                        description: "Prepare shared app content after saving, then prepare Connections in the background for services you have opened before. This may reduce wait times; it never signs in or tests a connection."
                        switchName: "settingsWarmStartSwitch"
                        checked: root.draftWarmStart
                        onToggled: checked => root.draftWarmStart = checked
                    }
                    BodyText {
                        objectName: "settingsWarmStartStatus"
                        Layout.fillWidth: true
                        visible: root.draftWarmStart
                        text: root.appController.warmStartStatus === "preparing" ?
                            "Preparing startup content… You can keep using the app. Let preparation finish before closing." :
                            root.appController.warmStartStatus === "ready" ?
                            "Shared startup content is prepared. Previously opened services prepare when the Main Menu is idle. Wait times can still vary." :
                            root.appController.warmStartStatus === "unavailable" ?
                            "Preparation could not finish. The app will still open normally and rebuild any missing content when needed." :
                            "Save to prepare startup content in the background. The first launch may still need additional preparation."
                    }
                    DialogDivider { Layout.fillWidth: true }
                    StartupOption {
                        Layout.fillWidth: true
                        title: "Skip splash on fast launches"
                        description: "Skip the splash when the Main Menu is ready quickly. This does not speed up loading; slower launches still show the splash until the app is ready."
                        switchName: "settingsAdaptiveSplashSwitch"
                        checked: root.draftAdaptiveSplash
                        onToggled: checked => root.draftAdaptiveSplash = checked
                    }
                    DialogDivider { Layout.fillWidth: true }
                    StartupOption {
                        Layout.fillWidth: true
                        enabled: root.appController.loginStartupSupported
                        opacity: enabled ? 1 : 0.4
                        title: "Open at login"
                        description: "Open azauthlib automatically when you sign in to this computer. Applies only to your account and this installation. Your operating system may ask you to allow startup apps."
                        switchName: "settingsLaunchAtLoginSwitch"
                        checked: root.draftLaunchAtLogin
                        onToggled: checked => root.draftLaunchAtLogin = checked
                    }
                    DialogDivider { Layout.fillWidth: true }
                    BodyText {
                        Layout.fillWidth: true
                        text: "Saving applies these choices; it does not guarantee a faster next launch. Closing azauthlib still exits it normally. Turn off Open at login before moving or removing this installation."
                    }
                }
            }
        }
        BodyText { objectName: "settingsSaveError"; visible: root.saveError.length > 0; text: root.saveError; color: "#ff94a2"; Layout.fillWidth: true }
        DialogDivider { Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true; spacing: 12
            ConnectionButton {
                objectName: "settingsResetButton"
                text: "Reset to default"; iconSource: Qt.resolvedUrl("../../../assets/icons/svg/actions/power-reset.svg")
                iconSize: 18; iconTextSpacing: 8; implicitHeight: 42
                onClicked: {
                    if (root.activeTab === "advanced") {
                        root.draftWarmStart = false
                        root.draftAdaptiveSplash = false
                        root.draftLaunchAtLogin = false
                    } else {
                        root.draftAccent = "blue"
                        root.draftShowInfo = true
                        root.draftServiceAnimation = "group"
                    }
                    root.saveError = ""
                }
            }
            Item { Layout.fillWidth: true }
            ConnectionButton {
                objectName: "settingsCancelButton"
                text: "Cancel"; variant: "cancel"; implicitWidth: 110; implicitHeight: 42
                onClicked: root.close()
            }
            ConnectionButton {
                objectName: "settingsSaveButton"
                text: "Save preferences"; variant: "primary"
                iconSource: Qt.resolvedUrl("../../../assets/icons/svg/actions/save.svg")
                iconSize: 18; implicitHeight: 42
                enabled: root.dirty && !root.saveConfirmationPending
                onClicked: {
                    if (!enabled) return
                    if (root.appController.savePreferences(root.draftAccent, root.draftShowInfo, root.draftServiceAnimation,
                            root.draftWarmStart, root.draftAdaptiveSplash, root.draftLaunchAtLogin)) {
                        root.saveConfirmationPending = true
                        root.close()
                    } else root.saveError = root.appController.preferencesError || "Preferences could not be saved. Check folder permissions and try again."
                }
            }
        }
    }
}
