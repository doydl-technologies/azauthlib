import QtQuick

// Sample the Image's existing texture directly. Only its shadow is drawn here;
// the foreground Image stays unlayered, so it is filtered exactly once.
ShaderEffect {
    id: root
    required property Item source
    readonly property real padding: 9
    readonly property vector2d artworkSize: Qt.vector2d(source.width, source.height)
    readonly property vector2d shadowOffset: Qt.vector2d(1, 2)
    readonly property real shadowSigma: 2
    x: source.x - padding; y: source.y - padding
    width: source.width + padding * 2; height: source.height + padding * 2
    fragmentShader: Qt.resolvedUrl("../shaders/svg-image-shadow.frag.qsb")
    Accessible.ignored: true
}
