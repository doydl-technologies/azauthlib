pragma ComponentBehavior: Bound
import QtQuick
import "../theme"
import QtQuick.Controls
import QtQuick.Effects

// Frosted close affordance: the backdrop is a separate, background-only item.
// Never capture an ancestor containing this button (that would feed back).
Button {
    id: root
    property Item backdropItem: null
    property string iconObjectName: objectName + "Icon"
    readonly property real blurMargin: 12
    readonly property rect backdropRect: {
        if (!backdropItem || !parent) return Qt.rect(0, 0, 1, 1)
        const center = parent.mapToItem(backdropItem, x + width / 2, y + height / 2)
        const extent = (width + blurMargin * 2) * scale
        return Qt.rect(center.x - extent / 2, center.y - extent / 2, extent, extent)
    }

    width: 32; height: 32
    padding: 4
    leftPadding: 4; rightPadding: 4; topPadding: 4; bottomPadding: 4
    hoverEnabled: enabled
    focusPolicy: enabled ? Qt.StrongFocus : Qt.NoFocus
    Accessible.name: "Close connections"
    scale: !enabled ? 1 : down ? 0.98 : hovered ? 1.04 : 1
    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
    containmentMask: QtObject {
        function contains(point: point): bool {
            const dx = point.x - root.width / 2
            const dy = point.y - root.height / 2
            return dx * dx + dy * dy <= root.width * root.width / 4
        }
    }
    contentItem: ConnectionIcon {
        objectName: root.iconObjectName
        name: "x"
    }
    background: Item {
        id: face
        ShaderEffectSource {
            id: backdrop
            objectName: root.objectName + "Backdrop"
            x: -root.blurMargin; y: -root.blurMargin
            width: face.width + root.blurMargin * 2
            height: face.height + root.blurMargin * 2
            sourceItem: root.backdropItem
            sourceRect: root.backdropRect
            live: root.visible
            visible: false
        }
        Item {
            id: circleMask
            width: backdrop.width; height: backdrop.height
            visible: false
            layer.enabled: true
            Rectangle {
                anchors.centerIn: parent
                width: face.width; height: face.height
                radius: width / 2
                color: "white"
                antialiasing: true
            }
        }
        MultiEffect {
            objectName: root.objectName + "Blur"
            x: backdrop.x; y: backdrop.y
            width: backdrop.width; height: backdrop.height
            source: backdrop
            visible: root.backdropItem !== null
            blurEnabled: true; blurMax: 8; blur: 0.8
            autoPaddingEnabled: false
            maskEnabled: true; maskSource: circleMask
        }
        Rectangle {
            objectName: root.objectName + "Background"
            anchors.fill: parent
            radius: width / 2
            antialiasing: true
            // QML colors use #AARRGGBB; the tint stays translucent at rest.
            color: root.enabled && root.down ? "#d006111c" : "#b306111c"
            border.width: root.enabled && root.visualFocus ? 1 : 0
            border.color: AccentTheme.color("#67caff")
            Behavior on color { ColorAnimation { duration: 120 } }
        }
    }
    HoverHandler { enabled: root.enabled; cursorShape: Qt.PointingHandCursor }
    Keys.onReturnPressed: if (enabled) clicked()
}
