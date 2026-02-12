import colorsys

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_hue(h1, h2, t):
    # interpolate along the shortest path around the hue circle
    dh = h2 - h1
    if abs(dh) > 0.5:
        if dh > 0:
            h1 += 1
        else:
            h2 += 1
    return (lerp(h1, h2, t)) % 1.0

def generate_gradient(start_rgb, end_rgb, n):
    # normalize RGB to 0–1
    s_rgb = [c / 255 for c in start_rgb]
    e_rgb = [c / 255 for c in end_rgb]

    # RGB → HLS (Python uses HLS, not HSL)
    sh, sl, ss = colorsys.rgb_to_hls(*s_rgb)
    eh, el, es = colorsys.rgb_to_hls(*e_rgb)

    for i in range(n):
        t = i / (n - 1)

        h = lerp_hue(sh, eh, t)
        l = lerp(sl, el, t)
        s = lerp(ss, es, t)

        r, g, b = colorsys.hls_to_rgb(h, l, s)

        rgb_255 = [round(r * 255), round(g * 255), round(b * 255)]
        rgb_01  = [round(r, 4), round(g, 4), round(b, 4)]

        print(f"{i}: RGB {rgb_255} | RGB [0–1] {rgb_01}")

# Example(0, 255, 0)
start = (0, 255, 0)   # dark red
end   = (128, 0, 0)   # bright green
n = 5

generate_gradient(start, end, n)
