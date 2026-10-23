pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    property var topicData: ({})
    property string markdownText: ""
    property string preloadedMarkdownText: ""
    property var legalDocuments: ({})
    property var legalDocumentUrls: ({})
    property string legalTopic: ""
    readonly property bool documentVisible: markdownText.length > 0 || legalTopic.length > 0
    signal dismissed()
    signal markdownDocumentReady(var document)
    signal legalDocumentReady(string topic, var document)
    signal legalTopicRequested(string topic)
    signal fullDocumentRequested(string topic)
    property real copyOpacity: 1
    onTopicDataChanged: {
        Qt.callLater(() => {
            const scroller = helpScroll.contentItem as Flickable
            if (scroller) scroller.contentY = 0
            contentTransition.restart()
        })
    }
    NumberAnimation {
        id: contentTransition
        target: root; property: "copyOpacity"; from: 0.3; to: 1; duration: ConnectionTheme.reducedMotion ? 0 : 340
    }
    Rectangle { x: 0; y: 17; width: 1; height: parent.height - 34; color: AccentTheme.color("#4573b1dd") }
    ColumnLayout {
        anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14
        anchors.topMargin: 20; anchors.bottomMargin: 16
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            ConnectionButton {
                objectName: "managerHelpCloseButton"
                symbol: "x"; implicitWidth: 28; implicitHeight: 28
                padding: 6
                Accessible.name: "Close help (Escape)"
                onClicked: root.dismissed()
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 10
            ConnectionSurface {
                Layout.preferredWidth: 35; Layout.preferredHeight: 35
                radius: 11; angle: 145; topColor: "#193959"; middleColor: "#112a43"; bottomColor: "#091a2d"
                Image {
                    objectName: "managerHelpTopicIcon"
                    anchors.centerIn: parent
                    width: 22
                    height: 22          
                    source: AccentTheme.customAccent ? AccentTheme.artwork("Monocolor-Filled-Sky-Blue-info-borderless.svg") :
                        Qt.resolvedUrl("../../../assets/icons/svg/status/information-alerts/Monocolor-Filled-Sky-Blue-info-borderless.svg")
                    sourceSize: Qt.size(96, 96)
                    fillMode: Image.PreserveAspectFit
                    smooth: true; mipmap: true
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                Text {
                    objectName: "managerHelpTitle"
                    Layout.fillWidth: true; text: root.topicData.title || "Help"
                    color: ConnectionTheme.text; font.family: ConnectionTheme.heading; font.pixelSize: 16; font.weight: Font.ExtraBold
                    wrapMode: Text.Wrap
                }
                Text {
                    Layout.fillWidth: true; text: root.topicData.subtitle || ""
                    color: ConnectionTheme.muted; font.family: ConnectionTheme.body; font.pixelSize: 11
                    wrapMode: Text.Wrap
                }
            }
        }
        ConnectionSurface {
            Layout.fillWidth: true; Layout.fillHeight: true
            radius: 16; sunken: true; depth: 7; blur: 15
            shadowColor: "#ab03101e"; lightColor: AccentTheme.color("#70345b85")
            lightOffset: Qt.point(-5, -5); lightBlur: 12; crispOutline: true
            ScrollView {
                id: helpScroll
                objectName: "managerHelpScroll"
                anchors.fill: parent; anchors.margins: 16
                anchors.rightMargin: 6
                rightPadding: ConnectionTheme.scrollBarGutter
                contentWidth: availableWidth
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical: ScrollBar {
                    objectName: "managerHelpVerticalBar"
                    parent: helpScroll
                    x: helpScroll.width - width
                    y: 0
                    width: ConnectionTheme.scrollBarWidth
                    height: helpScroll.height
                    policy: ScrollBar.AsNeeded
                }
                ColumnLayout {
                    objectName: "managerHelpScrollContent"
                    width: helpScroll.availableWidth; spacing: 18
                    opacity: root.copyOpacity
                    Loader {
                        Layout.fillWidth: true
                        // Load once during interface preparation behind the
                        // splash. Keep the document alive across shelf topics.
                        width: helpScroll.availableWidth
                        active: root.preloadedMarkdownText.length > 0
                        visible: root.markdownText.length > 0
                        sourceComponent: TextEdit {
                            id: aboutDocument
                            objectName: "managerAboutDocument"
                            // Give each supplied metadata field its own line.
                            text: root.preloadedMarkdownText.replace(/^(\*\*[^*\n]+:\*\*.*)$/gm, "$1  ")
                            textFormat: TextEdit.MarkdownText
                            wrapMode: TextEdit.Wrap
                            readOnly: true; selectByMouse: true
                            DrawerLinkCursor { textItem: aboutDocument }
                            color: "#c8daed"; selectionColor: AccentTheme.color("#345b85"); selectedTextColor: "#edf4ff"
                            font.family: ConnectionTheme.body
                            font.pixelSize: 10                            
                            Component.onCompleted: root.markdownDocumentReady(textDocument)
                            Accessible.name: "azauthlib independence and third-party legal notice"
                            onLinkActivated: link => {
                                if (link === "https://github.com/doydl-technologies/azauthlib")
                                    Qt.openUrlExternally(link)
                            }
                        }
                    }
                    Loader {
                        Layout.fillWidth: true
                        width: helpScroll.availableWidth
                        active: (root.legalDocuments.terms || "").length > 0
                        visible: root.legalTopic === "terms" && active
                        sourceComponent: LegalPolicyDocument {
                            policyTopic: "terms"
                            policyHtml: root.legalDocuments.terms || ""
                            onDocumentReady: (topic, document) => root.legalDocumentReady(topic, document)
                            onPolicyRequested: topic => root.legalTopicRequested(topic)
                        }
                    }
                    Loader {
                        Layout.fillWidth: true
                        width: helpScroll.availableWidth
                        active: (root.legalDocuments.privacy || "").length > 0
                        visible: root.legalTopic === "privacy" && active
                        sourceComponent: LegalPolicyDocument {
                            policyTopic: "privacy"
                            policyHtml: root.legalDocuments.privacy || ""
                            onDocumentReady: (topic, document) => root.legalDocumentReady(topic, document)
                            onPolicyRequested: topic => root.legalTopicRequested(topic)
                        }
                    }
                    Text {
                        objectName: "managerHelpDescription"
                        visible: !root.documentVisible
                        Layout.fillWidth: true; text: root.topicData.description || ""
                        textFormat: Text.PlainText; wrapMode: Text.Wrap
                        color: "#c8daed"; font.family: ConnectionTheme.body; font.pixelSize: 12
                        lineHeightMode: Text.FixedHeight; lineHeight: 20
                    }
                    ConnectionSurface {
                        visible: !root.documentVisible
                        Layout.fillWidth: true; implicitHeight: noteCopy.implicitHeight + 24
                        radius: 10; topColor: "#1a3856"; middleColor: "#142f4d"; bottomColor: "#102b49"
                        depth: 3; blur: 8; borderColor: AccentTheme.color("#80345b85")
                        Rectangle { x: 0; y: 12; width: 2; height: parent.height - 24; radius: 1; color: AccentTheme.color("#9838a8ff") }
                        ColumnLayout {
                            id: noteCopy
                            x: 14; y: 12; width: parent.width - 26; spacing: 5
                            Text {
                                Layout.fillWidth: true; text: (root.topicData.noteTitle || "").toUpperCase()
                                color: AccentTheme.color("#a2d2f6"); font.family: ConnectionTheme.body; font.pixelSize: 9
                                font.weight: Font.ExtraBold; font.letterSpacing: 0.85; wrapMode: Text.Wrap
                            }
                            Text {
                                id: noteText
                                objectName: "managerHelpNote"
                                DrawerLinkCursor { textItem: noteText }
                                Layout.fillWidth: true; text: root.topicData.note || ""
                                textFormat: Text.RichText; wrapMode: Text.Wrap
                                color: "#c6dbed"; font.family: ConnectionTheme.body; font.pixelSize: 11
                                lineHeightMode: Text.FixedHeight; lineHeight: 18
                            }
                        }
                    }
                    Text {
                        visible: !root.documentVisible
                        Layout.fillWidth: true; text: (root.topicData.section || "").toUpperCase()
                        color: ConnectionTheme.muted; font.family: ConnectionTheme.mono; font.pixelSize: 9
                        font.weight: Font.ExtraBold; font.letterSpacing: 1.1; wrapMode: Text.Wrap
                    }
                    ColumnLayout {
                        visible: !root.documentVisible
                        Layout.fillWidth: true; spacing: 12
                        Repeater {
                            model: root.topicData.steps || []
                            RowLayout {
                                id: stepRow
                                required property string modelData
                                required property int index
                                Layout.fillWidth: true; spacing: 10
                                ConnectionSurface {
                                    Layout.preferredWidth: 23; Layout.preferredHeight: 23; Layout.alignment: Qt.AlignTop
                                    radius: 7; sunken: true; recessedFill: true; depth: 2; blur: 4
                                    Text {
                                        anchors.centerIn: parent; text: String(stepRow.index + 1).padStart(2, "0")
                                        color: AccentTheme.color("#96c8f1"); font.family: ConnectionTheme.mono; font.pixelSize: 9
                                    }
                                }
                                Text {
                                    id: stepText
                                    DrawerLinkCursor { textItem: stepText }
                                    Layout.fillWidth: true; text: stepRow.modelData; textFormat: Text.RichText; wrapMode: Text.Wrap
                                    color: "#c4d8eb"; font.family: ConnectionTheme.body; font.pixelSize: 11
                                    lineHeightMode: Text.FixedHeight; lineHeight: 17
                                }
                            }
                        }
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            ConnectionButton {
                objectName: "managerHelpDoneButton"
                text: "Got it"; symbol: "thumbsUp"; iconSize: 16; implicitHeight: 29; font.pixelSize: 10
                onClicked: root.dismissed()
            }
        }
    }
}
