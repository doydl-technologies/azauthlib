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

    readonly property color border: darkMode ? "#2b4f6d" : "#93aec3"
    readonly property color borderStrong: darkMode ? "#397096" : "#6f96b3"
    readonly property color inputBorder: darkMode ? "#345a78" : "#b2c7d9"
    readonly property color highlight: darkMode ? "#4a789b" : "#ffffff"
    readonly property color shadow: darkMode ? "#01050c" : "#728598"

    readonly property color textPrimary: darkMode ? "#f4f7fb" : "#102039"
    readonly property color textSecondary: darkMode ? "#bed3e9" : "#586f87"
    readonly property color textMuted: darkMode ? "#849eb7" : "#6d8298"
    readonly property color textOnAccent: "#ffffff"
    readonly property color disabled: darkMode ? "#647b91" : "#98a8b8"

    readonly property color accent: darkMode ? "#1684f5" : "#1678e7"
    readonly property color accentTop: darkMode ? "#36a9ff" : "#43a5ff"
    readonly property color accentBottom: darkMode ? "#075dce" : "#0a5bc3"
    readonly property color accentHover: darkMode ? "#45b2ff" : "#3595f5"
    readonly property color accentPressed: darkMode ? "#0c63cf" : "#0b61c7"
    readonly property color accentBorder: darkMode ? "#65caff" : "#50affb"
    readonly property color accentGlow: darkMode ? "#1996ff" : "#43a5ff"
    readonly property color focus: darkMode ? "#73ceff" : "#167fe9"

    readonly property color icon: darkMode ? "#82d0ff" : "#146fd0"
    readonly property color iconSurface: darkMode ? "#173957" : "#e5f2fd"
    readonly property color iconSurfaceTop: darkMode ? "#214769" : "#f1f8ff"
    readonly property color iconSurfaceBottom: darkMode ? "#102a43" : "#dceefd"
    readonly property color iconBorder: darkMode ? "#2d638b" : "#b5d8f4"

    readonly property color callout: darkMode ? "#143a5b" : "#e7f4fe"
    readonly property color calloutBorder: darkMode ? "#207bb9" : "#87bee9"
    readonly property color calloutText: darkMode ? "#c8e6ff" : "#244c72"

    readonly property color error: darkMode ? "#ff727d" : "#c23b44"
    readonly property color errorSurface: darkMode ? "#3a1d25" : "#fdecef"
    readonly property color success: darkMode ? "#55ce91" : "#147a4b"
    readonly property color successSurface: darkMode ? "#153a29" : "#eaf7f0"
    readonly property color warning: darkMode ? "#f0b44d" : "#a86400"

    readonly property color themeSun: darkMode ? "#ffbd52" : "#1778d3"
    readonly property color themeMoon: darkMode ? "#d7e7ff" : "#5878a5"

    readonly property string fontFamily: "Museo Sans Cyrl 700"
}
