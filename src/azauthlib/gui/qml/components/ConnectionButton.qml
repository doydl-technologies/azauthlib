import QtQuick
import QtQuick.Controls
import "../theme"

Button {
    id: root
    property string symbol: ""
    property string iconAccentFamily: AccentTheme.preset
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
    property bool tileLayout: false
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
    property color textColor: variant === "cancel" ? "#ffffff" : variant === "warning" ? "#ffe2a6" :
                              variant === "danger" ? "#ff94a2" : variant === "good" ? "#8ef2c8" : ConnectionTheme.text
    property color outlineColor: variant === "primary" ? AccentTheme.border :
        variant === "cancel" ? Qt.lighter(ConnectionTheme.cancelColor, 1.35) :
        variant === "warning" ? (interactiveHover ? "#ffd083" : "#d9a552") :
        variant === "destructive" ? "#dc6b7c" : selected ? AccentTheme.color("#5684b8") :
        variant === "danger" ? "#669b4157" : variant === "good" ? AccentTheme.color("#378d7b") : AccentTheme.color("#345b85")
    property color focusOutlineColor: ConnectionTheme.accent
    implicitWidth: tileLayout ? 110 : contentRow.implicitWidth + 28
    implicitHeight: tileLayout ? 46 : Math.max(35, iconSize + 11)
    padding: tileLayout ? 4 : 12
    hoverEnabled: enabled
    focusPolicy: enabled ? Qt.StrongFocus : Qt.NoFocus
    opacity: (visualEnabled ? 1 : 0.37) * transitionOpacity
    Accessible.name: text
    Accessible.checked: selected
    font.family: ConnectionTheme.body
    font.pixelSize: tileLayout ? 9 : 12
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
        Item {
            id: contentRow
            // An icon-only button has no trailing label gap. Including that
            // invisible spacing shifts every drawer/picker close X off center.
            readonly property real labelGap: primaryIcon.visible && root.text.length > 0 ? root.iconTextSpacing : 0
            implicitWidth: root.tileLayout ? parent.width :
                (primaryIcon.visible ? primaryIcon.width : 0) + labelGap + buttonLabel.implicitWidth
            implicitHeight: Math.max(primaryIcon.visible ? primaryIcon.height : 0, buttonLabel.implicitHeight)
            width: root.tileLayout ? parent.width : implicitWidth
            height: root.tileLayout ? parent.height : implicitHeight
            anchors.verticalCenter: parent.verticalCenter
            x: root.alignLeft ? 0 : (parent.width - width) / 2
            transform: Translate {
                y: root.tileLayout ? 3 : 0
            }
            ConnectionIcon {
                id: primaryIcon
                anchors.verticalCenter: root.tileLayout ? undefined : parent.verticalCenter
                x: root.tileLayout ? (parent.width - width) / 2 : 0
                visible: root.symbol.length > 0 || root.iconSource.toString().length > 0
                width: root.iconSize; height: root.iconSize
                visualSize: root.iconVisualSize
                pulseResultBadge: root.pulseResultBadge
                badgeTransitionOpacity: root.badgeTransitionOpacity
                badgeTransitionOffset: root.badgeTransitionOffset
                name: root.symbol
                accentFamily: root.iconAccentFamily
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
                anchors.verticalCenter: root.tileLayout ? undefined : parent.verticalCenter
                x: root.tileLayout ? 0 : (primaryIcon.visible ? primaryIcon.width : 0) + contentRow.labelGap
                y: root.tileLayout ? (primaryIcon.visible ? primaryIcon.height + 2 : 0) : 0
                width: root.tileLayout ? parent.width : implicitWidth
                height: root.tileLayout ? Math.max(0, parent.height - y) : implicitHeight
                horizontalAlignment: root.tileLayout ? Text.AlignHCenter : Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                wrapMode: root.tileLayout ? Text.Wrap : Text.NoWrap
                maximumLineCount: root.tileLayout ? 2 : 1
                fontSizeMode: root.tileLayout ? Text.Fit : Text.FixedSize
                minimumPixelSize: 8
                elide: root.tileLayout ? Text.ElideRight : Text.ElideNone
            }
        }
    }








    background: ConnectionSurface {
        objectName: root.objectName + "Surface"
        sunken: root.selected || root.interactivePress
        recessedFill: root.selected || root.variant === "secondary" || root.interactivePress
        topColor: root.variant === "primary" ? (root.interactiveHover ? Qt.lighter(AccentTheme.primaryTop, 1.15) : AccentTheme.primaryTop) :
                  root.variant === "cancel" ? (root.interactivePress ? Qt.darker(ConnectionTheme.cancelColor, 1.25) :
                      Qt.lighter(ConnectionTheme.cancelColor, root.interactiveHover ? 1.25 : 1.12)) :
                  root.variant === "warning" ? (root.interactivePress ? "#382e22" : root.interactiveHover ? "#765732" : "#634a2b") :
                  root.variant === "destructive" ? "#bb3f55" : recessedFill ? "#071626" : root.interactiveHover ? "#21425f" : "#1a3550"
        middleColor: root.variant === "cancel" ? (root.interactivePress ? Qt.darker(ConnectionTheme.cancelColor, 1.35) :
                         root.interactiveHover ? Qt.lighter(ConnectionTheme.cancelColor, 1.1) : ConnectionTheme.cancelColor) :
                     root.variant === "warning" ? (root.interactivePress ? "#302a22" : "#483822") :
                     root.variant === "primary" ? AccentTheme.primaryMiddle : root.variant === "destructive" ? "#bb3f55" : recessedFill ? "#0c2137" : "#142d4e"
        middleStop: root.variant === "primary" || recessedFill ? 0.5 : 0.55
        bottomColor: root.variant === "cancel" ? Qt.darker(ConnectionTheme.cancelColor, root.interactivePress ? 1.5 : 1.22) :
                     root.variant === "warning" ? (root.interactivePress ? "#29261f" : "#332b23") :
                     root.variant === "primary" ? AccentTheme.primaryBottom : root.variant === "destructive" ? "#a82f45" : recessedFill ? "#102b48" : "#0d2238"
        diagonal: root.variant !== "primary" && !recessedFill
        borderColor: root.interactiveFocus ? root.focusOutlineColor : root.outlineColor
        borderWidth: root.interactiveFocus ? 2 : 1
        depth: root.interactiveHover ? 2 : 3
        blur: root.interactiveHover ? 4 : 7
        lightOffset: Qt.point(root.interactiveHover ? -1 : -2, root.interactiveHover ? -1 : -2)
        lightBlur: root.interactiveHover ? 4 : 6
        shadowColor: root.variant === "primary" ? AccentTheme.withAlpha(AccentTheme.glow, 0.36) : "#03101e"
        lightColor: root.variant === "cancel" ? AccentTheme.color("#668a93a5") : root.variant === "warning" ? "#665d482d" : root.variant === "primary" ? "transparent" : AccentTheme.color("#72345b85")
        rimColor: root.variant === "primary" ? AccentTheme.color("#40effbff") : "transparent"
    }
}
