#!/usr/bin/env python3
"""
Generate PWA Icons for Birdy
Erstellt Icons mit gezeichnetem rotem Vogel
"""
from PIL import Image, ImageDraw
from pathlib import Path

# Icon-Größen für PWA (Android, iOS)
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# Farben
BACKGROUND_COLOR = "#667eea"  # Lila-Blau (wie Header)

def create_icon(size, output_path):
    """Erstelle ein Icon mit gezeichnetem Vogel"""
    # Erstelle Bild mit Hintergrund
    img = Image.new('RGB', (size, size), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    # Zeichne stilisierten Vogel
    center_x = size // 2
    center_y = size // 2
    scale = size / 100.0  # Skalierungsfaktor für proportionale Größe

    # Körper (großer roter Kreis - leicht nach unten)
    body_radius = int(28 * scale)
    body_y_offset = int(8 * scale)
    body_bbox = [
        center_x - body_radius,
        center_y - body_radius + body_y_offset,
        center_x + body_radius,
        center_y + body_radius + body_y_offset
    ]
    draw.ellipse(body_bbox, fill="#ff4444", outline="#cc0000", width=int(2 * scale))

    # Kopf (kleinerer roter Kreis oben)
    head_radius = int(16 * scale)
    head_y = center_y - int(22 * scale)
    head_bbox = [
        center_x - head_radius,
        head_y - head_radius,
        center_x + head_radius,
        head_y + head_radius
    ]
    draw.ellipse(head_bbox, fill="#ff6666", outline="#cc0000", width=int(2 * scale))

    # Schnabel (Dreieck nach rechts)
    beak_size = int(10 * scale)
    beak_x = center_x + head_radius - int(2 * scale)
    beak_y = head_y
    beak_points = [
        (beak_x, beak_y),
        (beak_x + beak_size * 1.5, beak_y - beak_size // 3),
        (beak_x + beak_size * 1.5, beak_y + beak_size // 3)
    ]
    draw.polygon(beak_points, fill="#ffaa00", outline="#cc8800", width=int(1 * scale))

    # Auge (weißer Kreis mit schwarzer Pupille)
    eye_radius = int(4 * scale)
    eye_x = center_x + int(6 * scale)
    eye_y = head_y - int(3 * scale)
    eye_bbox = [
        eye_x - eye_radius,
        eye_y - eye_radius,
        eye_x + eye_radius,
        eye_y + eye_radius
    ]
    draw.ellipse(eye_bbox, fill="white", outline="black", width=1)

    # Pupille
    pupil_radius = int(2 * scale)
    pupil_bbox = [
        eye_x - pupil_radius,
        eye_y - pupil_radius,
        eye_x + pupil_radius,
        eye_y + pupil_radius
    ]
    draw.ellipse(pupil_bbox, fill="black")

    # Flügel links (dunkler roter Halbkreis)
    wing_radius = int(20 * scale)
    wing_x = center_x - int(15 * scale)
    wing_y = center_y + body_y_offset
    wing_bbox = [
        wing_x - wing_radius,
        wing_y - wing_radius,
        wing_x + wing_radius,
        wing_y + wing_radius
    ]
    draw.pieslice(wing_bbox, 120, 240, fill="#cc0000", outline="#990000", width=int(2 * scale))

    # Schwanz (3 Federn als Dreiecke nach rechts unten)
    tail_x = center_x + body_radius - int(8 * scale)
    tail_y = center_y + body_y_offset + int(12 * scale)
    tail_size = int(15 * scale)

    # Mittlere Feder
    tail_points_1 = [
        (tail_x, tail_y),
        (tail_x + tail_size * 1.2, tail_y - tail_size // 3),
        (tail_x + tail_size * 1.2, tail_y + tail_size // 3)
    ]
    draw.polygon(tail_points_1, fill="#cc0000", outline="#990000", width=int(1 * scale))

    # Obere Feder
    tail_points_2 = [
        (tail_x - int(3 * scale), tail_y - int(6 * scale)),
        (tail_x + tail_size, tail_y - tail_size),
        (tail_x + tail_size, tail_y - tail_size // 2)
    ]
    draw.polygon(tail_points_2, fill="#aa0000", outline="#880000", width=int(1 * scale))

    # Untere Feder
    tail_points_3 = [
        (tail_x - int(3 * scale), tail_y + int(6 * scale)),
        (tail_x + tail_size, tail_y + tail_size // 2),
        (tail_x + tail_size, tail_y + tail_size)
    ]
    draw.polygon(tail_points_3, fill="#aa0000", outline="#880000", width=int(1 * scale))

    # Beine (zwei dünne Linien nach unten)
    leg_length = int(12 * scale)
    leg_width = int(3 * scale)

    # Linkes Bein
    left_leg_x = center_x - int(8 * scale)
    leg_y_start = center_y + body_radius + body_y_offset - int(5 * scale)
    draw.line([
        (left_leg_x, leg_y_start),
        (left_leg_x - int(3 * scale), leg_y_start + leg_length)
    ], fill="#ff8800", width=leg_width)

    # Rechtes Bein
    right_leg_x = center_x + int(8 * scale)
    draw.line([
        (right_leg_x, leg_y_start),
        (right_leg_x + int(3 * scale), leg_y_start + leg_length)
    ], fill="#ff8800", width=leg_width)

    # Speichere Icon
    img.save(output_path, 'PNG', optimize=True)
    print(f"✓ Created {output_path.name} ({size}x{size})")

def main():
    """Generiere alle Icons"""
    icons_dir = Path(__file__).parent / 'static' / 'icons'
    icons_dir.mkdir(parents=True, exist_ok=True)

    print("=== Generating Birdy PWA Icons ===")
    print("Design: Roter Vogel mit Kopf, Schnabel, Auge, Flügel, Schwanz und Beinen\n")

    for size in ICON_SIZES:
        output_path = icons_dir / f'icon-{size}x{size}.png'
        create_icon(size, output_path)

    # Erstelle favicon (32x32)
    print("\nCreating favicon...")
    favicon_32_path = icons_dir / 'favicon-32x32.png'
    create_icon(32, favicon_32_path)

    # Konvertiere zu .ico
    favicon_path = Path(__file__).parent / 'static' / 'favicon.ico'
    img = Image.open(favicon_32_path)
    img.save(favicon_path, format='ICO', sizes=[(32, 32)])
    print(f"✓ Created favicon.ico")

    # Erstelle apple-touch-icon (180x180)
    print("\nCreating Apple Touch Icon...")
    apple_icon_path = icons_dir / 'apple-touch-icon.png'
    create_icon(180, apple_icon_path)

    print(f"\n{'='*50}")
    print(f"✅ Done! Created {len(ICON_SIZES) + 2} icons")
    print(f"{'='*50}")
    print("\nNext steps:")
    print("1. python manage.py collectstatic --noinput")
    print("2. Restart Django: ./stop_dev.sh && ./start_dev.sh")
    print("3. Hard refresh browser (Ctrl+Shift+R)")
    print("4. Check icons in browser DevTools > Application > Manifest")

if __name__ == '__main__':
    main()
