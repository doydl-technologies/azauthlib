#version 440
// Native translation of azauthlib-provider-selector-02.html's CSS surfaces.
// Rebuild: qsb --qt6 --qsbversion 65 -o provider-surface.frag.qsb provider-surface.frag
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float padding;
    vec2 surfaceSize;
    float cornerRadius;
    float surfaceKind;
    float selectedState;
    float hoverState;
    float pressState;
    float focusState;
    float unavailableState;
};

vec4 color(float r, float g, float b, float a) {
    return vec4(vec3(r, g, b) / 255.0 * a, a);
}
vec4 over(vec4 front, vec4 back) { return front + back * (1.0 - front.a); }
float sd(vec2 p, vec2 size, float radius) {
    vec2 q = abs(p - size * 0.5) - (size * 0.5 - radius);
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
}
float cdf(float x) {
    float t = 1.0 / (1.0 + 0.2316419 * abs(x));
    float tail = 0.39894228 * exp(-0.5 * x * x) * t *
        (0.31938153 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return x > 0.0 ? 1.0 - tail : tail;
}
// Gaussian integration of the actual rounded silhouette, including CSS spread.
// This avoids the squared-off corners produced by rectangular blur textures.
float shadow(vec2 p, vec2 size, float radius, vec2 offset, float blur, float spread) {
    p = p - offset + vec2(spread);
    size += 2.0 * spread;
    radius = clamp(radius + spread, 0.0, min(size.x, size.y) * 0.5);
    if (blur < 0.01) {
        float d = sd(p, size, radius);
        float aa = max(fwidth(d), 0.01);
        return 1.0 - smoothstep(-aa * 0.5, aa * 0.5, d);
    }
    float sigma = max(blur * 0.5, 0.25);
    float start = max(0.0, p.x - 3.5 * sigma);
    float end = min(size.x, p.x + 3.5 * sigma);
    if (end <= start) return 0.0;
    float stepSize = (end - start) / 12.0;
    float sum = 0.0;
    for (int i = 0; i < 12; ++i) {
        float x = start + (float(i) + 0.5) * stepSize;
        float cx = max(radius - min(x, size.x - x), 0.0);
        float top = radius - sqrt(max(radius * radius - cx * cx, 0.0));
        float vertical = cdf((size.y - top - p.y) / sigma) - cdf((top - p.y) / sigma);
        float horizontal = (x - p.x) / sigma;
        sum += vertical * exp(-0.5 * horizontal * horizontal);
    }
    return clamp(sum * stepSize * 0.39894228 / sigma, 0.0, 1.0);
}
float inset(vec2 p, vec2 offset, float blur, float spread) {
    return 1.0 - shadow(p, surfaceSize, cornerRadius, offset, blur, -spread);
}
float linearPosition(vec2 p, float angle) {
    vec2 direction = vec2(sin(radians(angle)), -cos(radians(angle)));
    return clamp(0.5 + dot(p - surfaceSize * 0.5, direction) /
                 max(dot(abs(direction), surfaceSize), 1.0), 0.0, 1.0);
}
vec4 linear3(vec2 p, float angle, vec4 a, vec4 b, vec4 c, float stop) {
    float t = linearPosition(p, angle);
    return t < stop ? mix(a, b, t / stop) : mix(b, c, (t - stop) / (1.0 - stop));
}
// Integrate the circle and its inner edge over the final framebuffer pixel.
// Unlike fwidth(d)'s direction-dependent ramp, this measures actual coverage
// at fractional positions/scales, without a raster layer or a blurred outline.
vec2 circleCoverage(vec2 p, float radius, float stroke, vec2 pixelX, vec2 pixelY) {
    vec2 centered = p - surfaceSize * 0.5;
    float d = length(centered) - radius;
    float footprint = 0.5 * (length(pixelX) + length(pixelY));
    if (d > footprint) return vec2(0.0);
    if (d < -stroke - footprint) return vec2(1.0);
    vec2 coverage = vec2(0.0);
    // Only the narrow edge band needs sampling; the fill/shadow stay unchanged.
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
    float d = sd(p, surfaceSize, cornerRadius);
    float aa = max(fwidth(d), 0.001);
    float mask = 1.0 - smoothstep(-aa * 0.5, aa * 0.5, d);
    vec4 fill = vec4(0.0), outside = vec4(0.0), border = vec4(0.0);
    float line = 1.0;
    float selected = selectedState, hovered = hoverState;
    if (surfaceKind < 2.5) {
        // .provider-card: four distinct inset shadows plus the inset ::before.
        fill = linear3(p,148.0,color(11,40,69,1),color(15,45,78,1),color(21,56,90,1),0.42);
        vec4 chosen = linear3(p,148.0,color(13,43,75,1),color(18,50,82,1),color(23,59,96,1),0.55);
        fill = mix(fill,chosen,selected);
        fill = over(color(19,105,191,0.13*selected) * inset(p,vec2(0),24.0,0.0),fill);
        fill = over(color(135,193,235,mix(0.24+hovered*0.03,0.0,selected)) * inset(p,vec2(-1),2.0,0.0),fill);
        vec4 reflection = mix(color(93+8*hovered,161+13*hovered,211+19*hovered,0.34+0.07*hovered),color(77,171,252,0.43),selected);
        fill = over(reflection * inset(p,vec2(-7,-8),13.0,-6.0),fill);
        fill = over(color(0,7,24,mix(0.74+hovered*0.05,0.7,selected)) * inset(p,vec2(3,4),7.0,0.0),fill);
        fill = over(color(0,6,20,0.95+0.01*max(selected,hovered)) * inset(p,vec2(8,10),15.0,-5.0),fill);
        vec2 innerSize = surfaceSize - 6.0;
        float innerD = sd(p-3.0,innerSize,19.0);
        float innerMask = 1.0-smoothstep(-aa*0.5,aa*0.5,innerD);
        fill = over(color(146,202,247,0.07) * (1.0-shadow(p-3.0,innerSize,19.0,vec2(-1),1.0,0.0))*innerMask,fill);
        fill = over(color(0,6,23,0.43) * (1.0-shadow(p-3.0,innerSize,19.0,vec2(1,2),3.0,0.0))*innerMask,fill);
        border = mix(mix(color(50,92,128,1),color(87,155,208,1),hovered),color(67,182,255,1),selected);
        line = 1.5;
        outside = color(135,199,244,0.24) * shadow(p,surfaceSize,cornerRadius,vec2(0,1),0.0,0.0);
        outside = over(color(43,149,239,0.16*hovered*(1.0-selected))*shadow(p,surfaceSize,cornerRadius,vec2(0),15.0,0.0),outside);
        outside = over(color(16,145,255,0.3*selected)*shadow(p,surfaceSize,cornerRadius,vec2(0),24.0,0.0),outside);
        outside = over(color(47,164,247,0.52*selected)*shadow(p,surfaceSize,cornerRadius,vec2(0),0.0,1.0),outside);
    } else if (surfaceKind < 3.5) {
        // .depth-halo: stationary raised circle, never a recessed card.
        float t = clamp(length(p-surfaceSize*vec2(0.4,0.35))/(surfaceSize.x*0.88459*0.7),0.0,1.0);
        fill = mix(color(28,69,109,1),color(13,35,60,1),t);
        fill = over(color(118,185,237,0.3333)*inset(p,vec2(0,1),0.0,0.0),fill);
        fill.rgb *= 1.0 + 0.1*hovered;
        border = mix(color(56,139,208,1),color(85,171,237,1),selected);
        outside = color(52,91,133,0.4)*shadow(p,surfaceSize,cornerRadius,vec2(-5),14.0,0.0);
        outside = over(color(3,16,30,1)*shadow(p,surfaceSize,cornerRadius,vec2(7),16.0,0.0),outside);
        outside = over(color(56,168,255,0.2196*selected)*shadow(p,surfaceSize,cornerRadius,vec2(0),14.0,0.0),outside);
    } else if (surfaceKind < 4.5) {
        // .continue: blue raised button with directional drop shadow and rim.
        fill = linear3(p,180.0,color(46,179,253,1),color(17,135,244,1),color(9,101,209,1),0.57);
        fill.rgb *= 1.0+0.12*hovered-0.06*pressState;
        fill = over(color(230,251,255,0.28)*inset(p,vec2(0,2),2.0,0.0),fill);
        border = color(129,207,255,1);
        outside = color(0,18,49,0.25)*shadow(p,surfaceSize,cornerRadius,vec2(0,6),13.0,0.0);
        outside = over(color(16,147,255,0.29)*shadow(p,surfaceSize,cornerRadius,vec2(0),18.0,0.0),outside);
        outside = over(color(65,167,255,0.22)*shadow(p,surfaceSize,cornerRadius,vec2(0),0.0,1.0),outside);
        if (unavailableState > 0.5) {
            // Muted raised surface, not a recoloring layer on any SVG artwork.
            fill = linear3(p,180.0,color(66,83,106,1),color(52,68,90,1),color(38,54,75,1),0.57);
            fill = over(color(230,251,255,0.08)*inset(p,vec2(0,2),2.0,0.0),fill);
            border = color(98,117,141,1);
            outside = color(0,18,49,0.25)*shadow(p,surfaceSize,cornerRadius,vec2(0,6),13.0,0.0);
        }
    } else {
        // .selected-check, drawn independently over the card well.
        fill = mix(color(64,186,255,1),color(4,113,236,1),clamp(linearPosition(p,145.0)/0.9,0.0,1.0));
        fill = over(color(141,213,255,1)*inset(p,vec2(0,1),2.0,0.0),fill);
        border = color(145,218,255,1);
        outside = color(20,154,255,0.55)*shadow(p,surfaceSize,cornerRadius,vec2(0),21.0,0.0);
    }
    float inner = 1.0-smoothstep(-aa*0.5,aa*0.5,d+line);
    vec4 surface = over(border*max(mask-inner,0.0),fill*mask);
    bool circular = ((surfaceKind > 2.5 && surfaceKind < 3.5) || surfaceKind > 4.5)
                 && abs(surfaceSize.x - surfaceSize.y) < 0.01
                 && abs(cornerRadius - surfaceSize.x * 0.5) < 0.01;
    if (circular) {
        // Preserve the outer radius while preventing the 1-unit stroke from
        // shrinking below one physical pixel under the compact page scaling.
        float stroke = max(line, max(length(pixelX), length(pixelY)));
        vec2 coverage = circleCoverage(p, cornerRadius, stroke, pixelX, pixelY);
        // Disjoint fill/ring coverage avoids applying the silhouette twice at
        // partially covered pixels, keeping the edge weight uniform.
        surface = fill * coverage.y + border * max(coverage.x - coverage.y, 0.0);
    }
    // Keyboard focus is a separate outer ring, rather than recoloring the SVG.
    float focusRing = shadow(p,surfaceSize,cornerRadius,vec2(0),0.0,5.0)
                    -shadow(p,surfaceSize,cornerRadius,vec2(0),0.0,3.0);
    outside = over(color(167,222,255,focusState)*max(focusRing,0.0),outside);
    fragColor = over(surface,outside)*qt_Opacity;
}
