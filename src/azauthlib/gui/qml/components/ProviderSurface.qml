import QtQuick

// The selector HTML's CSS gradients and layered shadows, rendered natively.
Item {
    id: root
    // 2 recessed card, 3 raised halo, 4 Continue, 5 check.
    // Backdrop and panel modes use the shared Connections surface.
    property int kind: 2
    property real radius: 23
    property bool selected: false
    property bool hovered: false
    property bool pressed: false
    property bool focused: false
    property bool unavailable: false
    property real selectionAmount: selected ? 1 : 0
    property real hoverAmount: hovered ? 1 : 0
    Behavior on selectionAmount { NumberAnimation { duration: 180 } }
    Behavior on hoverAmount { NumberAnimation { duration: 180 } }
    ShaderEffect {
        objectName: root.objectName + "Shader"
        readonly property real padding: 64
        x: -padding; y: -padding
        width: root.width + padding * 2; height: root.height + padding * 2
        readonly property vector2d surfaceSize: Qt.vector2d(root.width, root.height)
        readonly property real cornerRadius: Math.min(root.radius, root.width / 2, root.height / 2)
        readonly property real surfaceKind: root.kind
        readonly property real selectedState: root.selectionAmount
        readonly property real hoverState: root.hoverAmount
        readonly property real pressState: root.pressed ? 1 : 0
        readonly property real focusState: root.focused ? 1 : 0
        readonly property real unavailableState: root.unavailable ? 1 : 0
        fragmentShader: Qt.resolvedUrl("../shaders/provider-surface.frag.qsb")
    }
}
