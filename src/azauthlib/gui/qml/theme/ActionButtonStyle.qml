import QtQuick

QtObject {
    property color text: "white"
    property color icon: "white"
    property color top: "transparent"
    property color bottom: "transparent"
    property color hoverTop: "transparent"
    property color pressedTop: "transparent"
    property color border: "transparent"
    property color focusBorder: "white"
    property color glow: "transparent"
    property color highlight: "transparent"
    property color disabledText: "gray"
    property color disabledIcon: "gray"
    property color disabledTop: "transparent"
    property color disabledBottom: "transparent"
    property color disabledBorder: "transparent"
    property real glowOpacity: 0.0
    property real hoverGlowOpacity: 0.0
    property real pressedGlowOpacity: 0.0
    property real disabledGlowOpacity: 0.0
    property real highlightOpacity: 0.0
    property real glowBlur: 0.46
    property int glowBlurMax: 20
    property int radius: 10
    property int borderWidth: 1
    property int focusBorderWidth: 2
}
