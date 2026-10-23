pragma Singleton
import QtQuick

QtObject {
    property var controller: null
    readonly property string preset: controller ? controller.appearancePreferences.accent :
        (typeof accentPalette !== "undefined" && accentPalette ? accentPalette.initialAccent : "blue")
    readonly property bool showInfoButtons: controller ? controller.appearancePreferences.show_info_buttons : true
    readonly property bool customAccent: preset !== "blue"
    // Colored emblem faces sit on a fixed navy canvas. Keep their hue, but
    // temper the blush/highlight for alternate families; blue stays identical.
    readonly property real emblemTintStrength: customAccent ? 0.5 : 1.0
    readonly property real emblemLightStrength: customAccent ? 0.55 : 1.0
    readonly property var presets: [
        {key: "blue", label: "Blue", color: "#38a8ff"},
        {key: "gold", label: "Gold", color: "#f4c542"},
        {key: "orange", label: "Orange", color: "#ff963f"},
        {key: "pink", label: "Pink", color: "#ec65ad"},
        {key: "purple", label: "Purple", color: "#ad78f5"},
        {key: "teal", label: "Teal", color: "#2dd4bf"}
    ]
    function paletteFor(key) {
        switch (key) {
        case "gold": return {accent: "#f4c542", focus: "#ffe59a", border: "#f8d879", glow: "#e8ad24", top: "#9b771c", middle: "#775710", bottom: "#503908"}
        case "orange": return {accent: "#ff963f", focus: "#ffd0a3", border: "#ffb776", glow: "#f57c24", top: "#b86224", middle: "#944515", bottom: "#65300f"}
        case "pink": return {accent: "#ec65ad", focus: "#ffc0e0", border: "#f497c8", glow: "#e44196", top: "#b83f83", middle: "#943265", bottom: "#6b1e47"}
        case "purple": return {accent: "#ad78f5", focus: "#d8bdff", border: "#c5a0fc", glow: "#9954ed", top: "#8850cb", middle: "#6939ae", bottom: "#492578"}
        case "teal": return {accent: "#2dd4bf", focus: "#a0f5e8", border: "#6be5d5", glow: "#18baa7", top: "#167f79", middle: "#136963", bottom: "#0b4947"}
        default: return {accent: "#38a8ff", focus: "#73ceff", border: "#65caff", glow: "#1996ff", top: "#36aaff", middle: "#1f87e9", bottom: "#0863d4"}
        }
    }
    function withAlpha(value, amount) {
        const c = Qt.lighter(value, 1)
        return Qt.rgba(c.r, c.g, c.b, amount)
    }
    function emblemFill(reference) {
        if (!customAccent) return reference
        const navy = Qt.lighter(reference, 1)
        const family = Qt.lighter(color(reference), 1)
        const strength = emblemTintStrength
        return Qt.rgba(navy.r + (family.r - navy.r) * strength,
                       navy.g + (family.g - navy.g) * strength,
                       navy.b + (family.b - navy.b) * strength, family.a)
    }
    function emblemLight(reference) {
        const family = Qt.lighter(color(reference), 1)
        return withAlpha(family, family.a * emblemLightStrength)
    }
    // Translate only explicitly themeable reference colors. The native bridge
    // preserves perceptual lightness, alpha and shade differences in OKLCH.
    function color(reference) {
        return colorFor(reference, preset)
    }
    function colorFor(reference, family) {
        return typeof accentPalette !== "undefined" && accentPalette ?
            accentPalette.colorFor(reference.toString(), family) : reference
    }
    function artwork(filename, family) {
        return "image://accentart/" + (family || preset) + "/" + encodeURIComponent(filename)
    }
    readonly property color outlineMuted: color("#345b85")
    readonly property color outlineNormal: color("#388bd0")
    readonly property color outlineHover: color("#579bd0")
    readonly property color reflection: color("#7ddcff")
    readonly property color animationBright: color("#43c6ff")
    readonly property color animationDim: color("#2a74bd")
    readonly property var palette: paletteFor(preset)
    readonly property color accent: palette.accent
    readonly property color focus: palette.focus
    readonly property color border: palette.border
    readonly property color glow: palette.glow
    readonly property color primaryTop: palette.top
    readonly property color primaryMiddle: palette.middle
    readonly property color primaryBottom: palette.bottom
}
