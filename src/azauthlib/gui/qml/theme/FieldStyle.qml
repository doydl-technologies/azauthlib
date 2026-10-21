import QtQuick

QtObject {
    property int labelFontWeight: Font.DemiBold
    property color label: "white"
    property color helper: "white"
    property color error: "red"
    property color placeholder: "gray"
    property color text: "white"
    property color disabledText: "gray"
    property color selection: "blue"
    property color selectedText: "white"

    property color surfaceTop: "transparent"
    property color surfaceBottom: "transparent"
    // Optional multi-stop fill; null uses the top/bottom gradient.
    property Gradient surfaceGradient: null
    // Optional translucent elliptical overlay on top of the vertical gradient.
    property color surfaceGlowColor: "transparent"
    property point surfaceGlowCenter: Qt.point(0.6, 1.0)
    property size surfaceGlowRadii: Qt.size(0.7, 1.3)
    property color disabledSurface: "transparent"
    property color border: "transparent"
    property color hoverBorder: "transparent"
    property color focusBorder: "white"
    property color errorBorder: "red"
    property color disabledBorder: "transparent"
    property color focusGlow: "transparent"
    property color shadow: "transparent"
    property color highlight: "transparent"
    property real focusGlowOpacity: 0.0
    property real shadowOpacity: 0.0
    property real highlightOpacity: 0.0
    property int radius: 10
    property int borderWidth: 0
    property int hoverBorderWidth: 1
    property int focusBorderWidth: 2
    property int errorBorderWidth: 2
    property int headingTopOffset: -4
    property real focusRingLeftOutset: 0.0
    property real focusRingRightOutset: 0.0
    property real focusRingTopOutset: 0.0
    property real focusRingBottomOutset: 0.0
    property real hoverRingLeftOutset: 0.0
    property real hoverRingRightOutset: 0.0
    property real hoverRingTopOutset: 0.0
    property real hoverRingBottomOutset: 0.0
    property real inputVerticalOffset: 0.0

    property color actionText: "white"
    property color actionIcon: "white"
    property color actionHoverSurface: "transparent"
    property color actionPressedSurface: "transparent"
    property color actionFocusBorder: "white"
    property color actionDivider: "transparent"

    property real focusRingRadius: -1.0
    property real hoverRingRadius: -1.0    
}
