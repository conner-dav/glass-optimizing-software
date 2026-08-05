"""
One-off asset generator: draws a simple placeholder "glass cube" mark for
Cubed Glass (isometric cube made of three translucent-looking facets, like
stacked glass panes catching light). Not the real Cubed Glass logo -- just
a stand-in with an on-brand feel until the real logo file is dropped in.

Run once:  python generate_logo.py
Produces:  assets/logo_mark.png   (for in-app header, transparent bg)
           assets/logo_mark.ico   (for the Windows .exe icon)

To use your REAL logo instead: just replace assets/logo_mark.png (and
regenerate/replace the .ico) with your actual files of the same names --
the app doesn't need any code changes.
"""

from PIL import Image, ImageDraw

# Palette: Fiat 188/A "Rosa Poste Tedesche" rose-pink, the company's color
PINK_LIGHT = (237, 158, 178, 255)
PINK_MID = (224, 123, 150, 255)
PINK_DARK = (168, 78, 103, 255)
HIGHLIGHT = (255, 255, 255, 130)


def draw_cube(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size / 2, size / 2 + size * 0.05
    s = size * 0.34  # facet half-span

    # Isometric cube: top, left, right facets as parallelograms
    top = [(cx, cy - s * 1.15), (cx + s, cy - s * 0.55), (cx, cy), (cx - s, cy - s * 0.55)]
    left = [(cx - s, cy - s * 0.55), (cx, cy), (cx, cy + s * 1.15), (cx - s, cy + s * 0.55)]
    right = [(cx + s, cy - s * 0.55), (cx, cy), (cx, cy + s * 1.15), (cx + s, cy + s * 0.55)]

    draw.polygon(top, fill=PINK_LIGHT)
    draw.polygon(left, fill=PINK_DARK)
    draw.polygon(right, fill=PINK_MID)

    # Thin outline for a cut-glass edge look
    outline = (12, 40, 46, 255)
    for facet in (top, left, right):
        draw.line(facet + [facet[0]], fill=outline, width=max(2, size // 90))

    # Subtle glass "shine" streak across the top facet
    shine = [(cx - s * 0.55, cy - s * 0.85), (cx - s * 0.1, cy - s * 1.02),
             (cx + s * 0.25, cy - s * 0.75), (cx - s * 0.2, cy - s * 0.55)]
    draw.polygon(shine, fill=HIGHLIGHT)

    return img


def main():
    img = draw_cube(256)
    img.save("assets/logo_mark.png")

    # Multi-resolution .ico for a crisp Windows exe icon
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save("assets/logo_mark.ico", sizes=sizes)
    print("Wrote assets/logo_mark.png and assets/logo_mark.ico")


if __name__ == "__main__":
    main()
