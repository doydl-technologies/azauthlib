pragma Singleton
import QtQuick

// Typography, palette and shared sizing for the Connections home page.
QtObject {
    // Qt 6.12 exposes the platform motion preference. Older supported Qt
    // versions simply have no motion hint; the explicit override also aids QA.
    property var systemStyleHints: Qt.styleHints
    readonly property var accessibilityHints: systemStyleHints.accessibility || null
    property bool reduceMotionOverride: false
    readonly property bool reducedMotion: reduceMotionOverride || Boolean(accessibilityHints &&
        accessibilityHints.motionPreference !== undefined && Number(accessibilityHints.motionPreference) === 1)
    readonly property int pageTransitionDuration: reducedMotion ? 0 : 250
    readonly property int contentTransitionDuration: reducedMotion ? 0 : 200
    readonly property int popupExitDuration: reducedMotion ? 0 : 320
    // Keep roomy windows from enlarging every label/control excessively.
    // Increase this to make the Connections content larger without resizing it.
    property real maximumContentScale: 1.15
    // Default logical-pixel size for every plug icon on an action button.
    // Page zoom scales this automatically; decorative/card icons are separate.
    property real plugButtonIconSize: 20    
    // Keep scroll thumbs in their own lane, outside text and input content.
    readonly property real scrollBarWidth: 6
    readonly property real scrollBarTextGap: 10
    readonly property real scrollBarGutter: scrollBarWidth + scrollBarTextGap
    readonly property FontLoader bodyLoader: FontLoader { source: "../../../assets/fonts/DM-Sans.ttf" }
    readonly property FontLoader headingLoader: FontLoader { source: "../../../assets/fonts/Manrope.ttf" }
    readonly property FontLoader monoLoader: FontLoader { source: "../../../assets/fonts/JetBrains-Mono.ttf" }
    readonly property string body: bodyLoader.name
    readonly property string heading: headingLoader.name
    readonly property string mono: monoLoader.name
    readonly property color text: "#edf4ff"
    readonly property color muted: "#9bb2ce"
    readonly property color accent: AccentTheme.accent
    readonly property color border: AccentTheme.color("#345b85")
    readonly property color cancelColor: "#6b7280"
    // Shared by the live Connections page and its GUI simulator.
    property size newConnectionSuccessIconSize: Qt.size(300, 300)
    property point newConnectionSuccessIconOffset: Qt.point(160, -35)
    property int newConnectionOutlineFrameInterval: 75
    property int newConnectionSuccessHold: 1600
}
