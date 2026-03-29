#!/usr/bin/env python3
"""Generate PNG icons for BoxBunny Dashboard PWA.

Creates icon-192.png and icon-512.png from the favicon SVG concept:
a green (#00E676) rounded rectangle with "BB" text in white.
Uses PIL/Pillow to generate the images programmatically.
"""

import os
import sys

DASHBOARD_PUBLIC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src", "boxbunny_dashboard", "frontend", "public"
)


def generate_icon(size, filepath):
    """Generate a BoxBunny icon at the given size."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL/Pillow not available. Trying alternative approach...")
        generate_icon_raw(size, filepath)
        return

    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background
    margin = int(size * 0.08)
    radius = int(size * 0.18)
    rect_bbox = [margin, margin + int(size * 0.06), size - margin, size - margin - int(size * 0.06)]
    draw.rounded_rectangle(rect_bbox, radius=radius, fill=(0, 230, 118, 255))

    # Draw "BB" text
    font_size = int(size * 0.35)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
        except (IOError, OSError):
            font = ImageFont.load_default()

    text = "BB"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2
    draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

    img.save(filepath, 'PNG')
    print(f"  Created {os.path.basename(filepath)} ({size}x{size}, {os.path.getsize(filepath)} bytes)")


def generate_icon_raw(size, filepath):
    """Fallback: generate a minimal valid PNG without PIL.
    Creates a simple green square with white center area.
    """
    import struct
    import zlib

    # Create raw pixel data - RGBA
    pixels = bytearray()
    margin = int(size * 0.08)
    center_start = int(size * 0.3)
    center_end = int(size * 0.7)

    for y in range(size):
        pixels.append(0)  # Filter byte for each row
        for x in range(size):
            in_rect = margin <= x < size - margin and margin + int(size * 0.06) <= y < size - margin - int(size * 0.06)
            in_text = center_start <= x < center_end and center_start <= y < center_end

            if in_text and in_rect:
                # White for text area
                pixels.extend([255, 255, 255, 255])
            elif in_rect:
                # Green for background
                pixels.extend([0, 230, 118, 255])
            else:
                # Transparent
                pixels.extend([0, 0, 0, 0])

    # Build PNG
    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', zlib.crc32(chunk) & 0xFFFFFFFF)

    png = b'\x89PNG\r\n\x1a\n'
    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)  # 8-bit RGBA
    png += make_chunk(b'IHDR', ihdr_data)
    # IDAT
    compressed = zlib.compress(bytes(pixels), 9)
    png += make_chunk(b'IDAT', compressed)
    # IEND
    png += make_chunk(b'IEND', b'')

    with open(filepath, 'wb') as f:
        f.write(png)
    print(f"  Created {os.path.basename(filepath)} ({size}x{size}, {os.path.getsize(filepath)} bytes) [fallback mode]")


def main():
    os.makedirs(DASHBOARD_PUBLIC, exist_ok=True)
    print(f"Generating PWA icons in: {DASHBOARD_PUBLIC}")
    print()

    generate_icon(192, os.path.join(DASHBOARD_PUBLIC, "icon-192.png"))
    generate_icon(512, os.path.join(DASHBOARD_PUBLIC, "icon-512.png"))

    print()
    print("PWA icons generated successfully!")


if __name__ == "__main__":
    main()
