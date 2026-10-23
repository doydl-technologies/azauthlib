#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float hoverAmount;
    float pressAmount;
};
layout(binding = 1) uniform sampler2D raisedSource;
layout(binding = 2) uniform sampler2D hoverSource;
layout(binding = 3) uniform sampler2D sunkenSource;

void main() {
    // Interpolate premultiplied RGBA once, rather than compositing multiple
    // translucent image items. The button never fades out between states,
    // transparent margins do not reveal a second stacked icon, and endpoints
    // reproduce the original SVG textures exactly, without tinting.
    vec4 raised = texture(raisedSource, qt_TexCoord0);
    vec4 hovered = texture(hoverSource, qt_TexCoord0);
    vec4 sunken = texture(sunkenSource, qt_TexCoord0);
    vec4 normal = mix(raised, hovered, clamp(hoverAmount, 0.0, 1.0));
    fragColor = mix(normal, sunken, clamp(pressAmount, 0.0, 1.0)) * qt_Opacity;
}
