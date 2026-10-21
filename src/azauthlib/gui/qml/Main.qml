import QtQuick
import QtQuick.Controls
import QtQuick.Window
import "components"
import "theme"

ApplicationWindow {
    id: window
    objectName: "azauthlibWindow"
    required property var appController
    property bool closingAllowed: false
    property bool startupMinimumElapsed: false
    property bool startupRevealed: false
    property var startupSplash: null
    readonly property bool startupVisible: Boolean(startupSplash && startupSplash.visible)
    property string pendingStartupError: ""
    property string currentPage: "providers"
    readonly property bool onProviderHome: currentPage === "providers"
    property bool navigating: false
    property real navigationProgress: 0
    readonly property bool creationFocused: connectionsPage.creationFocused
    readonly property bool editingFocused: connectionsPage.editingFocused
    // Temporary animation locks block input, not the permanent chrome's appearance.
    readonly property bool persistentControlsEnabled: startupRevealed && !startupVisible &&
        !appController.connectionManager.editing && !appController.connectionManager.testing
    readonly property bool navigationLocked: navigating || connectionsPage.contentTransitionBusy || editingFocused ||
        appController.connectionManager.testing
    signal startupRevealRequested()

    function openConnections() {
        if (appController.selectedProviderId !== "graph") return
        navigateTo("connections")
    }
    function showProviderHome() {
        navigateTo("providers")
    }
    function navigateTo(page) {
        if (!startupRevealed || startupVisible || navigationLocked || currentPage === page) return
        if (!["providers", "connections"].includes(page)) return
        currentPage = page
        if (ConnectionTheme.reducedMotion) {
            navigationProgress = page === "connections" ? 1 : 0
            finishNavigation()
            return
        }
        navigating = true
        pageTransition.to = page === "connections" ? 1 : 0
        pageTransition.start()
    }
    function finishNavigation() {
        navigating = false
        if (onProviderHome) {
            connectionsPage.cleanup()
            providerHome.forceActiveFocus()
        } else {
            providerHome.closeAbout()
            connectionsPage.forceActiveFocus()
        }
    }
    function legalDrawerOpen(topic) {
        return window.onProviderHome ? providerHome.drawerTopic === topic : connectionsPage.drawerTopic === topic
    }
    function openLegalDrawer(topic, trigger) {
        if (navigationLocked) return
        if (!(appController.legalDocuments[topic] || "").length) return
        if (window.onProviderHome) providerHome.openTopic(topic, trigger)
        else connectionsPage.openTopic(topic, trigger)
    }

    function revealConnectionsWhenReady() {
        if (startupMinimumElapsed && providerHome.ready && (connectionsPage.opened || connectionsPage.loadFailed) &&
                !startupRevealed) {
            startupRevealed = true
            if (startupVisible) {
                startupSplash.progress = 100
                startupSplash.statusText = "Ready"
            }
            // Main stays hidden throughout the splash, including its fade-out.
            if (startupVisible) {
                startupSplash.raise()
                startupTransition.start()
            } else finishStartup()
        }
    }
    function finishStartup() {
        // Main takes over the shared taskbar group before the faded splash
        // hides, so there is no interval with neither window represented.
        window.startupRevealRequested()
        if (startupSplash) startupSplash.hide()
        providerHome.forceActiveFocus()
        if (pendingStartupError.length > 0) {
            appDialog.showDialog("Unable to load Connections", pendingStartupError, "error", false)
            pendingStartupError = ""
        } else if (providerHome.assetError.length > 0) {
            appDialog.showDialog("Home artwork unavailable", providerHome.assetError, "error", false)
        }
    }

    width: 1293
    height: 776

    // Keep native resizing, minimizing and closing, but no maximize control.
    flags: Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint |
           Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint
           


    minimumWidth: 1293
    minimumHeight: 776    
    maximumWidth: 1293
    maximumHeight: 776

    visible: false
    opacity: 0
    title: "azauthlib"
    color: "#091a2d"
    font.family: ConnectionTheme.body

    // Do not accept maximize requests from shortcuts or other window-manager paths.
    onVisibilityChanged: visibility => {
        if (visibility === Window.Maximized)
            Qt.callLater(() => window.showNormal())
    }

    Component.onCompleted: {
        Theme.darkMode = true
        // Python centers the final native frame on the splash's monitor at reveal.
        if (!startupMinimumElapsed) startupTimer.start()
    }
    onClosing: event => {
        if (!closingAllowed) {
            event.accepted = false
            connectionsPage.requestClose()
        } else {
            if (startupSplash) startupSplash.hide()
            actionSuccess.dismiss()
            connectionsPage.cleanup()
        }
    }

    Connections {
        target: window.appController
        function onDialogRequested(title, message, variant, closeAfter) {
            appDialog.showDialog(title, message, variant, closeAfter)
        }
    }

    background: Rectangle {
        id: appBackdrop
        readonly property color topColor: "#112d4d"
        readonly property color bottomColor: "#071626"
        function colorAt(y, alpha) {
            const t = Math.max(0, Math.min(1, y / window.height))
            return Qt.rgba(topColor.r + (bottomColor.r - topColor.r) * t,
                           topColor.g + (bottomColor.g - topColor.g) * t,
                           topColor.b + (bottomColor.b - topColor.b) * t, alpha)
        }
        gradient: Gradient {
            GradientStop { position: 0; color: appBackdrop.topColor }
            GradientStop { position: 1; color: appBackdrop.bottomColor }
        }
    }
    Item {
        id: pageViewport
        objectName: "pageTransitionViewport"
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        anchors.bottom: appFooter.top
        clip: true
    }
    NumberAnimation {
        id: pageTransition
        objectName: "pagePushTransition"
        target: window; property: "navigationProgress"
        duration: ConnectionTheme.pageTransitionDuration
        easing.type: Easing.InOutCubic
        onFinished: window.finishNavigation()
    }
    Connections {
        target: ConnectionTheme
        function onReducedMotionChanged() {
            if (ConnectionTheme.reducedMotion && window.navigating) {
                pageTransition.complete()
                if (window.navigating) window.finishNavigation()
            }
        }
    }
    ProviderSelectorHome {
        id: providerHome
        objectName: "providerSelectorHome"
        parent: pageViewport
        width: window.width; height: window.height
        transform: Translate { x: window.navigationProgress * pageViewport.width }
        appController: window.appController
        helpContentScale: connectionsPage.contentScale
        // Match the Connections corner in window coordinates before
        // Home's independent design-canvas scaling is applied.
        outerCornerRadius: (connectionsPage.closeBackdrop as ConnectionSurface).radius * connectionsPage.baseScale
        visible: window.onProviderHome || window.navigating
        enabled: window.onProviderHome && !window.navigating && window.startupRevealed && !window.startupVisible
        onReadyChanged: window.revealConnectionsWhenReady()
        onContinued: window.openConnections()
    }
    Image {
        objectName: "brandLogo"

        x: 24
        y: 12
        width: 205
        height: 43

        source: window.appController.logoUrl
        fillMode: Image.PreserveAspectFit
        horizontalAlignment: Image.AlignLeft
        smooth: true; mipmap: true
    }
    ConnectionButton {
        objectName: "createAppShortcutButton"
        anchors.right: mainMenuButton.visible ? mainMenuButton.left : parent.right
        anchors.rightMargin: mainMenuButton.visible ? 12 : 30
        y: 15
        text: window.appController.shortcutBusy ? "Creating shortcut…" : "Create app shortcut"
        visible: window.appController.shortcutSupported
        enabled: window.startupRevealed && !window.startupVisible &&
            !window.navigationLocked && !window.appController.shortcutBusy
        visualEnabled: window.persistentControlsEnabled && !window.appController.shortcutBusy
        fadeDisabledState: false
        onClicked: window.appController.createAppShortcut()
    }
    ConnectionButton {
        id: mainMenuButton
        objectName: "connectionsBackHomeButton"
        anchors.right: parent.right
        anchors.rightMargin: 30
        y: 15

        text: "Main Menu"
        visualEnabled: window.persistentControlsEnabled
        fadeDisabledState: false
        symbol: "menu"
        iconSize: 18
        textColor: "#ffffff"
        background: ConnectionSurface {
            objectName: "connectionsMainMenuSurface"
            sunken: mainMenuButton.interactivePress
            topColor: mainMenuButton.interactivePress ? "#126981" :
                      mainMenuButton.interactiveHover ? "#1b91ae" : "#167d9a"
            middleColor: mainMenuButton.interactivePress ? "#0e4b5d" :
                         mainMenuButton.interactiveHover ? "#177a93" : "#146c85"
            bottomColor: mainMenuButton.interactivePress ? "#0b3d4d" :
                         mainMenuButton.interactiveHover ? "#14647a" : "#125369"
            borderColor: "#56d7ef"
            borderWidth: mainMenuButton.interactiveFocus ? 2 : 1
            depth: mainMenuButton.interactiveHover ? 2 : 3
            blur: mainMenuButton.interactiveHover ? 4 : 7
            lightOffset: Qt.point(mainMenuButton.interactiveHover ? -1 : -2,
                                  mainMenuButton.interactiveHover ? -1 : -2)
            lightBlur: mainMenuButton.interactiveHover ? 4 : 6
            shadowColor: "#03101e"
            lightColor: "#5538bcd7"
            rimColor: "#30edfdff"
        }

        visible: !window.onProviderHome
        enabled: !window.navigationLocked && connectionsPage.canNavigateHome
        onClicked: connectionsPage.requestHome()
    }    
    Item {
        id: appFooter
        objectName: "appFooter"
        z: 1 // Keep legal links above the workspace's drop-shadow tail.
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        anchors.leftMargin: 25
        anchors.rightMargin: 25
        anchors.bottomMargin: 6
        height: 28
        Rectangle {
            id: footerBackdrop
            objectName: "footerBackdrop"
            // Blend the workspace shadow into the window gradient below the rounded edge.
            // This prevents footer clipping without an offscreen layer or surface changes.
            readonly property real shadowFeather: connectionsPage.anchors.bottomMargin
            z: -1
            anchors.fill: parent
            anchors.topMargin: -shadowFeather
            anchors.leftMargin: -25; anchors.rightMargin: -25; anchors.bottomMargin: -6
            gradient: Gradient {
                GradientStop {
                    position: 0
                    color: appBackdrop.colorAt(appFooter.y - footerBackdrop.shadowFeather, 0)
                }
                GradientStop {
                    position: footerBackdrop.shadowFeather * 0.5 / footerBackdrop.height
                    color: appBackdrop.colorAt(appFooter.y - footerBackdrop.shadowFeather * 0.5, 0.5)
                }
                GradientStop {
                    position: footerBackdrop.shadowFeather / footerBackdrop.height
                    color: appBackdrop.colorAt(appFooter.y, 1)
                }
                GradientStop { position: 1; color: appBackdrop.bottomColor }
            }
        }
        Row {
            objectName: "appFooterLinks"
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            spacing: 10
            enabled: window.startupRevealed && !window.startupVisible && !window.navigationLocked
            FooterLink {
                objectName: "footerTermsLink"
                visualEnabled: window.persistentControlsEnabled
                text: "Terms of Use"
                openExternally: false
                active: window.legalDrawerOpen("terms")
                enabled: !active && (window.onProviderHome ? providerHome.ready : connectionsPage.interactionEnabled)
                onClicked: window.openLegalDrawer("terms", this)
                padding: 5
                font.pixelSize: 11
                font.weight: Font.Bold
                linkColor: "#91aac5"
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "|"; color: "#6a8aab"; font.pixelSize: 12
                Accessible.ignored: true
            }
            FooterLink {
                objectName: "footerPrivacyLink"
                visualEnabled: window.persistentControlsEnabled
                text: "Privacy Policy"
                openExternally: false
                active: window.legalDrawerOpen("privacy")
                enabled: !active && (window.onProviderHome ? providerHome.ready : connectionsPage.interactionEnabled)
                onClicked: window.openLegalDrawer("privacy", this)
                padding: 5
                font.pixelSize: 11
                font.weight: Font.Bold
                linkColor: "#91aac5"
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "|"; color: "#6a8aab"; font.pixelSize: 12
                Accessible.ignored: true
            }
            FooterLink {
                objectName: "footerAboutLink"
                visualEnabled: window.persistentControlsEnabled
                text: "About azauthlib"
                padding: 5
                font.pixelSize: 11
                font.weight: Font.Bold
                linkColor: "#91aac5"
                active: window.onProviderHome ? providerHome.aboutOpen : connectionsPage.aboutOpen
                enabled: !active && (window.onProviderHome ? providerHome.ready :
                         connectionsPage.opened && connectionsPage.interactionEnabled)
                onClicked: {
                    if (window.onProviderHome) providerHome.openAbout(this)
                    else connectionsPage.openAbout(this)
                }
            }
        }
    }
    ConnectionsHomePage {
        id: connectionsPage
        // Retain this object name for the isolated connection-test launcher.
        objectName: "connectionManagerWindow"
        parent: pageViewport
        anchors.left: parent.left; anchors.right: parent.right
        anchors.top: parent.top; anchors.bottom: parent.bottom
        transform: Translate { x: (window.navigationProgress - 1) * pageViewport.width }
        // Leave visible backdrop around the raised workspace, not just a rim.
        anchors.leftMargin: 30; anchors.rightMargin: 30
        anchors.topMargin: 70; anchors.bottomMargin: 14
        appController: window.appController
        visible: !window.onProviderHome || window.navigating
        enabled: !window.onProviderHome && !window.navigating && window.startupRevealed && !window.startupVisible
        onHomeRequested: window.showProviderHome()
        onCloseRequested: {
            window.closingAllowed = true
            Qt.callLater(() => window.close())
        }
        onPreparationFailed: message => {
            window.pendingStartupError = message
            if (window.startupRevealed && !window.startupVisible) {
                appDialog.showDialog("Unable to load Connections", message, "error", false)
                window.pendingStartupError = ""
            }
        }
        onStartupProgressChanged: (progress, message) => {
            if (window.startupVisible) {
                window.startupSplash.progress = progress
                window.startupSplash.statusText = message
            }
        }
    }
    Connections {
        target: connectionsPage
        function onOpenedChanged() {
            window.revealConnectionsWhenReady()
        }
        function onLoadFailedChanged() { window.revealConnectionsWhenReady() }
    }

    // StartupSplash is created independently by the Python loader, not nested
    // beneath this hidden Window (Qt suppresses nested windows during startup).
    Timer {
        id: startupTimer
        objectName: "startupTimer"
        interval: 520; repeat: false
        onTriggered: {
            window.startupMinimumElapsed = true
            window.revealConnectionsWhenReady()
        }
    }
    NumberAnimation {
        id: startupTransition
        target: window.startupSplash || null; property: "opacity"
        to: 0; duration: 180; easing.type: Easing.OutCubic
        onFinished: window.finishStartup()
    }
    AppDialog {
        id: appDialog
        objectName: "appDialog"
        onAcknowledged: window.appController.acknowledgeDialog()
    }
    ActionSuccessOverlay {
        id: actionSuccess
        objectName: "actionSuccessOverlay"
        anchors.fill: parent
    }
    Connections {
        target: window.appController.connectionManager
        function onEditorChanged() {
            if (window.appController.connectionManager.editing) actionSuccess.dismiss()
        }
        function onActionCompleted(action) {
            if (["created", "saved", "activated", "removed"].includes(action))
                actionSuccess.play()
        }
        function onStatusChanged() {
            if (window.appController.connectionManager.statusKind === "error")
                actionSuccess.dismiss()
        }
    }
}
