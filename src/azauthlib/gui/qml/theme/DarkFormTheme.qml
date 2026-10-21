import QtQuick

FormThemeDefinition {
    id: darkTheme

    // Layered gradients take precedence over the alternate multi-stop fill.
    // With both switches disabled, fields use surfaceTop/surfaceBottom.
    property bool useLayeredFieldGradient: true
    property Gradient layeredCredentialsGradient: Gradient {
        GradientStop { position: 0.00; color: "#091428" }
        GradientStop { position: 0.35; color: "#0B182C" }
        GradientStop { position: 0.75; color: "#0E2139" }
        GradientStop { position: 1.00; color: "#0F2236" }
    }
    property color fieldGlowColor: Qt.rgba(15 / 255, 38 / 255, 66 / 255, 0.85)
    property point fieldGlowCenter: Qt.point(0.6, 1.0)
    property size fieldGlowRadii: Qt.size(0.7, 1.3)

    // Alternate multi-stop fill when the layered gradient is disabled.
    property bool useFiveStopFieldGradient: true
    property Gradient credentialsGradient: Gradient {
        GradientStop { position: 0.00; color: "#0A1422" }
        GradientStop { position: 0.25; color: "#0C1525" }
        GradientStop { position: 0.50; color: "#0D1728" }
        GradientStop { position: 0.75; color: "#0E192A" }
    }

    // The form uses native surfaces rather than a background image.
    layoutImage: ""

    authenticationSection: SectionStyle {
        surfaceTop: "transparent"
        surfaceBottom: "transparent"
        border: "transparent"
        edgeGlow: "#397096"
        surfaceOpacity: 1.0
        shadowOpacity: 0.0
        shadowBlur: 0.52
        shadowHorizontalOffset: 2
        shadowVerticalOffset: 6
        edgeGlowOpacity: 0.0
        headingText: "#f4f7fb"
        descriptionText: "#bed3e9"
        
        icon: "#82d0ff"
        iconSurfaceTop: "#142a41"
        iconSurfaceBottom: "#14293e"

        iconBorder: "#112D4D"
        iconInnerBorder: "#52aeff"        

        iconShadow: "#01050c"
        iconShadowOpacity: 0.0
        headerHorizontalOffset: 0
        headerVerticalOffset: -5
    }

    authenticationButton: AuthButtonStyle {
        activeText: "#ffffff"
        activeIcon: "#ffffff"
        activeTop: "#36a9ff"
        activeBottom: "#075dce"
        activeHoverTop: "#45b2ff"
        activePressedTop: "#0c63cf"
        activeBorder: "#65caff"
        activeGlow: "#1996ff"
        activeGlowOpacity: 0.0
        activeHoverGlowOpacity: 0.0
        activeHighlight: "#b8e9ff"
        activeHighlightOpacity: 0.58
        inactiveText: "#f4f7fb"
        inactiveIcon: "#f4f7fb"
        inactiveTop: "transparent"
        inactiveBottom: "transparent"
        inactiveHoverTop: "#141d8ceb"
        inactiveHoverBottom: "transparent"
        inactivePressedTop: "#241684f5"
        inactivePressedBottom: "transparent"
        inactiveBorder: "transparent"
        inactiveGlow: "#1996ff"
        inactiveGlowOpacity: 0.0
        inactiveHoverGlowOpacity: 0.0
        inactiveHighlight: "#23425f"
        inactiveHighlightOpacity: 0.0
        focusBorder: "#73ceff"
        disabledText: "#647b91"
        disabledIcon: "#647b91"
        disabledTop: "transparent"
        disabledBottom: "transparent"
        disabledBorder: "transparent"
    }

    // Geometry is relative to the authentication card's padded content area.
    authenticationButtonLayout: AuthButtonLayout {
        top: 56.057
        height: 48.144
        interactiveLeft: -0.293
        interactiveWidth: 224.286
        deviceCodeLeft: 229.600
        deviceCodeWidth: 220.361
        clientCredentialsLeft: 455.568
        clientCredentialsWidth: 224.846
    }

    interactiveButtonGeometry: AuthButtonGeometry {
        horizontalInset: 0.0
        horizontalOffset: 0.0
        verticalInset: 0.0
        verticalOffset: 0.0
    }

    deviceCodeButtonGeometry: AuthButtonGeometry {
        horizontalInset: 0.0
        horizontalOffset: 0.0
        verticalInset: 0.0
        verticalOffset: 0.0
    }

    clientCredentialsButtonGeometry: AuthButtonGeometry {
        horizontalInset: 0.0
        horizontalOffset: 0.0
        verticalInset: 0.0
        verticalOffset: 0.0
    }

    credentialsSection: SectionStyle {
        surfaceTop: "transparent"
        surfaceBottom: "transparent"
        border: "transparent"
        edgeGlow: "#397096"
        surfaceOpacity: 1.0
        shadowOpacity: 0.0
        shadowBlur: 0.54
        shadowHorizontalOffset: 2
        shadowVerticalOffset: 7
        edgeGlowOpacity: 0.0
        headingText: "#f4f7fb"
        descriptionText: "#bed3e9"

        icon: "#82d0ff"
        iconSurfaceTop: "#142a41"
        iconSurfaceBottom: "#14293e"
        iconBorder: "#112D4D"
        iconInnerBorder: "#52aeff"  
        
        iconShadow: "#01050c"
        iconShadowOpacity: 0.0
        headerHorizontalOffset: 0
        headerVerticalOffset: -4
    }

    tenantField: FieldStyle {
        surfaceGradient: darkTheme.useLayeredFieldGradient ? darkTheme.layeredCredentialsGradient :
                         darkTheme.useFiveStopFieldGradient ? darkTheme.credentialsGradient : null
        surfaceGlowColor: darkTheme.useLayeredFieldGradient ? darkTheme.fieldGlowColor : "transparent"
        surfaceGlowCenter: darkTheme.fieldGlowCenter
        surfaceGlowRadii: darkTheme.fieldGlowRadii
        label: "#f4f7fb"; helper: "#bed3e9"; error: "#ff727d"
        placeholder: "#849eb7"; text: "#f4f7fb"; disabledText: "#647b91"
        selection: "#1684f5"; selectedText: "#ffffff"
        // Opaque native gradients cover the textured slots in the background.
        surfaceTop: "#081827"; surfaceBottom: "#102b45"
        disabledSurface: "#0c2136"; border: "#345774"
        borderWidth: 2; radius: 8
        hoverBorder: "#345a78"; focusBorder: "#73ceff"
        errorBorder: "#ff727d"; disabledBorder: "#345774"
        focusGlow: "#1996ff"; shadow: "#01050c"; highlight: "#23425f"
        focusGlowOpacity: 0.18; shadowOpacity: 0.0; highlightOpacity: 0.0

        headingTopOffset: 0
        inputVerticalOffset: -1.0



        focusRingLeftOutset: 3
        focusRingRightOutset: 1

        hoverRingLeftOutset: 3
        hoverRingRightOutset: 1

        focusRingRadius: 8
        hoverRingRadius: 8        
    }



    clientField: FieldStyle {
        surfaceGradient: darkTheme.useLayeredFieldGradient ? darkTheme.layeredCredentialsGradient :
                         darkTheme.useFiveStopFieldGradient ? darkTheme.credentialsGradient : null
        surfaceGlowColor: darkTheme.useLayeredFieldGradient ? darkTheme.fieldGlowColor : "transparent"
        surfaceGlowCenter: darkTheme.fieldGlowCenter
        surfaceGlowRadii: darkTheme.fieldGlowRadii
        label: "#f4f7fb"; helper: "#bed3e9"; error: "#ff727d"
        placeholder: "#849eb7"; text: "#f4f7fb"; disabledText: "#647b91"
        selection: "#1684f5"; selectedText: "#ffffff"
        surfaceTop: "#081827"; surfaceBottom: "#102b45"
        disabledSurface: "#0c2136"; border: "#345774"
        borderWidth: 2; radius: 8
        hoverBorder: "#345a78"; focusBorder: "#73ceff"
        errorBorder: "#ff727d"; disabledBorder: "#345774"
        focusGlow: "#1996ff"; shadow: "#01050c"; highlight: "#23425f"
        focusGlowOpacity: 0.18; shadowOpacity: 0.0; highlightOpacity: 0.0

        headingTopOffset: 6
        inputVerticalOffset: 5.0



        focusRingLeftOutset: 3
        focusRingRightOutset: 1

        hoverRingLeftOutset: 3
        hoverRingRightOutset: 1

        focusRingRadius: 8
        hoverRingRadius: 8        
    }

    secretField: FieldStyle {
        surfaceGradient: darkTheme.useLayeredFieldGradient ? darkTheme.layeredCredentialsGradient :
                         darkTheme.useFiveStopFieldGradient ? darkTheme.credentialsGradient : null
        surfaceGlowColor: darkTheme.useLayeredFieldGradient ? darkTheme.fieldGlowColor : "transparent"
        surfaceGlowCenter: darkTheme.fieldGlowCenter
        surfaceGlowRadii: darkTheme.fieldGlowRadii
        label: "#f4f7fb"; helper: "#bed3e9"; error: "#ff727d"
        placeholder: "#849eb7"; text: "#f4f7fb"; disabledText: "#647b91"
        selection: "#1684f5"; selectedText: "#ffffff"
        // Match the other entries; this bezel fades with the secret controls.
        surfaceTop: "#081827"; surfaceBottom: "#102b45"
        disabledSurface: "#0c2136"; border: "#345774"
        borderWidth: 2; radius: 8
        hoverBorder: "#345a78"; focusBorder: "#73ceff"
        errorBorder: "#ff727d"; disabledBorder: "#345774"
        focusGlow: "#1996ff"; shadow: "#01050c"; highlight: "#23425f"
        focusGlowOpacity: 0.18; shadowOpacity: 0.0; highlightOpacity: 0.0
        actionText: "#36a9ff"; actionIcon: "#36a9ff"
        actionHoverSurface: "#1d3a58"; actionPressedSurface: "#10243a"
        actionFocusBorder: "#73ceff"; actionDivider: "#345a78"

        headingTopOffset: 12
        inputVerticalOffset: 11.0
      


        focusRingLeftOutset: 3
        focusRingRightOutset: 1

        hoverRingLeftOutset: 3
        hoverRingRightOutset: 1     


        focusRingRadius: 8
        hoverRingRadius: 8

    }

    saveButton: ActionButtonStyle {
        text: "#ffffff"; icon: "#ffffff"
        top: "#36a9ff"; bottom: "#075dce"
        hoverTop: "#45b2ff"; pressedTop: "#0c63cf"
        border: "#65caff"; focusBorder: "#73ceff"
        glow: "#1996ff"; highlight: "#d5f3ff"
        disabledText: "#a9bac9"; disabledIcon: "#a9bac9"
        disabledTop: "#29435d"; disabledBottom: "#1b3045"
        disabledBorder: "#345a78"
        glowOpacity: 0.29; hoverGlowOpacity: 0.42
        pressedGlowOpacity: 0.18; disabledGlowOpacity: 0.0
        highlightOpacity: 0.62
    }

    tooltip: TooltipStyle {
        background: "#132b43"
        border: "#397096"
        text: "#dcecff"
        shadow: "#01050c"
        shadowOpacity: 0.58
        shadowBlur: 0.58
        shadowVerticalOffset: 6
        radius: 9
    }
}
