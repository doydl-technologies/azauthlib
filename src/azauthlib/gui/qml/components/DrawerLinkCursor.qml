import QtQuick

// Passive: do not intercept activation, scrolling, or text selection.
HoverHandler {
    id: root
    required property var textItem
    objectName: textItem.objectName + "LinkCursor"
    enabled: textItem.enabled
    cursorShape: textItem.hoveredLink.length > 0 ? Qt.PointingHandCursor :
        (textItem.selectByMouse !== undefined && textItem.selectByMouse ? Qt.IBeamCursor : Qt.ArrowCursor)
}
