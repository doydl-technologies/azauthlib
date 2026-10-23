import QtQuick
import "../theme"

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
        readonly property real customAccent: AccentTheme.customAccent ? 1 : 0
        readonly property real emblemTintStrength: AccentTheme.emblemTintStrength
        readonly property real emblemLightStrength: AccentTheme.emblemLightStrength
        readonly property color accentBase: AccentTheme.accent
        readonly property color accentFocus: AccentTheme.focus
        readonly property color accentGlow: AccentTheme.glow
        readonly property color accentTop: AccentTheme.primaryTop
        readonly property color accentMiddle: AccentTheme.primaryMiddle
        readonly property color accentBottom: AccentTheme.primaryBottom
        readonly property color familya7deff: AccentTheme.color("#a7deff")
        readonly property color family149aff: AccentTheme.color("#149aff")
        readonly property color family91daff: AccentTheme.color("#91daff")
        readonly property color family8dd5ff: AccentTheme.color("#8dd5ff")
        readonly property color family0471ec: AccentTheme.color("#0471ec")
        readonly property color family40baff: AccentTheme.color("#40baff")
        readonly property color familye6fbff: AccentTheme.color("#e6fbff")
        readonly property color family41a7ff: AccentTheme.color("#41a7ff")
        readonly property color family1093ff: AccentTheme.color("#1093ff")
        readonly property color family81cfff: AccentTheme.color("#81cfff")
        readonly property color family0965d1: AccentTheme.color("#0965d1")
        readonly property color family1187f4: AccentTheme.color("#1187f4")
        readonly property color family2eb3fd: AccentTheme.color("#2eb3fd")
        readonly property color family38a8ff: AccentTheme.color("#38a8ff")
        readonly property color family345b85: AccentTheme.color("#345b85")
        readonly property color family55abed: AccentTheme.color("#55abed")
        readonly property color family388bd0: AccentTheme.color("#388bd0")
        readonly property color family76b9ed: AccentTheme.color("#76b9ed")
        readonly property color family1c456d: AccentTheme.color("#1c456d")
        readonly property color family2fa4f7: AccentTheme.color("#2fa4f7")
        readonly property color family1091ff: AccentTheme.color("#1091ff")
        readonly property color family2b95ef: AccentTheme.color("#2b95ef")
        readonly property color family87c7f4: AccentTheme.color("#87c7f4")
        readonly property color family43b6ff: AccentTheme.color("#43b6ff")
        readonly property color family579bd0: AccentTheme.color("#579bd0")
        readonly property color family325c80: AccentTheme.color("#325c80")
        readonly property color family92caf7: AccentTheme.color("#92caf7")
        readonly property color family4dabfc: AccentTheme.color("#4dabfc")
        readonly property color family87c1eb: AccentTheme.color("#87c1eb")
        readonly property color family1369bf: AccentTheme.color("#1369bf")
        readonly property color family5da1d3: AccentTheme.color("#5da1d3")
        readonly property color family65aee6: AccentTheme.color("#65aee6")
        fragmentShader: Qt.resolvedUrl("../shaders/provider-surface.frag.qsb")
    }
}
