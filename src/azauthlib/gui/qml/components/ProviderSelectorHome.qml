pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.VectorImage
import "../theme"

// Reference canvas: 1534 × 960 pixels, excluding a 42-pixel title bar.
// Only the live scene is scaled: fonts, hit targets, SVGs and relief stay native.
FocusScope {
    id: root
    required property var appController
    property bool selectionHidden: false
    function selectedSpotlightSubject(mode, target) {
        for (let i = 0; i < cards.count; ++i) {
            const card = cards.itemAt(i)
            if (card && card.providerId === selectedProvider)
                return card.spotlightSubject(mode, target)
        }
        return null
    }
    readonly property real designScale: Math.min(width / 1534, height / 918)
    readonly property real designX: (width - 1534 * designScale) / 2
    readonly property real designY: (height - 918 * designScale) / 2
    // Window-space radius; compensate for this page's scaled design canvas.
    property real outerCornerRadius: 25
    readonly property string selectedProvider: appController.selectedProviderId
    readonly property bool selectedProviderAvailable: selectedProvider === "graph"
    property var loadedLogos: ({})
    property int loadedLogoCount: 0
    property int settledLogoCount: 0
    // A damaged installation should report missing artwork, not hang startup.
    readonly property bool fontsSettled: [FontLoader.Ready, FontLoader.Error].includes(ConnectionTheme.bodyLoader.status) && [FontLoader.Ready, FontLoader.Error].includes(ConnectionTheme.headingLoader.status)
    readonly property bool ready: settledLogoCount === providers.length && fontsSettled
    readonly property string assetError: settledLogoCount > loadedLogoCount ? "Some provider artwork could not be loaded. Reinstall azauthlib to restore the bundled SVG assets." : fontsSettled && (ConnectionTheme.bodyLoader.status === FontLoader.Error || ConnectionTheme.headingLoader.status === FontLoader.Error) ? "The bundled Home page fonts could not be loaded. Reinstall azauthlib to restore them." : ""
    property string drawerTopic: ""
    property string displayedDrawerTopic: "about"
    readonly property bool aboutOpen: drawerTopic === "about"
    readonly property bool drawerOpen: drawerTopic.length > 0
    // Keep the drawer's typography/dimensions at the Connections content scale.
    property real helpContentScale: 1
    readonly property real shelfScale: helpContentScale / Math.max(designScale, 0.01)
    readonly property real helpWidth: 342 * shelfScale
    property real helpProgress: drawerOpen ? 1 : 0
    Behavior on helpProgress {
        NumberAnimation {
            duration: ConnectionTheme.reducedMotion ? 0 : 520
            easing.type: Easing.OutCubic
        }
    }
    property var aboutTrigger: null
    signal continued
    readonly property var providers: [
        {
            key: "graph",
            title: "Microsoft Graph",
            size: 66,
            copy: "Access Microsoft 365, Azure AD and\nother Microsoft services via Graph API.",
            logo: "logo-microsoft-graph-symbol.svg"
        },
        {
            key: "keyvault",
            title: "Azure Key Vault",
            size: 56,
            copy: "Securely access and manage secrets,\nkeys, and certificates.",
            logo: "subscriptions.svg"
        },
        {
            key: "dataverse",
            title: "Dataverse / Dynamics 365",
            size: 75,
            copy: "Connect to Microsoft Dataverse\nand Dynamics 365 applications.",
            logo: "logo-microsoft-dataverse.svg"
        },
        {
            key: "storage",
            title: "Azure Storage",
            size: 65,
            copy: "Access blobs, files, queues, and tables\nin Azure Storage.",
            logo: "storage-accounts.svg"
        },
        {
            key: "sql",
            title: "Azure SQL",
            size: 72,
            copy: "Connect to Azure SQL Database\nand manage your data.",
            logo: "sql-database.svg"
        },
        {
            key: "exchange",
            title: "Exchange Online",
            size: 74,
            copy: "Access Exchange Online mailboxes,\ncalendars, and other data.",
            logo: "logo-microsoft-exchange.svg"
        }
    ]

    function recordLogo(key, success) {
        if (!loadedLogos[key]) {
            loadedLogos[key] = true;
            if (success)
                loadedLogoCount += 1;
            settledLogoCount += 1;
        }
    }
    function toggleProvider(key) {
        appController.setSelectedProvider(selectedProvider === key ? "" : key);
    }
    function moveSelection(index, delta) {
        const next = (index + delta + providers.length) % providers.length;
        appController.setSelectedProvider(providers[next].key);
        cards.itemAt(next).forceActiveFocus(Qt.TabFocusReason);
        revealProvider(next);
    }
    function openAbout(trigger) {
        openTopic("about", trigger);
    }
    function openTopic(topic, trigger) {
        if (!helpTopics.topics[topic]) return;
        aboutTrigger = trigger;
        displayedDrawerTopic = topic;
        drawerTopic = topic;
        Qt.callLater(() => aboutShelf.forceActiveFocus());
    }
    function closeAbout() {
        if (!drawerOpen)
            return;
        drawerTopic = "";
        if (aboutTrigger && aboutTrigger.visible && aboutTrigger.enabled)
            aboutTrigger.forceActiveFocus();
    }
    function revealProvider(index) {
        Qt.callLater(() => {
            const card = cards.itemAt(index);
            if (!card)
                return;
            const top = grid.y + card.y * grid.scale - 24;
            const bottom = top + card.height * grid.scale + 48;
            let next = providerScroll.contentY;
            if (top < next)
                next = top;
            if (bottom > next + providerScroll.height)
                next = bottom - providerScroll.height;
            providerScroll.contentY = Math.max(0, Math.min(next, Math.max(0, providerScroll.contentHeight - providerScroll.height)));
        });
    }
    Shortcut {
        sequence: "Escape"
        enabled: root.visible && root.enabled && root.drawerOpen
        onActivated: root.closeAbout()
    }
    ConnectionHelpTopics {
        id: helpTopics
    }
    Connections {
        target: AccentTheme
        function onShowInfoButtonsChanged() {
            if (!AccentTheme.showInfoButtons && root.drawerTopic === "shortcut") root.closeAbout()
        }
    }
    Connections {
        target: root.appController
        function onLegalDocumentsChanged() {
            if (["terms", "privacy"].includes(root.drawerTopic) &&
                    !(root.appController.legalDocuments[root.drawerTopic] || "").length)
                root.closeAbout();
        }
    }

    // Keep the shared Connections backdrop visible behind this page.
    Item {
        x: root.designX
        y: root.designY
        width: 1534
        height: 918
        scale: root.designScale
        transformOrigin: Item.TopLeft
        ConnectionPageSurface {
            id: panel
            objectName: "providerMainPanel"
            x: 36
            y: 82
            width: 1462
            height: 778
            radius: root.outerCornerRadius / Math.max(root.designScale, 0.01)
            Item {
                id: workspace
                objectName: "providerWorkspace"
                visible: !root.selectionHidden
                width: parent.width - root.helpWidth * root.helpProgress
                height: parent.height
                Text {
                    objectName: "providerHomeTitle"
                    x: 36
                    y: 32
                    width: parent.width - 72
                    height: 36.96
                    text: "Choose a Microsoft service"
                    color: "#f1f6ff"
                    font.family: ConnectionTheme.heading
                    font.pixelSize: 28
                    font.weight: Font.ExtraBold
                    font.letterSpacing: -0.95
                    lineHeightMode: Text.FixedHeight
                    lineHeight: 36.96
                    style: Text.Raised
                    styleColor: "#1a000000"
                }
                Text {
                    x: 36
                    y: 76.96
                    width: parent.width - 72
                    text: "Select the Microsoft service you want to configure a connection for."
                    color: AccentTheme.color("#9fbddd")
                    font.family: ConnectionTheme.body
                    font.pixelSize: 16
                }
                Flickable {
                    id: providerScroll
                    objectName: "providerCardsViewport"
                    x: 10
                    y: 102.953125
                    width: parent.width - 20
                    height: 561.046875
                    contentWidth: width
                    contentHeight: height
                    interactive: false
                    // Allow card glows outside the grid when no scrolling is required.
                    clip: root.helpProgress > 0
                    boundsBehavior: Flickable.StopAtBounds
                    flickableDirection: Flickable.VerticalFlick
                    onContentHeightChanged: if (contentHeight <= height)
                        contentY = 0
                    Grid {
                        id: grid
                        objectName: "providerGrid"
                        x: 24
                        y: (providerScroll.height - height * scale) / 2
                        // Scale live cards, text, vectors, and high-resolution
                        // logos together, not a captured/rasterized grid layer.
                        width: 1394
                        scale: Math.min(1, Math.max(0.01, (providerScroll.width - 48) / width))
                        transformOrigin: Item.TopLeft
                        columns: 3
                        readonly property int rowCount: Math.ceil(root.providers.length / columns)
                        height: rowCount * 243.5234375 + (rowCount - 1) * 26
                        columnSpacing: 26
                        rowSpacing: 26
                        Repeater {
                            id: cards
                            model: root.providers
                            ProviderCard {
                                required property var modelData
                                required property int index
                                objectName: "providerCard_" + providerId
                                width: (grid.width - (grid.columns - 1) * 26) / grid.columns
                                height: 243.5234375
                                providerId: modelData.key
                                providerName: modelData.title
                                summary: modelData.copy
                                logoSize: modelData.size
                                // The image provider resolves each filename to its package-relative directory.
                                logoSource: modelData.logo
                                selected: root.selectedProvider === providerId
                                onClicked: root.toggleProvider(providerId)
                                onActiveFocusChanged: if (activeFocus)
                                    root.revealProvider(index)
                                onLogoSettled: (key, success) => root.recordLogo(key, success)
                                Keys.onRightPressed: root.moveSelection(index, 1)
                                Keys.onLeftPressed: root.moveSelection(index, -1)
                                Keys.onDownPressed: root.moveSelection(index, grid.columns)
                                Keys.onUpPressed: root.moveSelection(index, -grid.columns)
                            }
                        }
                    }
                }
                Row {
                    objectName: "providerShortcutControls"
                    x: 36
                    y: parent.height - 28 - height
                    height: 80
                    spacing: 8
                    visible: root.appController.shortcutSupported
                    Button {
                        id: shortcutButton
                        objectName: "createAppShortcutButton"
                        // Qt reports macOS as "osx". Leave the original SVGs
                        // untouched and select each platform's complete set.
                        property string platformName: Qt.platform.os
                        readonly property string artworkPrefix: platformName === "osx"
                            ? "Monocolor-Filled-Blue-Pink-shortcuts-ios"
                            : platformName === "linux"
                                ? "Monocolor-Filled-Purple-shortcuts-linux"
                                : "Monocolor-Filled-Blue-shortcuts-win"
                        property real hoverProgress: enabled && hovered ? 1 : 0
                        property int hoverInDuration: 450
                        property int hoverOutDuration: 550
                        Behavior on hoverProgress {
                            NumberAnimation {
                                duration: ConnectionTheme.reducedMotion ? 0 :
                                    (shortcutButton.enabled && shortcutButton.hovered ? shortcutButton.hoverInDuration : shortcutButton.hoverOutDuration)
                                easing.type: Easing.InOutCubic
                            }
                        }
                        property int pressDuration: 300
                        property int releaseDuration: 400
                        property bool pressVisualRequested: false
                        property real pressProgress: pressVisualRequested ? 1 : 0
                        Behavior on pressProgress {
                            NumberAnimation {
                                duration: ConnectionTheme.reducedMotion ? 0 :
                                    (shortcutButton.pressVisualRequested ? shortcutButton.pressDuration : shortcutButton.releaseDuration)
                                easing.type: Easing.InOutCubic
                            }
                        }
                        onPressProgressChanged: {
                            if (pressProgress >= 1 && pressVisualRequested && !down)
                                shortcutReleaseHold.restart()
                        }
                        onDownChanged: {
                            if (down) {
                                shortcutReleaseHold.stop()
                                pressVisualRequested = true
                            } else if (ConnectionTheme.reducedMotion) {
                                pressVisualRequested = false
                            } else if (pressProgress >= 1) {
                                // A quick tap still reaches the full sunken state
                                // before smoothly returning; no action is delayed.
                                shortcutReleaseHold.restart()
                            }
                        }
                        onVisibleChanged: if (!visible) {
                            shortcutReleaseHold.stop()
                            pressVisualRequested = false
                        }
                        Timer {
                            id: shortcutReleaseHold
                            interval: 80
                            onTriggered: if (!shortcutButton.down) shortcutButton.pressVisualRequested = false
                        }
                        Connections {
                            target: ConnectionTheme
                            function onReducedMotionChanged() {
                                if (ConnectionTheme.reducedMotion) {
                                    shortcutReleaseHold.stop()
                                    shortcutButton.pressVisualRequested = shortcutButton.down
                                }
                            }
                        }
                        // Input targets change immediately; lighting and relief
                        // interpolate independently in one premultiplied layer.
                        readonly property string displayedArtwork: down ? "sunken" :
                            enabled && hovered ? "hover" : "raised"
                        readonly property real artworkLift: ConnectionTheme.reducedMotion ? 0 :
                            -3 * hoverProgress * (1 - pressProgress)
                        containmentMask: QtObject {
                            function contains(point: point): bool {
                                // SVG face geometry, excluding transparent padding,
                                // drop shadow and outer glow. Track the moving face.
                                const dx = point.x - shortcutButton.width * 0.5
                                const cy = shortcutButton.height *
                                    (57.2 + 2.8 * shortcutButton.pressProgress) / 120 + shortcutButton.artworkLift
                                const dy = point.y - cy
                                const radius = shortcutButton.width * 45.5 / 120
                                return dx * dx + dy * dy <= radius * radius
                            }
                        }
                        width: 80
                        height: 80
                        padding: 0
                        enabled: root.enabled && !root.appController.shortcutBusy
                        opacity: root.appController.shortcutBusy ? 0.37 : 1
                        hoverEnabled: enabled
                        focusPolicy: enabled ? Qt.StrongFocus : Qt.NoFocus
                        text: root.appController.shortcutBusy ? "Creating shortcut…" : "Create app shortcut"
                        Accessible.name: text
                        Accessible.description: "Create a shortcut to launch azauthlib from your Desktop."
                        Keys.onReturnPressed: if (enabled) clicked()
                        onClicked: if (enabled) root.appController.createAppShortcut()
                        HoverHandler {
                            objectName: "providerShortcutPointer"
                            enabled: shortcutButton.enabled
                            cursorShape: Qt.PointingHandCursor
                        }
                        background: Rectangle {
                            color: "transparent"
                            radius: width / 2
                            border.width: shortcutButton.visualFocus ? 1 : 0
                            border.color: AccentTheme.color("#56d7ef")
                        }
                        contentItem: Item {
                            transform: Translate {
                                objectName: "providerShortcutHoverLift"
                                // Move only the artwork, keeping the hit target
                                // steady. Pressing smoothly settles it back down.
                                y: shortcutButton.artworkLift
                            }
                            // Original SVGs supply textures only, never stacked
                            // image items. The shader is the sole visible artwork.
                            Image {
                                id: shortcutRaisedImage
                                objectName: "providerShortcutRaisedImage"
                                anchors.fill: parent
                                visible: false
                                source: AccentTheme.customAccent ? AccentTheme.artwork(shortcutButton.artworkPrefix + "-raised.svg") : Qt.resolvedUrl("../../../assets/icons/svg/actions/relief/shortcuts/" + shortcutButton.artworkPrefix + "-raised.svg")
                                sourceSize: Qt.size(240, 240)
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                mipmap: true
                            }
                            Image {
                                id: shortcutHoverImage
                                objectName: "providerShortcutHoverImage"
                                anchors.fill: parent
                                visible: false
                                source: AccentTheme.customAccent ? AccentTheme.artwork(shortcutButton.artworkPrefix + "-raised-Blue-highlight-ring.svg") : Qt.resolvedUrl("../../../assets/icons/svg/actions/relief/shortcuts/" + shortcutButton.artworkPrefix + "-raised-Blue-highlight-ring.svg")
                                sourceSize: Qt.size(240, 240)
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                mipmap: true
                            }
                            Image {
                                id: shortcutSunkenImage
                                objectName: "providerShortcutSunkenImage"
                                anchors.fill: parent
                                visible: false
                                source: AccentTheme.customAccent ? AccentTheme.artwork(shortcutButton.artworkPrefix + "-sunken.svg") : Qt.resolvedUrl("../../../assets/icons/svg/actions/relief/shortcuts/" + shortcutButton.artworkPrefix + "-sunken.svg")
                                sourceSize: Qt.size(240, 240)
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                mipmap: true
                            }
                            ShaderEffect {
                                objectName: "providerShortcutArtwork"
                                anchors.fill: parent
                                readonly property var raisedSource: shortcutRaisedImage
                                readonly property var hoverSource: shortcutHoverImage
                                readonly property var sunkenSource: shortcutSunkenImage
                                readonly property real hoverAmount: shortcutButton.hoverProgress
                                readonly property real pressAmount: shortcutButton.pressProgress
                                fragmentShader: Qt.resolvedUrl("../shaders/shortcut-state.frag.qsb")
                            }
                        }
                    }
                    Item {
                        visible: AccentTheme.showInfoButtons
                        width: 21 * root.shelfScale
                        height: parent.height
                        ConnectionHelpButton {
                            id: shortcutInfoButton
                            objectName: "providerShortcutInfoButton"
                            anchors.centerIn: parent
                            scale: root.shelfScale
                            text: "About creating an app shortcut"
                            expanded: root.drawerTopic === "shortcut"
                            onClicked: root.openTopic("shortcut", shortcutInfoButton)
                        }
                    }
                }
                Button {
                    id: continueButton
                    objectName: "providerContinueButton"
                    x: parent.width - 42 - width
                    y: parent.height - 28 - 71 + 8
                    width: 204
                    height: 55
                    padding: 0
                    visible: root.selectedProvider.length > 0
                    enabled: visible && root.enabled && root.selectedProviderAvailable
                    hoverEnabled: enabled
                    text: root.selectedProviderAvailable ? "Open" : "Currently Unavailable"
                    Accessible.name: root.selectedProviderAvailable ?
                        "Choose a Microsoft Graph connection" :
                        root.appController.selectedProviderName + " is currently unavailable"
                    Keys.onReturnPressed: if (enabled) clicked()
                    onClicked: if (root.selectedProviderAvailable) root.continued()
                    HoverHandler {
                        enabled: continueButton.enabled
                        cursorShape: Qt.PointingHandCursor
                    }
                    transform: Translate {
                        y: continueButton.down ? 1 : continueButton.hovered ? -1 : 0
                        Behavior on y {
                            NumberAnimation {
                                duration: 160
                            }
                        }
                    }
                    background: ProviderSurface {
                        kind: 4
                        unavailable: !root.selectedProviderAvailable
                        radius: 12
                        hovered: continueButton.hovered
                        pressed: continueButton.down
                        focused: continueButton.visualFocus
                    }
                    contentItem: Item {
                        Text {
                            objectName: "providerContinueLabel"
                            // Center against the button itself without rounding
                            // the text's position at odd control heights.
                            x: (continueButton.width - width) / 2 - parent.x
                            y: (continueButton.height - height) / 2 - parent.y
                            text: continueButton.text
                            color: root.selectedProviderAvailable ? "#ffffff" : "#9aaac0"
                            font.family: ConnectionTheme.body
                            font.pointSize: 12
                            font.weight: 750
                        }
                    }
                }
            }
            Item {
                id: aboutViewport
                objectName: "providerAboutDrawer"
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: root.helpWidth * root.helpProgress
                clip: true
                visible: width > 0 && !root.selectionHidden
                enabled: root.drawerOpen
                ConnectionHelpShelf {
                    id: aboutShelf
                    objectName: "providerAboutShelf"
                    width: 342
                    height: parent.height / root.shelfScale
                    scale: root.shelfScale
                    transformOrigin: Item.TopLeft
                    topicData: helpTopics.topics[root.displayedDrawerTopic]
                    markdownText: root.displayedDrawerTopic === "about" ? root.appController.aboutMarkdown : ""
                    preloadedMarkdownText: root.appController.aboutMarkdown
                    legalDocuments: root.appController.legalDocuments
                    legalDocumentUrls: root.appController.legalDocumentUrls
                    legalTopic: ["terms", "privacy"].includes(root.displayedDrawerTopic) ? root.displayedDrawerTopic : ""
                    onMarkdownDocumentReady: document => root.appController.formatAboutDocument(document)
                    onLegalDocumentReady: (topic, document) => root.appController.prepareLegalDocument(topic, document)
                    onLegalTopicRequested: topic => root.openTopic(topic, root.aboutTrigger)
                    onFullDocumentRequested: topic => root.appController.openLegalDocument(topic)
                    onDismissed: root.closeAbout()
                }
            }
        }
    }
}
