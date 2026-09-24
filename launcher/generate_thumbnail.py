"""Generate a high-fidelity 1280x720 thumbnail for the Compust Capture extension demo."""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "media" / "extension-demo-thumbnail.png"
LOGO_PATH = REPO_ROOT / "docs" / "logo-transparent.png"
POSTER_PATH = REPO_ROOT / "docs" / "media" / "compust-capture-demo-poster.png"

WIDTH = 1280
HEIGHT = 720

def create_puzzle_icon(size=48, fill_color=(56, 189, 248, 255), stroke_color=(255, 255, 255, 220)):
    """Draw a clean, crisp puzzle-piece icon at high resolution and downscale with anti-aliasing."""
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Base square coordinates with padding
    pad = int(s * 0.18)
    bx0, by0 = pad, pad
    bx1, by1 = s - pad, s - pad
    bw = bx1 - bx0
    bh = by1 - by0

    tab_r = int(bw * 0.19)
    tab_neck = int(tab_r * 0.75)
    cx = (bx0 + bx1) // 2
    cy = (by0 + by1) // 2

    # Draw base rounded body
    corner_r = int(bw * 0.12)
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=corner_r, fill=fill_color)

    # Top tab (protruding outward)
    draw.ellipse([cx - tab_r, by0 - tab_r - int(tab_r * 0.4), cx + tab_r, by0 + tab_r - int(tab_r * 0.4)], fill=fill_color)
    draw.rectangle([cx - tab_neck, by0 - int(tab_r * 0.5), cx + tab_neck, by0 + 2], fill=fill_color)

    # Right tab (protruding outward)
    draw.ellipse([bx1 - tab_r + int(tab_r * 0.4), cy - tab_r, bx1 + tab_r + int(tab_r * 0.4), cy + tab_r], fill=fill_color)
    draw.rectangle([bx1 - 2, cy - tab_neck, bx1 + int(tab_r * 0.5), cy + tab_neck], fill=fill_color)

    # Bottom tab cutout (inward hole)
    # Mask out bottom indentation
    mask_cut = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    cut_draw = ImageDraw.Draw(mask_cut)
    cut_draw.ellipse([cx - tab_r, by1 - tab_r - int(tab_r * 0.3), cx + tab_r, by1 + tab_r - int(tab_r * 0.3)], fill=(0, 0, 0, 255))
    cut_draw.rectangle([cx - tab_neck, by1 - 4, cx + tab_neck, by1 + 4], fill=(0, 0, 0, 255))

    # Left tab cutout (inward hole)
    cut_draw.ellipse([bx0 - tab_r - int(tab_r * 0.3), cy - tab_r, bx0 + tab_r - int(tab_r * 0.3), cy + tab_r], fill=(0, 0, 0, 255))
    cut_draw.rectangle([bx0 - 4, cy - tab_neck, bx0 + 4, cy + tab_neck], fill=(0, 0, 0, 255))

    # Apply cuts
    # Subtract mask_cut from img
    img_data = img.load()
    cut_data = mask_cut.load()
    for y in range(s):
        for x in range(s):
            if cut_data[x, y][3] > 0:
                img_data[x, y] = (0, 0, 0, 0)

    # Downscale smoothly
    return img.resize((size, size), Image.Resampling.LANCZOS)


