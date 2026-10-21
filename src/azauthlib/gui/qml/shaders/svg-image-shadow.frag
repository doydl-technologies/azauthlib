#version 440
// HTML filter: drop-shadow(1px 2px 2px #03101e99), alpha only.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float padding;
    vec2 artworkSize;
    vec2 shadowOffset;
    float shadowSigma;
};
layout(binding = 1) uniform sampler2D source;

float alphaAt(vec2 uv) {
    if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) return 0.0;
    return texture(source, uv).a;
}
void main() {
    vec2 uv = (qt_TexCoord0 * (artworkSize + 2.0 * padding) - padding - shadowOffset) / artworkSize;
    float alpha = 0.0, weight = 0.0;
    for (int y = -3; y <= 3; ++y) {
        for (int x = -3; x <= 3; ++x) {
            vec2 sampleOffset = vec2(float(x), float(y));
            float w = exp(-0.5 * dot(sampleOffset, sampleOffset));
            alpha += alphaAt(uv + sampleOffset * shadowSigma / artworkSize) * w;
            weight += w;
        }
    }
    float opacity = alpha / weight * 0.6 * qt_Opacity;
    fragColor = vec4(vec3(3.0, 16.0, 30.0) / 255.0 * opacity, opacity);
}
