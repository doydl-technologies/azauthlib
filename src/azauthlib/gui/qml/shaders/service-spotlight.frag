#version 440
// Premultiplied, three-stop radial gradient. No raster blur or hard glow disc.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 surfaceSize;
    float cornerRadius;
    vec2 gradientCenter;
    float middleStop;
    float edgeStop;
    vec4 colorCenter;
    vec4 colorMiddle;
    vec4 colorEdge;
};
void main() {
    vec2 farthest = max(gradientCenter, vec2(1.0) - gradientCenter);
    float t = length(qt_TexCoord0 - gradientCenter) / max(length(farthest), 0.001);
    vec4 fill = t < middleStop ? mix(colorCenter, colorMiddle, clamp(t / middleStop, 0.0, 1.0)) :
        mix(colorMiddle, colorEdge, clamp((t - middleStop) / (edgeStop - middleStop), 0.0, 1.0));
    vec2 q = abs((qt_TexCoord0 - vec2(0.5)) * surfaceSize) - (surfaceSize * 0.5 - cornerRadius);
    float d = length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - cornerRadius;
    float aa = max(fwidth(d), 0.001);
    float coverage = 1.0 - smoothstep(-aa * 0.5, aa * 0.5, d);
    fragColor = fill * coverage * qt_Opacity;
}
