pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Effects
import "../theme"

// Shared by the real startup screen and its loading-screen-only preview.
Item {
    id: root
    required property url logoSource
    // Toggle the background overlay without affecting foreground artwork.
    property bool overlayEnabled: true

    property real logoAspectRatio: 0.394285714285714    
    property real logoWidth: 550
    property real logoHeight: root.logoWidth * root.logoAspectRatio

    property real wordmarkOffsetY: -30 

    // Separate mark above the wordmark; does not change the loading layout.
    // Height-to-width ratio of the SVG's 440 x 520.75 viewBox.
    property real logoMarkAspectRatio: 520.75 / 440    
    property real logoMarkWidth: 200  // Mark size; height scales automatically.
    property real logoMarkGap: 16    // Gap above the wordmark.
    property real logoMarkHeight: root.logoMarkWidth * root.logoMarkAspectRatio

    property real authorlogoAspectRatio: 0.250725478816018   
    property real authorlogoWidth: 300
    property real authorlogoHeight: root.authorlogoWidth * root.authorlogoAspectRatio

    property int headingFontSize: 20
    property int statusFontSize: 13
    property real contentWidth: 440
    property real cornerRadius: 24
    property real progress: 0
    property string statusText: "Starting azauthlib…"
    property bool failed: false
    // Generic display messages leave detailed milestone reporting intact.
    readonly property string loadingMessage: progress >= 100 ? "Ready" :
                                             progress >= 92 ? "Finalizing your workspace…" :
                                             progress >= 88 ? "Configuring runtime environment…" :
                                             progress >= 82 ? "Initializing interface components…" :
                                             progress >= 80 ? "Organizing application content…" :
                                             progress >= 77 ? "Preparing supporting resources…" :
                                             progress >= 75 ? "Restoring session preferences…" :
                                             progress >= 65 ? "Verifying application readiness…" :
                                             progress >= 50 ? "Applying configuration…" :
                                             progress >= 35 ? "Loading workspace settings…" :
                                             progress >= 10 ? "Initializing application…" :
                                                              "Starting azauthlib…"
    signal retryRequested()
    signal abortRequested()

    property real loadingOffsetY: -58


    // Mask the background itself: a rounded frame alone leaves square image
    // corners visible. Keep the logo and text outside the offscreen layer.
    Item {
        id: backgroundMask
        anchors.fill: parent
        visible: false
        layer.enabled: true
        Rectangle {
            anchors.fill: parent
            radius: root.cornerRadius
            color: "white"
            antialiasing: true
        }
    }
    Item {
        anchors.fill: parent
        layer.enabled: true
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: backgroundMask
            autoPaddingEnabled: false
        }
        Rectangle { anchors.fill: parent; color: Theme.background }
        Image {
            objectName: "startupBackground"
            anchors.fill: parent
            source: "../../../assets/themes/azauthlib-mountain-background.png"
            fillMode: Image.PreserveAspectCrop
            smooth: true
            mipmap: true
        }
        Image {
            objectName: "startupBackgroundOverlay"
            anchors.fill: parent
            visible: root.overlayEnabled
            source: "../../../assets/themes/overlay.png"
            fillMode: Image.PreserveAspectCrop
            smooth: true
            mipmap: true
            Accessible.ignored: true
        }
    }
    Rectangle {
        objectName: "startupBorder"
        anchors.fill: parent
        radius: root.cornerRadius
        color: "transparent"
        border.width: 1.5
        border.color: Theme.borderStrong
        antialiasing: true
    }
    Column {
        id: splashContent
        z: 2 // Status and failure actions must paint above decorative artwork.
        anchors.centerIn: parent
        anchors.verticalCenterOffset: 50        
        width: Math.min(root.contentWidth, parent.width - 48)
        spacing: root.failed ? 10 : 16
        Image {
            objectName: "startupLogo"
            anchors.horizontalCenter: parent.horizontalCenter
            width: root.logoWidth
            height: root.logoHeight
            source: root.logoSource
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true
            transform: Translate { y: 40 + root.wordmarkOffsetY }

            Image {
                objectName: "startupLogoMark"
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.top
                anchors.bottomMargin: root.logoMarkGap
                width: root.logoMarkWidth
                height: root.logoMarkHeight                
                source: "../../../assets/logo/svg/azauthlib-mark-glow-border.svg"                
                fillMode: Image.PreserveAspectFit
                smooth: true
                mipmap: true
                transform: Translate {
                    y: 70 - root.wordmarkOffsetY  // Keep the mark independent of wordmark movement.
                }
            }            
        }
        Text {
            objectName: "startupHeading"
            anchors.horizontalCenter: parent.horizontalCenter
            color: Theme.textPrimary; font.family: Theme.fontFamily
            font.pixelSize: root.headingFontSize; font.weight: Font.DemiBold
        }
        Text {
            objectName: "startupStatus"
            height: 44
            maximumLineCount: 2
            elide: Text.ElideRight
            verticalAlignment: Text.AlignBottom            

            transform: Translate { y: root.loadingOffsetY }
            anchors.horizontalCenter: parent.horizontalCenter

            width: Math.min(800, root.width - 48)

            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: root.failed ? root.statusText : root.loadingMessage + " · " + Math.round(root.progress) + "%"
            color: Theme.textSecondary
            font.family: Theme.fontFamily
            font.pixelSize: root.statusFontSize
        }
        Rectangle {
            id: progressTrack
            objectName: "startupProgressTrack"
            transform: Translate { y: root.loadingOffsetY }
            anchors.horizontalCenter: parent.horizontalCenter
            width: 300
            height: 5
            radius: 3
            color: Theme.surfaceInput; clip: true
            Rectangle {
                objectName: "startupProgressFill"
                width: parent.width * Math.max(0, Math.min(100, root.progress)) / 100
                height: parent.height; radius: 3
                color: Theme.accent
            }
        }
        Row {
            id: failureActions
            objectName: "startupFailureActions"
            anchors.horizontalCenter: parent.horizontalCenter
            transform: Translate { y: root.loadingOffsetY }
            spacing: 12
            visible: root.failed
            ConnectionButton {
                objectName: "startupRetryButton"
                text: "Retry"; onClicked: root.retryRequested()
            }
            ConnectionButton {
                objectName: "startupExitButton"
                text: "Close"; variant: "warning"; onClicked: root.abortRequested()
            }
        }
    }
    Image {
        objectName: "startupAuthorLogo"
        anchors.horizontalCenter: parent.horizontalCenter
        // Center in the gap without changing the Column's layout.
        y: (splashContent.y + (root.failed ? failureActions.y + failureActions.height : progressTrack.y + progressTrack.height) + root.loadingOffsetY
            + disclaimerDivider.y - height) / 2
        width: root.authorlogoWidth
        height: root.authorlogoHeight
        source: "../../../assets/logo/svg/author-powered_by.svg"
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        Accessible.name: "Powered by DOYDL Technologies"
    }
    Image {
        id: disclaimerDivider
        objectName: "startupDisclaimerDivider"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: disclaimer.top
        anchors.bottomMargin: -4
        // Use the SVG's own width and height, without extra effects.
        source: "../../../assets/controls/glowing-blue-divider.svg"
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        Accessible.ignored: true
    }
    Text {
        id: disclaimer
        objectName: "startupDisclaimer"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12        
        width: Math.min(900, parent.width - 48)
        text: "Independent open-source software developed by DOYDL Technologies, LLC.\n" +
              "Not affiliated with, sponsored by, or endorsed by Microsoft Corporation."
        textFormat: Text.PlainText
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
        color: Theme.textSecondary
        opacity: 0.8
        font.family: Theme.fontFamily
        font.pixelSize: 11
        lineHeight: 1.3
        Accessible.name: text
    }
}
