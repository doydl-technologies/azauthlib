import QtQuick
import QtQuick.Controls
import "../theme"

ToolTip {
    id: root
    width: Math.min(310, implicitWidth)
    padding: 11; delay: 650; timeout: 6000
    contentItem: Text {
        text: root.text; wrapMode: Text.Wrap; color: ConnectionTheme.text
        font.family: ConnectionTheme.body; font.pixelSize: 11; lineHeight: 1.4
    }
    background: ConnectionSurface { radius: 9; depth: 3; blur: 8 }
}
