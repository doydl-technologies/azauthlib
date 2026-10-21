import QtQuick
import QtQuick.Effects
import "../theme"

// Connections keeps its recessed fill, but shares the main form's ring colors,
// width, corner radius, glow and timing. Used by every entry and method selector.
Item {
    id: root
    // TextField and ComboBox have different base types but both expose these states.
    required property var control
    readonly property string controlName: control ? control.objectName : ""
    readonly property bool controlEnabled: control ?
        (control.visualEnabled !== undefined ? control.visualEnabled : control.enabled) : false
    readonly property bool controlFocused: control ? control.activeFocus : false
    readonly property bool controlHovered: control ? control.hovered : false
    readonly property bool controlInvalid: control && control.validationError !== undefined &&
                                          control.validationError.length > 0
    property var visualStyle: FormTheme.current.tenantField

    Rectangle {
        objectName: root.controlName + "FocusGlow"
        anchors.fill: parent; anchors.margins: -2
        radius: root.visualStyle.radius + 2
        color: root.visualStyle.focusGlow
        opacity: root.controlEnabled && root.controlFocused ? root.visualStyle.focusGlowOpacity : 0
        layer.enabled: opacity > 0
        layer.effect: MultiEffect { blurEnabled: true; blur: 0.42; blurMax: 16 }
        Behavior on opacity { NumberAnimation { duration: 140 } }
    }
    ConnectionSurface {
        anchors.fill: parent
        radius: root.visualStyle.radius
        sunken: true; recessedFill: true; depth: 2; blur: 5
        lightOffset: Qt.point(-2, -2); lightBlur: 4; lightColor: "#5a345b85"
        borderColor: root.controlInvalid ? "#ff889e" : root.controlEnabled ? root.visualStyle.border : root.visualStyle.disabledBorder
        borderWidth: root.visualStyle.borderWidth
    }
    Rectangle {
        objectName: root.controlName + "HoverRing"
        anchors.fill: parent
        radius: root.visualStyle.hoverRingRadius >= 0 ? root.visualStyle.hoverRingRadius : root.visualStyle.radius
        color: "transparent"
        border.width: root.visualStyle.hoverBorderWidth
        border.color: root.visualStyle.hoverBorder
        opacity: root.controlEnabled && root.controlHovered && !root.controlFocused ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 100 } }
    }
    Rectangle {
        objectName: root.controlName + "FocusRing"
        anchors.fill: parent
        radius: root.visualStyle.focusRingRadius >= 0 ? root.visualStyle.focusRingRadius : root.visualStyle.radius
        color: "transparent"
        border.width: root.controlFocused ? root.visualStyle.focusBorderWidth : 0
        border.color: root.visualStyle.focusBorder
        visible: root.controlEnabled && root.controlFocused
        Behavior on border.width { NumberAnimation { duration: 100 } }
    }
}