def generate_thumbnail():
    print(f"Generating thumbnail at {WIDTH}x{HEIGHT}...")
    
    # 1. Base image from poster / video screenshot
    if POSTER_PATH.exists():
        base = Image.open(POSTER_PATH).convert("RGBA")
        base = base.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        # Apply gentle blur so text and controls pop
        base = base.filter(ImageFilter.GaussianBlur(radius=5))
    else:
        # Fallback dark background
        base = Image.new("RGBA", (WIDTH, HEIGHT), (8, 12, 20, 255))

    # 2. Gradient / Dark overlay (Compust brand palette: #080c14, #0f1623, #162032)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    # Vertical gradient + radial vignette
    for y in range(HEIGHT):
        alpha = int(170 + 75 * (y / HEIGHT)) # 170 to 245
        draw_ov.line([(0, y), (WIDTH, y)], fill=(8, 12, 20, min(240, alpha)))

    # Subtle radial glow in the center for the play button
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    cx, cy = WIDTH // 2, HEIGHT // 2 - 20
    for r in range(220, 0, -5):
        alpha = int(35 * (1 - r / 220))
        glow_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(59, 130, 246, alpha))

    base = Image.alpha_composite(base, overlay)
    base = Image.alpha_composite(base, glow)

    # 3. Branding Header (Top Left)
    # Load fonts
    font_bold_lg = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 36)
    font_bold_md = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 22)
    font_semibold = ImageFont.truetype("C:/Windows/Fonts/seguisb.ttf", 16)
    font_caption = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
    font_tag = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 15)

    # Composite logo
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert("RGBA")
        # Resize logo maintaining aspect ratio (target height = 60)
        logo_h = 60
        logo_w = int(logo.width * (logo_h / logo.height))
        logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        
        logo_x = 50
        logo_y = 40
        base.paste(logo, (logo_x, logo_y), logo)
        
        # Title "Compust"
        title_x = logo_x + logo_w + 16
        title_y = logo_y + 10
    else:
        title_x = 50
        title_y = 50

    draw = ImageDraw.Draw(base)
    draw.text((title_x, title_y), "Compust", font=font_bold_lg, fill=(255, 255, 255, 255))
    
    # Title width
    bbox_title = draw.textbbox((title_x, title_y), "Compust", font=font_bold_lg)
    badge_x = bbox_title[2] + 16
    badge_y = title_y + 4

    # Browser Extension Badge with Puzzle Piece Icon
    # Badge background
    puzzle_size = 22
    puzzle_img = create_puzzle_icon(size=puzzle_size, fill_color=(56, 189, 248, 255))
    badge_text = "Browser Extension Demo"
    bbox_bt = draw.textbbox((0, 0), badge_text, font=font_semibold)
    bt_w = bbox_bt[2] - bbox_bt[0]
    badge_w = puzzle_size + bt_w + 32
    badge_h = 36

    # Draw rounded badge
    badge_rect = [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h]
    draw.rounded_rectangle(badge_rect, radius=18, fill=(15, 23, 42, 220), outline=(56, 189, 248, 120), width=1)
    base.paste(puzzle_img, (badge_x + 10, badge_y + (badge_h - puzzle_size) // 2), puzzle_img)
    draw.text((badge_x + 10 + puzzle_size + 8, badge_y + 7), badge_text, font=font_semibold, fill=(56, 189, 248, 255))

    # Top-right duration / quality pill
    tr_text = "1080p HD  •  1:22 min"
    bbox_tr = draw.textbbox((0, 0), tr_text, font=font_tag)
    tr_w = bbox_tr[2] - bbox_tr[0] + 28
    tr_x = WIDTH - 50 - tr_w
    tr_y = 50
    draw.rounded_rectangle([tr_x, tr_y, tr_x + tr_w, tr_y + 32], radius=16, fill=(15, 23, 42, 180), outline=(255, 255, 255, 30), width=1)
    draw.text((tr_x + 14, tr_y + 6), tr_text, font=font_tag, fill=(148, 163, 184, 255))

    # 4. Large Centered Play Button
    # Center coordinates
    play_cx = WIDTH // 2
    play_cy = HEIGHT // 2 - 30
    btn_r = 54  # 108px diameter

    # Outer soft glow ring
    glow_btn = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_btn_draw = ImageDraw.Draw(glow_btn)
    for r in range(btn_r + 25, btn_r, -2):
        a = int(60 * (1 - (r - btn_r) / 25))
        glow_btn_draw.ellipse([play_cx - r, play_cy - r, play_cx + r, play_cy + r], fill=(59, 130, 246, a))
    base = Image.alpha_composite(base, glow_btn)
    draw = ImageDraw.Draw(base)

    # Main Play Button Circle: Vibrant gradient feel (#2563eb / #1d4ed8)
    draw.ellipse(
        [play_cx - btn_r, play_cy - btn_r, play_cx + btn_r, play_cy + btn_r],
        fill=(37, 99, 235, 240),
        outline=(255, 255, 255, 220),
        width=3
    )

    # Play Triangle glyph (pointing right, centered visually)
    # Visual center of a triangle is 1/3 from base, so offset x slightly forward
    tri_w = 34
    tri_h = 38
    x_offset = 4
    tri_p1 = (play_cx - tri_w // 2 + x_offset, play_cy - tri_h // 2)
    tri_p2 = (play_cx - tri_w // 2 + x_offset, play_cy + tri_h // 2)
    tri_p3 = (play_cx + tri_w // 2 + x_offset, play_cy)
    draw.polygon([tri_p1, tri_p2, tri_p3], fill=(255, 255, 255, 255))

    # 5. Prominent Caption Banner: "Click to see how the extension works!"
    caption_text = "Click to see how the extension works!"
    bbox_cap = draw.textbbox((0, 0), caption_text, font=font_caption)
    cap_w = bbox_cap[2] - bbox_cap[0]
    cap_h = bbox_cap[3] - bbox_cap[1]

    banner_pad_x = 36
    banner_pad_y = 16
    banner_w = cap_w + banner_pad_x * 2
    banner_h = cap_h + banner_pad_y * 2
    banner_x = (WIDTH - banner_w) // 2
    banner_y = play_cy + btn_r + 40

    # Banner shadow
    banner_shadow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    b_s_draw = ImageDraw.Draw(banner_shadow)
    b_s_draw.rounded_rectangle(
        [banner_x - 3, banner_y - 1, banner_x + banner_w + 3, banner_y + banner_h + 6],
        radius=24,
        fill=(0, 0, 0, 140)
    )
    banner_shadow = banner_shadow.filter(ImageFilter.GaussianBlur(radius=8))
    base = Image.alpha_composite(base, banner_shadow)
    draw = ImageDraw.Draw(base)

    # High-contrast glass banner
    draw.rounded_rectangle(
        [banner_x, banner_y, banner_x + banner_w, banner_y + banner_h],
        radius=banner_h // 2,
        fill=(11, 17, 30, 235),
        outline=(59, 130, 246, 180),
        width=2
    )

    # Draw Caption Text
    text_x = banner_x + banner_pad_x
    text_y = banner_y + banner_pad_y - 2
    draw.text((text_x, text_y), caption_text, font=font_caption, fill=(255, 255, 255, 255))

    # Sub-caption below banner
    sub_text = "Live in-browser job extraction  •  Instant resume match score  •  One-click tracking"
    bbox_sub = draw.textbbox((0, 0), sub_text, font=font_semibold)
    sub_w = bbox_sub[2] - bbox_sub[0]
    draw.text(((WIDTH - sub_w) // 2, banner_y + banner_h + 18), sub_text, font=font_semibold, fill=(148, 163, 184, 230))

    # 6. Save output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Save optimized PNG
    base.save(OUTPUT_PATH, format="PNG", optimize=True)
    print(f"Successfully saved thumbnail to: {OUTPUT_PATH}")
    print(f"File size: {OUTPUT_PATH.stat().st_size} bytes ({OUTPUT_PATH.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    generate_thumbnail()
