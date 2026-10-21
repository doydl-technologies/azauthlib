pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import "../theme"

// Only the circular face is interactive; shadows/halo never enlarge the hit area.
Button {
    id: root
    implicitWidth: 69
    implicitHeight: 69
    padding: 0
    hoverEnabled: enabled
    focusPolicy: enabled ? Qt.StrongFocus : Qt.NoFocus
    Accessible.name: "Manage connections"
    property bool busy: false
    // Use the same size control, preserving the launcher's taller artwork ratio.
    property real iconSize: ConnectionTheme.plugButtonIconSize
    property real loadingRotation: 0
    Accessible.description: busy ? "Opening connections" : ""
    readonly property bool visualHovered: enabled && pointer.onFace
    readonly property bool visualPressed: enabled && (busy || (pointer.pressed && pointer.onFace) || down)
    property real pressProgress: visualPressed ? 1 : 0
    property real haloAngle: busy || visualHovered ? 55 : -40
    property real haloStrength: busy ? 1 : visualPressed ? (visualHovered ? 0.65 : 0.35) : 1
    property real motionY: visualPressed ? 1 : visualHovered ? -2 : 0
    property real motionScale: visualPressed ? 0.985 : 1
    Behavior on pressProgress { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    Behavior on haloAngle { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }
    Behavior on haloStrength { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    Behavior on motionY { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    Behavior on motionScale { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
    NumberAnimation on loadingRotation {
        objectName: root.objectName + "LoadingAnimation"
        from: 0; to: 360; duration: 1200
        loops: Animation.Infinite
        running: root.busy
    }
    onBusyChanged: if (!busy) loadingRotation = 0
    Keys.onReturnPressed: if (enabled && !busy) clicked()
    transform: [
        Translate { y: root.motionY },
        Scale {
            origin.x: root.width / 2; origin.y: root.height / 2
            xScale: root.motionScale; yScale: root.motionScale
        }
    ]
    MouseArea {
        id: pointer
        objectName: root.objectName + "MouseArea"
        anchors.fill: parent
        z: 10
        enabled: root.enabled
        hoverEnabled: true
        acceptedButtons: Qt.AllButtons
        readonly property bool onFace: containsMouse &&
            Math.pow(mouseX - width / 2, 2) + Math.pow(mouseY - height / 2, 2) <=
            Math.pow(Math.min(width, height) / 2, 2)
        cursorShape: onFace ? (root.busy ? Qt.BusyCursor : Qt.PointingHandCursor) : Qt.ArrowCursor
        onClicked: mouse => {
            if (root.enabled && !root.busy && onFace && mouse.button === Qt.LeftButton)
                root.clicked()
        }
    }
    contentItem: Item {
        Image {
            objectName: root.objectName + "Icon"
            anchors.centerIn: parent
            width: root.iconSize * 32 / 24; height: root.iconSize * 42 / 24
            source: Qt.resolvedUrl("../../../assets/icons/svg/plugs/relief/monocolor-single-plug-raised-strong.svg")
            sourceSize: Qt.size(Math.max(128, Math.ceil(width * 4)), Math.max(168, Math.ceil(height * 4)))
            fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
            opacity: 1 - root.pressProgress
        }
        Image {
            objectName: root.objectName + "PressedIcon"
            anchors.centerIn: parent
            width: root.iconSize * 32 / 24; height: root.iconSize * 42 / 24
            source: Qt.resolvedUrl("../../../assets/icons/svg/plugs/relief/monocolor-single-plug-sunken.svg")
            sourceSize: Qt.size(Math.max(128, Math.ceil(width * 4)), Math.max(168, Math.ceil(height * 4)))
            fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
            opacity: root.pressProgress
        }
    }
    background: ShaderEffect {
        objectName: root.objectName + "Surface"
        readonly property real padding: 28
        x: -padding; y: -padding
        width: root.width + 2 * padding; height: root.height + 2 * padding
        readonly property vector2d faceSize: Qt.vector2d(root.width, root.height)
        readonly property real pressAmount: root.pressProgress
        readonly property real haloRotation: root.haloAngle + root.loadingRotation
        readonly property real haloOpacity: root.haloStrength
        readonly property real focused: root.enabled && root.visualFocus ? 1 : 0
        fragmentShader: Qt.resolvedUrl("../shaders/connections-halo.frag.qsb")
    }
}
