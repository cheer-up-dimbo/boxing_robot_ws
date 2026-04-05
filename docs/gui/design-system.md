# BoxBunny GUI -- Design System

Complete visual design reference for the BoxBunny touchscreen interface.
All values are sourced from `src/boxbunny_gui/boxbunny_gui/theme.py`.

---

## 1. Design Philosophy

- **Target display:** 7-inch touchscreen at 1024x600 pixels (Jetson Orin NX).
- **Gloved-hand UX:** All interactive elements have a minimum 60px touch target
  (`Size.MIN_TOUCH = 60`). Pattern lock dots use a 48px hit radius even though
  they render at 22px, accommodating boxing gloves.
- **Dark theme:** Deep navy-black background reduces glare under bright gym
  lighting and preserves focus on high-contrast content.
- **Fullscreen scaling:** The UI is pixel-designed at 1024x600 and scaled
  uniformly via `QGraphicsView` for fullscreen, so all proportions hold on any
  display resolution.

---

## 2. Color Palette

All colors are defined as class constants on `Color` in `theme.py`. No inline hex
codes appear anywhere else in the codebase.

### Background Layers

| Constant | Hex | Usage |
|----------|-----|-------|
| `BG` | `#0B0F14` | Root background -- deep navy-black |
| `BG_GRADIENT_TOP` | `#0E1319` | Slightly lighter for gradient backgrounds |
| `BG_GRADIENT_BTM` | `#080B10` | Slightly darker for gradient backgrounds |
| `SURFACE` | `#131920` | Cards, panels, input fields |
| `SURFACE_LIGHT` | `#1A2029` | Raised elements, disabled button backgrounds |
| `SURFACE_HOVER` | `#222B37` | Hover state for surface elements |
| `SURFACE_GLASS` | `rgba(19, 25, 32, 0.85)` | Glassmorphism-style translucent panels |

### Accent Colors

| Constant | Hex | Usage |
|----------|-----|-------|
| `PRIMARY` | `#FF6B35` | Warm orange -- primary CTA buttons, active states, accent bars |
| `PRIMARY_DARK` | `#E85E2C` | Hover state for primary elements |
| `PRIMARY_PRESSED` | `#CC5025` | Pressed state for primary elements |
| `PRIMARY_LIGHT` | `#FF8C5E` | Highlights, glow effects, slider handle hover |
| `PRIMARY_MUTED` | `#FF6B3518` | Very subtle orange tint (8% opacity) |
| `PRIMARY_GLOW` | `#FF6B3530` | Subtle glow background (19% opacity) |
| `WARNING` | `#FFAB40` | Warm amber -- warnings, right hook punch color |
| `WARNING_DARK` | `#FF9100` | Hover state for warning elements |
| `DANGER` | `#FF5C5C` | Vibrant coral-red -- destructive actions, cross punch color |
| `DANGER_DARK` | `#E84545` | Hover state for danger elements |
| `SUCCESS` | `#56D364` | Fresh green -- confirmations, left hook punch color |
| `SUCCESS_DARK` | `#3FB950` | Hover state for success elements |
| `INFO` | `#58A6FF` | Soft blue -- informational, jab punch color |
| `INFO_DARK` | `#388BFD` | Hover state for info elements |
| `PURPLE` | `#BC8CFF` | Lavender accent -- left uppercut punch color |

### Text Colors

| Constant | Hex | Usage |
|----------|-----|-------|
| `TEXT` | `#E6EDF3` | Primary text -- bright off-white |
| `TEXT_SECONDARY` | `#8B949E` | Muted grey -- labels, descriptions, inactive nav |
| `TEXT_DISABLED` | `#484F58` | Very dim -- disabled text, placeholders |
| `TEXT_ACCENT` | `#FFB088` | Warm accent text -- titles, highlighted values |

### Border Colors

| Constant | Hex | Usage |
|----------|-----|-------|
| `BORDER` | `#1C222A` | Default border -- barely visible separation |
| `BORDER_LIGHT` | `#2A3340` | Slightly brighter border -- input fields, cards |
| `BORDER_ACCENT` | `#FF6B3540` | Subtle orange border (25% opacity) |
| `TRANSPARENT` | `transparent` | Ghost buttons, overlay backgrounds |

### Punch Type Colors

Used by `ComboDisplay`, `DevOverlay`, and chart components to color-code punches:

