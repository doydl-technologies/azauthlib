import QtQuick

QtObject {
    property real horizontalInset: 2.0   // Larger values make the selected face narrower
    property real verticalInset: 2.0     // Larger values make the selected face shorter
    property real horizontalOffset: 0.0  // Positive moves right; negative moves left
    property real verticalOffset: 0.0    // Positive moves down; negative moves up
}
