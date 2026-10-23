pragma Singleton
import QtQuick

QtObject {
    // Spotlight reference colors / accent inventory. These are decorative
    // roles, translated by the same OKLCH family mapping as the rest of the UI.
    readonly property color glowCore: AccentTheme.color("#139dff")
    readonly property color glowOuter: AccentTheme.color("#1784e2")
    readonly property color ripple: AccentTheme.color("#5cccff")
    readonly property color progressFill: AccentTheme.color("#35c8ff")
    readonly property color progressTrack: AccentTheme.color("#1e425d")
    readonly property color loadingText: AccentTheme.color("#97cbee")
    // Opaque navy foundations, not accents. Branding/service logos stay original.
    readonly property color curtainCenter: "#123b60"
    readonly property color curtainMiddle: "#0b2743"
    readonly property color curtainEdge: "#061628"
    readonly property int popDuration: 1100
    readonly property int minimumDuration: 2350
}