| Constant | Hex | Color | Punch Type |
|----------|-----|-------|------------|
| `JAB` | `#58A6FF` | Blue | Jab (1) |
| `CROSS` | `#FF5C5C` | Coral | Cross (2) |
| `L_HOOK` | `#56D364` | Green | Left Hook (3) |
| `R_HOOK` | `#FFAB40` | Amber | Right Hook (4) |
| `L_UPPERCUT` | `#BC8CFF` | Purple | Left Uppercut (5) |
| `R_UPPERCUT` | `#F8E45C` | Yellow | Right Uppercut (6) |
| `BLOCK` | `#8B949E` | Grey | Block / Defense |
| `IDLE` | `#484F58` | Dark Grey | Idle / No punch |

---

## 3. Typography

### Font Family

**Inter** (variable weight) loaded at startup from `assets/fonts/InterVariable.ttf`.

Fallback stack: `"Inter", "Segoe UI", "Helvetica Neue", sans-serif`

The global stylesheet sets a base `font-size: 15px` and `font-weight: 500` on
all `QWidget` elements.

### `font()` Helper

```python
def font(size: int = 16, bold: bool = False) -> QFont:
```

Creates a `QFont("Inter", size)` with optional bold weight. Used throughout pages
and widgets for consistent font creation.

### Size Hierarchy

All text sizes are defined as `Size` constants:

| Constant | Pixels | Usage |
|----------|--------|-------|
| `TEXT_TIMER_XL` | 96 | Extra-large timer (countdown splash) |
| `TEXT_TIMER` | 80 | Primary timer display |
| `TEXT_TIMER_SM` | 60 | Compact timer display |
| `TEXT_HEADER` | 28 | Page titles, section headers |
| `TEXT_SUBHEADER` | 22 | Subtitles, card headers |
| `TEXT_BODY` | 16 | Body text, button labels |
| `TEXT_LABEL` | 14 | Form labels, badge text, outline buttons |
| `TEXT_CAPTION` | 12 | Captions, stat card titles |
| `TEXT_OVERLINE` | 10 | Overline text, very small labels |

### Weight Conventions

- **700 (Bold)** -- Section title overlines, active tab pills, hero CTAs, badge labels
- **600 (SemiBold)** -- Standard buttons, card titles, mode card text, nav buttons
- **500 (Medium)** -- Base body text (set globally)

### Letter Spacing

- `0.3px` -- Standard buttons and hero CTAs
- `0.6px` -- Badge pill labels
- `1.2px` -- Section title overlines (uppercase)

---

## 4. Spacing System

Based on a **20px base grid** (`Size.SPACING = 20`).

| Constant | Pixels | Usage |
|----------|--------|-------|
| `SPACING_XS` | 6 | Tight padding (between icon and text) |
| `SPACING_SM` | 10 | Compact spacing (between related elements) |
| `SPACING` | 20 | Standard spacing (margins, gaps, padding) |
| `SPACING_LG` | 24 | Generous spacing (section gaps) |
| `SPACING_XL` | 32 | Large spacing (major section separation) |

### Layout Margins

`Size.LAYOUT_MARGINS = (60, 40, 60, 40)` -- left, top, right, bottom padding
for page content areas.

---

## 5. Corner Radii

| Constant | Pixels | Usage |
|----------|--------|-------|
| `RADIUS_SM` | 8 | Small elements: back buttons, nav pills, checkboxes |
| `RADIUS` | 12 | Standard: buttons, input fields, stat cards, pill toggles |
| `RADIUS_LG` | 16 | Large: mode cards, config tiles, hero buttons, elevated cards |
| `RADIUS_XL` | 20 | Extra-large: special overlay panels |

---

## 6. Button Styles

All button styles are generated by the `button_style()` factory function, which
produces a complete `QPushButton` stylesheet with background, hover, pressed, and
disabled states.

### Pre-built Button Styles

| Constant | Background | Hover | Text | Purpose |
|----------|------------|-------|------|---------|
| `PRIMARY_BTN` | `#FF6B35` (orange) | `#E85E2C` | `#FFFFFF` | Primary call-to-action |
| `DANGER_BTN` | `#FF5C5C` (coral) | `#E84545` | `#E6EDF3` | Destructive / stop actions |
| `WARNING_BTN` | `#FFAB40` (amber) | `#FF9100` | `#E6EDF3` | Warning actions |
| `SUCCESS_BTN` | `#56D364` (green) | `#3FB950` | `#E6EDF3` | Positive confirmations |
| `SURFACE_BTN` | `#1A2029` (surface) | `#222B37` | `#8B949E` | Secondary actions (bordered) |
| `GHOST_BTN` | `transparent` | `#131920` | `#8B949E` | Minimal / tertiary actions |
| `INFO_BTN` | `#131920` (surface) | `#222B37` | `#58A6FF` | Informational actions (bordered) |

