import QtQuick
import QtQuick.VectorImage
import QtQuick.Window
import "../theme"

// Theme only allowlisted application decoration. Brand art and semantic
// result badges keep their original colors; no flat colorization is applied.
Item {
    id: root
    property string name: "info"
    // Settings can preview a draft family without changing the saved app theme.
    property string accentFamily: AccentTheme.preset
    // Optional per-control artwork; an empty URL uses the shared symbol map.
    property url sourceOverride: ""
    property real visualSize: Math.min(width, height)
    property bool pulseResultBadge: false
    property real badgeTransitionOpacity: 1
    property real badgeTransitionOffset: 0
    readonly property Item resultBadgeItem: resultBadge
    readonly property bool showingResultDot: pulseResultBadge &&
        (name === "testPassed" || name === "testFailed")
    implicitWidth: 17; implicitHeight: 17
    readonly property var files: ({
        plug: "plugs/general/Monocolor-Filled-Sky-Blue-Single-Plug.svg",
        animatedPlug: "plugs/general/single-plug.svg",


        add: "plugs/connections/x-disconnected-wall-socket-plug-short-cord-25-thick.svg",


        create: "plugs/connections/plug-disconnected-filled.svg",

        edit: "actions/edit-content.svg",

        trash: "actions/Monocolor-Outlined-Pink-Red-trash.svg",

        check: "actions/Monocolor-Filled-Ice-Blue-check.svg",
        checkProfile: "actions/Monocolor-Filled-Sky-Blue-check.svg",
        checkActive: "actions/Monocolor-Filled-Light-Mint-Green-check.svg",
        checkSuccess: "actions/Monocolor-Filled-Mint-Green-check.svg",
        thumbsUp: "actions/Monocolor-Filled-Ice-Blue-thumbs-up-hand.svg",

        save: "actions/save.svg",

        chevron: "navigation/Monocolor-Filled-Sky-Blue-chevron-right.svg",
        down: "navigation/Monocolor-Filled-Dusty-Blue-chevron-down.svg",
        lock: "security/Monocolor-Filled-Dusty-Blue-padlock.svg",
        info: "status/information-alerts/Monocolor-Filled-Sky-Blue-info.svg",
        bolt: "plugs/badges/multicolor-circle-blue-single-plug-bolt_1.svg",
        testPassed: "plugs/badges/multicolor-circle-green-single-plug-check.svg",
        testFailed: "plugs/badges/multicolor-circle-red-single-plug-caution-triangle-alert_1.svg",
        x: "actions/Monocolor-Filled-Ice-Blue-close.svg",
        alert: "status/information-alerts/Monocolor-Filled-Apricot-Orange-triangle-alert.svg",
        alertError: "status/information-alerts/Monocolor-Filled-Soft-Coral-Pink-triangle-alert.svg",
        copy: "actions/Monocolor-Filled-Ice-Blue-Copy.svg",
        eye: "interaction/Monocolor-Filled-Dusty-Blue-eye.svg",
        eyeOff: "interaction/Monocolor-Filled-Dusty-Blue-eye-off.svg",
        internet: "technology/Monocolor-Filled-Ice-Blue-internet.svg",
        menu: "navigation/menu-hamberger-02.svg"
    })
    readonly property string assetPath: files[name] || files.info
    readonly property string filename: assetPath.substring(assetPath.lastIndexOf("/") + 1)
    readonly property string overrideFilename: sourceOverride.toString().split("/").pop()
    readonly property bool familyAsset: accentFamily !== "blue" &&
        (sourceOverride.toString().length === 0 ?
            ["plug", "check", "checkProfile", "thumbsUp", "chevron", "down", "lock", "info", "x", "copy", "eye", "eyeOff", "internet"].includes(name) :
            ["Monocolor-Filled-Sky-Blue-circle-plus.svg", "avatar-loading.svg"].includes(overrideFilename))
    readonly property bool compatibleAction: [
        "Monocolor-Filled-Sky-Blue-circle-plus.svg",
        "edit-utensil.svg",
        "Monocolor-Outlined-Pink-Red-trash.svg",
        "Multicolor-Filled-Mint-Green-Transparent-circle-check.svg",
        "Monocolor-Rounded-Filled-Light-Gray-Radio-Button-Checked.svg",
        "accessibility.svg", "paint-brush-solid.svg", "settings-gear.svg",
        "settings-horizontal.svg", "power-reset.svg", "save.svg"
    ].includes(overrideFilename) && sourceOverride.toString() ===
        Qt.resolvedUrl("../../../assets/icons/svg/actions/" + overrideFilename).toString()
    Image {
        objectName: "connectionCompatibleSvgImage"
        anchors.centerIn: parent
        width: root.visualSize; height: root.visualSize
        visible: root.compatibleAction || root.familyAsset
        source: root.familyAsset ? AccentTheme.artwork(root.sourceOverride.toString().length > 0 ? root.overrideFilename : root.filename, root.accentFamily) :
            root.compatibleAction ? "image://actionicons/" + encodeURIComponent(root.overrideFilename) : ""
        sourceSize.width: Math.ceil(width * Screen.devicePixelRatio * 4)
        sourceSize.height: Math.ceil(height * Screen.devicePixelRatio * 4)
        fillMode: Image.PreserveAspectFit
        // Tiny, cached toolbar textures. Keep requests on the GUI thread:
        // a Python image provider can deadlock a synchronous window reveal if
        // the render thread waits for an asynchronous callback holding the GIL.
        smooth: true; mipmap: true; asynchronous: false
    }
    VectorImage {
        id: originalSvg
        objectName: "connectionSvgImage"
        anchors.centerIn: parent
        anchors.alignWhenCentered: true
        width: root.visualSize; height: root.visualSize
        visible: root.name !== "refresh" && !root.compatibleAction && !root.familyAsset
        source: root.name === "refresh" || root.compatibleAction || root.familyAsset ? "" : root.sourceOverride.toString().length > 0 ?
            root.sourceOverride : Qt.resolvedUrl("../../../assets/icons/svg/" +
                (root.showingResultDot ? "plugs/general/single-plug-test-result-body.svg" : root.assetPath))
        fillMode: VectorImage.PreserveAspectFit
        preferredRendererType: VectorImage.CurveRenderer
        Item {
            id: resultBadge
            opacity: root.badgeTransitionOpacity
            transform: Translate { y: root.badgeTransitionOffset }
            objectName: "connectionResultBadge"
            // Both SVG badges share a 512-unit viewBox: center (384, 355.56), r=128.
            // Follow the rendered artwork, not the button's reserved icon space.
            x: originalSvg.width * 256 / 512
            y: originalSvg.height * 227.56 / 512
            width: originalSvg.width * 256 / 512
            height: width
            visible: root.showingResultDot
            // Keep the status core opaque throughout the pulse.
            readonly property color badgeColor: root.name === "testPassed" ? "#27d87b" : "#ff3b45"

            readonly property color coreColor: Qt.darker(badgeColor, 2.0 - 1.0 * pulseStrength)

            property real pulseStrength: 0
            SequentialAnimation on pulseStrength {
                running: resultBadge.visible && root.visible
                loops: Animation.Infinite

                NumberAnimation { from: 0; to: 1; duration: 1300; easing.type: Easing.InOutSine }
                NumberAnimation { from: 1; to: 0; duration: 1300; easing.type: Easing.InOutSine }
            }
            ConnectionSurface {
                objectName: "connectionResultDot"
                anchors.fill: parent
                radius: width / 2
                opacity: 1
                // A single native pass joins an opaque core to two colored glows.
                // No dark shadow, rim, border, or independently blended SVG badge.

                topColor: resultBadge.coreColor
                middleColor: resultBadge.coreColor
                bottomColor: resultBadge.coreColor

                borderWidth: 0
                borderColor: "transparent"
                rimColor: "transparent"
                diagonal: false
                shadowOffset: Qt.point(0, 0)
                lightOffset: Qt.point(0, 0)

                blur: width * (2 + 18 * resultBadge.pulseStrength) / 18
                lightBlur: width * (2 + 25 * resultBadge.pulseStrength) / 18

                // Both shadow slots supply glow rather than directional shadows.
                shadowColor: Qt.rgba(resultBadge.badgeColor.r, resultBadge.badgeColor.g,
                                    resultBadge.badgeColor.b, 0.18 + 0.82 * resultBadge.pulseStrength)

                lightColor: Qt.rgba(resultBadge.badgeColor.r, resultBadge.badgeColor.g,
                                   resultBadge.badgeColor.b, 0.60 * resultBadge.pulseStrength)
            }
        }
    }
    Loader {
        objectName: "connectionTestSignalLoader"
        anchors.centerIn: parent
        width: root.visualSize; height: root.visualSize
        visible: root.name === "refresh"
        active: visible && root.visible
        sourceComponent: ConnectionTestSignal { objectName: "connectionTestSignal" }
    }
}
