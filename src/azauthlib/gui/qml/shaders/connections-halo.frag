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
    vec4 family8cdaff;
    vec4 family168ee3;
    vec4 family3eaff3;
    vec4 family7ad6ff;
    vec4 family5e93b9;
    vec4 family3b6589;
    vec4 family4d9aca;
    vec4 family477ca2;
    vec4 family0a5481;
    vec4 family356689;
    vec4 family1f4767;
};

vec4 color(float r, float g, float b, float a) {
    return vec4(vec3(r, g, b) * a / 255.0, a);
}
vec4 familyColor(vec4 shade, float alpha) { return vec4(shade.rgb * alpha, alpha); }
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
    vec4 fill = mix(mix(familyColor(family1f4767,1), color(10,34,55,1), raisedT),
                    mix(color(22,59,91,1), color(6,23,40,1), sunkenT), pressAmount);
    // Raised outer shadows and subtle inset blue rim.
    vec4 outside = over(color(2,9,21,1) * blurredCircle(q - vec2(6,8), radius, 13),
                        familyColor(family356689,119.0/255.0) * blurredCircle(q + vec2(4,4), radius, 10));
    outside *= 1.0 - pressAmount;
    fill = over(familyColor(family0a5481,108.0/255.0) *
                (1.0 - blurredCircle(q, radius, 12)) * (1.0 - pressAmount), fill);
    // Sunken face: dark upper-left inset and pale lower-right inset.
    fill = over(familyColor(family477ca2,100.0/255.0) *
                (1.0 - blurredCircle(q + vec2(4,4), radius, 9)) * pressAmount, fill);
    fill = over(color(1,8,19,1) *
                (1.0 - blurredCircle(q - vec2(6,7), radius, 11)) * pressAmount, fill);
    vec4 border = mix(familyColor(family4d9aca,1), familyColor(family3b6589,1), pressAmount);
    vec4 surface = over(border * max(face - inner, 0.0), fill * face);
    surface = over(familyColor(family5e93b9,53.0/255.0) * lineMask(d + 7.5, 1.0, aa), surface);

    // HTML ::before: two colored quadrants, rotating together around the face.
    float haloD = length(q) - (radius + 5.0);
    float angle = degrees(atan(q.y, q.x)) - haloRotation;
    angle = mod(angle + 135.0, 360.0);
    float segment = step(angle, 180.0);
    vec4 arc = angle < 90.0 ? familyColor(family7ad6ff,1) : familyColor(family3eaff3,1);
    float haloLine = lineMask(haloD, 2.0, aa) * segment;
    float haloGlow = exp(-0.5 * pow(haloD / 6.0, 2.0));
    vec4 halo = over(arc * haloLine,
                     familyColor(family168ee3,102.0/255.0) * haloGlow * 0.45);
    halo *= haloOpacity;
    vec4 result = over(surface, over(halo, outside));
    // A focus-visible ring, distinct from the pointer-hover halo.
    result = over(familyColor(family8cdaff,1) * lineMask(d - 7.0, 2.0, aa) * focused, result);
    fragColor = result * qt_Opacity;
}
