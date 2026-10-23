import QtQuick
import QtQuick.Window

Item {
    id: root
    property string avatarId: ""
    readonly property int rasterEdge: Math.max(128, Math.ceil(Math.max(width, height) * Screen.devicePixelRatio / 64) * 64)
    readonly property bool loading: avatarId.length > 0 && artwork.status !== Image.Ready
    Image {
        id: artwork
        objectName: root.objectName + "Artwork"
        anchors.fill: parent
        visible: status === Image.Ready
        source: root.avatarId.length > 0 ? "image://profileavatars/" + encodeURIComponent(root.avatarId) : ""
        sourceSize.width: root.rasterEdge
        sourceSize.height: root.rasterEdge
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        retainWhileLoading: false
        smooth: true
        mipmap: true
    }
    ConnectionIcon {
        objectName: root.objectName + "DefaultPlug"
        anchors.fill: parent
        visible: root.avatarId.length === 0
        name: "plug"
    }
    ConnectionIcon {
        objectName: root.objectName + "LoadingPlaceholder"
        anchors.centerIn: parent
        width: parent.width * 0.8; height: parent.height * 0.8
        visible: root.loading
        sourceOverride: Qt.resolvedUrl("../../../assets/icons/svg/interaction/avatar-loading.svg")
    }
}