All pre-built buttons use:
- `font-size: 16px`, `font-weight: 600`
- `min-height: 44px`, `border-radius: 12px`
- `padding: 8px 24px`, `letter-spacing: 0.3px`
- Disabled state: `background: #1A2029`, `color: #484F58`

### Specialized Button Style Functions

#### `hero_btn_style(bg, hover, size=22)`
Large hero CTA button. Default orange background, white text, `font-weight: 700`,
`border-radius: 16px`, `letter-spacing: 0.5px`. No border.

#### `secondary_btn_style()`
Border-emphasized button for Log In, Sign Up, etc. `font-size: 18px`, `2px solid`
border, hover turns border orange with light orange text.

#### `outline_btn_style(accent)`
Transparent button with colored border. Fills with solid accent color on hover,
text turns white. `font-size: 14px`, `border-radius: 8px`.

#### `subtle_btn_style()`
Very minimal button for secondary actions. `font-size: 13px`, `1px solid` border,
surface background on hover. `padding: 7px 16px`.

#### `pill_toggle_style(active: bool)`
Segmented control pill. Active state: orange background, white text, `2px solid`
orange border. Inactive: surface background, grey text, dark border.
`font-size: 14px`, `padding: 8px 16px`.

#### `top_bar_btn_style()`
Small ghost button for top-bar actions (Settings, Close). `font-size: 13px`,
`1px solid` border, hover adds orange border color.

#### `close_btn_style()`
Same as top-bar button but hover turns red (`DANGER` background + white text).

#### `back_link_style()`
Back button with border. `min-height: 30px`, `min-width: 70px`, `border-radius: 8px`,
`margin-right: 8px`. Hover adds orange border.

#### `tab_btn_style(active: bool)`
Filter/tab pill button. Active: orange background, `font-weight: 700`,
`border-radius: 10px`. Inactive: surface background, grey text with border.

---

## 7. Card Styles

### Mode Cards

#### `mode_card_style(accent)`
Premium mode selection card with a **colored left accent bar** (`4px` wide) and
glow hover effect. `border-radius: 16px`, `padding: 16px 20px`, `font-size: 16px`,
`font-weight: 600`, `text-align: left`. Hover adds tinted border color.

#### `mode_card_style_v2(accent)`
Enhanced variant with a `5px` left accent bar, zero padding (layout is custom
inside), and a more pronounced hover glow (50% opacity accent border).

### Config Tiles

#### `config_tile_style()`
Tappable configuration tile that cycles through values on tap. Standard surface
background with border, `border-radius: 16px`, hover adds orange border.

#### `config_tile_style_v2(accent)`
Config tile with a **colored top accent** (`3px` top border). Accent defaults to
`PRIMARY` orange.

### Card Frames

#### `elevated_card_style(accent="")`
QFrame card with subtle hover elevation. Optional colored top accent bar (`3px`).
`border-radius: 16px`. Hover lightens background and brightens border.

#### `glass_card_style()`
Glassmorphism-inspired card with semi-transparent background
(`rgba(19, 25, 32, 0.82)`). `border-radius: 16px`, light border.

#### `accent_frame_style(accent)`
QFrame with a colored **left accent bar** (`4px`). Used for stat cards and info
panels. `border-radius: 12px`.

### Badges

#### `badge_style(color="")`
Small inline pill label. `font-size: 11px`, `font-weight: 700`,
`border-radius: 8px`, `padding: 4px 12px`, `letter-spacing: 0.6px`. Surface
background.

### Section Titles

#### `section_title_style(color="")`
Section header label. `font-size: 13px`, `font-weight: 700`,
`letter-spacing: 1.2px`, `text-transform: uppercase`. Color defaults to orange.

---

## 8. Dimensions and Layout

### Screen

| Constant | Value | Purpose |
|----------|-------|---------|
| `SCREEN_W` | 1024 | Design-time width |
| `SCREEN_H` | 600 | Design-time height |
| `SIDEBAR_W` | 200 | Sidebar width (if used) |
| `TOP_BAR_H` | 50 | Top navigation bar height |

### Buttons

