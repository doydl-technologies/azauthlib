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
    property bool loadFailed: false
    readonly property bool opened: contentLoader.status === Loader.Ready && !preparing
    readonly property bool creationFocused: manager.creatingConnection
    readonly property bool editingFocused: manager.editing
    readonly property bool contentTransitionBusy: panel ? panel.contentTransitionBusy : false
    // The controller restores/persists zoom; render live text/vectors, not a bitmap.
    readonly property int zoomPercent: appController.zoomPercent
    readonly property real baseScale: Math.max(1, Math.min(width / 970, height / 609))
    readonly property real contentScale: Math.min(baseScale, ConnectionTheme.maximumContentScale) * zoomPercent / 100
    readonly property bool interactionEnabled: enabled && visible && opened && panel && !manager.testing && !panel.zoomBlocked && !leaveTestDialog.visible
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
        if (manager.testing || editingFocused || contentTransitionBusy) return
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
        if (preparing || opened) return
        loadFailed = false
        preparing = true
        manager.prepareForOpen()
    }
    function failPreparation() {
        contentLoader.active = false
        preparing = false
        loadFailed = true
        preparationFailed("Check your saved connection files and secure storage, then choose Retry.")
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
    Component.onCompleted: openManager()
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
                root.startupProgressChanged(92, "Connection data ready; preparing the interface and About drawer…")
                contentLoader.active = true
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
                x: zoomScroll.width - width - 5; y: 24
                height: zoomScroll.height - 48
                policy: zoomViewport.contentHeight > zoomViewport.height + 1 ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
            }
            ScrollBar.horizontal: ScrollBar {
                objectName: "connectionsZoomHorizontalBar"
                parent: zoomScroll
                x: 24; y: zoomScroll.height - height - 5
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
                    Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                    onLoaded: root.preparing = false
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
