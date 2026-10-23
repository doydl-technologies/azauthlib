import QtQuick

ShaderEffect {
    readonly property vector2d surfaceSize: Qt.vector2d(width, height)
    property real cornerRadius: 0
    property vector2d gradientCenter: Qt.vector2d(0.5, 0.5)
    property real middleStop: 0.28
    property real edgeStop: 0.69
    property color colorCenter: "transparent"
    property color colorMiddle: "transparent"
    property color colorEdge: "transparent"
    fragmentShader: Qt.resolvedUrl("../shaders/service-spotlight.frag.qsb")
}
