import QtQuick

QtObject {
    property int activeFontWeight: Font.DemiBold
    property int inactiveFontWeight: Font.DemiBold

    property color activeText: "white"
    property color activeIcon: "white"
    property color activeTop: "transparent"
    property color activeBottom: "transparent"
    property color activeHoverTop: "transparent"
    property color activePressedTop: "transparent"
    property color activeBorder: "transparent"
    property color activeGlow: "transparent"
    property real activeGlowOpacity: 0.0
    property real activeHoverGlowOpacity: 0.0
    property color activeHighlight: "transparent"
    property real activeHighlightOpacity: 0.0

    property color inactiveText: "white"
    property color inactiveIcon: "white"
    property color inactiveTop: "transparent"
    property color inactiveBottom: "transparent"
    property color inactiveHoverTop: "transparent"
    property color inactiveHoverBottom: "transparent"
    property color inactivePressedTop: "transparent"
    property color inactivePressedBottom: "transparent"
    property color inactiveBorder: "transparent"
    property color inactiveGlow: "transparent"
    property real inactiveGlowOpacity: 0.0
    property real inactiveHoverGlowOpacity: 0.0
    property color inactiveHighlight: "transparent"
    property real inactiveHighlightOpacity: 0.0

    property color focusBorder: "white"
    property color disabledText: "gray"
    property color disabledIcon: "gray"
    property color disabledTop: "transparent"
    property color disabledBottom: "transparent"
    property color disabledBorder: "transparent"

    property real activeHorizontalInset: 2.0
    property real activeVerticalInset: 2.0
    property int inactiveInset: 0
    property int radius: 9
    property int activeBorderWidth: 1
    property int inactiveBorderWidth: 0
    property int focusBorderWidth: 2
    property real glowBlur: 0.48
    property int glowBlurMax: 20

    property real activeHorizontalOffset: 0.0   
    property real activeVerticalOffset: 0.0     
}
