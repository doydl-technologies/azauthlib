import QtQuick
import QtQuick.VectorImage

// Render every SVG in its saved colors, regardless of its filename.
// Result pulses and the testing frame sequence are separate animations.
Item {
    id: root
    property string name: "info"
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

        trash: "actions/Monocolor-Outlined-Red-trash.svg",        

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
        copy: "actions/Monocolor-Filled-Ice-Blue-copy.svg",
        eye: "interaction/Monocolor-Filled-Dusty-Blue-eye.svg",
        eyeOff: "interaction/Monocolor-Filled-Dusty-Blue-eye-off.svg",
        internet: "technology/Monocolor-Filled-Ice-Blue-internet.svg",
        menu: "navigation/menu-hamberger-02.svg" 
    })
    readonly property string assetPath: files[name] || files.info
    readonly property string filename: assetPath.substring(assetPath.lastIndexOf("/") + 1)
    VectorImage {
        id: originalSvg
        objectName: "connectionSvgImage"
        anchors.centerIn: parent
        anchors.alignWhenCentered: true
        width: root.visualSize; height: root.visualSize
        visible: root.name !== "refresh"
        source: root.name === "refresh" ? "" : root.sourceOverride.toString().length > 0 ?
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
