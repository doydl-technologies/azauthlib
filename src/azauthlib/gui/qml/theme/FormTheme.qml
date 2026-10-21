pragma Singleton

import QtQuick

QtObject {
    readonly property FormThemeDefinition dark: DarkFormTheme {}
    readonly property FormThemeDefinition light: LightFormTheme {}
    readonly property FormThemeDefinition current: Theme.darkMode ? dark : light
}
