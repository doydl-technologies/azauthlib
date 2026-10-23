import QtQuick
import "../theme"

// A single smooth outline, without inset duplicate rims or straight edge glints.
ConnectionSurface {
    radius: 15
    borderColor: Theme.darkMode ? AccentTheme.color("#5684b8") : AccentTheme.color("#90bfe9")
    topColor: Theme.darkMode ? "#1a3550" : "#ffffff"
    middleColor: Theme.darkMode ? "#142d4e" : "#f4f9ff"
    bottomColor: Theme.darkMode ? "#0d2238" : "#e9f3ff"
    depth: 14
    blur: 32
    shadowColor: "#bb000000"
    lightColor: "transparent"
    crispOutline: true
    outlineWidth: 1
}
