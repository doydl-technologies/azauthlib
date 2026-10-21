import QtQuick
import "../theme"

TextEdit {
    id: root
    required property string policyTopic
    required property string policyHtml
    signal documentReady(string topic, var document)
    signal policyRequested(string topic)
    objectName: "managerLegalDocument_" + policyTopic
    text: policyHtml
    textFormat: TextEdit.RichText
    wrapMode: TextEdit.Wrap
    readOnly: true
    selectByMouse: true
    DrawerLinkCursor { textItem: root }
    color: "#c8daed"
    selectionColor: "#345b85"
    selectedTextColor: "#edf4ff"
    font.family: ConnectionTheme.body
    font.pixelSize: 10
    Accessible.name: policyTopic === "terms" ? "Terms of Use" : "Privacy Policy"
    Component.onCompleted: documentReady(policyTopic, textDocument)
    onLinkActivated: link => {
        if (link === "policy:terms" || link === "policy:privacy")
            root.policyRequested(link.substring(7))
        else if (link.toLowerCase().startsWith("https://") ||
                 link === "mailto:privacy@doydl.studio" || link === "mailto:legal@doydl.studio")
            Qt.openUrlExternally(link)
    }
}
