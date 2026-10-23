pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import "../theme"

Button {
    id: root

    property url iconSource
    property var visualStyle: null

    readonly property color effectiveText: visualStyle ? visualStyle.text : Theme.textOnAccent
    readonly property color effectiveTop: visualStyle ? visualStyle.top : Theme.accentTop
    readonly property color effectiveBottom: visualStyle ? visualStyle.bottom : Theme.accentBottom
    readonly property color effectiveHoverTop: visualStyle ? visualStyle.hoverTop : Theme.accentHover
    readonly property color effectivePressedTop: visualStyle ? visualStyle.pressedTop : Theme.accentPressed
    readonly property color effectiveBorder: visualStyle ? visualStyle.border : Theme.accentBorder
    readonly property color effectiveFocusBorder: visualStyle ? visualStyle.focusBorder : Theme.focus
    readonly property color effectiveGlow: visualStyle ? visualStyle.glow : Theme.accentGlow
    readonly property color effectiveHighlight: visualStyle ? visualStyle.highlight : AccentTheme.color("#d5f3ff")

    implicitWidth: 180
    implicitHeight: 44
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: text

    Keys.onReturnPressed: clicked()

    HoverHandler {
        acceptedDevices: PointerDevice.Mouse
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    contentItem: RowLayout {
        spacing: 8

        Item { Layout.fillWidth: true }
        Image {
            objectName: root.objectName + "Icon"
            visible: root.iconSource.toString().length > 0
            Layout.preferredWidth: visible ? 20 : 0
            Layout.preferredHeight: 20
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
            sourceSize: Qt.size(80, 80)
            smooth: true
            mipmap: true
            // Disabled state changes opacity only, never the SVG's colors.
            opacity: root.enabled ? 1 : 0.37
        }
        Text {
            objectName: root.objectName + "Label"
            text: root.text
            color: root.enabled ? root.effectiveText :
                   root.visualStyle ? root.visualStyle.disabledText : Theme.disabled
            font.family: Theme.fontFamily
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }
        Item { Layout.fillWidth: true }
    }

    background: Item {
        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: root.visualStyle ? root.visualStyle.radius + 2 : 12
            color: root.effectiveGlow
            opacity: !root.enabled ?
                         (root.visualStyle ? root.visualStyle.disabledGlowOpacity : 0) :
                     root.pressed ?
                         (root.visualStyle ? root.visualStyle.pressedGlowOpacity : 0.18) :
                     root.hovered ?
                         (root.visualStyle ? root.visualStyle.hoverGlowOpacity : 0.42) :
                         (root.visualStyle ? root.visualStyle.glowOpacity : 0.29)
            layer.enabled: opacity > 0
            layer.effect: MultiEffect {
                blurEnabled: true
                blur: root.visualStyle ? root.visualStyle.glowBlur : 0.46
                blurMax: root.visualStyle ? root.visualStyle.glowBlurMax : 20
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: root.visualStyle ? root.visualStyle.radius : 10
            border.width: root.activeFocus ?
                              (root.visualStyle ? root.visualStyle.focusBorderWidth : 2) :
                              (root.visualStyle ? root.visualStyle.borderWidth : 1)
            border.color: !root.enabled && root.visualStyle ? root.visualStyle.disabledBorder :
                          root.activeFocus ? root.effectiveFocusBorder : root.effectiveBorder
            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: !root.enabled && root.visualStyle ? root.visualStyle.disabledTop :
                           root.pressed ? root.effectivePressedTop :
                           root.hovered ? root.effectiveHoverTop : root.effectiveTop
                }
                GradientStop {
                    position: 1.0
                    color: !root.enabled && root.visualStyle ? root.visualStyle.disabledBottom :
                                                                 root.effectiveBottom
                }
            }


            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                height: 1
                color: root.effectiveHighlight
                opacity: !root.enabled ? 0 :
                         root.visualStyle ? root.visualStyle.highlightOpacity : 0.62
            }
        }
    }
}