| Constant | Value | Purpose |
|----------|-------|---------|
| `BUTTON_H` | 60 | Standard button height (matches MIN_TOUCH) |
| `BUTTON_H_SM` | 44 | Compact button height |
| `BUTTON_H_LG` | 64 | Large button height |
| `BUTTON_W_SM` | 120 | Small button width |
| `BUTTON_W_MD` | 300 | Medium button width |
| `BUTTON_W_LG` | 500 | Large button width |

### Visual Effects

| Constant | Value | Purpose |
|----------|-------|---------|
| `SHADOW_BLUR` | 20 | Standard drop shadow blur radius |
| `SHADOW_BLUR_LG` | 32 | Large drop shadow blur radius |
| `ACCENT_BAR_W` | 4 | Width of accent bars on cards |
| `RING_THICKNESS` | 6 | Progress ring stroke width |

---

## 9. Global Stylesheet

`GLOBAL_STYLESHEET` is applied once at application startup and styles all
base Qt widgets:

### Widget Defaults

- **QWidget** -- Background: `#0B0F14`, text: `#E6EDF3`, font: Inter 15px weight 500.
- **QLabel, QFrame** -- Transparent background, no border.
- **QScrollArea** -- No border, transparent. Scrollbar: 5px wide, handle `#2A3340`,
  hover `#484F58`, rounded 2px.
- **QCheckBox** -- 26x26 indicator with 7px radius. Unchecked: surface background
  with border. Checked: orange fill with orange border. Hover: light orange border.
- **QSlider** -- 6px groove, 22px round handle. Sub-page (filled portion) is orange.
  Handle hover turns light orange.
- **QLineEdit** -- Surface background, light border, 12px radius, focus border turns
  orange. Placeholder text in dim grey. Selection highlight is orange.
- **QProgressBar** -- 8px height, surface background, orange chunk, 4px radius.

---

## 10. Icon System

Text-based icons from the `Icon` class (no image assets, no emojis):

| Constant | Character | Usage |
|----------|-----------|-------|
| `CHECK` | `\u2713` | Completion, success |
| `CLOSE` | `\u2715` | Close, dismiss |
| `BACK` | `\u2190` | Back navigation |
| `NEXT` | `\u2192` | Forward navigation |
| `PLAY` | `\u25B6` | Start, play |
| `STOP` | `\u25A0` | Stop, end |

---

## 11. Accessibility

### Touch Targets

- **Minimum 60px** (`Size.MIN_TOUCH`) for all interactive elements.
- **Pattern lock** uses 48px hit radius around 22px dots for gloved fingers.
- **Back buttons** have `min-height: 30px` / `min-width: 70px` with padding,
  exceeding the minimum on both axes when combined.

### Contrast Ratios

- Primary text (`#E6EDF3`) on background (`#0B0F14`): approximately 14:1 (exceeds WCAG AAA).
- Secondary text (`#8B949E`) on background (`#0B0F14`): approximately 5:1 (meets WCAG AA).
- Orange primary (`#FF6B35`) on dark background: approximately 5.5:1 (meets WCAG AA for large text).
- White text on orange buttons (`#FF6B35`): approximately 3.1:1 (meets WCAG AA for large text, given 16px+ bold).

### Audio Feedback

- `SoundManager` provides audio cues for button presses (`btn_press`), navigation
  (`nav_tick`), errors (`error`), and training events (stimulus, bells, hit confirm).
- Per-sound toggles allow users to disable specific sounds.
- Master volume control via Settings page.

### IMU Navigation

The entire application can be navigated without touching the screen:

| Pad | Action | Context |
|-----|--------|---------|
| Left pad | Previous item / navigate left | Menu selection, preset cycling |
| Right pad | Next item / navigate right | Menu selection, preset cycling |
| Centre pad | Confirm / select / start | Start drill, confirm selection |
| Head pad | Back / toggle presets | Back navigation, open preset overlay on home |

Keyboard fallback (Left/Right/Enter/Escape) mirrors these for development.

Navigation is automatically disabled during active training sessions to prevent
accidental page changes from punch impacts.

---

## 12. Design Tokens Quick Reference

```
Background:     #0B0F14
Surface:        #131920
Primary:        #FF6B35
Text:           #E6EDF3
Text Secondary: #8B949E

Font:           Inter (variable)
Base Size:      15px / weight 500
Header Size:    28px / weight 700
Timer Size:     80px

Spacing:        20px base
Touch Target:   60px minimum
Border Radius:  12px standard / 16px cards

Button Height:  60px standard / 44px compact
Accent Bar:     4px wide
Shadow Blur:    20px standard / 32px large
```
