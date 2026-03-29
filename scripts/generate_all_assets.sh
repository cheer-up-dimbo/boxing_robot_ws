#!/bin/bash
# Generate all BoxBunny assets
set -e

WORKSPACE="/home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws"

echo "=== Generating Sound Effects ==="
python3 "$WORKSPACE/scripts/generate_sounds.py"

echo ""
echo "=== Generating PWA Icons ==="
python3 "$WORKSPACE/scripts/generate_icons.py"

echo ""
echo "=== Setting up Inter Font ==="
FONTS_DIR="$WORKSPACE/src/boxbunny_gui/assets/fonts"
mkdir -p "$FONTS_DIR"

# Try to download Inter font
if command -v wget &> /dev/null; then
    echo "Attempting to download Inter font..."
    wget -q "https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip" -O /tmp/inter.zip 2>/dev/null && {
        cd "$FONTS_DIR"
        unzip -o /tmp/inter.zip "*.ttf" 2>/dev/null || true
        find /tmp/ -name "Inter*.ttf" -exec cp {} . \; 2>/dev/null || true
        rm -f /tmp/inter.zip
        echo "Inter font files:"
        ls -la *.ttf 2>/dev/null || echo "No TTF files found - see FONT_README.txt"
    } || {
        echo "Download failed - creating instructions file"
    }
fi

# Create font readme if no fonts found
if [ ! -f "$FONTS_DIR/Inter-Variable.ttf" ]; then
    cat > "$FONTS_DIR/FONT_README.txt" << 'FONTEOF'
Inter Font - Manual Installation Required
==========================================

The Inter font could not be downloaded automatically.

To install manually:
1. Visit: https://github.com/rsms/inter/releases
2. Download the latest Inter release ZIP
3. Extract Inter-Variable.ttf and Inter-Variable-Italic.ttf
4. Place them in this directory (src/boxbunny_gui/assets/fonts/)

The GUI will fall back to system sans-serif fonts if Inter is not available.
FONTEOF
    echo "Created FONT_README.txt with installation instructions"
fi

echo ""
echo "=== Asset Generation Complete ==="
echo ""
echo "File counts:"
echo "  Sounds: $(find "$WORKSPACE/src/boxbunny_gui/assets/sounds" -name "*.wav" | wc -l) WAV files"
echo "  Icons:  $(find "$WORKSPACE/src/boxbunny_gui/assets/icons" -name "*.svg" | wc -l) SVG files"
echo "  PWA:    $(find "$WORKSPACE/src/boxbunny_dashboard/frontend/public" -maxdepth 1 -name "*.png" -o -name "*.svg" | wc -l) files"
echo "  Ranks:  $(find "$WORKSPACE/src/boxbunny_dashboard/frontend/public/ranks" -name "*.svg" | wc -l) SVG files"
echo "  Badges: $(find "$WORKSPACE/src/boxbunny_dashboard/frontend/public/achievements" -name "*.svg" | wc -l) SVG files"
echo ""
echo "Total asset files:"
find "$WORKSPACE/src/boxbunny_gui/assets" "$WORKSPACE/src/boxbunny_dashboard/frontend/public" -type f | wc -l
