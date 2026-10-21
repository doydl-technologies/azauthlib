import QtQuick
import QtQuick.Window

// A real top-level splash, not an overlay inside the main application window.
Window {
    id: root
    required property url logoSource
    property bool previewMode: false
    property real progress: 0
    property string statusText: "Starting azauthlib…"
    property bool failed: false
    signal retryRequested()
    signal abortRequested()
    objectName: "startupPage"

 
    width: 1300
    height: 700
    minimumWidth: 1300
    maximumWidth: 1300
    minimumHeight: 700
    maximumHeight: 700

    // A normal frameless window gets a taskbar button while startup is visible.
    // It is not always-on-top, so other applications can cover it.
    flags: Qt.Window | Qt.FramelessWindowHint
    
    // A nested Window would otherwise follow its hidden parent's visibility.
    transientParent: null
    visible: true
    title: "azauthlib"
    // Transparent native corners let the rounded background reveal the desktop.
    color: "transparent"
    // The shared Python loader centers this on the launch monitor's work area.
    StartupScreen {
        objectName: "startupContent"
        anchors.fill: parent
        logoSource: root.logoSource
        visible: root.visible
        progress: root.progress
        statusText: root.statusText
        failed: root.failed
        onRetryRequested: root.retryRequested()
        onAbortRequested: root.previewMode ? root.close() : root.abortRequested()
    }
    Shortcut {
        sequence: "Escape"
        enabled: root.previewMode && root.visible
        onActivated: root.close()
    }
    // Programmatic startup completion hides the splash, so this only handles
    // a user/system close (e.g. Alt+F4) while startup is still pending.
    onClosing: event => {
        if (!previewMode) {
            event.accepted = false
            abortRequested()
        }
    }
}
