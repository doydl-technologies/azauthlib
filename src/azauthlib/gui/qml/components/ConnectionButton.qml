import QtQuick
import QtQuick.Controls
import "../theme"

Button {
    id: root
    property string symbol: ""
    property string secondarySymbol: ""
    property url iconSource: ""
    property real iconOffsetX: symbol === "add" ? -6 : 0
    property real iconOffsetY: 0
    property real iconTextSpacing: symbol === "add" ? 0 :
        (symbol.length > 0 || iconSource.toString().length > 0 ? 3 : 0)
    property real iconSize: ["plug", "add", "create", "edit", "save", "trash", "bolt", "testPassed", "testFailed"].includes(symbol) ? ConnectionTheme.plugButtonIconSize : 14
    // Artwork can grow without changing its reserved space or click target.

    property real iconVisualSize: symbol === "add" ? 32 : iconSize    

    property bool pulseResultBadge: symbol === "testPassed" || symbol === "testFailed"
    property string variant: "normal"
    property bool selected: false
    property bool alignLeft: false
    property bool visualEnabled: enabled
    property bool fadeDisabledState: true
    property bool hoverLiftEnabled: true
    property bool transitionBusy: false
    property real transitionOpacity: 1
    property real transitionOffset: 0
    property real badgeTransitionOpacity: 1
    property real badgeTransitionOffset: 0
    property real labelTransitionOpacity: 1
    property real labelTransitionOffset: 0
    readonly property Item labelTransitionItem: buttonLabel
    readonly property Item resultBadgeItem: primaryIcon.resultBadgeItem
    readonly property bool interactiveHover: enabled && hovered
    readonly property bool interactivePress: enabled && down
    readonly property bool interactiveFocus: enabled && visualFocus
    property color textColor: variant === "warning" ? "#ffe2a6" :
                              variant === "danger" ? "#ff94a2" : variant === "good" ? "#8ef2c8" : ConnectionTheme.text
    implicitWidth: contentRow.implicitWidth + 28
    implicitHeight: Math.max(35, iconSize + 11)
    padding: 12
    hoverEnabled: enabled
    focusPolicy: enabled ? Qt.StrongFocus : Qt.NoFocus
    opacity: (visualEnabled ? 1 : 0.37) * transitionOpacity
    Accessible.name: text
    Accessible.checked: selected
    font.family: ConnectionTheme.body
    font.pixelSize: 12
    font.weight: Font.ExtraBold
    Keys.onReturnPressed: if (enabled) clicked()
    HoverHandler { enabled: root.enabled; cursorShape: Qt.PointingHandCursor }
    transform: [Translate {
        y: root.hoverLiftEnabled && root.interactiveHover && !root.interactivePress ? -1 : 0
        Behavior on y { NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 140; easing.type: Easing.OutCubic } }
    }, Translate { y: root.transitionOffset }]
    Behavior on opacity {
        enabled: root.fadeDisabledState && !root.transitionBusy
        NumberAnimation { duration: ConnectionTheme.reducedMotion ? 0 : 130 }
    }
    contentItem: Item {
        Row {
            id: contentRow
            anchors.verticalCenter: parent.verticalCenter
            x: root.alignLeft ? 0 : (parent.width - width) / 2
            spacing: root.iconTextSpacing
            ConnectionIcon {
                id: primaryIcon
                anchors.verticalCenter: parent.verticalCenter
                visible: root.symbol.length > 0 || root.iconSource.toString().length > 0
                width: root.iconSize; height: root.iconSize
                visualSize: root.iconVisualSize
                pulseResultBadge: root.pulseResultBadge
                badgeTransitionOpacity: root.badgeTransitionOpacity
                badgeTransitionOffset: root.badgeTransitionOffset
                name: root.symbol
                sourceOverride: root.iconSource
                transform: Translate {
                    x: root.iconOffsetX
                    y: root.iconOffsetY
                }                
            }
            Text {
                id: buttonLabel
                objectName: root.objectName + "TransitionLabel"
                opacity: root.labelTransitionOpacity
                transform: Translate { y: root.labelTransitionOffset }
                text: root.text; font: root.font; color: root.textColor
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }








    background: ConnectionSurface {
        objectName: root.objectName + "Surface"
        sunken: root.selected || root.interactivePress
        recessedFill: root.selected || root.variant === "secondary" || root.interactivePress
        topColor: root.variant === "primary" ? (root.interactiveHover ? "#52b6ff" : "#36aaff") :
                  root.variant === "warning" ? (root.interactivePress ? "#382e22" : root.interactiveHover ? "#765732" : "#634a2b") :
                  root.variant === "destructive" ? "#bb3f55" : recessedFill ? "#071626" : root.interactiveHover ? "#21425f" : "#1a3550"
        middleColor: root.variant === "warning" ? (root.interactivePress ? "#302a22" : "#483822") :
                     root.variant === "primary" ? "#1f87e9" : root.variant === "destructive" ? "#bb3f55" : recessedFill ? "#0c2137" : "#142d4e"
        middleStop: root.variant === "primary" || recessedFill ? 0.5 : 0.55
        bottomColor: root.variant === "warning" ? (root.interactivePress ? "#29261f" : "#332b23") :
                     root.variant === "primary" ? "#0863d4" : root.variant === "destructive" ? "#a82f45" : recessedFill ? "#102b48" : "#0d2238"
        diagonal: root.variant !== "primary" && !recessedFill
        borderColor: root.interactiveFocus ? ConnectionTheme.accent : root.variant === "primary" ? "#6bc8ff" :
                     root.variant === "warning" ? (root.interactiveHover ? "#ffd083" : "#d9a552") :
                     root.variant === "destructive" ? "#dc6b7c" : root.selected ? "#5684b8" :
                     root.variant === "danger" ? "#669b4157" : root.variant === "good" ? "#378d7b" : "#345b85"
        borderWidth: root.interactiveFocus ? 2 : 1
        depth: root.interactiveHover ? 2 : 3
        blur: root.interactiveHover ? 4 : 7
        lightOffset: Qt.point(root.interactiveHover ? -1 : -2, root.interactiveHover ? -1 : -2)
        lightBlur: root.interactiveHover ? 4 : 6
        shadowColor: root.variant === "primary" ? "#5d1676d5" : "#03101e"
        lightColor: root.variant === "warning" ? "#665d482d" : root.variant === "primary" ? "transparent" : "#72345b85"
        rimColor: root.variant === "primary" ? "#40effbff" : "transparent"
    }
}
