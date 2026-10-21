#version 440
// Native, DPI-aware counterpart of the halo launcher's CSS; premultiplied output.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float padding;
    vec2 faceSize;
    float pressAmount;
    float haloRotation;
    float haloOpacity;
    float focused;
};

vec4 color(float r, float g, float b, float a) {
    return vec4(vec3(r, g, b) * a / 255.0, a);
}
vec4 over(vec4 front, vec4 back) { return front + back * (1.0 - front.a); }
float cdf(float x) {
    float t = 1.0 / (1.0 + 0.2316419 * abs(x));
    float tail = 0.39894228 * exp(-0.5 * x * x) * t *
        (0.31938153 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return x > 0.0 ? 1.0 - tail : tail;
}
float blurredCircle(vec2 q, float radius, float blur) {
    return cdf((radius - length(q)) / max(blur * 0.5, 0.25));
}
float lineMask(float d, float width, float aa) {
    return 1.0 - smoothstep(width * 0.5 - aa * 0.5, width * 0.5 + aa * 0.5, abs(d));
}
void main() {
    vec2 p = qt_TexCoord0 * (faceSize + 2.0 * padding) - padding;
    vec2 q = p - faceSize * 0.5;
    float radius = min(faceSize.x, faceSize.y) * 0.5;
    float d = length(q) - radius;
    float aa = max(fwidth(d), 0.001);
    float face = 1.0 - smoothstep(-aa * 0.5, aa * 0.5, d);
    float inner = 1.0 - smoothstep(-aa * 0.5, aa * 0.5, d + 1.0);

    float raisedT = clamp(length(p - faceSize * vec2(0.35, 0.28)) /
                         (length(faceSize * vec2(0.65, 0.72)) * 0.66), 0.0, 1.0);
    float sunkenT = clamp(length(p - faceSize * vec2(0.65, 0.70)) /
                         (length(faceSize * vec2(0.65, 0.70)) * 0.70), 0.0, 1.0);
    vec4 fill = mix(mix(color(31,71,103,1), color(10,34,55,1), raisedT),
                    mix(color(22,59,91,1), color(6,23,40,1), sunkenT), pressAmount);
    // Raised outer shadows and subtle inset blue rim.
    vec4 outside = over(color(2,9,21,1) * blurredCircle(q - vec2(6,8), radius, 13),
                        color(53,102,137,119.0/255.0) * blurredCircle(q + vec2(4,4), radius, 10));
    outside *= 1.0 - pressAmount;
    fill = over(color(10,84,129,108.0/255.0) *
                (1.0 - blurredCircle(q, radius, 12)) * (1.0 - pressAmount), fill);
    // Sunken face: dark upper-left inset and pale lower-right inset.
    fill = over(color(71,124,162,100.0/255.0) *
                (1.0 - blurredCircle(q + vec2(4,4), radius, 9)) * pressAmount, fill);
    fill = over(color(1,8,19,1) *
                (1.0 - blurredCircle(q - vec2(6,7), radius, 11)) * pressAmount, fill);
    vec4 border = mix(color(77,154,202,1), color(59,101,137,1), pressAmount);
    vec4 surface = over(border * max(face - inner, 0.0), fill * face);
    surface = over(color(94,147,185,53.0/255.0) * lineMask(d + 7.5, 1.0, aa), surface);

    // HTML ::before: two colored quadrants, rotating together around the face.
    float haloD = length(q) - (radius + 5.0);
    float angle = degrees(atan(q.y, q.x)) - haloRotation;
    angle = mod(angle + 135.0, 360.0);
    float segment = step(angle, 180.0);
    vec4 arc = angle < 90.0 ? color(122,214,255,1) : color(62,175,243,1);
    float haloLine = lineMask(haloD, 2.0, aa) * segment;
    float haloGlow = exp(-0.5 * pow(haloD / 6.0, 2.0));
    vec4 halo = over(arc * haloLine,
                     color(22,142,227,102.0/255.0) * haloGlow * 0.45);
    halo *= haloOpacity;
    vec4 result = over(surface, over(halo, outside));
    // A focus-visible ring, distinct from the pointer-hover halo.
    result = over(color(140,218,255,1) * lineMask(d - 7.0, 2.0, aa) * focused, result);
    fragColor = result * qt_Opacity;
}
