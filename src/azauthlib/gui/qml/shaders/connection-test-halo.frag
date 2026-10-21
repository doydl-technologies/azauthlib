#version 440
// CSS conic gradients, radial masks, glow, and orbit-arm dots.
// Rebuild: qsb --qt6 --qsbversion 65 -o connection-test-halo.frag.qsb connection-test-halo.frag
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float outerRotation;
    float innerRotation;
    float outerDotRotation;
    float innerDotRotation;
};

vec4 rgba(float r, float g, float b, float a) {
    return vec4(vec3(r, g, b) / 255.0 * a, a);
}
vec4 over(vec4 front, vec4 back) { return front + back * (1.0 - front.a); }
vec4 outerTrail(float angle) {
    angle = mod(angle + 360.0, 360.0);
    vec4 blue = rgba(79, 180, 255, 1.0);
    vec4 dimBlue = rgba(42, 116, 189, 1.0);
    if (angle < 42.0) return vec4(0.0);
    if (angle < 86.0) return blue * (angle - 42.0) / 44.0;
    if (angle < 105.0) return blue * (105.0 - angle) / 19.0;
    if (angle < 222.0) return vec4(0.0);
    if (angle < 248.0) return dimBlue * (angle - 222.0) / 26.0;
    if (angle < 264.0) return dimBlue * (264.0 - angle) / 16.0;
    return vec4(0.0);
}
vec4 innerTrail(float angle) {
    angle = mod(angle + 720.0, 360.0);
    vec4 cyan = rgba(67, 198, 255, 0.95);
    vec4 blue = rgba(23, 94, 166, 1.0);
    if (angle < 90.0) return vec4(0.0);
    if (angle < 139.0) return cyan * (angle - 90.0) / 49.0;
    if (angle < 155.0) return cyan * (155.0 - angle) / 16.0;
    if (angle < 275.0) return vec4(0.0);
    if (angle < 325.0) return blue * (angle - 275.0) / 50.0;
    if (angle < 352.0) return blue * (352.0 - angle) / 27.0;
    return vec4(0.0);
}
float radialMask(float radius, float farCorner, vec4 stops) {
    float t = radius / farCorner;
    // CSS radial color stops interpolate linearly, not with a solid stroked arc.
    return clamp((t - stops.x) / (stops.y - stops.x), 0.0, 1.0) *
           clamp((stops.w - t) / (stops.w - stops.z), 0.0, 1.0);
}
float gaussian(float distance, float sigma) {
    return exp(-0.5 * distance * distance / (sigma * sigma));
}
vec4 dot(vec2 p, float rotation, vec2 initial, float radius, vec4 face, float aa) {
    float angle = radians(rotation);
    vec2 center = vec2(cos(angle) * initial.x - sin(angle) * initial.y,
                       sin(angle) * initial.x + cos(angle) * initial.y);
    float distance = length(p - center);
    float disc = 1.0 - smoothstep(radius - aa * 0.5, radius + aa * 0.5, distance);
    vec4 glow = over(rgba(91, 202, 255, 0.55) * gaussian(distance, 4.5),
                     rgba(61, 183, 249, 0.42) * gaussian(distance, 8.5));
    return over(face * disc, glow);
}
void main() {
    vec2 q = qt_TexCoord0 * 212.0 - vec2(106.0);
    float radius = length(q);
    float aa = max(fwidth(radius), 0.01);
    float angle = degrees(atan(q.x, -q.y)); // CSS conic origin: twelve o'clock.
    vec4 result = rgba(32, 119, 212, 0.18) *
                  clamp(1.0 - radius / (84.0 * 0.65), 0.0, 1.0);
    float outline = 1.0 - smoothstep(0.5 - aa * 0.5, 0.5 + aa * 0.5, abs(radius - 74.5));
    result = over(rgba(65, 147, 228, 0.15) * outline, result);
    result = over(rgba(33, 119, 205, 0.015) * gaussian(radius - 75.0, 12.5), result);

    float outerAngle = angle - outerRotation;
    // Approximate the CSS drop-shadow's blurred alpha, separately from the
    // sharp masked gradient, so neither ring becomes a fuzzy raster sprite.
    float blurredAlpha = (outerTrail(outerAngle - 2.5).a +
                          2.0 * outerTrail(outerAngle).a + outerTrail(outerAngle + 2.5).a) * 0.25;
    result = over(rgba(77, 179, 255, 0.50) * gaussian(radius - 81.75, 3.8) * blurredAlpha, result);
    result = over(outerTrail(outerAngle) * radialMask(radius, 85.0 * sqrt(2.0),
                  vec4(0.64, 0.66, 0.68, 0.70)), result);
    result = over(innerTrail(angle - innerRotation) * radialMask(radius, 63.0 * sqrt(2.0),
                  vec4(0.61, 0.64, 0.69, 0.72)), result);
    result = over(dot(q, outerDotRotation, vec2(0.5, -80.5), 3.5, rgba(140, 234, 255, 1.0), aa), result);
    result = over(dot(q, innerDotRotation, vec2(-0.5, -59.5), 2.5, rgba(49, 127, 239, 1.0), aa), result);
    fragColor = result * qt_Opacity;
}
