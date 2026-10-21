import QtQuick

QtObject {
    property color surfaceTop: "transparent"
    property color surfaceBottom: "transparent"
    property color border: "transparent"
    property color innerBorder: "transparent"
    property color edgeGlow: "transparent"
    property real surfaceOpacity: 1.0
    property real shadowOpacity: 0.0
    property real shadowBlur: 0.0
    property int shadowHorizontalOffset: 0
    property int shadowVerticalOffset: 0
    property real edgeGlowOpacity: 0.0

    property color headingText: "white"
    property color descriptionText: "white"

    property color icon: "white"
    property color iconSurfaceTop: "transparent"
    property color iconSurfaceBottom: "transparent"
    property color iconBorder: "transparent"
    property color iconInnerBorder: "transparent"
    property color iconShadow: "transparent"
    property real iconShadowOpacity: 0.0
    property int headerHorizontalOffset: 0
    property int headerVerticalOffset: 0
}
