import QtQuick

// Shared outer workspace: Home and Connections must have the same navy fill,
// soft downwards shadow, upper-left highlight and rounded illuminated rim.
ConnectionSurface {
    radius: 25
    topColor: "#173656"; middleColor: "#112d4d"; bottomColor: "#091a2d"
    depth: 10; blur: 20; shadowOffset: Qt.point(0, 10)
    shadowColor: "#d9000308"; lightColor: "#203f6a94"
    lightOffset: Qt.point(-2, -3); lightBlur: 12
    rimColor: "#5c7fb7e2"
}
