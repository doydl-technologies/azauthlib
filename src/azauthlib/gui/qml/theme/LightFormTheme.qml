import QtQuick

FormThemeDefinition {
    // Archived .dormant artwork is excluded from distributions and must not be referenced.
    layoutImage: ""

    authenticationSection: SectionStyle {
        surfaceTop: "transparent"
        surfaceBottom: "transparent"
        border: "transparent"
        edgeGlow: AccentTheme.color("#6f96b3")
        surfaceOpacity: 1.0
        shadowOpacity: 0.0
        shadowBlur: 0.52
        shadowHorizontalOffset: 4
        shadowVerticalOffset: 7
        edgeGlowOpacity: 0.0
        headingText: "#102039"
        descriptionText: "#586f87"
        icon: AccentTheme.color("#146fd0")
        iconSurfaceTop: AccentTheme.color("#f1f8ff")
        iconSurfaceBottom: AccentTheme.color("#dceefd")
        iconBorder: AccentTheme.color("#b5d8f4")
        iconInnerBorder: "#c2ffffff"
        iconShadow: "#728598"
        iconShadowOpacity: 0.0
        headerHorizontalOffset: 0
        headerVerticalOffset: -5        
    }

    authenticationButton: AuthButtonStyle {
        activeFontWeight: Font.DemiBold
        inactiveFontWeight: Font.Normal
        activeText: "#ffffff"
        activeIcon: "#ffffff"
        activeTop: AccentTheme.color("#43a5ff")
        activeBottom: AccentTheme.color("#0a5bc3")
        activeHoverTop: AccentTheme.color("#3595f5")
        activePressedTop: AccentTheme.color("#0b61c7")
        activeBorder: AccentTheme.color("#50affb")
        activeGlow: AccentTheme.color("#43a5ff")
        activeGlowOpacity: 0.0
        activeHoverGlowOpacity: 0.0
        activeHighlight: AccentTheme.color("#d5f3ff")
        activeHighlightOpacity: 0.0
        inactiveText: "#102039"
        inactiveIcon: "#102039"
        inactiveTop: "transparent"
        inactiveBottom: "transparent"
        inactiveHoverTop: AccentTheme.color("#142f8fd8")
        inactiveHoverBottom: "transparent"
        inactivePressedTop: AccentTheme.color("#241678e7")
        inactivePressedBottom: "transparent"
        inactiveBorder: "transparent"
        inactiveGlow: AccentTheme.color("#43a5ff")
        inactiveGlowOpacity: 0.0
        inactiveHoverGlowOpacity: 0.0
        inactiveHighlight: "#ffffff"
        inactiveHighlightOpacity: 0.0
        focusBorder: AccentTheme.color("#167fe9")
        disabledText: "#98a8b8"
        disabledIcon: "#98a8b8"
        disabledTop: "transparent"
        disabledBottom: "transparent"
        disabledBorder: "transparent"
    }

    // The light background has different recess sizes and positions, so it
    // intentionally owns a separate set of measured slot rectangles.
    authenticationButtonLayout: AuthButtonLayout {
        top: 59.225
        height: 44.977
        interactiveLeft: 3.071
        interactiveWidth: 227.650
        deviceCodeLeft: 237.450
        deviceCodeWidth: 216.996
        clientCredentialsLeft: 460.614
        clientCredentialsWidth: 216.996
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
        edgeGlow: AccentTheme.color("#6f96b3")
        surfaceOpacity: 1.0
        shadowOpacity: 0.0
        shadowBlur: 0.54
        shadowHorizontalOffset: 4
        shadowVerticalOffset: 8
        edgeGlowOpacity: 0.0
        headingText: "#102039"
        descriptionText: "#586f87"
        icon: AccentTheme.color("#146fd0")
        iconSurfaceTop: AccentTheme.color("#f1f8ff")
        iconSurfaceBottom: AccentTheme.color("#dceefd")
        iconBorder: AccentTheme.color("#b5d8f4")
        iconInnerBorder: "#c2ffffff"
        iconShadow: "#728598"
        iconShadowOpacity: 0.0
        headerHorizontalOffset: 0
        headerVerticalOffset: -4        
    }

    tenantField: FieldStyle {
        labelFontWeight: Font.Normal
        label: "#102039"; helper: "#586f87"; error: "#c23b44"
        placeholder: "#6d8298"; text: "#102039"; disabledText: "#98a8b8"
        selection: AccentTheme.color("#1678e7"); selectedText: "#ffffff"
        surfaceTop: "transparent"; surfaceBottom: "transparent"
        disabledSurface: "transparent"; border: "transparent"
        hoverBorder: AccentTheme.color("#b2c7d9"); focusBorder: AccentTheme.color("#167fe9")
        errorBorder: "#c23b44"; disabledBorder: "transparent"
        focusGlow: AccentTheme.color("#43a5ff"); shadow: "#728598"; highlight: "#ffffff"
        focusGlowOpacity: 0.16; shadowOpacity: 0.0; highlightOpacity: 0.0

        headingTopOffset: 0
        inputVerticalOffset: 1.0



        focusRingLeftOutset: 2
        focusRingRightOutset: 0

        hoverRingLeftOutset: 0
        hoverRingRightOutset: 0

        focusRingRadius: 8
        hoverRingRadius: 8  
    }

    clientField: FieldStyle {
        labelFontWeight: Font.Normal
        label: "#102039"; helper: "#586f87"; error: "#c23b44"
        placeholder: "#6d8298"; text: "#102039"; disabledText: "#98a8b8"
        selection: AccentTheme.color("#1678e7"); selectedText: "#ffffff"
        surfaceTop: "transparent"; surfaceBottom: "transparent"
        disabledSurface: "transparent"; border: "transparent"
        hoverBorder: AccentTheme.color("#b2c7d9"); focusBorder: AccentTheme.color("#167fe9")
        errorBorder: "#c23b44"; disabledBorder: "transparent"
        focusGlow: AccentTheme.color("#43a5ff"); shadow: "#728598"; highlight: "#ffffff"
        focusGlowOpacity: 0.16; shadowOpacity: 0.0; highlightOpacity: 0.0

        headingTopOffset: 6
        inputVerticalOffset: 5.0



        focusRingLeftOutset: 2
        focusRingRightOutset: 0

        hoverRingLeftOutset: 0
        hoverRingRightOutset: 0

        focusRingRadius: 8
        hoverRingRadius: 8  
    }

    secretField: FieldStyle {
        labelFontWeight: Font.Normal
        label: "#102039"; helper: "#586f87"; error: "#c23b44"
        placeholder: "#6d8298"; text: "#102039"; disabledText: "#98a8b8"
        selection: AccentTheme.color("#1678e7"); selectedText: "#ffffff"
        surfaceTop: "transparent"; surfaceBottom: "transparent"
        disabledSurface: "transparent"; border: "transparent"
        hoverBorder: AccentTheme.color("#b2c7d9"); focusBorder: AccentTheme.color("#167fe9")
        errorBorder: "#c23b44"; disabledBorder: "transparent"
        focusGlow: AccentTheme.color("#43a5ff"); shadow: "#728598"; highlight: "#ffffff"
        focusGlowOpacity: 0.16; shadowOpacity: 0.0; highlightOpacity: 0.0
        actionText: AccentTheme.color("#1678e7"); actionIcon: AccentTheme.color("#1678e7")
        actionHoverSurface: "#e8f1f8"; actionPressedSurface: "#dceefd"
        actionFocusBorder: AccentTheme.color("#167fe9"); actionDivider: "#b2c7d9"

        inputVerticalOffset: 11.0
        headingTopOffset: 12
      


        focusRingLeftOutset: 2
        focusRingRightOutset: 0

        hoverRingLeftOutset: 0
        hoverRingRightOutset: 0

        focusRingRadius: 8
        hoverRingRadius: 8        
    }

    saveButton: ActionButtonStyle {
        text: "#ffffff"; icon: "#ffffff"
        top: AccentTheme.color("#43a5ff"); bottom: AccentTheme.color("#0a5bc3")
        hoverTop: AccentTheme.color("#3595f5"); pressedTop: AccentTheme.color("#0b61c7")
        border: AccentTheme.color("#50affb"); focusBorder: AccentTheme.color("#167fe9")
        glow: AccentTheme.color("#43a5ff"); highlight: AccentTheme.color("#d5f3ff")
        disabledText: "#e1e8ef"; disabledIcon: "#e1e8ef"
        disabledTop: "#a8b9c8"; disabledBottom: "#879caf"
        disabledBorder: AccentTheme.color("#9db1c2")
        glowOpacity: 0.0; hoverGlowOpacity: 0.0
        pressedGlowOpacity: 0.0; disabledGlowOpacity: 0.0
        highlightOpacity: 0.0
    }

    tooltip: TooltipStyle {
        background: "#f7fbfe"
        border: AccentTheme.color("#93aec3")
        text: AccentTheme.color("#244c72")
        shadow: "#728598"
        shadowOpacity: 0.34
        shadowBlur: 0.55
        shadowVerticalOffset: 5
        radius: 9
    }
}
