pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    required property var popup
    required property var appController
    readonly property var manager: appController.connectionManager
    readonly property bool addingConnection: manager.creatingConnection
    readonly property bool contentTransitionBusy: contentSwap.busy
    readonly property bool unrelatedControlsEnabled: !manager.testing && !manager.editing && !contentTransitionBusy
    readonly property bool empty: manager.profiles.length === 0 && !manager.editing
    readonly property bool selectedIsActive: manager.selectedId.length > 0 &&
        manager.selectedId === appController.currentProfileId
    readonly property bool canAct: !manager.editing && !manager.testing && manager.profiles.length > 0
    readonly property var draftValidation: {
        // Track controller metadata too (duplicate names and stored-secret reuse).
        const editor = manager.editor
        const profiles = manager.profiles
        return manager.validateConnectionDraft(nameField.text, tenantField.text, clientField.text,
            methodBox.currentIndex === 2 ? secretField.text : "",
            ["interactive", "device_code", "client_credentials"][methodBox.currentIndex] || "")
    }
    readonly property bool draftChanged: {
        const editor = manager.editor
        const editing = manager.editing
        return manager.connectionDraftChanged(nameField.text, tenantField.text, clientField.text,
            methodBox.currentIndex === 2 ? secretField.text : "",
            ["interactive", "device_code", "client_credentials"][methodBox.currentIndex] || "")
    }
    onDraftChangedChanged: if (manager.editing && !addingConnection) popup.editorDirty = draftChanged
    function markDraftEdited() { popup.editorDirty = addingConnection || draftChanged }
    property real testingLayout: manager.testing ? 1 : 0
    Behavior on testingLayout { NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 180; easing.type: Easing.OutCubic } }
    readonly property bool editorDirty: popup.editorDirty
    property bool deviceCodeCopied: false
    property var pendingAction: null
    property string helpTopic: ""
    property string displayedHelpTopic: "auth"
    property var lastHelpTrigger: null
    readonly property bool helpOpen: helpTopic.length > 0
    readonly property bool zoomBlocked: discardDialog.visible || removeDialog.visible || useDialog.visible ||
        methodBox.popup.visible || nameField.menuVisible || tenantField.menuVisible || clientField.menuVisible || secretField.menuVisible
    // A closing overlay can restore its old focus after the test starts.
    onZoomBlockedChanged: if (manager.testing && !zoomBlocked) Qt.callLater(focusCancelTest)
    onHelpOpenChanged: if (helpOpen && root.popup.homePage)
        Qt.callLater(() => root.popup.revealItem(helpViewport))
    readonly property real helpWidth: Math.min(342, width * 0.4)
    readonly property real sidebarWidth: Math.min(288 - 92 * helpProgress,
        Math.max(196, (workspace.width - (52 - 22 * helpProgress)) * 0.3))
    readonly property bool compactDetails: detailsColumn.width < 440
    readonly property bool compactStatus: workspace.width < 700
    property real helpProgress: helpOpen ? 1 : 0
    Behavior on helpProgress { NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 520; easing.type: Easing.OutCubic } }
    ConnectionHelpTopics { id: helpTopics }
    function toggleHelp(topic, trigger) {
        if (manager.testing || contentTransitionBusy) return
        if (manager.editing && !["name", "auth", "tenant", "client", "secret"].includes(topic)) return
        if (!helpTopics.topics[topic]) return
        lastHelpTrigger = trigger
        if (helpTopic === topic) { closeHelp(); return }
        displayedHelpTopic = topic
        helpTopic = topic
    }
    function closeHelp() {
        helpTopic = ""
        if (lastHelpTrigger && lastHelpTrigger.visible && lastHelpTrigger.enabled)
            lastHelpTrigger.forceActiveFocus()
    }

    function focusCancelTest() {
        if (manager.testing && root.visible && root.enabled) cancelTestButton.forceActiveFocus()
    }
    function lockTestingInteractions() {
        // Popups live in the window overlay, outside the disabled details subtree.
        // Dismiss them too so no previous menu or help action remains reachable.
        closeHelp()
        methodBox.popup.close()
        for (const field of [nameField, tenantField, clientField, secretField])
            field.dismissInteractions()
        pendingAction = null
        discardDialog.close(); removeDialog.close(); useDialog.close()
        Qt.callLater(focusCancelTest)
    }

    function guardDraft(action) {
        if (editorDirty) { pendingAction = action; discardDialog.open() }
        else action()
    }
    function synchronizeEditor() {
        const value = manager.editor
        nameField.text = value.name || ""
        tenantField.text = value.tenant || ""
        clientField.text = value.client || ""
        secretField.text = ""
        secretField.passwordVisible = false
        methodBox.currentIndex = Math.max(0, ["interactive", "device_code", "client_credentials"].indexOf(value.method))
        nameField.validationTouched = false
        tenantField.validationTouched = false
        clientField.validationTouched = false
        secretField.validationTouched = false
        popup.editorDirty = false
        if (manager.editing && helpOpen && !["name", "auth", "tenant", "client", "secret"].includes(helpTopic))
            closeHelp()
    }
    function changeContent(action, focusEditor, reverse, instantFields) {
        if (contentTransitionBusy) return
        secretField.passwordVisible = false
        contentSwap.run(action, focusEditor === true ? () => nameField.focusInput() :
            focusEditor === false ? () => {
                if (manager.editing) nameField.focusInput()
                else if (root.empty) emptyAddButton.forceActiveFocus()
                else editButton.forceActiveFocus()
            } : null, reverse, instantFields)
    }
    function beginConnection() {
        if (manager.editing || manager.testing || contentTransitionBusy) return
        changeContent(() => {
            if (helpOpen && !["name", "auth", "tenant", "client", "secret"].includes(helpTopic)) closeHelp()
            manager.beginAdd()
        }, true)
    }
    function requestClose() { guardDraft(() => root.popup.close()) }
    function cleanup() {
        contentSwap.cancel()
        manager.cancelTest()
        manager.cancelEdit()
        secretField.text = ""
        secretField.passwordVisible = false
        tenantField.dismissHelp()
        clientField.dismissHelp()
        secretField.dismissHelp()
        closeHelp()
    }
    Component.onCompleted: synchronizeEditor()
    Item {
        id: contentSwap
        objectName: "managerContentTransition"
        property bool busy: false
        property bool revealing: false
        property real progress: 1
        property real direction: 1
        property int remaining: 0
        property bool captureFailed: false
        property var action: null
        property var after: null
        property bool instantFields: false
        // Resolve presence before text, so a newly appearing field animates once,
        // while an existing field animates only a genuinely different value.
        readonly property var frames: [emptyChange, titleChange, namePresence, methodPresence,
            tenantPresence, clientPresence, secretPresence, nameText, methodText, tenantText,
            clientText, secretText, badgeChange, editChange, removeChange, useChange,
            useLabelChange, cancelChange, saveChange]
        function run(callback, finished, reverse, keepFields) {
            if (busy) return
            instantFields = keepFields === true
            if (ConnectionTheme.reducedMotion || !root.visible) {
                callback()
                if (finished) Qt.callLater(finished)
                return
            }
            busy = true
            direction = reverse ? -1 : 1
            action = callback; after = finished
            remaining = frames.length; captureFailed = false
            for (const frame of frames) frame.capture()
        }
        function captured(success) {
            if (!busy || revealing) return
            captureFailed = captureFailed || !success
            if (--remaining > 0) return
            const callback = action
            action = null
            progress = 0
            if (callback) callback()
            for (const frame of frames) frame.resolve()
            if (captureFailed || ConnectionTheme.reducedMotion) finish()
            else { revealing = true; revealAnimation.start() }
        }
        function finish() {
            const callback = after
            after = null
            revealing = false; progress = 1; busy = false
            for (const frame of frames) frame.release()
            if (callback) Qt.callLater(callback)
        }
        function cancel() {
            revealAnimation.stop()
            action = null; after = null
            finish()
        }
        component Change: ContentChange {
            coordinator: contentSwap
            overlayParent: detailsAnimationViewport
        }
        Change { id: emptyChange; sourceItem: emptyState; compareValue: false }
        Change { id: titleChange; sourceItem: detailsTitle; value: detailsTitle.text }
        Change { id: namePresence; sourceItem: nameField; compareValue: false; instant: contentSwap.instantFields }
        Change { id: methodPresence; sourceItem: methodRegion; compareValue: false; instant: contentSwap.instantFields }
        Change { id: tenantPresence; sourceItem: tenantField; compareValue: false; instant: contentSwap.instantFields }
        Change { id: clientPresence; sourceItem: clientField; compareValue: false; instant: contentSwap.instantFields }
        Change { id: secretPresence; sourceItem: secretField; compareValue: false; instant: contentSwap.instantFields }
        Change {
            id: nameText; sourceItem: nameField.transitionItem; value: nameField.transitionValue
            instant: contentSwap.instantFields; suppressed: namePresence.changed
        }
        Change {
            id: methodText; sourceItem: methodBox.transitionItem; value: methodBox.currentText
            instant: contentSwap.instantFields; suppressed: methodPresence.changed
        }
        Change {
            id: tenantText; sourceItem: tenantField.transitionItem; value: tenantField.transitionValue
            instant: contentSwap.instantFields; suppressed: tenantPresence.changed
        }
        Change {
            id: clientText; sourceItem: clientField.transitionItem; value: clientField.transitionValue
            instant: contentSwap.instantFields; suppressed: clientPresence.changed
        }
        Change {
            id: secretText; sourceItem: secretField.transitionItem; value: secretField.transitionValue
            instant: contentSwap.instantFields; suppressed: secretPresence.changed
        }
        Change { id: badgeChange; sourceItem: testButton.resultBadgeItem; value: root.manager.testResult }
        Change { id: editChange; sourceItem: editButton; compareValue: false }
        Change { id: removeChange; sourceItem: removeButton; compareValue: false }
        Change { id: useChange; sourceItem: useButton; compareValue: false }
        Change {
            id: useLabelChange; sourceItem: useButton.labelTransitionItem; value: useButton.text
            suppressed: useChange.changed
        }
        Change { id: cancelChange; sourceItem: cancelButton; compareValue: false }
        Change { id: saveChange; sourceItem: saveButton; compareValue: false }
        NumberAnimation {
            id: revealAnimation
            objectName: "managerContentRevealAnimation"
            target: contentSwap; property: "progress"; from: 0; to: 1
            duration: ConnectionTheme.contentTransitionDuration
            easing.type: Easing.InOutCubic
            onFinished: contentSwap.finish()
        }
        Connections {
            target: ConnectionTheme
            function onReducedMotionChanged() {
                if (ConnectionTheme.reducedMotion && contentSwap.revealing) {
                    revealAnimation.complete()
                    if (contentSwap.busy) contentSwap.finish()
                }
            }
        }
    }
    Shortcut {
        sequence: "Escape"
        enabled: root.enabled && !root.manager.testing && !root.contentTransitionBusy && !root.popup.homePage && root.popup.visible && !discardDialog.visible && !removeDialog.visible && !useDialog.visible &&
                 !methodBox.popup.visible && !tenantField.helpVisible && !clientField.helpVisible && !secretField.helpVisible &&
                 !root.helpOpen && !nameField.menuVisible && !tenantField.menuVisible && !clientField.menuVisible && !secretField.menuVisible
        onActivated: root.requestClose()
    }
    Shortcut {
        sequence: "Escape"
        enabled: root.enabled && !root.manager.testing && !root.contentTransitionBusy && root.helpOpen && !discardDialog.visible && !removeDialog.visible && !useDialog.visible &&
                 !methodBox.popup.visible && !nameField.menuVisible && !tenantField.menuVisible && !clientField.menuVisible && !secretField.menuVisible
        onActivated: root.closeHelp()
    }
    layer.enabled: discardDialog.visible || removeDialog.visible || useDialog.visible
    layer.effect: MultiEffect { blurEnabled: true; blurMax: 16; blur: 0.3 }
    Connections {
        target: root.manager
        function onEditorChanged() { root.synchronizeEditor() }
        function onDeviceCodeChanged() { copiedCodeTimer.stop(); root.deviceCodeCopied = false }
        function onTestChanged() { if (root.manager.testing) root.lockTestingInteractions() }
    }
    Connections {
        target: root.appController
        function onLegalDocumentsChanged() {
            if (["terms", "privacy"].includes(root.helpTopic) &&
                    !(root.appController.legalDocuments[root.helpTopic] || "").length)
                root.closeHelp()
        }
    }
    Timer { id: copiedCodeTimer; interval: 1800; onTriggered: root.deviceCodeCopied = false }

    Item {
        id: workspace
        objectName: "managerWorkspace"
        anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
        width: parent.width - root.helpWidth * root.helpProgress

    // The home page uses the native window close button; reclaim its header space.
    RowLayout {
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        anchors.leftMargin: 29 - 12 * root.helpProgress
        anchors.rightMargin: (root.popup.homePage ? 29 : 49) - 12 * root.helpProgress
        anchors.topMargin: 23 - 5 * root.helpProgress
        spacing: 16
        Column {
            Layout.fillWidth: true
            spacing: 5
            Text {
                text: "Connections"; color: ConnectionTheme.text
                font.family: ConnectionTheme.heading; font.pixelSize: Math.round(23 - 2 * root.helpProgress); font.weight: Font.ExtraBold; font.letterSpacing: -0.8
            }
            Text {
                text: "Your Microsoft Graph connection profiles, organized."
                color: ConnectionTheme.muted; font.family: ConnectionTheme.body; font.pixelSize: 12
            }
        }
        ConnectionSurface {
            objectName: "managerHeaderPlug"
            Layout.preferredWidth: 43 - 8 * root.helpProgress; Layout.preferredHeight: 43 - 8 * root.helpProgress
            radius: 14; depth: 5; blur: 11; borderColor: "transparent"
            angle: 145; middleStop: 0.5
            lightOffset: Qt.point(-3, -3); lightBlur: 9; lightColor: "#66345b85"
            topColor: "#193959"; middleColor: "#112a43"; bottomColor: "#091a2d"; rimColor: "#3a5684b8"
            ConnectionIcon { anchors.centerIn: parent; width: 22; height: 22; name: "plug" }
        }
    }
        Loader {
            active: !root.popup.homePage
            anchors.top: parent.top; anchors.right: parent.right
            anchors.topMargin: 8; anchors.rightMargin: 8
            width: 32; height: 32
            sourceComponent: CircularCloseButton {
                objectName: "managerCloseButton"
                iconObjectName: "managerCloseIcon"
                backdropItem: root.popup.closeBackdrop
                onClicked: root.requestClose()
            }
        }

    RowLayout {
        id: mainContent
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: statusPanel.top
        anchors.leftMargin: 26 - 11 * root.helpProgress; anchors.rightMargin: 26 - 11 * root.helpProgress
        anchors.topMargin: 93 - 10 * root.helpProgress; anchors.bottomMargin: 16
        spacing: 22 - 10 * root.helpProgress
        ColumnLayout {
            objectName: "managerSidebar"
            Layout.preferredWidth: root.sidebarWidth
            Layout.maximumWidth: root.sidebarWidth; Layout.alignment: Qt.AlignTop
            spacing: 14 - 4 * root.helpProgress
            ConnectionSurface {
                id: spotlightPanel
                objectName: "managerSpotlight"
                Layout.fillWidth: true; Layout.preferredHeight: 204 - 34 * root.helpProgress + 36 * root.testingLayout
                Layout.minimumHeight: Layout.preferredHeight
                radius: 19; sunken: true; depth: 7; blur: 16
                shadowColor: "#aa03101e"; lightColor: "#45345b85"
                lightOffset: Qt.point(-6, -6); lightBlur: 13
                crispOutline: true
                Item {
                    id: spotlightContent
                    objectName: "managerSpotlightContent"
                    anchors.fill: parent
                ConnectionTestHalo {
                    objectName: "managerTestHalo"
                    anchors.horizontalCenter: parent.horizontalCenter; y: 20 - 6 * root.helpProgress
                    width: idleFaceSize + 36 * root.testingLayout; height: width
                    idleFaceSize: 82 - 27 * root.helpProgress
                    idleIconSize: 31 - 7 * root.helpProgress
                    testing: root.manager.testing
                }
                Text {
                    id: spotlightName
                    objectName: "managerSpotlightName"
                    x: 12; y: 112 - 28 * root.helpProgress + 36 * root.testingLayout; width: parent.width - 24
                    text: root.empty ? "No connections yet" : root.manager.editing ?
                        (nameField.text.trim() || "New connection") : root.manager.editor.name || "No connection"
                    textFormat: Text.PlainText
                    elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter
                    color: "#e0f2ff"; font.family: ConnectionTheme.heading; font.pixelSize: 15; font.weight: Font.ExtraBold
                }
                Text {
                    anchors.top: spotlightName.bottom; anchors.topMargin: 5; anchors.horizontalCenter: parent.horizontalCenter
                    text: root.empty ? "Add a connection to get started" : root.addingConnection ?
                        "Unsaved profile" : root.selectedIsActive ? "Currently active connection" : "Saved authentication profile"
                    color: ConnectionTheme.muted; font.family: ConnectionTheme.body; font.pixelSize: 11
                }
                Rectangle {
                    visible: !root.empty
                    anchors.horizontalCenter: parent.horizontalCenter; y: 164 - 34 * root.helpProgress + 36 * root.testingLayout
                    width: methodChip.width + 20; height: 26; radius: 7
                    color: "#0d233c"; border.color: ConnectionTheme.border
                    Row {
                        id: methodChip
                        anchors.centerIn: parent; spacing: 6
                        ConnectionIcon { width: 14; height: 14; name: "lock" }
                        Text { text: methodBox.currentText; color: ConnectionTheme.muted; font.family: ConnectionTheme.body; font.pixelSize: 10 }
                    }
                }
                }
            }
            Row {
                objectName: "managerProfilesHeading"
                spacing: 6
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "MY CONNECTIONS  " + String(root.manager.profiles.length).padStart(2, "0")
                    color: ConnectionTheme.muted; font.family: ConnectionTheme.mono; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.1
                }
                ConnectionHelpButton {
                    id: profilesInfoButton
                    objectName: "managerProfilesInfoButton"
                    text: "About saved connections"; expanded: root.helpTopic === "profiles"
                    enabled: root.unrelatedControlsEnabled && !expanded
                    opacity: !root.manager.testing && !root.manager.editing && !expanded ? 1 : 0.4
                    onClicked: root.toggleHelp("profiles", profilesInfoButton)
                }
            }
            Item {
                objectName: "managerProfilesViewport"
                // Vertical shadow padding must fit inside the adjacent gaps;
                // scrolling rows are clipped before reaching the heading/actions.
                readonly property real shadowPaddingY: (14 - 4 * root.helpProgress) / 2
                readonly property real availableHeight: Math.max(39,
                    mainContent.height - spotlightPanel.height - addButton.implicitHeight - 21 -
                    (14 - 4 * root.helpProgress) * 3)
                Layout.fillWidth: true
                // Reserve space for the growing halo and device-code footer;
                // show complete rows rather than clipped button fragments.
                Layout.preferredHeight: Math.max(39,
                    Math.floor((Math.min(108, profileList.contentHeight, availableHeight) + 8) / 47) * 47 - 8)
                Layout.maximumHeight: Layout.preferredHeight
                Layout.minimumHeight: 39
                ListView {
                    id: profileList
                    objectName: "managerProfileSelector"
                    anchors.fill: parent
                    anchors.leftMargin: -16; anchors.rightMargin: -16
                    anchors.topMargin: -parent.shadowPaddingY; anchors.bottomMargin: -parent.shadowPaddingY
                    topMargin: parent.shadowPaddingY; bottomMargin: parent.shadowPaddingY
                    leftMargin: 16; rightMargin: 16
                    clip: true; spacing: 8
                    model: root.manager.profiles
                    currentIndex: root.manager.profiles.findIndex(profile => profile.id === root.manager.selectedId)
                    // Align rows, not their outside shadow padding, when the halo
                    // changes the available height during a connection test.
                    onCurrentIndexChanged: if (currentIndex >= 0) positionViewAtIndex(currentIndex, ListView.Beginning)
                    onHeightChanged: if (currentIndex >= 0) positionViewAtIndex(currentIndex, ListView.Beginning)
                    enabled: !root.manager.editing && !root.manager.testing && !root.contentTransitionBusy
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {
                        policy: profileList.contentHeight > profileList.height - profileList.topMargin - profileList.bottomMargin ?
                            ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                    }
                    delegate: Button {
                        id: profilePick
                        required property var modelData
                        required property int index
                        readonly property bool selected: modelData.id === root.manager.selectedId && !root.addingConnection
                        objectName: "managerProfile_" + index
                        width: profileList.width - 32; height: 39
                        padding: 12; hoverEnabled: enabled
                        focusPolicy: enabled ? Qt.StrongFocus : Qt.NoFocus
                        Accessible.name: modelData.name
                        Accessible.checked: selected
                        onActiveFocusChanged: if (activeFocus) profileList.positionViewAtIndex(index, ListView.Beginning)
                        opacity: !root.manager.editing && !root.manager.testing ? 1 : 0.45
                        HoverHandler { enabled: profilePick.enabled; cursorShape: Qt.PointingHandCursor }
                        background: ConnectionSurface {
                            radius: 11; sunken: profilePick.selected; recessedFill: profilePick.selected
                            depth: 4; blur: 8
                            lightOffset: Qt.point(-3, -3); lightBlur: profilePick.selected ? 8 : 7
                            lightColor: profilePick.selected ? "#77345b85" : "#55345b85"
                            borderColor: profilePick.enabled && profilePick.visualFocus ? "#38a8ff" : profilePick.selected ? "#5684b8" : "#345b85"
                            borderWidth: profilePick.enabled && profilePick.visualFocus ? 2 : 1
                            rimColor: profilePick.enabled && profilePick.hovered ? "#335684b8" : "transparent"
                        }
                        contentItem: Item {
                            Text {
                                anchors.left: parent.left; anchors.right: stateIcon.left; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                                text: profilePick.modelData.name; color: ConnectionTheme.text; elide: Text.ElideRight
                                textFormat: Text.PlainText
                                font.family: ConnectionTheme.heading; font.pixelSize: 11; font.weight: Font.ExtraBold
                            }
                            ConnectionIcon {
                                id: stateIcon
                                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                width: 14; height: 14; name: profilePick.modelData.id === root.appController.currentProfileId ? "checkProfile" : "chevron"
                            }
                        }
                        onClicked: if (modelData.id !== root.manager.selectedId)
                            root.changeContent(() => root.manager.selectConnection(modelData.id), null)
                        Keys.onReturnPressed: if (enabled) clicked()
                    }
                }
            }
            ConnectionButton {
                id: addButton
                objectName: "managerAddButton"
                Layout.fillWidth: true
                text: "Add a connection"
                symbol: "add"
                font.pixelSize: 11
                // Sidebar Add button: adjust this artwork independently.
                iconSource: Qt.resolvedUrl("../../../assets/icons/svg/plugs/connections/x-disconnected-wall-socket-plug-short-cord-25-thick.svg")                
                iconSize: ConnectionTheme.plugButtonIconSize + 4 // Reserved layout space
                iconVisualSize: 32 // Artwork size
                iconOffsetX: -11
                iconOffsetY: 7


                iconTextSpacing: 0 // Layout gap before text
                
                selected: root.addingConnection
                enabled: !root.manager.testing && !root.manager.editing && !root.contentTransitionBusy
                visualEnabled: !root.manager.testing && !root.manager.editing
                fadeDisabledState: false
                onClicked: root.beginConnection()
            }
        }
        ConnectionSurface {
            objectName: "managerDetailsPanel"
            Layout.fillWidth: true; Layout.fillHeight: true
            radius: 18; sunken: true; depth: 7; blur: 15; shadowColor: "#ab03101e"; lightColor: "#70345b85"
            lightOffset: Qt.point(-5, -5); lightBlur: 12
            crispOutline: true
            Item {
                id: detailsAnimationViewport
                objectName: "managerDetailsAnimationViewport"
                anchors.fill: parent
                clip: true
            Item {
                id: detailsContent
                objectName: "managerDetailsContent"
                anchors.fill: parent
                // Leave the separate status panel enabled for Cancel/Copy/Sign-in.
                enabled: !root.manager.testing && !root.contentTransitionBusy
            Column {
                id: emptyState
                objectName: "managerEmptyState"
                opacity: emptyChange.incomingOpacity
                transform: Translate { y: emptyChange.incomingOffset }
                visible: root.empty
                anchors.centerIn: parent
                width: parent.width - 48
                spacing: 14
                Text {
                    width: parent.width
                    text: "No connections yet"
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    color: ConnectionTheme.text
                    font.family: ConnectionTheme.heading; font.pixelSize: 18; font.weight: Font.ExtraBold
                }
                Text {
                    width: parent.width
                    text: "Add a connection to save your authentication settings and test them."
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    color: ConnectionTheme.muted
                    font.family: ConnectionTheme.body; font.pixelSize: 12
                }
                ConnectionButton {
                    id: emptyAddButton
                    objectName: "managerEmptyAddButton"
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Add a connection"
                    symbol: "add"
                    variant: "primary"
                    visualEnabled: !root.manager.editing && !root.manager.testing
                    fadeDisabledState: false
                    // Empty-state Add button: its own artwork and positioning.
                    iconSource: Qt.resolvedUrl("../../../assets/icons/svg/plugs/connections/x-disconnected-wall-socket-plug-short-cord-25-thick.svg")
                    iconSize: ConnectionTheme.plugButtonIconSize + 4 // Reserved layout space
                    iconVisualSize: 32 // Artwork size
                    iconOffsetX: -8
                    iconOffsetY: 7
                    iconTextSpacing: 0 // Layout gap before text

                    width: 220
                    height: 40
                    font.pixelSize: 13                    
                                     
                    onClicked: root.beginConnection()
                }
            }
            ScrollView {
                id: detailsScroll
                objectName: "managerDetailsScroll"
                visible: !root.empty
                anchors.fill: parent
                contentWidth: availableWidth
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            // ScrollView's implicit Flickable clips even when ScrollView.clip
            // is false. Put the inset on the content, not the viewport, so the
            // buttons' rounded shadows can fade into the surrounding card.
            Flickable {
                id: detailsViewport
                objectName: "managerDetailsViewport"
                anchors.fill: parent
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.VerticalFlick
                readonly property real sideInset: 20 - 7 * root.helpProgress
                readonly property real topInset: 19 - 5 * root.helpProgress
                readonly property real bottomInset: 15 - 2 * root.helpProgress
                contentWidth: width
                contentHeight: detailsColumn.height + topInset + bottomInset
            ColumnLayout {
                id: detailsColumn
                x: detailsViewport.sideInset; y: detailsViewport.topInset
                width: detailsViewport.width - detailsViewport.sideInset * 2
                height: Math.max(implicitHeight, detailsViewport.height - detailsViewport.topInset - detailsViewport.bottomInset)
                spacing: 0
                GridLayout {
                    Layout.fillWidth: true; Layout.bottomMargin: 15
                    columns: root.compactDetails ? 1 : 2; columnSpacing: 6; rowSpacing: 8
                    Column {
                        Layout.fillWidth: true; Layout.preferredHeight: 39; spacing: 2
                        Text { objectName: "managerProfileHeading"; text: "AUTHENTICATION PROFILE"; color: ConnectionTheme.muted; font.family: ConnectionTheme.mono; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                        Text {
                            id: detailsTitle
                            objectName: "managerDetailsTitle"
                            opacity: titleChange.incomingOpacity
                            transform: Translate { y: titleChange.incomingOffset }
                            text: root.addingConnection ? "New connection" : root.manager.editing ? "Edit connection" : "Connection details"
                            color: ConnectionTheme.text; font.family: ConnectionTheme.heading; font.pixelSize: 16; font.weight: Font.ExtraBold
                        }
                    }
                    RowLayout {
                    Layout.alignment: root.compactDetails ? Qt.AlignLeft : Qt.AlignRight
                    spacing: 6
                    Item {
                        Layout.preferredWidth: testButton.implicitWidth
                        Layout.preferredHeight: testButton.implicitHeight
                    Item {
                        id: testButtonRegion
                        objectName: "managerTestButtonRegion"
                        anchors.fill: parent
                    ConnectionButton {
                        id: testButton
                        objectName: "managerTestButton"
                        anchors.fill: parent
                        text: root.manager.testing ? "Testing…" : "Test connection"
                        symbol: root.manager.testing ? "refresh" :
                                root.manager.testResult === "passed" ? "testPassed" :
                                root.manager.testResult === "failed" ? "testFailed" : "bolt"
                        variant: "secondary"
                        Accessible.description: root.manager.testing ? "Connection test running" :
                            root.manager.testResult === "passed" ? "Last test passed for these saved credentials. You can test again." :
                            root.manager.testResult === "failed" ? "Last test failed for these saved credentials. You can test again." :
                            "These saved credentials have not been tested yet."
                        enabled: root.canAct
                        visualEnabled: root.canAct
                        fadeDisabledState: false; hoverLiftEnabled: false
                        badgeTransitionOpacity: badgeChange.incomingOpacity
                        badgeTransitionOffset: badgeChange.incomingOffset
                        onClicked: root.manager.testSelected()
                    }
                    }
                    }
                    ConnectionHelpButton {
                        id: testInfoButton
                        objectName: "managerTestInfoButton"
                        text: "About testing connections"; expanded: root.helpTopic === "test"
                        enabled: root.unrelatedControlsEnabled && !expanded
                        opacity: root.contentTransitionBusy ?
                            (!root.manager.testing && !root.manager.editing && !expanded ? 1 : 0.4) : enabled ? 1 : 0.4
                        onClicked: root.toggleHelp("test", testInfoButton)
                    }
                    }
                }
                GridLayout {
                    Layout.fillWidth: true
                    uniformCellWidths: true
                    columns: root.compactDetails ? 1 : 2
                    columnSpacing: 12; rowSpacing: 14 - 4 * root.helpProgress
                    ConnectionField {
                        id: nameField
                        transitionBusy: root.contentTransitionBusy && !root.manager.testing && root.enabled
                        transitionOpacity: nameText.incomingOpacity
                        transitionOffset: nameText.incomingOffset
                        presenceOpacity: namePresence.incomingOpacity
                        presenceOffset: namePresence.incomingOffset
                        objectName: "managerNameField"; Layout.fillWidth: true
                        label: "Connection name"; readOnly: !root.manager.editing || root.manager.testing
                        validationFeedbackEnabled: root.manager.editing
                        validationError: root.manager.editing && validationTouched ? root.draftValidation.name || "" : ""
                        helpTopic: "name"; helpExpanded: root.helpTopic === helpTopic
                        onHelpRequested: trigger => root.toggleHelp(helpTopic, trigger)
                        onEdited: root.markDraftEdited()
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 6
                        Row {
                            objectName: "managerAuthenticationLabelRow"
                            spacing: 6
                            Text { anchors.verticalCenter: parent.verticalCenter; text: "Authentication method"; color: "#c1d5ec"; font.family: ConnectionTheme.body; font.pixelSize: 11; font.weight: Font.ExtraBold }
                            ConnectionHelpButton {
                                id: authenticationInfoButton
                                objectName: "managerAuthenticationInfoButton"
                                text: "About authentication methods"; expanded: root.helpTopic === "auth"
                                opacity: root.contentTransitionBusy && !root.manager.testing ?
                                    (expanded ? 0.4 : 1) : enabled ? 1 : 0.4
                                onClicked: root.toggleHelp("auth", authenticationInfoButton)
                            }
                        }
                        Item {
                            Layout.fillWidth: true; Layout.preferredHeight: 37
                        Item {
                            id: methodRegion
                            objectName: "managerMethodRegion"
                            anchors.fill: parent
                            opacity: methodPresence.incomingOpacity
                            transform: Translate { y: methodPresence.incomingOffset }
                        ConnectionCombo {
                            id: methodBox
                            objectName: "managerMethodSelector"; anchors.fill: parent
                            model: ["Interactive", "Device code", "Client credentials"]
                            enabled: root.manager.editing && !root.manager.testing
                            visualEnabled: root.manager.editing && !root.manager.testing
                            transitionOpacity: methodText.incomingOpacity
                            transitionOffset: methodText.incomingOffset
                            onActivated: root.markDraftEdited()
                            onCurrentIndexChanged: if (currentIndex !== 2 && root.helpTopic === "secret") root.closeHelp()
                        Text {
                            objectName: "managerMethodValidationError"
                            anchors.left: parent.left; anchors.right: parent.right
                            y: parent.height
                            height: 10
                            visible: root.manager.editing
                            text: root.draftValidation.method || ""
                            color: "#ff889e"; font.family: ConnectionTheme.body; font.pixelSize: 9
                            elide: Text.ElideRight
                        }
                        }
                        }
                        }
                    }
                    ConnectionField {
                        id: tenantField
                        transitionBusy: root.contentTransitionBusy && !root.manager.testing && root.enabled
                        transitionOpacity: tenantText.incomingOpacity
                        transitionOffset: tenantText.incomingOffset
                        presenceOpacity: tenantPresence.incomingOpacity
                        presenceOffset: tenantPresence.incomingOffset
                        objectName: "managerTenantField"; Layout.fillWidth: true
                        label: "Tenant ID / Directory ID"; readOnly: !root.manager.editing || root.manager.testing
                        validationFeedbackEnabled: root.manager.editing
                        validationError: root.manager.editing && validationTouched ? root.draftValidation.tenant || "" : ""
                        helpTopic: "tenant"; helpExpanded: root.helpTopic === helpTopic
                        onHelpRequested: trigger => root.toggleHelp(helpTopic, trigger)
                        infoDescription: "Tenant ID is also known as Directory ID. Microsoft Entra labels it Directory (tenant) ID. It identifies the directory used for sign-in; a verified tenant domain can also be used."
                        infoGuidance: "Use the value from your Microsoft Entra app registration: App registrations → your app → Overview → Directory (tenant) ID. For supported interactive or device-code apps, common, organizations, or consumers selects the sign-in audience. Client credentials requires a specific tenant."
                        onEdited: root.markDraftEdited()
                    }
                    ConnectionField {
                        id: clientField
                        transitionBusy: root.contentTransitionBusy && !root.manager.testing && root.enabled
                        transitionOpacity: clientText.incomingOpacity
                        transitionOffset: clientText.incomingOffset
                        presenceOpacity: clientPresence.incomingOpacity
                        presenceOffset: clientPresence.incomingOffset
                        objectName: "managerClientField"; Layout.fillWidth: true
                        label: "Client ID / Application ID"; readOnly: !root.manager.editing || root.manager.testing
                        validationFeedbackEnabled: root.manager.editing
                        validationError: root.manager.editing && validationTouched ? root.draftValidation.client || "" : ""
                        helpTopic: "client"; helpExpanded: root.helpTopic === helpTopic
                        onHelpRequested: trigger => root.toggleHelp(helpTopic, trigger)
                        infoDescription: "Client ID is also known as Application ID (App ID). Microsoft Entra labels it Application (client) ID. It uniquely identifies your app registration, not its display name or Object ID."
                        infoGuidance: "Use the value from your Microsoft Entra app registration: App registrations → your app → Overview → Application (client) ID. Use the Application ID, not the Object ID."
                        onEdited: root.markDraftEdited()
                    }
                    ConnectionField {
                        id: secretField
                        transitionBusy: root.contentTransitionBusy && !root.manager.testing && root.enabled
                        transitionOpacity: secretText.incomingOpacity
                        transitionOffset: secretText.incomingOffset
                        presenceOpacity: secretPresence.incomingOpacity
                        presenceOffset: secretPresence.incomingOffset
                        objectName: "managerSecretField"; Layout.fillWidth: true
                        Layout.columnSpan: root.compactDetails ? 1 : 2
                        label: "Client secret value"; password: true
                        validationFeedbackEnabled: root.manager.editing
                        validationError: root.manager.editing && validationTouched ? root.draftValidation.secret || "" : ""
                        helpTopic: "secret"; helpExpanded: root.helpTopic === helpTopic
                        onHelpRequested: trigger => root.toggleHelp(helpTopic, trigger)
                        visible: methodBox.currentIndex === 2
                        readOnly: !root.manager.editing || root.manager.testing
                        placeholderText: root.manager.editing ?
                            (root.manager.editor.hasSecret ? "Leave blank to keep existing secret" : "Enter your client secret value") :
                            (root.manager.editor.hasSecret ? "Stored securely (value hidden)" : "No client secret saved")
                        infoDescription: "A client secret is an application password, not your Microsoft account password. Use its Value, not its Secret ID. Only client credentials sign-in needs it."
                        infoGuidance: "Create it in your Microsoft Entra app registration under Certificates & secrets → Client secrets. Copy the Value when created; it cannot be viewed again."
                        infoStorageNote: "Secrets stay in the operating-system credential manager. Leave blank to keep the saved secret for the same Client ID."
                        onEdited: root.markDraftEdited()
                    }
                }
                Text {
                    objectName: "managerFieldGuidance"
                    Layout.fillWidth: true; Layout.topMargin: 10
                    text: root.addingConnection ? "Enter your Entra app registration values. Testing can be done after saving." :
                          root.manager.editing ? "Save your changes securely. Leave the secret blank to retain it for the same Client ID." :
                          methodBox.currentIndex === 2 ? (root.manager.editor.hasSecret ? "A client secret is stored securely. Choose Edit to replace it." : "No client secret is stored. Choose Edit to add one before testing.") :
                          "Saved identifiers are shown for reference. Choose Edit to make changes."
                    color: ConnectionTheme.muted; font.family: ConnectionTheme.body; font.pixelSize: 11; lineHeight: 1.5; wrapMode: Text.Wrap
                }
                Item { Layout.fillHeight: true; Layout.minimumHeight: 11 }
                Item {
                    Layout.fillWidth: true; Layout.preferredHeight: detailActions.implicitHeight
                Flow {
                    id: detailActions
                    objectName: "managerDetailActions"
                    width: parent.width; spacing: 8
                    ConnectionButton {
                        id: editButton
                        objectName: "managerEditButton"
                        visible: !root.manager.editing; text: "Edit"; symbol: "edit"; variant: "secondary"
                        selected: root.manager.editing && !root.addingConnection
                        enabled: root.canAct
                        visualEnabled: root.canAct; fadeDisabledState: false
                        transitionBusy: root.contentTransitionBusy
                        transitionOpacity: editChange.incomingOpacity
                        transitionOffset: editChange.incomingOffset
                        onClicked: root.changeContent(() => root.manager.beginEdit(), true, false, true)
                    }
                    ConnectionButton {
                        id: removeButton
                        objectName: "managerRemoveButton"
                        iconSize: 16
                        iconVisualSize: 16
                        visible: !root.manager.editing; text: "Remove"; symbol: "trash"; variant: "danger"
                        enabled: root.canAct
                        visualEnabled: root.canAct; fadeDisabledState: false
                        transitionBusy: root.contentTransitionBusy
                        transitionOpacity: removeChange.incomingOpacity
                        transitionOffset: removeChange.incomingOffset
                        onClicked: removeDialog.open()
                    }
                    ConnectionButton {
                        id: useButton
                        objectName: "managerUseButton"
                        // Reserve the longer caption so its outgoing text never
                        // spills past a shrinking surface. Keep the shared check
                        // icon in the same slot while only the wording changes.
                        alignLeft: true
                        implicitWidth: Math.max(Math.ceil(activeCaptionMetrics.advanceWidth),
                            Math.ceil(useCaptionMetrics.advanceWidth)) + iconSize + iconTextSpacing + 28
                        TextMetrics { id: activeCaptionMetrics; font: useButton.font; text: "Active connection" }
                        // TextMetrics { id: useCaptionMetrics; font: useButton.font; text: "Set as active" }
                        TextMetrics { id: useCaptionMetrics; font: useButton.font; text: "Activate connection" }                        
                        visible: !root.manager.editing
                        // text: root.selectedIsActive ? "Active connection" : "Set as active"; symbol: "checkActive"; variant: "good"
                        text: root.selectedIsActive ? "Active connection" : "Activate connection"; symbol: "checkActive"; variant: "good"                        
                        enabled: root.canAct && !root.selectedIsActive
                        visualEnabled: root.canAct && !root.selectedIsActive; fadeDisabledState: false
                        transitionBusy: root.contentTransitionBusy
                        transitionOpacity: useChange.incomingOpacity
                        transitionOffset: useChange.incomingOffset
                        labelTransitionOpacity: useLabelChange.incomingOpacity
                        labelTransitionOffset: useLabelChange.incomingOffset
                        onClicked: useDialog.open()
                    }
                    ConnectionButton {
                        id: cancelButton
                        objectName: "managerCancelButton"
                        visualEnabled: !root.manager.testing; fadeDisabledState: false
                        transitionBusy: root.contentTransitionBusy
                        transitionOpacity: cancelChange.incomingOpacity
                        transitionOffset: cancelChange.incomingOffset
                        visible: root.manager.editing; text: "Cancel"; variant: "warning"
                        onClicked: {
                            if (root.addingConnection)
                                root.changeContent(() => root.manager.cancelEdit(), false, true)
                            else root.guardDraft(() => root.changeContent(() => root.manager.cancelEdit(), false, true))
                        }
                    }
                    ConnectionButton {
                        id: saveButton
                        objectName: "managerSaveButton"
                        visualEnabled: root.manager.editing && !root.manager.testing && root.draftValidation.valid
                        fadeDisabledState: false
                        transitionBusy: root.contentTransitionBusy
                        transitionOpacity: saveChange.incomingOpacity
                        transitionOffset: saveChange.incomingOffset
                        visible: root.manager.editing && (root.addingConnection ||
                            (root.draftChanged && root.draftValidation.valid))
                        text: root.addingConnection ? "Create connection" : "Save changes"
                        symbol: root.addingConnection ? "create" : "save"; variant: "primary"
                        enabled: visible && root.manager.editing && !root.manager.testing && root.draftValidation.valid && !root.contentTransitionBusy
                        onClicked: if (enabled) root.changeContent(() => root.manager.saveConnection(
                            nameField.text, tenantField.text, clientField.text,
                            methodBox.currentIndex === 2 ? secretField.text : "",
                            ["interactive", "device_code", "client_credentials"][methodBox.currentIndex]), false, true)
                    }
                }
                }
            }
            }
            }
            }
            }
        }
    }
    ConnectionSurface {
        id: statusPanel
        objectName: "managerStatusPanel"
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        anchors.leftMargin: 26 - 11 * root.helpProgress; anchors.rightMargin: 26 - 11 * root.helpProgress; anchors.bottomMargin: 22
        height: Math.max(42, statusContent.implicitHeight + 20)
        radius: 12; sunken: true; recessedFill: true; depth: 3; blur: 8
        lightOffset: Qt.point(-2, -2); lightBlur: 6; lightColor: "#44345b85"
        borderColor: root.manager.statusKind === "success" ? "#77327e6e" : root.manager.statusKind === "error" ? "#77d85870" : root.manager.statusKind === "warning" ? "#77c58d47" : "#345b85"
        ColumnLayout {
            id: statusContent
            anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 13; anchors.rightMargin: 13; spacing: 8
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                ConnectionIcon {
                    id: statusIcon
                    objectName: "managerStatusIcon"
                    Layout.preferredWidth: 17; Layout.preferredHeight: 17
                    Layout.alignment: Qt.AlignVCenter
                    name: root.manager.testing ? "refresh" : root.manager.statusKind === "success" ? "checkSuccess" : root.manager.statusKind === "error" ? "alertError" : root.manager.statusKind === "warning" ? "alert" : "info"
                }
                Text {
                    objectName: "managerStatusText"
                    Layout.fillWidth: true; text: root.manager.status
                    Layout.minimumHeight: 17
                    Layout.alignment: Qt.AlignVCenter
                    verticalAlignment: Text.AlignVCenter
                    textFormat: Text.PlainText
                    color: ConnectionTheme.text; font.family: ConnectionTheme.body; font.pixelSize: 11; font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                    Accessible.role: Accessible.StaticText; Accessible.name: text
                }
            }
            GridLayout {
                visible: root.manager.testing; Layout.fillWidth: true
                columns: root.compactStatus ? 1 : 2; columnSpacing: 8; rowSpacing: 8
                Text {
                    Layout.fillWidth: true
                    text: root.manager.deviceCode ? "Sign-in code: " + root.manager.deviceCode : "Authenticating…"
                    font.family: ConnectionTheme.mono; font.pixelSize: 12; color: "#65caff"
                }
                Flow {
                Layout.fillWidth: root.compactStatus
                Layout.preferredWidth: cancelTestButton.implicitWidth +
                    (copyCodeButton.visible ? copyCodeButton.implicitWidth + spacing : 0) +
                    (openSignInButton.visible ? openSignInButton.implicitWidth + spacing : 0)
                spacing: 8
                ConnectionButton {
                    id: copyCodeButton
                    objectName: "managerCopyCodeButton"
                    visible: root.manager.deviceCode.length > 0
                    enabled: root.manager.testing && root.manager.deviceCode.length > 0
                    text: root.deviceCodeCopied ? "Copied!" : "Copy code"; symbol: root.deviceCodeCopied ? "check" : "copy"
                    Accessible.name: "Copy sign-in code"
                    onClicked: if (root.manager.copyDeviceCode()) { root.deviceCodeCopied = true; copiedCodeTimer.restart() }
                }
                ConnectionButton {
                    id: openSignInButton
                    objectName: "managerOpenSignInButton"
                    visible: root.manager.deviceCode.length > 0
                    enabled: root.manager.testing && root.manager.deviceCode.length > 0 && root.manager.deviceUrl.length > 0
                    text: "Open sign-in page"
                    symbol: "internet"
                    onClicked: Qt.openUrlExternally(root.manager.deviceUrl)
                }
                ConnectionButton {
                    id: cancelTestButton
                    objectName: "managerCancelTestButton"
                    text: "Cancel test"; variant: "warning"
                    enabled: root.manager.testing
                    onClicked: root.manager.cancelTest()
                }
                }
            }
        }
    }
    }
    Item {
        id: helpViewport
        objectName: "managerHelpViewport"
        anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom
        width: root.helpWidth * root.helpProgress
        clip: true
        visible: width > 0
        enabled: root.helpOpen && !root.manager.testing
        ConnectionHelpShelf {
            objectName: "managerHelpShelf"
            width: root.helpWidth; height: parent.height
            topicData: helpTopics.topics[root.displayedHelpTopic]
            preloadedMarkdownText: root.appController.aboutMarkdown
            legalDocuments: root.appController.legalDocuments
            legalDocumentUrls: root.appController.legalDocumentUrls
            legalTopic: ["terms", "privacy"].includes(root.displayedHelpTopic) ? root.displayedHelpTopic : ""
            markdownText: root.displayedHelpTopic === "about" ? root.appController.aboutMarkdown : ""
            onMarkdownDocumentReady: document => root.appController.formatAboutDocument(document)
            onLegalDocumentReady: (topic, document) => root.appController.prepareLegalDocument(topic, document)
            onLegalTopicRequested: topic => root.toggleHelp(topic, root.lastHelpTrigger)
            onFullDocumentRequested: topic => root.appController.openLegalDocument(topic)
            onDismissed: root.closeHelp()
        }
    }
    ConnectionConfirmDialog {
        id: discardDialog; objectName: "managerDiscardDialog"
        title: "Discard unsaved changes?"; confirmText: "Discard changes"; cancelText: "Keep editing"; destructive: true; discardAction: true
        message: "Your unsaved connection edits will be discarded. Your saved connection will stay as it is."
        onDiscarded: {
            root.popup.editorDirty = false
            const action = root.pendingAction; root.pendingAction = null
            if (action) action()
        }
        onRejected: root.pendingAction = null
    }
    ConnectionConfirmDialog {
        id: removeDialog; objectName: "managerRemoveDialog"
        title: "Remove connection?"; confirmText: "Remove profile"; cancelText: "Keep connection"; destructive: true
        message: "Remove “" + (root.manager.editor.name || "this connection") + "”? Its configuration and cache files will be archived. Shared OS-stored secrets will be kept."
        onAccepted: root.changeContent(() => root.manager.removeSelected(), false, true)
    }
    ConnectionConfirmDialog {
        id: useDialog; objectName: "managerUseDialog"
        // title: "Set as active connection?"; confirmText: "Set as active"
        title: "Set as active connection?"; confirmText: "Activate connection"        
        message: "Use this saved connection as the default for azauthlib. Its saved authentication settings will be used."
        onAccepted: root.changeContent(() => root.manager.useSelected(), null)
    }
}
