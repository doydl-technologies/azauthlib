#version 440
// Rebuild: pyside6-qsb --qt6 --qsbversion 65 -o connection-surface.frag.qsb connection-surface.frag
// The Qt 6.5 pack format supports the application's minimum Qt 6.8.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float padding;
    vec2 surfaceSize;
    float cornerRadius;
    float lineWidth;
    float shadowBlur;
    float highlightBlur;
    vec2 darkOffset;
    vec2 brightOffset;
    float inset;
    float hasShadows;
    float gradientAngle;
    float radialFill;
    float centerStop;
    float circleOutline;
    vec4 colorTop;
    vec4 colorMiddle;
    vec4 colorBottom;
    vec4 colorBorder;
    vec4 colorShadow;
    vec4 colorLight;
    vec4 colorRim;
};

float distanceToBox(vec2 p) {
    vec2 q = abs(p - surfaceSize * 0.5) - (surfaceSize * 0.5 - cornerRadius);
    return length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - cornerRadius;
}

// Normal CDF: a Gaussian-blurred silhouette edge, with no hard inset wall.
float cdf(float x) {
    float t = 1.0 / (1.0 + 0.2316419 * abs(x));
    float tail = 0.39894228 * exp(-0.5 * x * x) * t *
        (0.31938153 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return x > 0.0 ? 1.0 - tail : tail;
}

float blurredBox(vec2 p, float blur) {
    // CSS blur radius corresponds to twice the Gaussian standard deviation.
    return cdf(-distanceToBox(p) / max(blur * 0.5, 0.25));
}

// Blur the rounded silhouette itself, rather than its signed distance. The
// distance approximation leaves a box-like halo around small raised controls.
// Integrate the Gaussian horizontally; each vertical slice has an exact CDF.
float roundedShadow(vec2 p, float blur) {
    float sigma = max(blur * 0.5, 0.25);
    float start = max(0.0, p.x - 3.5 * sigma);
    float end = min(surfaceSize.x, p.x + 3.5 * sigma);
    if (end <= start) return 0.0;
    float stepSize = (end - start) / 12.0;
    float result = 0.0;
    for (int i = 0; i < 12; ++i) {
        float x = start + (float(i) + 0.5) * stepSize;
        float cornerX = max(cornerRadius - min(x, surfaceSize.x - x), 0.0);
        float top = cornerRadius - sqrt(max(cornerRadius * cornerRadius - cornerX * cornerX, 0.0));
        float vertical = cdf((surfaceSize.y - top - p.y) / sigma) - cdf((top - p.y) / sigma);
        float horizontal = (x - p.x) / sigma;
        result += vertical * exp(-0.5 * horizontal * horizontal);
    }
    return clamp(result * stepSize * 0.39894228 / sigma, 0.0, 1.0);
}

vec4 over(vec4 foreground, vec4 background) {
    return foreground + background * (1.0 - foreground.a);
}

// Same screen-pixel coverage as the Home provider halos. Only the narrow rim
// is sampled; no texture layer, blur, or change to the surface's outer radius.
vec2 circleCoverage(vec2 p, float radius, float stroke, vec2 pixelX, vec2 pixelY) {
    vec2 centered = p - surfaceSize * 0.5;
    float d = length(centered) - radius;
    float footprint = 0.5 * (length(pixelX) + length(pixelY));
    if (d > footprint) return vec2(0.0);
    if (d < -stroke - footprint) return vec2(1.0);
    vec2 coverage = vec2(0.0);
    for (int y = 0; y < 8; ++y) {
        for (int x = 0; x < 8; ++x) {
            vec2 offset = (vec2(float(x), float(y)) + 0.5) / 8.0 - 0.5;
            float distance = length(centered + offset.x * pixelX + offset.y * pixelY) - radius;
            coverage += vec2(step(distance, 0.0), step(distance, -stroke));
        }
    }
    return coverage / 64.0;
}

void main() {
    vec2 p = qt_TexCoord0 * (surfaceSize + 2.0 * padding) - padding;
    vec2 pixelX = dFdx(p), pixelY = dFdy(p);
    float d = distanceToBox(p);
    float aa = max(fwidth(d), 0.001);
    float mask = 1.0 - smoothstep(-aa * 0.5, aa * 0.5, d);
    float inner = 1.0 - smoothstep(-aa * 0.5, aa * 0.5, d + lineWidth);
    bool circular = circleOutline > 0.5 && lineWidth > 0.0
                 && abs(surfaceSize.x - surfaceSize.y) < 0.01
                 && abs(cornerRadius - surfaceSize.x * 0.5) < 0.01;
    if (circular) {
        float stroke = max(lineWidth, max(length(pixelX), length(pixelY)));
        vec2 coverage = circleCoverage(p, cornerRadius, stroke, pixelX, pixelY);
        mask = coverage.x;
        inner = coverage.y;
    }
    vec2 direction = vec2(sin(radians(gradientAngle)), -cos(radians(gradientAngle)));
    float gradientLength = dot(abs(direction), surfaceSize);
    float t = clamp(0.5 + dot(p - surfaceSize * 0.5, direction) / max(gradientLength, 1.0), 0.0, 1.0);
    vec4 fill;
    if (radialFill > 0.5) {
        float radialLength = length(surfaceSize * vec2(0.6, 0.65)) * 0.7;
        fill = mix(colorTop, colorBottom, clamp(length(p - surfaceSize * vec2(0.4, 0.35)) / radialLength, 0.0, 1.0));
    } else {
        fill = t < centerStop ? mix(colorTop, colorMiddle, t / centerStop)
             : mix(colorMiddle, colorBottom, (t - centerStop) / (1.0 - centerStop));
    }
    vec4 outside = vec4(0.0);
    if (hasShadows > 0.5) {
        if (inset > 0.5) {
            float dark = blurredBox(p - darkOffset, shadowBlur);
            float light = blurredBox(p - brightOffset, highlightBlur);
            fill = over(colorLight * (1.0 - light), fill);
            fill = over(colorShadow * (1.0 - dark), fill);
        } else if (mask * fill.a < 1.0) {
            // Opaque surfaces hide the outside shadows: skip their integration
            // over the panel interior to keep the large home page inexpensive.
            float dark = roundedShadow(p - darkOffset, shadowBlur);
            float light = roundedShadow(p - brightOffset, highlightBlur);
            outside = over(colorShadow * dark, colorLight * light);
        }
    }
    // CSS inset 0 1px highlight, not a second outline on all four edges.
    float rim = smoothstep(-aa * 0.5, aa * 0.5, distanceToBox(p - vec2(0.0, 1.0)));
    fill = over(colorRim * rim, fill);
    vec4 surface = fill * mask;
    surface = over(colorBorder * max(mask - inner, 0.0), surface);
    if (circular) {
        // Partition coverage once rather than blending the edge over itself.
        surface = fill * inner + colorBorder * max(mask - inner, 0.0);
    }
    fragColor = over(surface, outside) * qt_Opacity;
}
