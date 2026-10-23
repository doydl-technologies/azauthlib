pragma Singleton

import QtQuick

QtObject {
    property bool darkMode: true

    readonly property color background: darkMode ? "#081522" : "#edf4fa"
    readonly property color backgroundTop: darkMode ? "#112d4d" : "#e2e6e9"
    readonly property color backgroundBottom: darkMode ? "#06101b" : "#e5eef7"
    readonly property color backgroundBloom: darkMode ? "#112d4d" : "#e2e6e9"
    readonly property color backgroundBloomSoft: darkMode ? "#102f53" : "#dceefa"

    readonly property color surface: darkMode ? "#10243a" : "#f7fbfe"
    readonly property color surfaceRaised: darkMode ? "#18314b" : "#ffffff"
    readonly property color surfaceAlt: darkMode ? "#152b43" : "#f2f7fb"
    readonly property color surfaceInput: darkMode ? "#081725" : "#f9fbfd"
    readonly property color surfaceHover: darkMode ? "#1d3a58" : "#e8f1f8"
    readonly property color surfaceHighlight: darkMode ? "#23425f" : "#ffffff"

    readonly property color border: darkMode ? AccentTheme.color("#2b4f6d") : AccentTheme.color("#93aec3")
    readonly property color borderStrong: darkMode ? AccentTheme.color("#397096") : AccentTheme.color("#6f96b3")
    readonly property color inputBorder: darkMode ? AccentTheme.color("#345a78") : AccentTheme.color("#b2c7d9")
    readonly property color highlight: darkMode ? AccentTheme.color("#4a789b") : "#ffffff"
    readonly property color shadow: darkMode ? "#01050c" : "#728598"

    readonly property color textPrimary: darkMode ? "#f4f7fb" : "#102039"
    readonly property color textSecondary: darkMode ? "#bed3e9" : "#586f87"
    readonly property color textMuted: darkMode ? "#849eb7" : "#6d8298"
    readonly property color textOnAccent: "#ffffff"
    readonly property color disabled: darkMode ? "#647b91" : "#98a8b8"

    readonly property color accent: AccentTheme.customAccent ? AccentTheme.primaryMiddle : darkMode ? AccentTheme.color("#1684f5") : AccentTheme.color("#1678e7")
    readonly property color accentTop: AccentTheme.customAccent ? AccentTheme.primaryTop : darkMode ? AccentTheme.color("#36a9ff") : AccentTheme.color("#43a5ff")
    readonly property color accentBottom: AccentTheme.customAccent ? AccentTheme.primaryBottom : darkMode ? AccentTheme.color("#075dce") : AccentTheme.color("#0a5bc3")
    readonly property color accentHover: AccentTheme.customAccent ? Qt.lighter(AccentTheme.primaryTop, 1.15) : darkMode ? AccentTheme.color("#45b2ff") : AccentTheme.color("#3595f5")
    readonly property color accentPressed: AccentTheme.customAccent ? AccentTheme.primaryBottom : darkMode ? AccentTheme.color("#0c63cf") : AccentTheme.color("#0b61c7")
    readonly property color accentBorder: AccentTheme.customAccent ? AccentTheme.border : darkMode ? AccentTheme.color("#65caff") : AccentTheme.color("#50affb")
    readonly property color accentGlow: AccentTheme.customAccent ? AccentTheme.glow : darkMode ? AccentTheme.color("#1996ff") : AccentTheme.color("#43a5ff")
    readonly property color focus: AccentTheme.customAccent ? AccentTheme.focus : darkMode ? AccentTheme.color("#73ceff") : AccentTheme.color("#167fe9")

    readonly property color icon: darkMode ? AccentTheme.color("#82d0ff") : AccentTheme.color("#146fd0")
    readonly property color iconSurface: darkMode ? "#173957" : AccentTheme.color("#e5f2fd")
    readonly property color iconSurfaceTop: darkMode ? AccentTheme.color("#214769") : AccentTheme.color("#f1f8ff")
    readonly property color iconSurfaceBottom: darkMode ? "#102a43" : AccentTheme.color("#dceefd")
    readonly property color iconBorder: darkMode ? AccentTheme.color("#2d638b") : AccentTheme.color("#b5d8f4")

    readonly property color callout: darkMode ? "#143a5b" : "#e7f4fe"
    readonly property color calloutBorder: darkMode ? AccentTheme.color("#207bb9") : AccentTheme.color("#87bee9")
    readonly property color calloutText: darkMode ? "#c8e6ff" : AccentTheme.color("#244c72")

    readonly property color error: darkMode ? "#ff727d" : "#c23b44"
    readonly property color errorSurface: darkMode ? "#3a1d25" : "#fdecef"
    readonly property color success: darkMode ? "#55ce91" : "#147a4b"
    readonly property color successSurface: darkMode ? "#153a29" : "#eaf7f0"
    readonly property color warning: darkMode ? "#f0b44d" : "#a86400"

    readonly property color themeSun: darkMode ? "#ffbd52" : "#1778d3"
    readonly property color themeMoon: darkMode ? "#d7e7ff" : "#5878a5"

    readonly property string fontFamily: "Museo Sans Cyrl 700"
}
