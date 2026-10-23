pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "../theme"

Control {
    id: root
    required property var appController
    readonly property var manager: appController.connectionManager
    readonly property string providerId: appController.selectedProviderId
    readonly property string providerName: appController.selectedProviderName
    readonly property bool homePage: true
    property bool editorDirty: false
    property bool preparing: false
    property bool awaitingData: false
    property bool backgroundPreparation: false
    property bool publicStateOnly: false
    property real loadProgress: 0
    property string loadMessage: ""
    property bool loadFailed: false
    property bool externalModalOpen: false
    readonly property bool opened: contentLoader.status === Loader.Ready && !preparing
    readonly property bool creationFocused: manager.creatingConnection
    readonly property bool editingFocused: manager.editing
    readonly property bool contentTransitionBusy: panel ? panel.contentTransitionBusy : false
    // The controller restores/persists zoom; render live text/vectors, not a bitmap.
    readonly property int zoomPercent: appController.zoomPercent
    readonly property real baseScale: Math.max(1, Math.min(width / 970, height / 609))
    readonly property real contentScale: Math.min(baseScale, ConnectionTheme.maximumContentScale) * zoomPercent / 100
    readonly property bool interactionEnabled: enabled && visible && opened && panel && !manager.testing && !panel.zoomBlocked && !leaveTestDialog.visible && !externalModalOpen
    readonly property bool canNavigateHome: enabled && visible && !manager.testing && !editingFocused && !contentTransitionBusy && !leaveTestDialog.visible &&
        (!panel || !panel.zoomBlocked)
    readonly property bool zoomEnabled: interactionEnabled && !editingFocused && !contentTransitionBusy && !appController.zoomLocked
    readonly property ConnectionManagerContent panel: contentLoader.item as ConnectionManagerContent
    readonly property bool aboutOpen: panel && panel.helpTopic === "about"
    readonly property string drawerTopic: panel ? panel.helpTopic : ""
    readonly property Item closeBackdrop: pageSurface
    readonly property bool deviceCodeCopied: panel ? panel.deviceCodeCopied : false
    signal closeRequested()
    signal homeRequested()
    signal preparationFailed(string message)
    signal startupProgressChanged(real progress, string message)
    padding: 0

    function openAbout(trigger) {
        openTopic("about", trigger)
    }
    function openTopic(topic, trigger) {
        if (manager.testing || editingFocused || contentTransitionBusy || externalModalOpen) return
        if (opened && panel && !panel.zoomBlocked) panel.toggleHelp(topic, trigger)
    }

    function setZoomPercent(value) {
        if (manager.testing || editingFocused || appController.zoomLocked) return
        const next = Math.max(70, Math.min(125, Math.round(value)))
        if (next === zoomPercent) return
        const centerX = (zoomViewport.contentX + zoomViewport.width / 2) / contentScale
        const centerY = (zoomViewport.contentY + zoomViewport.height / 2) / contentScale
        appController.setZoomPercent(next)
        Qt.callLater(() => {
            zoomViewport.contentX = Math.max(0, Math.min(zoomViewport.contentWidth - zoomViewport.width,
                centerX * root.contentScale - zoomViewport.width / 2))
            zoomViewport.contentY = Math.max(0, Math.min(zoomViewport.contentHeight - zoomViewport.height,
                centerY * root.contentScale - zoomViewport.height / 2))
            root.ensureFocusedItemVisible()
        })
    }
    function revealItem(item) {
        if (!item) return
        let ancestor = item
        while (ancestor && ancestor !== contentLoader) ancestor = ancestor.parent
        if (!ancestor) return // Overlay dialogs/menus are outside the scroll canvas.
        // Reveal focused controls in inner details/help scrollers as well as
        // the outer zoom viewport. Mapping both corners includes live scaling.
        ancestor = item.parent
        while (ancestor && ancestor !== root) {
            const scroller = ancestor as Flickable
            if (scroller) keepItemVisible(scroller, item)
            ancestor = ancestor.parent
        }
    }
    function keepItemVisible(scroller, item) {
        const start = item.mapToItem(scroller.contentItem, 0, 0)
        const end = item.mapToItem(scroller.contentItem, item.width, item.height)
        const left = start.x; const top = start.y
        const right = end.x; const bottom = end.y
        const margin = 12
        let x = scroller.contentX
        let y = scroller.contentY
        if (right + margin > x + scroller.width) x = right + margin - scroller.width
        if (left - margin < x) x = left - margin
        if (bottom + margin > y + scroller.height) y = bottom + margin - scroller.height
        if (top - margin < y) y = top - margin
        // ListView uses negative offsets for its outside shadow padding. Zero
        // is not its start: clamping there moves rows under a mouse press and
        // can prevent the release from reaching the original button.
        const minX = scroller.originX - scroller.leftMargin
        const minY = scroller.originY - scroller.topMargin
        const maxX = Math.max(minX, scroller.originX + scroller.contentWidth + scroller.rightMargin - scroller.width)
        const maxY = Math.max(minY, scroller.originY + scroller.contentHeight + scroller.bottomMargin - scroller.height)
        scroller.contentX = Math.max(minX, Math.min(x, maxX))
        scroller.contentY = Math.max(minY, Math.min(y, maxY))
    }
    function ensureFocusedItemVisible() {
        if (root.Window.window) revealItem(root.Window.window.activeFocusItem)
    }
    Shortcut {
        objectName: "connectionsZoomInShortcut"
        sequences: ["Ctrl++", "Ctrl+=", "Ctrl+Shift++"]
        context: Qt.WindowShortcut; enabled: root.zoomEnabled
        onActivated: root.setZoomPercent(root.zoomPercent + 5)
        // Some keyboard layouts resolve shifted '+' through two aliases.
        // They have the same action, so an ambiguous alias still zooms once.
        onActivatedAmbiguously: root.setZoomPercent(root.zoomPercent + 5)
    }
    Shortcut {
        objectName: "connectionsZoomOutShortcut"
        sequence: "Ctrl+-"
        context: Qt.WindowShortcut; enabled: root.zoomEnabled
        onActivated: root.setZoomPercent(root.zoomPercent - 5)
    }
    Shortcut {
        objectName: "connectionsZoomResetShortcut"
        sequence: "Ctrl+0"
        context: Qt.WindowShortcut; enabled: root.zoomEnabled
        onActivated: root.setZoomPercent(100)
    }
    Connections {
        target: root.Window.window
        function onActiveFocusItemChanged() { Qt.callLater(root.ensureFocusedItemVisible) }
    }
    function openManager() {
        if (backgroundPreparation) {
            // Supersede a running public-only worker with the normal foreground
            // refresh; the controller generation guard rejects late results.
            backgroundPreparation = false
            preparing = true
            awaitingData = true
            appController.prepareConnections()
            return
        }
        if (preparing || (opened && !publicStateOnly)) return
        loadFailed = false
        preparing = true
        if (!appController.connectionsReady || publicStateOnly) {
            awaitingData = true
            appController.prepareConnections()
        } else {
            loadProgress = 90
            manager.prepareForOpen()
        }
    }
    function prepareInBackground() {
        if (preparing || opened || !appController.canWarmVisitedService ||
                manager.editing || manager.testing) return
        backgroundPreparation = true
        publicStateOnly = true
        preparing = true
        awaitingData = true
        loadFailed = false
        appController.prepareVisitedService()
    }
    function discardBackgroundPreparation() {
        if (!backgroundPreparation && !publicStateOnly) return
        backgroundPreparation = false
        publicStateOnly = false
        preparing = false
        awaitingData = false
        contentLoader.active = false
        loadFailed = false
        appController.discardBackgroundConnections()
    }
    function cancelPreparation() {
        if (opened) return
        backgroundPreparation = false
        awaitingData = false
        preparing = false
        contentLoader.active = false
        loadFailed = false
        loadProgress = 0
        appController.cancelConnectionPreparation()
    }
    function failPreparation() {
        const quiet = backgroundPreparation
        contentLoader.active = false
        preparing = false
        awaitingData = false
        backgroundPreparation = false
        if (!quiet) publicStateOnly = false
        loadFailed = true
        if (!quiet) preparationFailed("Check your saved connection files and secure storage, then choose Retry.")
    }
    function requestClose() {
        if (panel) panel.requestClose()
        else close()
    }
    function requestHome() {
        if (!canNavigateHome) return
        if (manager.testing) leaveTestDialog.open()
        else if (panel) panel.guardDraft(() => root.leaveToHome())
        else leaveToHome()
    }
    function leaveToHome() {
        manager.cancelTest()
        editorDirty = false
        homeRequested()
    }
    // Native window Close still exits; the separate Home action navigates back.
    function close() { closeRequested() }
    function cleanup() {
        if (panel) panel.cleanup()
        else manager.cancelTest()
    }
    // Diagnostic/eager controllers open directly; production defers content
    // loading until a service is chosen.
    Component.onCompleted: if (!appController.connectionsDeferred) openManager()
    Connections {
        target: root.appController
        function onStartupPreferencesChanged() {
            if (!root.appController.startupPreferences.warm_start)
                root.discardBackgroundPreparation()
        }
        function onProviderChanged() {
            if (root.providerId !== "graph") root.discardBackgroundPreparation()
        }
        function onConnectionPreparationChanged() {
            if (!root.preparing || !root.awaitingData) return
            root.loadProgress = root.appController.connectionLoadProgress
            root.loadMessage = root.appController.connectionLoadMessage
            if (root.appController.connectionsError.length > 0) root.failPreparation()
            else if (root.appController.connectionsReady) {
                root.awaitingData = false
                if (!root.backgroundPreparation) root.publicStateOnly = false
                root.manager.prepareForOpen()
            }
        }
    }
    ConnectionConfirmDialog {
        id: leaveTestDialog
        objectName: "connectionsLeaveTestDialog"
        title: "Leave the connection test?"
        message: "Going Home cancels the current connection test. Your saved connections will not change."
        cancelText: "Keep testing"
        confirmText: "Go Home"
        onAccepted: root.leaveToHome()
    }
    Connections {
        target: root.manager
        function onOpeningPrepared(success) {
            if (!root.preparing) return
            if (success) {
                if (root.awaitingData) return // A foreground refresh superseded public preparation.
                root.loadProgress = 94
                root.loadMessage = "Composing the render graph…"
                root.startupProgressChanged(94, root.loadMessage)
                if (contentLoader.status === Loader.Ready) {
                    root.preparing = false
                    root.backgroundPreparation = false
                } else contentLoader.active = true
            }
            else root.failPreparation()
        }
    }
    background: Item {
        ConnectionPageSurface {
            id: pageSurface
            objectName: "managerPageSurface"
            width: parent.width / root.baseScale
            height: parent.height / root.baseScale
            scale: root.baseScale; transformOrigin: Item.TopLeft
        }
    }
    contentItem: Item {
        ScrollView {
            id: zoomScroll
            objectName: "connectionsZoomScroll"
            anchors.fill: parent
            clip: true
            ScrollBar.vertical: ScrollBar {
                objectName: "connectionsZoomVerticalBar"
                parent: zoomScroll
                x: zoomScroll.width - width - 2; y: 24
                width: ConnectionTheme.scrollBarWidth
                height: zoomScroll.height - 48
                policy: zoomViewport.contentHeight > zoomViewport.height + 1 ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
            }
            ScrollBar.horizontal: ScrollBar {
                objectName: "connectionsZoomHorizontalBar"
                parent: zoomScroll
                x: 24; y: zoomScroll.height - height - 2
                height: ConnectionTheme.scrollBarWidth
                width: zoomScroll.width - 48
                policy: zoomViewport.contentWidth > zoomViewport.width + 1 ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
            }
            Flickable {
                id: zoomViewport
                objectName: "connectionsZoomViewport"
                anchors.fill: parent
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.HorizontalAndVerticalFlick
                contentWidth: Math.max(width, contentLoader.width * root.contentScale)
                contentHeight: Math.max(height, contentLoader.height * root.contentScale)
                Loader {
                    id: contentLoader
                    objectName: "connectionsZoomCanvas"
                    // Keep a usable form width (the form reflows beside help),
                    // and scroll vertically instead of crushing controls at 125%.
                    width: Math.max(780, zoomViewport.width / root.contentScale)
                    height: Math.max(609, zoomViewport.height / root.contentScale)
                    scale: root.contentScale; transformOrigin: Item.TopLeft
                    active: false; asynchronous: true
                    opacity: status === Loader.Ready ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 220; easing.type: Easing.OutCubic } }
                    onLoaded: {
                        root.loadProgress = 100
                        root.loadMessage = "Runtime context synchronized"
                        if (!root.awaitingData) {
                            root.preparing = false
                            root.backgroundPreparation = false
                        }
                    }
                    onStatusChanged: if (status === Loader.Error) root.failPreparation()
                    sourceComponent: ConnectionManagerContent {
                        objectName: "connectionsHomeContent"
                        popup: root
                        appController: root.appController
                    }
                }
            }
        }
        ColumnLayout {
            objectName: "connectionsLoadingState"
            anchors.centerIn: parent
            visible: root.preparing || root.loadFailed
            spacing: 14
            ConnectionsHaloButton {
                Layout.alignment: Qt.AlignHCenter
                enabled: false; busy: root.preparing
                Accessible.name: "Loading connections"
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: root.loadFailed ? "Connections could not be loaded." : "Loading your connections…"
                color: ConnectionTheme.muted; font.family: ConnectionTheme.body; font.pixelSize: 13
            }
            ConnectionButton {
                objectName: "connectionsRetryButton"
                Layout.alignment: Qt.AlignHCenter
                visible: root.loadFailed
                text: "Retry"; onClicked: root.openManager()
            }
        }
    }
}
