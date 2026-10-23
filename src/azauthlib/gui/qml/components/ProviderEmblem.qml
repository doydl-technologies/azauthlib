pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window

// Shared by stationary cards and the moving spotlight subject. The service's
// original artwork never gets tinted or flattened into the surrounding badge.
ProviderSurface {
    id: root
    required property url logoSource
    property real logoSize: 66
    property string providerObjectName: ""
    property bool asynchronousLogo: true
    readonly property Item logoItem: originalLogo
    signal logoSettled(bool success)
    width: 108; height: 108; radius: width / 2; kind: 3
    SvgImageShadow {
        objectName: root.providerObjectName + "LogoShadow"
        source: originalLogo
    }
    Image {
        id: originalLogo
        objectName: root.providerObjectName + "Logo"
        readonly property url originalSvgSource: root.logoSource
        readonly property int renderEdge: Math.max(384,
            Math.ceil(root.logoSize * Screen.devicePixelRatio * 4))
        anchors.centerIn: parent
        width: root.logoSize; height: root.logoSize
        source: root.logoSource.toString().length ? "image://providerlogos/" + root.logoSource.toString().split("/").pop() : ""
        sourceSize: Qt.size(renderEdge, renderEdge)
        fillMode: Image.PreserveAspectFit
        asynchronous: root.asynchronousLogo
        retainWhileLoading: true
        smooth: true; mipmap: true
        onStatusChanged: {
            if (status === Image.Ready || status === Image.Error)
                root.logoSettled(status === Image.Ready)
        }
        Component.onCompleted: {
            if (status === Image.Ready || status === Image.Error)
                root.logoSettled(status === Image.Ready)
        }
    }
}
