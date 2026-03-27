#!/usr/bin/env python3
"""Generate Clawd pixel art spinner GIFs for Claude Code.

Clawd grid structure (matched from the local reference animation):
  12 cols × 8 rows, grid=18px

  Col: 0  1  2  3  4  5  6  7  8  9  10 11
  R0:  .  .  #  #  #  #  #  #  #  #  .  .   head
  R1:  .  .  #  @  #  #  #  #  @  #  .  .   head (eyes)
  R2:  #  #  #  #  #  #  #  #  #  #  #  #   body + arms
  R3:  #  #  #  #  #  #  #  #  #  #  #  #   body + arms
  R4:  .  .  #  #  #  #  #  #  #  #  .  .   lower body
  R5:  .  .  #  #  #  #  #  #  #  #  .  .   lower body
  R6:  .  .  #  .  #  .  .  #  .  #  .  .   legs
  R7:  .  .  #  .  #  .  .  #  .  #  .  .   legs

  ox, oy = top-left of the HEAD (col 2 in grid terms).
  Arms extend 2 blocks left/right of head at rows 2-3.
"""

from PIL import Image, ImageDraw
import math
import os
import random
import unicodedata

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
CORAL = (212, 132, 90)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_CORAL = (180, 100, 65)
LIGHT_CORAL = (230, 165, 130)
BROWN = (120, 70, 40)
DARK_BROWN = (80, 50, 25)
YELLOW = (240, 200, 80)
BLUE = (100, 160, 220)
LIGHT_BLUE = (160, 200, 240)
RED = (220, 80, 80)
GREEN = (80, 180, 100)
GRAY = (140, 140, 140)
DARK_GRAY = (80, 80, 80)
PURPLE = (160, 100, 200)
PINK = (240, 160, 180)
ORANGE = (240, 160, 60)
LIME = (160, 220, 80)
TEAL = (80, 180, 180)

CANVAS = 400
GRID = 16  # super-pixel size (16 keeps character ~192x128, fits scenes better)
TRANS = (0, 0, 0, 0)
g = GRID  # shorthand used by compact scene functions

# Character dimensions in grid units
CLAWD_HEAD_W = 8   # head width in blocks
CLAWD_FULL_W = 12  # full width including arms
CLAWD_H = 8        # total height in blocks

# Reference-inspired Clawd palette and internal sprite model.
CLAWD_BASE = (227, 126, 82)
CLAWD_HIGHLIGHT = (239, 149, 104)
CLAWD_SHADOW = (214, 112, 74)
CLAWD_ACCENT_BLUE = (20, 65, 124)
CLAWD_ACCENT_BLUE_LIGHT = (100, 153, 205)
CLAWD_ACCENT_GRAY = (189, 189, 187)
CLAWD_SPRITE_W = 24
CLAWD_SPRITE_H = 16
CLAWD_OCCUPANCY = [
    ".....##############.....",
    "....################....",
    "....################....",
    "....################....",
    "########################",
    "########################",
    "########################",
    "########################",
    "....################....",
    "....################....",
    "....################....",
    "....################....",
    "....###.###..###.###....",
    "....###.###..###.###....",
    "....###.###..###.###....",
    "....###.###..###.###....",
]
CLAWD_LEG_SEGMENTS = [(4, 7), (8, 11), (13, 16), (17, 20)]
CLAWD_POSE_PRESETS = {
    "default": {
        "row_offsets": [0] * CLAWD_SPRITE_H,
        "leg_offsets": [0, 0, 0, 0],
        "scale_x": 1.0,
        "scale_y": 1.0,
    },
    "lean_left": {
        "row_offsets": [-2, -2, -2, -2, -2, -2, -1, -1, -1, -1, 0, 0, 0, 0, 0, 0],
        "leg_offsets": [-1, -1, 0, 0],
        "scale_x": 1.0,
        "scale_y": 1.0,
    },
    "lean_right": {
        "row_offsets": [2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
        "leg_offsets": [0, 0, 1, 1],
        "scale_x": 1.0,
        "scale_y": 1.0,
    },
    "squash": {
        "row_offsets": [0] * CLAWD_SPRITE_H,
        "leg_offsets": [0, 0, 0, 0],
        "scale_x": 1.08,
        "scale_y": 0.92,
    },
    "stretch": {
        "row_offsets": [0] * CLAWD_SPRITE_H,
        "leg_offsets": [0, 0, 0, 0],
        "scale_x": 0.94,
        "scale_y": 1.08,
    },
    "step_left": {
        "row_offsets": [-1, -1, -1, -1, -1, -1, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1],
        "leg_offsets": [-1, 0, 0, 0],
        "scale_x": 1.0,
        "scale_y": 1.0,
    },
    "step_right": {
        "row_offsets": [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
        "leg_offsets": [0, 0, 0, 1],
        "scale_x": 1.0,
        "scale_y": 1.0,
    },
}
CLAWD_LOCKED_COLORS = [
    CLAWD_BASE,
    CLAWD_HIGHLIGHT,
    CLAWD_SHADOW,
    BLACK,
    WHITE,
    CLAWD_ACCENT_GRAY,
    CLAWD_ACCENT_BLUE,
    CLAWD_ACCENT_BLUE_LIGHT,
]

# ---------------------------------------------------------------------------
# Pixel font (5x7 per glyph)
# ---------------------------------------------------------------------------
FONT_GLYPHS = {
    'A': ["01110","10001","10001","11111","10001","10001","10001"],
    'B': ["11110","10001","10001","11110","10001","10001","11110"],
    'C': ["01110","10001","10000","10000","10000","10001","01110"],
    'D': ["11110","10001","10001","10001","10001","10001","11110"],
    'E': ["11111","10000","10000","11110","10000","10000","11111"],
    'F': ["11111","10000","10000","11110","10000","10000","10000"],
    'G': ["01110","10001","10000","10111","10001","10001","01110"],
    'H': ["10001","10001","10001","11111","10001","10001","10001"],
    'I': ["01110","00100","00100","00100","00100","00100","01110"],
    'J': ["00111","00010","00010","00010","00010","10010","01100"],
    'K': ["10001","10010","10100","11000","10100","10010","10001"],
    'L': ["10000","10000","10000","10000","10000","10000","11111"],
    'M': ["10001","11011","10101","10101","10001","10001","10001"],
    'N': ["10001","11001","10101","10011","10001","10001","10001"],
    'O': ["01110","10001","10001","10001","10001","10001","01110"],
    'P': ["11110","10001","10001","11110","10000","10000","10000"],
    'Q': ["01110","10001","10001","10001","10101","10010","01101"],
    'R': ["11110","10001","10001","11110","10100","10010","10001"],
    'S': ["01110","10001","10000","01110","00001","10001","01110"],
    'T': ["11111","00100","00100","00100","00100","00100","00100"],
    'U': ["10001","10001","10001","10001","10001","10001","01110"],
    'V': ["10001","10001","10001","10001","01010","01010","00100"],
    'W': ["10001","10001","10001","10101","10101","11011","10001"],
    'X': ["10001","10001","01010","00100","01010","10001","10001"],
    'Y': ["10001","10001","01010","00100","00100","00100","00100"],
    'Z': ["11111","00001","00010","00100","01000","10000","11111"],
    'a': ["00000","00000","01110","00001","01111","10001","01111"],
    'b': ["10000","10000","10110","11001","10001","10001","11110"],
    'c': ["00000","00000","01110","10000","10000","10001","01110"],
    'd': ["00001","00001","01101","10011","10001","10001","01111"],
    'e': ["00000","00000","01110","10001","11111","10000","01110"],
    'f': ["00110","01001","01000","11100","01000","01000","01000"],
    'g': ["00000","01111","10001","10001","01111","00001","01110"],
    'h': ["10000","10000","10110","11001","10001","10001","10001"],
    'i': ["00100","00000","01100","00100","00100","00100","01110"],
    'j': ["00010","00000","00110","00010","00010","10010","01100"],
    'k': ["10000","10000","10010","10100","11000","10100","10010"],
    'l': ["01100","00100","00100","00100","00100","00100","01110"],
    'm': ["00000","00000","11010","10101","10101","10001","10001"],
    'n': ["00000","00000","10110","11001","10001","10001","10001"],
    'o': ["00000","00000","01110","10001","10001","10001","01110"],
    'p': ["00000","00000","11110","10001","11110","10000","10000"],
    'q': ["00000","00000","01101","10011","01111","00001","00001"],
    'r': ["00000","00000","10110","11001","10000","10000","10000"],
    's': ["00000","00000","01110","10000","01110","00001","11110"],
    't': ["01000","01000","11100","01000","01000","01001","00110"],
    'u': ["00000","00000","10001","10001","10001","10011","01101"],
    'v': ["00000","00000","10001","10001","10001","01010","00100"],
    'w': ["00000","00000","10001","10001","10101","10101","01010"],
    'x': ["00000","00000","10001","01010","00100","01010","10001"],
    'y': ["00000","00000","10001","10001","01111","00001","01110"],
    'z': ["00000","00000","11111","00010","00100","01000","11111"],
    '0': ["01110","10001","10011","10101","11001","10001","01110"],
    '1': ["00100","01100","00100","00100","00100","00100","01110"],
    '2': ["01110","10001","00001","00110","01000","10000","11111"],
    '3': ["01110","10001","00001","00110","00001","10001","01110"],
    '4': ["00010","00110","01010","10010","11111","00010","00010"],
    '5': ["11111","10000","11110","00001","00001","10001","01110"],
    '6': ["00110","01000","10000","11110","10001","10001","01110"],
    '7': ["11111","00001","00010","00100","01000","01000","01000"],
    '8': ["01110","10001","10001","01110","10001","10001","01110"],
    '9': ["01110","10001","10001","01111","00001","00010","01100"],
    '*': ["00000","00100","10101","01110","10101","00100","00000"],
    '.': ["00000","00000","00000","00000","00000","01100","01100"],
    ' ': ["00000","00000","00000","00000","00000","00000","00000"],
    '-': ["00000","00000","00000","11111","00000","00000","00000"],
    '!': ["00100","00100","00100","00100","00100","00000","00100"],
    '?': ["01110","10001","00001","00110","00100","00000","00100"],
    ',': ["00000","00000","00000","00000","00000","00100","01000"],
    ':': ["00000","00000","00100","00000","00000","00100","00000"],
    '$': ["00100","01111","10100","01110","00101","11110","00100"],
    '%': ["11001","11010","00100","01000","10110","00110","00000"],
    '&': ["01100","10010","10100","01010","10101","10010","01101"],
    '#': ["01010","11111","01010","01010","11111","01010","00000"],
    '@': ["01110","10001","10111","10101","10111","10000","01110"],
    '§': ["01111","10000","01110","00001","11110","00001","11110"],
}

FONT_PX = 4


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def resolve_font_glyph(ch):
    """Return the best available glyph, degrading accented Latin chars to base forms."""
    if ch in FONT_GLYPHS:
        return FONT_GLYPHS[ch]

    decomposed = unicodedata.normalize('NFKD', ch)
    for candidate in decomposed:
        if unicodedata.combining(candidate):
            continue
        if candidate in FONT_GLYPHS:
            return FONT_GLYPHS[candidate]

    return FONT_GLYPHS[' ']


def draw_text(draw, text, start_x, start_y, color=CORAL, scale=FONT_PX):
    """Render text using the pixel font."""
    cx = start_x
    for ch in text:
        glyph = resolve_font_glyph(ch)
        for row_i, row in enumerate(glyph):
            for col_i, pixel in enumerate(row):
                if pixel == '1':
                    px = cx + col_i * scale
                    py = start_y + row_i * scale
                    draw.rectangle([px, py, px + scale - 1, py + scale - 1], fill=color)
        cx += (len(glyph[0]) + 1) * scale


def text_width(text, scale=FONT_PX):
    """Return the rendered width of text in the pixel font."""
    width = 0
    for ch in text:
        glyph = resolve_font_glyph(ch)
        width += (len(glyph[0]) + 1) * scale
    return width


def draw_heart(draw, cx, cy, size, color=RED):
    """Draw a tiny pixel heart centred at (cx, cy)."""
    s = size
    offsets = [
        (-2, -1), (-1, -1), (1, -1), (2, -1),
        (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0),
        (-1, 1), (0, 1), (1, 1),
        (0, 2),
    ]
    for ox, oy in offsets:
        draw.rectangle([cx + ox*s, cy + oy*s, cx + ox*s + s - 1, cy + oy*s + s - 1], fill=color)


def draw_steam(draw, x, y, frame, color=(200, 200, 200)):
    """Draw wispy steam puffs that animate with frame."""
    puffs = [(0, 0, 5), (8, -8, 4), (-5, -14, 3), (6, -20, 4)]
    for i, (px, py, r) in enumerate(puffs):
        offset = ((frame + i) % 4) * 4
        draw.ellipse([x+px-r, y+py-r-offset, x+px+r, y+py+r-offset], fill=color)


def draw_bubbles(draw, x, y, w, frame, color=LIGHT_BLUE):
    """Draw rising bubbles in a region."""
    positions = [(0.2, 0), (0.5, 0.3), (0.8, 0.6), (0.3, 0.5), (0.7, 0.2), (0.1, 0.8)]
    for i, (fx, fy) in enumerate(positions):
        bx = x + int(fx * w)
        rise = ((frame + i * 2) % 6) * 8
        by = y - rise
        r = 3 + (i % 3)
        draw.ellipse([bx-r, by-r, bx+r, by+r], fill=color)


CURRENT_FRAME = 0
AUTO_BLINK_FRAME = 3


def set_current_frame(frame):
    """Track the frame currently being rendered for shared animations."""
    global CURRENT_FRAME
    CURRENT_FRAME = frame


def should_auto_blink(frame_offset=0):
    """Use the Blanching-style blink timing across scenes by default."""
    return (CURRENT_FRAME + frame_offset) % NUM_FRAMES == AUTO_BLINK_FRAME


# ---------------------------------------------------------------------------
# Clawd character drawing
# ---------------------------------------------------------------------------
def tint_color(color, amount):
    return tuple(min(255, round(c + (255 - c) * amount)) for c in color)


def shade_color(color, amount):
    return tuple(max(0, round(c * (1 - amount))) for c in color)


def resolve_clawd_palette(body_color=CORAL, eye_color=BLACK):
    if body_color == CORAL:
        base = CLAWD_BASE
        highlight = CLAWD_HIGHLIGHT
        shadow = CLAWD_SHADOW
    else:
        base = body_color
        highlight = tint_color(base, 0.18)
        shadow = shade_color(base, 0.18)
    return {
        "base": base,
        "highlight": highlight,
        "shadow": shadow,
        "eye": eye_color,
        "gray": CLAWD_ACCENT_GRAY,
        "blue": CLAWD_ACCENT_BLUE,
        "blue_light": CLAWD_ACCENT_BLUE_LIGHT,
    }


def get_clawd_pose(pose):
    return CLAWD_POSE_PRESETS.get(pose, CLAWD_POSE_PRESETS["default"])


def _clawd_transform_x(sprite_x, row, pose_cfg):
    center = CLAWD_SPRITE_W / 2
    row_shift = pose_cfg["row_offsets"][max(0, min(CLAWD_SPRITE_H - 1, row))]
    return (sprite_x - center) * pose_cfg["scale_x"] + center + row_shift


def _clawd_transform_y(sprite_y, pose_cfg):
    center = CLAWD_SPRITE_H / 2
    return (sprite_y - center) * pose_cfg["scale_y"] + center


def _clawd_box(ox, oy, grid, sx0, sy0, sx1, sy1, pose_cfg):
    row = max(0, min(CLAWD_SPRITE_H - 1, int((sy0 + sy1 - 1) / 2)))
    left = ox - 2 * grid
    x0 = left + round(_clawd_transform_x(sx0, row, pose_cfg) * grid / 2)
    x1 = left + round(_clawd_transform_x(sx1, row, pose_cfg) * grid / 2) - 1
    y0 = oy + round(_clawd_transform_y(sy0, pose_cfg) * grid / 2)
    y1 = oy + round(_clawd_transform_y(sy1, pose_cfg) * grid / 2) - 1
    return x0, y0, x1, y1


def _draw_clawd_box(draw, ox, oy, grid, sx0, sy0, sx1, sy1, color, pose_cfg):
    x0, y0, x1, y1 = _clawd_box(ox, oy, grid, sx0, sy0, sx1, sy1, pose_cfg)
    if x1 >= x0 and y1 >= y0:
        draw.rectangle([x0, y0, x1, y1], fill=color)


def _clawd_point(ox, oy, grid, sx, sy, pose_cfg):
    row = max(0, min(CLAWD_SPRITE_H - 1, int(round(sy))))
    left = ox - 2 * grid
    px = left + round(_clawd_transform_x(sx, row, pose_cfg) * grid / 2)
    py = oy + round(_clawd_transform_y(sy, pose_cfg) * grid / 2)
    return px, py


def get_clawd_anchors(ox, oy, grid=GRID, pose="default", head_only=False):
    pose_cfg = get_clawd_pose(pose)
    return {
        "head_top_center": _clawd_point(ox, oy, grid, 12, 0.5, pose_cfg),
        "head_top_left": _clawd_point(ox, oy, grid, 6, 1, pose_cfg),
        "head_top_right": _clawd_point(ox, oy, grid, 18, 1, pose_cfg),
        "head_left": _clawd_point(ox, oy, grid, 4.5, 3.5, pose_cfg),
        "head_right": _clawd_point(ox, oy, grid, 19.5, 3.5, pose_cfg),
        "left_eye": _clawd_point(ox, oy, grid, 7.0, 4.5, pose_cfg),
        "right_eye": _clawd_point(ox, oy, grid, 17.0, 4.5, pose_cfg),
        "mouth": _clawd_point(ox, oy, grid, 12.0, 7.0, pose_cfg),
        "left_hand": _clawd_point(ox, oy, grid, 2.0, 6.5, pose_cfg),
        "right_hand": _clawd_point(ox, oy, grid, 22.0, 6.5, pose_cfg),
        "above_head": _clawd_point(ox, oy, grid, 12.0, -2.0, pose_cfg),
    }


def _normalize_accessories(accessories):
    if not accessories:
        return []
    normalized = []
    for accessory in accessories:
        if isinstance(accessory, str):
            normalized.append((accessory, {}))
        else:
            name, opts = accessory
            normalized.append((name, dict(opts)))
    return normalized


def draw_clawd_headphones(draw, anchors, grid, palette):
    left_x, left_y = anchors["head_left"]
    right_x, right_y = anchors["head_right"]
    top_x, top_y = anchors["head_top_center"]
    band_top = top_y + max(2, grid // 10)
    draw.arc([left_x - grid // 2, band_top - grid // 2, right_x + grid // 2, band_top + grid],
             180, 360, fill=palette["blue"], width=max(2, grid // 5))
    pad_w = max(8, grid - 2)
    pad_h = max(10, int(grid * 1.1))
    draw.rectangle([left_x - pad_w, left_y - pad_h // 2, left_x - 2, left_y + pad_h // 2], fill=palette["blue"])
    draw.rectangle([right_x + 2, right_y - pad_h // 2, right_x + pad_w, right_y + pad_h // 2], fill=palette["blue"])
    draw.rectangle([left_x - pad_w + 2, left_y - pad_h // 2 + 2, left_x - 4, left_y + pad_h // 2 - 2], fill=palette["blue_light"])
    draw.rectangle([right_x + 4, right_y - pad_h // 2 + 2, right_x + pad_w - 2, right_y + pad_h // 2 - 2], fill=palette["blue_light"])


def draw_clawd_chef_hat(draw, anchors, grid, palette, tall=False):
    top_x, top_y = anchors["head_top_center"]
    brim_w = int(grid * (5.6 if tall else 4.9))
    brim_h = max(6, grid // 2)
    neck_w = int(grid * (3.0 if tall else 2.6))
    neck_h = int(grid * (1.7 if tall else 1.15))
    lobe_r = int(grid * (1.15 if tall else 0.95))
    crown_r = int(grid * (1.65 if tall else 1.3))
    brim_y = top_y - int(grid * 0.42)
    neck_top = brim_y - neck_h
    crown_y = neck_top - crown_r + max(2, grid // 8)
    fold = (216, 216, 216)

    draw.rectangle([top_x - brim_w // 2, brim_y, top_x + brim_w // 2, brim_y + brim_h], fill=WHITE, outline=palette["gray"])
    draw.line([top_x - brim_w // 2 + 6, brim_y + 2, top_x + brim_w // 2 - 6, brim_y + 2], fill=fold, width=1)

    draw.rectangle([top_x - neck_w // 2, neck_top, top_x + neck_w // 2, brim_y], fill=WHITE, outline=palette["gray"])
    draw.line([top_x - neck_w // 2 + 4, neck_top + 4, top_x + neck_w // 2 - 4, neck_top + 4], fill=fold, width=1)

    left_box = [top_x - crown_r - lobe_r + 4, crown_y + 6, top_x - 4, crown_y + crown_r + 12]
    center_box = [top_x - lobe_r - 4, crown_y - 4, top_x + lobe_r + 4, crown_y + crown_r + 10]
    right_box = [top_x + 4, crown_y + 6, top_x + crown_r + lobe_r - 4, crown_y + crown_r + 12]
    for box in (left_box, center_box, right_box):
        draw.ellipse(box, fill=WHITE, outline=palette["gray"])

    draw.line([top_x - neck_w // 2 + 3, neck_top, top_x - neck_w // 2 + 3, brim_y - 2], fill=fold, width=1)
    draw.line([top_x + neck_w // 2 - 3, neck_top, top_x + neck_w // 2 - 3, brim_y - 2], fill=fold, width=1)
    draw.arc([top_x - int(grid * 1.1), crown_y + 8, top_x + int(grid * 1.1), crown_y + crown_r + 10], 200, 340, fill=fold, width=1)
    draw.arc([top_x - int(grid * 0.65), crown_y + 2, top_x + int(grid * 0.65), crown_y + crown_r + 8], 200, 340, fill=fold, width=1)


def draw_clawd_wizard_hat(draw, anchors, grid, palette):
    top_x, top_y = anchors["head_top_center"]
    brim_y = top_y + max(2, grid // 8)
    draw.rectangle([top_x - int(grid * 2.7), brim_y, top_x + int(grid * 2.7), brim_y + max(4, grid // 3)], fill=DARK_GRAY)
    draw.polygon([
        (top_x - int(grid * 2.0), brim_y),
        (top_x - int(grid * 1.1), brim_y - int(grid * 0.9)),
        (top_x + int(grid * 0.1), brim_y - int(grid * 2.2)),
        (top_x + int(grid * 1.9), brim_y - int(grid * 0.7)),
        (top_x + int(grid * 1.2), brim_y),
    ], fill=DARK_GRAY)
    buckle_y = brim_y - int(grid * 0.55)
    draw.rectangle([top_x - grid // 2, buckle_y, top_x + grid // 2, buckle_y + max(3, grid // 4)], fill=YELLOW)


def draw_clawd_helmet(draw, anchors, grid, palette):
    top_x, top_y = anchors["head_top_center"]
    helmet_w = int(grid * 4.8)
    brim_y = top_y + max(2, grid // 8)
    dome_h = int(grid * 1.8)
    draw.pieslice([top_x - helmet_w // 2, brim_y - dome_h, top_x + helmet_w // 2, brim_y + dome_h], 180, 360, fill=YELLOW)
    draw.rectangle([top_x - helmet_w // 2, brim_y, top_x + helmet_w // 2, brim_y + max(4, grid // 3)], fill=YELLOW)
    draw.line([top_x, brim_y - dome_h + 4, top_x, brim_y + max(4, grid // 3)], fill=ORANGE, width=max(2, grid // 6))
    draw.ellipse([top_x - grid // 2, brim_y - grid // 2, top_x + grid // 2, brim_y + grid // 2], outline=ORANGE, width=max(1, grid // 7))


def draw_clawd_camera(draw, anchors, grid, palette):
    hand_x, hand_y = anchors["right_hand"]
    cam_x = hand_x + grid // 3
    cam_y = hand_y - grid // 2
    draw.rectangle([cam_x, cam_y, cam_x + int(grid * 1.2), cam_y + int(grid * 0.9)], fill=DARK_BROWN)
    draw.ellipse([cam_x + 4, cam_y + 4, cam_x + int(grid * 0.8), cam_y + int(grid * 0.8)], fill=palette["gray"])
    draw.rectangle([cam_x + int(grid * 0.9), cam_y + 4, cam_x + int(grid * 1.15), cam_y + int(grid * 0.28)], fill=PURPLE)


def draw_clawd_magnifier(draw, anchors, grid, palette):
    hand_x, hand_y = anchors["right_hand"]
    cx = hand_x + int(grid * 0.6)
    cy = hand_y - int(grid * 0.4)
    r = max(6, grid // 2)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=palette["blue"], width=max(2, grid // 8))
    draw.line([cx + r - 2, cy + r - 2, cx + r + grid // 2, cy + r + grid // 2], fill=DARK_BROWN, width=max(2, grid // 8))


def draw_clawd_tool(draw, anchors, grid, palette, tool="wrench"):
    hand_x, hand_y = anchors["right_hand"]
    if tool == "wand":
        tip_x = hand_x + int(grid * 1.3)
        tip_y = hand_y - int(grid * 1.2)
        draw.line([hand_x, hand_y, tip_x, tip_y], fill=WHITE, width=max(2, grid // 8))
        draw_text(draw, "*", tip_x - 4, tip_y - 10, color=YELLOW, scale=max(2, grid // 5))
    elif tool == "wrench":
        tip_x = hand_x + int(grid * 1.2)
        tip_y = hand_y - int(grid * 0.8)
        draw.line([hand_x, hand_y, tip_x, tip_y], fill=palette["gray"], width=max(2, grid // 8))
        jaw = max(4, grid // 4)
        draw.line([tip_x - jaw, tip_y - jaw, tip_x + jaw, tip_y + jaw], fill=palette["gray"], width=max(2, grid // 10))
        draw.line([tip_x - jaw, tip_y + jaw, tip_x + jaw, tip_y - jaw], fill=palette["gray"], width=max(2, grid // 10))


def draw_clawd_icon_accessory(draw, anchors, grid, palette, name):
    above_x, above_y = anchors["above_head"]
    if name == "idea_bulb":
        draw_lightbulb(draw, above_x, above_y - grid // 2, size=max(12, int(grid * 0.95)), glow=4)
    elif name == "speech_bubble":
        bx = above_x - int(grid * 1.2)
        by = above_y - int(grid * 0.8)
        draw.rectangle([bx, by, bx + int(grid * 2.4), by + int(grid * 1.4)], fill=palette["blue_light"])
        draw.polygon([(bx + 6, by + int(grid * 1.4)), (bx + 14, by + int(grid * 1.4)), (bx + 10, by + int(grid * 1.8))], fill=palette["blue_light"])
        for i in range(3):
            draw.rectangle([bx + 6 + i * 9, by + 7, bx + 10 + i * 9, by + 11], fill=BLACK)
    elif name == "heart":
        draw_heart(draw, above_x, above_y, max(3, grid // 4), RED)
    elif name == "steam_puff":
        draw_steam(draw, above_x - grid // 3, above_y + grid // 2, CURRENT_FRAME, color=palette["gray"])


def draw_clawd_accessories(draw, ox, oy, grid=GRID, accessories=None, pose="default", body_color=CORAL, head_only=False):
    palette = resolve_clawd_palette(body_color)
    anchors = get_clawd_anchors(ox, oy, grid, pose=pose, head_only=head_only)
    for name, opts in _normalize_accessories(accessories):
        if name == "headphones":
            draw_clawd_headphones(draw, anchors, grid, palette)
        elif name == "chef_hat":
            draw_clawd_chef_hat(draw, anchors, grid, palette, tall=opts.get("tall", False))
        elif name == "wizard_hat":
            draw_clawd_wizard_hat(draw, anchors, grid, palette)
        elif name == "helmet":
            draw_clawd_helmet(draw, anchors, grid, palette)
        elif name == "camera":
            draw_clawd_camera(draw, anchors, grid, palette)
        elif name == "magnifier":
            draw_clawd_magnifier(draw, anchors, grid, palette)
        elif name in {"tool", "wand"}:
            draw_clawd_tool(draw, anchors, grid, palette, tool="wand" if name == "wand" else opts.get("tool", "wrench"))
        elif name in {"idea_bulb", "speech_bubble", "heart", "steam_puff"}:
            draw_clawd_icon_accessory(draw, anchors, grid, palette, name)


def _clawd_leg_shift(x, y, pose_cfg):
    if y < 12:
        return 0
    for idx, (start, end) in enumerate(CLAWD_LEG_SEGMENTS):
        if start <= x < end:
            return pose_cfg["leg_offsets"][idx]
    return 0


def _clawd_body_tone(x, y, palette):
    if y <= 2 and 6 <= x <= 17:
        return palette["highlight"]
    if x <= 5 and 2 <= y <= 10:
        return palette["highlight"]
    if x >= 18 or (y >= 10 and x >= 6):
        return palette["shadow"]
    return palette["base"]


def _draw_clawd_body(draw, ox, oy, grid=GRID, body_color=CORAL, pose="default", head_only=False):
    palette = resolve_clawd_palette(body_color)
    pose_cfg = get_clawd_pose(pose)
    max_rows = 8 if head_only else CLAWD_SPRITE_H
    for y, row in enumerate(CLAWD_OCCUPANCY[:max_rows]):
        for x, cell in enumerate(row):
            if cell != "#":
                continue
            x_shift = _clawd_leg_shift(x, y, pose_cfg)
            color = _clawd_body_tone(x, y, palette)
            _draw_clawd_box(draw, ox, oy, grid, x + x_shift, y, x + 1 + x_shift, y + 1, color, pose_cfg)


def draw_clawd_face(draw, ox, oy, grid=GRID, blink=False, eye_color=BLACK, wink=None, mouth=None,
                    pose="default", expression=None, head_only=False):
    """Draw Clawd's simple face."""
    if expression == "blink" or expression == "sleepy":
        blink = True
    elif expression == "wink_left":
        wink = "left"
    elif expression == "wink_right":
        wink = "right"

    eye_y = oy + grid
    blink_y = eye_y + grid // 2

    if wink == "left":
        draw.rectangle([ox + grid, blink_y, ox + 2 * grid - 1, blink_y + 2], fill=eye_color)
        draw.rectangle([ox + 6 * grid, eye_y, ox + 7 * grid - 1, oy + 2 * grid - 1], fill=eye_color)
    elif wink == "right":
        draw.rectangle([ox + grid, eye_y, ox + 2 * grid - 1, oy + 2 * grid - 1], fill=eye_color)
        draw.rectangle([ox + 6 * grid, blink_y, ox + 7 * grid - 1, blink_y + 2], fill=eye_color)
    elif blink or wink == "both":
        draw.rectangle([ox + grid, blink_y, ox + 2 * grid - 1, blink_y + 2], fill=eye_color)
        draw.rectangle([ox + 6 * grid, blink_y, ox + 7 * grid - 1, blink_y + 2], fill=eye_color)
    else:
        draw.rectangle([ox + grid, eye_y, ox + 2 * grid - 1, oy + 2 * grid - 1], fill=eye_color)
        draw.rectangle([ox + 6 * grid, eye_y, ox + 7 * grid - 1, oy + 2 * grid - 1], fill=eye_color)

    if mouth == "cheeky":
        mx = ox + 4 * grid
        my = oy + int(1.55 * grid)
        draw.line([mx, my, mx + grid // 2, my + 3, mx + grid, my], fill=eye_color, width=1)
    elif mouth == "smile":
        mx = ox + 4 * grid
        my = oy + int(1.55 * grid)
        draw.arc([mx - grid // 2, my - 2, mx + grid, my + grid // 2], 10, 170, fill=eye_color, width=1)


def draw_clawd(draw, ox, oy, grid=GRID, blink=None, body_color=CORAL, eye_color=BLACK, wink=None, mouth=None,
               pose="default", expression=None, accessories=None):
    """Draw the original simple blocky Clawd. ox,oy = top-left of the 8-block-wide head."""
    if blink is None:
        blink = should_auto_blink()

    # Head (8x2 blocks)
    for gx in range(8):
        for gy in range(2):
            draw.rectangle([ox + gx * grid, oy + gy * grid,
                            ox + (gx + 1) * grid - 1, oy + (gy + 1) * grid - 1], fill=body_color)

    # Body + arms (12x2 blocks)
    for gx in range(-2, 10):
        for gy in range(2, 4):
            draw.rectangle([ox + gx * grid, oy + gy * grid,
                            ox + (gx + 1) * grid - 1, oy + (gy + 1) * grid - 1], fill=body_color)

    # Lower body (8x2 blocks)
    for gx in range(8):
        for gy in range(4, 6):
            draw.rectangle([ox + gx * grid, oy + gy * grid,
                            ox + (gx + 1) * grid - 1, oy + (gy + 1) * grid - 1], fill=body_color)

    # Legs
    for lc in [0, 2, 5, 7]:
        for gy in range(6, 8):
            draw.rectangle([ox + lc * grid, oy + gy * grid,
                            ox + (lc + 1) * grid - 1, oy + (gy + 1) * grid - 1], fill=body_color)

    draw_clawd_face(draw, ox, oy, grid, blink=blink, eye_color=eye_color, wink=wink, mouth=mouth,
                    pose=pose, expression=expression, head_only=False)
    if accessories:
        draw_clawd_accessories(draw, ox, oy, grid=grid, accessories=accessories, pose=pose, body_color=body_color, head_only=False)


def draw_clawd_head_only(draw, ox, oy, grid=GRID, blink=None, body_color=CORAL, eye_color=BLACK, wink=None, mouth=None,
                         pose="default", expression=None, accessories=None):
    """Draw just the original simple head + upper body portion."""
    if blink is None:
        blink = should_auto_blink()

    for gx in range(8):
        for gy in range(2):
            draw.rectangle([ox + gx * grid, oy + gy * grid,
                            ox + (gx + 1) * grid - 1, oy + (gy + 1) * grid - 1], fill=body_color)

    for gx in range(-2, 10):
        for gy in range(2, 4):
            draw.rectangle([ox + gx * grid, oy + gy * grid,
                            ox + (gx + 1) * grid - 1, oy + (gy + 1) * grid - 1], fill=body_color)

    draw_clawd_face(draw, ox, oy, grid, blink=blink, eye_color=eye_color, wink=wink, mouth=mouth,
                    pose=pose, expression=expression, head_only=True)
    if accessories:
        draw_clawd_accessories(draw, ox, oy, grid=grid, accessories=accessories, pose=pose, body_color=body_color, head_only=True)


def draw_mini_clawd(draw, ox, oy, grid=10, **kwargs):
    """Draw a small Clawd (for booping scene)."""
    draw_clawd(draw, ox, oy, grid, **kwargs)


def clawd_pixel_size(grid=GRID):
    """Return (width, height) of full Clawd in pixels.
    Width includes the 2-block arms on each side."""
    return (12 * grid, 8 * grid)


# ---------------------------------------------------------------------------
# Frame generators
# ---------------------------------------------------------------------------
NUM_FRAMES = 6
TEXT_Y = 355
TEXT_X = 30


def draw_loading_label(draw, word, frame, start_x=TEXT_X, start_y=TEXT_Y, color=CORAL, scale=FONT_PX):
    """Draw the animated spinner label with a pulsing star and loading dots."""
    label_scale = scale
    while label_scale > 2:
        candidate_star_slot_w = text_width("*", label_scale) + 2 * label_scale
        candidate_total_w = candidate_star_slot_w + text_width(word, label_scale) + text_width("...", label_scale)
        if candidate_total_w <= CANVAS - 16:
            break
        label_scale -= 1

    star_scales = [
        max(1, label_scale - 1),
        label_scale,
        label_scale + 1,
        label_scale,
        max(1, label_scale - 1),
        label_scale,
    ]
    dot_counts = [1, 1, 2, 2, 3, 3]

    star_scale = star_scales[frame % len(star_scales)]
    dot_count = dot_counts[frame % len(dot_counts)]

    star_slot_w = text_width("*", label_scale) + 2 * label_scale
    total_w = star_slot_w + text_width(word, label_scale) + text_width("...", label_scale)
    label_x = max(8, min(start_x, CANVAS - total_w - 8))

    base_h = len(FONT_GLYPHS['*']) * label_scale
    star_w = len(FONT_GLYPHS['*'][0]) * star_scale
    star_h = len(FONT_GLYPHS['*']) * star_scale

    star_x = label_x + (star_slot_w - star_w) // 2
    star_y = start_y + (base_h - star_h) // 2
    draw_text(draw, "*", star_x, star_y, color=color, scale=star_scale)

    word_x = label_x + star_slot_w
    draw_text(draw, word, word_x, start_y, color=color, scale=label_scale)

    dots_x = word_x + text_width(word, label_scale)
    draw_text(draw, "." * dot_count, dots_x, start_y, color=color, scale=label_scale)


def frames_baking():
    """Clawd with chef hat + oven, bread rising, steam."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # Clawd (left side) — position head top-left
        cx, cy = 40, 140
        draw_clawd(draw, cx, cy, g)

        # Chef hat on Clawd head
        hat_x = cx + g  # slightly inset from head left
        hat_y = cy - int(g * 1.8)
        draw.rectangle([hat_x, hat_y + g, hat_x + 6*g, hat_y + g + g//3], fill=WHITE)  # brim
        draw.rectangle([hat_x + g//2, hat_y, hat_x + 6*g - g//2, hat_y + g], fill=WHITE)  # puff

        # Oven (right side)
        oven_x, oven_y = 240, 130
        ow, oh = 130, 130
        draw.rectangle([oven_x, oven_y, oven_x+ow, oven_y+oh], fill=BROWN)
        draw.rectangle([oven_x+4, oven_y+4, oven_x+ow-4, oven_y+16], fill=DARK_BROWN)
        # Oven window
        draw.rectangle([oven_x+15, oven_y+28, oven_x+ow-15, oven_y+90], fill=DARK_BROWN)
        draw.rectangle([oven_x+20, oven_y+33, oven_x+ow-20, oven_y+85], fill=(50, 30, 15))
        # Bread rising
        bread_rise = f * 2
        by = 75 - bread_rise
        draw.rectangle([oven_x+35, oven_y+by, oven_x+ow-35, oven_y+85], fill=YELLOW)
        draw.rectangle([oven_x+28, oven_y+by-5, oven_x+ow-28, oven_y+by+8], fill=(230, 190, 60))
        # Handle
        draw.rectangle([oven_x+40, oven_y+oh-20, oven_x+ow-40, oven_y+oh-14], fill=GRAY)
        # Legs
        draw.rectangle([oven_x+10, oven_y+oh, oven_x+25, oven_y+oh+15], fill=DARK_BROWN)
        draw.rectangle([oven_x+ow-25, oven_y+oh, oven_x+ow-10, oven_y+oh+15], fill=DARK_BROWN)

        # Steam
        sx = oven_x + ow // 2
        draw_steam(draw, sx - 15 + (f % 2) * 20, oven_y - 8, f)

        draw_loading_label(draw, "Baking", f)
        frames.append(img)
    return frames


def frames_beaming():
    """Clawd in a Star Trek transporter beam — flickering."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 136, 120

        # Beam lines (vertical, shimmering)
        beam_colors = [(255, 235, 160), (255, 220, 120), (255, 245, 180)]
        beam_left = cx - 2*g - 10
        beam_right = cx + 10*g + 10
        for bx in range(beam_left, beam_right, 14):
            idx = (bx - beam_left) // 14
            jitter = ((f + idx) % 3) * 4 - 4
            if (idx + f) % 2 == 0:
                bc = beam_colors[(idx + f) % 3]
                draw.rectangle([bx + jitter, 15, bx + 5 + jitter, cy + 8*g + 10],
                               fill=bc)

        # Clawd flickers
        if f % 3 != 2:
            draw_clawd(draw, cx, cy, g, blink=(f % 4 == 2))

        # Sparkles
        for i, (sx, sy) in enumerate([(cx-25, 60+f*18), (cx+10*g+5, 50+f*12),
                                       (cx+3*g, 30+f*22), (cx+7*g, 70+f*10)]):
            if (f + i) % 3 == 0:
                draw.rectangle([sx, sy, sx+5, sy+5], fill=YELLOW)

        draw_loading_label(draw, "Beaming", f)
        frames.append(img)
    return frames


def frames_booping():
    """Clawd booping a small creature's nose, hearts pop up."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # Clawd (left)
        cx, cy = 30, 130
        draw_clawd(draw, cx, cy, g)

        # Small creature (right)
        sg = 9  # small grid
        sc_x, sc_y = 280, 195
        draw_mini_clawd(draw, sc_x, sc_y, sg)

        # Boop arm extending from Clawd's right arm (row 2-3 area)
        arm_ext = min(f, 4)
        arm_y = cy + 2*g + g//2
        arm_x0 = cx + 10*g  # right edge of arms
        arm_x1 = arm_x0 + arm_ext * 16
        if arm_ext > 0:
            draw.rectangle([arm_x0, arm_y, arm_x1, arm_y + g//2 - 1], fill=CORAL)
            # Paw
            draw.rectangle([arm_x1 - 3, arm_y - 3, arm_x1 + 5, arm_y + g//2 + 2], fill=CORAL)

        # Hearts after boop
        if f >= 3:
            rise = (f - 3) * 14
            draw_heart(draw, sc_x + 20, sc_y - 15 - rise, 4, RED)
        if f >= 4:
            rise = (f - 4) * 12
            draw_heart(draw, sc_x + 50, sc_y - 5 - rise, 3, (255, 120, 120))

        # Small creature happy squint after boop
        if f >= 3:
            # Overdraw eyes with squints
            ey = sc_y + sg + sg // 2
            draw.rectangle([sc_x + 1*sg, sc_y + 1*sg, sc_x + 2*sg - 1, sc_y + 2*sg - 1], fill=LIGHT_CORAL)
            draw.rectangle([sc_x + 6*sg, sc_y + 1*sg, sc_x + 7*sg - 1, sc_y + 2*sg - 1], fill=LIGHT_CORAL)
            draw.rectangle([sc_x + 1*sg, ey, sc_x + 2*sg - 1, ey + 2], fill=BLACK)
            draw.rectangle([sc_x + 6*sg, ey, sc_x + 7*sg - 1, ey + 2], fill=BLACK)

        draw_loading_label(draw, "Booping", f)
        frames.append(img)
    return frames


def frames_blanching():
    """Clawd sitting in a pot with bubbles and steam."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # Pot
        pot_cx = CANVAS // 2
        pot_w, pot_h = 220, 110
        pot_x = pot_cx - pot_w // 2
        pot_y = 185

        # Clawd head + arms poking out of pot (rows 0-3 only)
        clawd_x = pot_cx - 4 * g
        clawd_y = pot_y - 3 * g - 5
        draw_clawd_head_only(draw, clawd_x, clawd_y, g, blink=(f == 3))

        # Pot body (drawn OVER Clawd's lower part)
        draw.rectangle([pot_x, pot_y, pot_x + pot_w, pot_y + pot_h], fill=GRAY)
        # Pot rim
        draw.rectangle([pot_x - 8, pot_y - 6, pot_x + pot_w + 8, pot_y + 10], fill=DARK_GRAY)
        # Handles
        draw.rectangle([pot_x - 22, pot_y + 20, pot_x - 4, pot_y + 40], fill=DARK_GRAY)
        draw.rectangle([pot_x + pot_w + 4, pot_y + 20, pot_x + pot_w + 22, pot_y + 40], fill=DARK_GRAY)

        # Water
        draw.rectangle([pot_x + 4, pot_y + 14, pot_x + pot_w - 4, pot_y + pot_h - 4], fill=BLUE)

        # Bubbles
        draw_bubbles(draw, pot_x + 20, pot_y + 25, pot_w - 40, f, LIGHT_BLUE)

        # Steam
        draw_steam(draw, pot_cx - 25 + (f % 2) * 15, clawd_y - 12, f)
        if f % 2 == 0:
            draw_steam(draw, pot_cx + 20, clawd_y - 8, f + 2)

        draw_loading_label(draw, "Blanching", f)
        frames.append(img)
    return frames


def frames_brewing():
    """Clawd next to a pour-over coffee setup."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # Clawd (left)
        cx, cy = 30, 140
        draw_clawd(draw, cx, cy, g)

        # Pour-over (right)
        po_x, po_y = 265, 80

        # Stand
        draw.rectangle([po_x + 42, po_y, po_x + 52, po_y + 195], fill=DARK_BROWN)
        draw.rectangle([po_x + 15, po_y + 195, po_x + 80, po_y + 205], fill=DARK_BROWN)

        # Dripper
        draw.polygon([(po_x + 10, po_y + 35), (po_x + 85, po_y + 35),
                       (po_x + 47, po_y + 100)], fill=LIGHT_CORAL)
        draw.polygon([(po_x + 22, po_y + 42), (po_x + 72, po_y + 42),
                       (po_x + 47, po_y + 88)], fill=DARK_CORAL)
        draw.polygon([(po_x + 28, po_y + 48), (po_x + 66, po_y + 48),
                       (po_x + 47, po_y + 78)], fill=DARK_BROWN)

        # Cup
        cup_y = po_y + 135
        draw.rectangle([po_x + 20, cup_y, po_x + 72, cup_y + 50], fill=WHITE)
        draw.rectangle([po_x + 25, cup_y + 5, po_x + 67, cup_y + 45], fill=DARK_BROWN)
        draw.rectangle([po_x + 72, cup_y + 12, po_x + 85, cup_y + 32], fill=WHITE)

        # Dripping coffee
        drip_y = po_y + 100 + (f * 9) % 35
        draw.ellipse([po_x + 44, drip_y, po_x + 52, drip_y + 8], fill=DARK_BROWN)
        if f % 2 == 0:
            drip_y2 = po_y + 100 + ((f * 9 + 18) % 35)
            draw.ellipse([po_x + 45, drip_y2, po_x + 53, drip_y2 + 7], fill=DARK_BROWN)

        # Steam from cup
        draw_steam(draw, po_x + 40, cup_y - 10, f)

        draw_loading_label(draw, "Brewing", f)
        frames.append(img)
    return frames


def frames_canoodling():
    """Two Clawds leaning together with hearts."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        lean = [0, 3, 5, 7, 5, 3][f]

        # Left Clawd
        draw_clawd(draw, 30 + lean, 155, g)

        # Right Clawd
        draw_clawd(draw, 222 - lean, 155, g)

        # Hearts floating up between them
        mid_x = 200
        heart_data = [(mid_x, 120, 5), (mid_x - 20, 95, 4), (mid_x + 22, 100, 3)]
        for i, (hx, hy, hs) in enumerate(heart_data):
            rise = ((f + i * 2) % NUM_FRAMES) * 10
            if (f + i) % NUM_FRAMES > 1:
                draw_heart(draw, hx, hy - rise, hs, RED)

        draw_loading_label(draw, "Canoodling", f)
        frames.append(img)
    return frames


def draw_gear(draw, cx, cy, size, step=0):
    """Draw a pixel gear shape. step rotates the teeth pattern."""
    s = size
    # Core square
    draw.rectangle([cx - s, cy - s, cx + s, cy + s], fill=GRAY)
    # Teeth around the edges (4 positions, shifted by step)
    teeth = [(-s - s//2, 0), (s + s//2, 0), (0, -s - s//2), (0, s + s//2)]
    # Rotate teeth by shifting which ones are drawn
    for i, (tx, ty) in enumerate(teeth):
        if (i + step) % 2 == 0:
            draw.rectangle([cx + tx - s//3, cy + ty - s//3,
                            cx + tx + s//3, cy + ty + s//3], fill=DARK_GRAY)
    # Center hole
    draw.rectangle([cx - s//3, cy - s//3, cx + s//3, cy + s//3], fill=DARK_GRAY)


def draw_thought_bubble(draw, x, y, w, h):
    """Draw a cloud-shaped thought bubble with connector dots."""
    # Main bubble
    draw.ellipse([x, y, x + w, y + h], fill=WHITE)
    draw.ellipse([x - w//6, y + h//4, x + w//3, y + h - h//4], fill=WHITE)
    draw.ellipse([x + w - w//3, y + h//4, x + w + w//6, y + h - h//4], fill=WHITE)
    # Connector dots below
    draw.ellipse([x + w//2 - 4, y + h + 2, x + w//2 + 4, y + h + 10], fill=WHITE)
    draw.ellipse([x + w//2 - 2, y + h + 14, x + w//2 + 2, y + h + 20], fill=WHITE)


def draw_music_note(draw, x, y, color=BLACK):
    """Draw a tiny pixel music note."""
    # Stem
    draw.rectangle([x + 4, y, x + 5, y + 10], fill=color)
    # Note head
    draw.ellipse([x, y + 8, x + 5, y + 13], fill=color)
    # Flag
    draw.rectangle([x + 5, y, x + 8, y + 3], fill=color)


def draw_lightbulb(draw, cx, cy, size=18, glow=0):
    """Draw a lightbulb with a visible filament."""
    bulb_fill = (255, 228, 120)
    bulb_outline = ORANGE
    glass_w = size + 8
    glass_h = int(size * 1.35)
    if glow:
        draw.ellipse([cx - glass_w//2 - glow, cy - glass_h//2 - glow,
                      cx + glass_w//2 + glow, cy + glass_h//2 + glow],
                     fill=(255, 240, 170))
    draw.ellipse([cx - glass_w//2, cy - glass_h//2,
                  cx + glass_w//2, cy + glass_h//2], fill=bulb_fill, outline=bulb_outline)
    neck_y = cy + glass_h//2 - 6
    draw.rectangle([cx - size//5, neck_y, cx + size//5, neck_y + 8], fill=GRAY)
    draw.rectangle([cx - size//4, neck_y + 8, cx + size//4, neck_y + 14], fill=DARK_GRAY)
    support_y = cy + 4
    draw.line([cx - size//6, support_y, cx - size//6, support_y + 8], fill=DARK_GRAY, width=1)
    draw.line([cx + size//6, support_y, cx + size//6, support_y + 8], fill=DARK_GRAY, width=1)
    filament = [
        (cx - size//6, support_y + 8),
        (cx - size//10, support_y + 5),
        (cx, support_y + 8),
        (cx + size//10, support_y + 5),
        (cx + size//6, support_y + 8),
    ]
    draw.line(filament, fill=DARK_GRAY, width=1)
    draw.ellipse([cx - size//3, cy - glass_h//3, cx - size//9, cy - glass_h//7], fill=WHITE)


def draw_brain_icon(draw, cx, cy, pulse=0):
    """Draw a front-view pixel-art brain closer to the reference image."""
    brain_fill = (247, 183, 190)
    brain_shadow = (226, 145, 160)
    outline = BLACK
    top = cy - 28 - pulse
    bottom = cy + 20 + pulse

    lobes = [
        (cx - 34, top + 6, cx - 2, cy + 6),
        (cx - 24, top - 6, cx - 1, cy - 2),
        (cx - 36, cy - 4, cx - 8, bottom - 2),
        (cx - 18, cy + 8, cx + 2, bottom),
        (cx + 2, top + 6, cx + 34, cy + 6),
        (cx + 1, top - 6, cx + 24, cy - 2),
        (cx + 8, cy - 4, cx + 36, bottom - 2),
        (cx - 2, cy + 8, cx + 18, bottom),
    ]
    for x0, y0, x1, y1 in lobes:
        draw.ellipse([x0, y0, x1, y1], fill=brain_fill, outline=outline)

    stem_top = bottom - 4
    draw.polygon([(cx - 11, stem_top), (cx + 11, stem_top), (cx + 4, bottom + 16), (cx - 4, bottom + 16)],
                 fill=(168, 55, 95), outline=outline)

    draw.line([cx, top + 2, cx, bottom - 6], fill=outline, width=2)

    left_folds = [
        [(cx - 24, top + 6), (cx - 30, top + 12), (cx - 18, top + 18), (cx - 26, top + 24)],
        [(cx - 12, top + 2), (cx - 18, top + 10), (cx - 8, top + 18), (cx - 18, top + 24)],
        [(cx - 28, cy - 2), (cx - 18, cy + 4), (cx - 28, cy + 12), (cx - 14, cy + 18)],
        [(cx - 14, cy - 6), (cx - 6, cy + 2), (cx - 16, cy + 10), (cx - 6, cy + 18)],
    ]
    right_folds = [
        [(cx + 24, top + 6), (cx + 30, top + 12), (cx + 18, top + 18), (cx + 26, top + 24)],
        [(cx + 12, top + 2), (cx + 18, top + 10), (cx + 8, top + 18), (cx + 18, top + 24)],
        [(cx + 28, cy - 2), (cx + 18, cy + 4), (cx + 28, cy + 12), (cx + 14, cy + 18)],
        [(cx + 14, cy - 6), (cx + 6, cy + 2), (cx + 16, cy + 10), (cx + 6, cy + 18)],
    ]
    for fold in left_folds + right_folds:
        draw.line(fold, fill=outline, width=2)
    for x_off in [-18, -8, 8, 18]:
        draw.arc([cx + x_off - 9, cy + 2, cx + x_off + 9, cy + 18], 200, 350, fill=brain_shadow, width=2)


def draw_stick_figure(draw, x, y, pose=0, color=CORAL):
    """Draw a tiny stick figure in one of two poses.
    pose=0: arms out, pose=1: arms up."""
    s = 2
    # Head
    draw.ellipse([x - 2*s, y - 2*s, x + 2*s, y + 2*s], fill=color)
    # Body
    draw.rectangle([x - s//2, y + 2*s, x + s//2, y + 8*s], fill=color)
    # Legs
    draw.line([x, y + 8*s, x - 2*s, y + 12*s], fill=color, width=2)
    draw.line([x, y + 8*s, x + 2*s, y + 12*s], fill=color, width=2)
    # Arms
    if pose == 0:
        draw.line([x, y + 4*s, x - 3*s, y + 6*s], fill=color, width=2)
        draw.line([x, y + 4*s, x + 3*s, y + 6*s], fill=color, width=2)
    else:
        draw.line([x, y + 4*s, x - 3*s, y + 2*s], fill=color, width=2)
        draw.line([x, y + 4*s, x + 3*s, y + 2*s], fill=color, width=2)


def draw_sweat_drop(draw, x, y, scale=1, color=LIGHT_BLUE):
    """Draw a simple animated sweat drop."""
    s = max(3, scale)
    draw.polygon([(x, y - 3*s), (x - 2*s, y), (x + 2*s, y)], fill=color)
    draw.ellipse([x - 2*s, y - s, x + 2*s, y + 3*s], fill=color)


def draw_storm_cloud(draw, x, y, scale=1.0, fill_color=DARK_GRAY):
    """Draw a chunky storm cloud."""
    w = int(48 * scale)
    h = int(24 * scale)
    draw.ellipse([x - w, y - h//2, x, y + h//2], fill=fill_color)
    draw.ellipse([x - w//2, y - h, x + w//2, y + h//3], fill=fill_color)
    draw.ellipse([x, y - h//2, x + w, y + h//2], fill=fill_color)
    draw.rectangle([x - w + 10, y, x + w - 10, y + h//2], fill=fill_color)


def draw_lightning_bolt(draw, x, y, scale=1.0, color=YELLOW):
    """Draw a branching lightning bolt."""
    s = scale
    draw.polygon([
        (x, y),
        (x - 14 * s, y + 42 * s),
        (x + 4 * s, y + 38 * s),
        (x - 12 * s, y + 92 * s),
        (x + 18 * s, y + 48 * s),
        (x + 2 * s, y + 52 * s),
        (x + 20 * s, y + 10 * s),
    ], fill=color)


def draw_data_card(draw, x, y, accent=TEAL, skew=0):
    """Draw a tiny tabbed data card."""
    left = x
    right = x + 34
    top = y
    bottom = y + 42
    draw.polygon([(left, top + skew), (right, top), (right, bottom), (left, bottom + skew)],
                 fill=WHITE, outline=DARK_GRAY)
    draw.rectangle([left + 5, top - 6 + skew//2, left + 18, top + 2 + skew//2], fill=accent)
    draw.rectangle([left + 7, top + 10 + skew//2, right - 6, top + 13 + skew//2], fill=accent)
    draw.rectangle([left + 7, top + 18 + skew//2, right - 10, top + 21 + skew//2], fill=GRAY)
    draw.rectangle([left + 7, top + 26 + skew//2, right - 6, top + 29 + skew//2], fill=GRAY)
    draw.rectangle([left + 7, top + 34 + skew//2, left + 14, top + 37 + skew//2], fill=accent)


def draw_crystal(draw, cx, cy, size=24, fill_color=YELLOW, outline=ORANGE):
    """Draw a faceted crystal."""
    points = [
        (cx, cy - size),
        (cx - size // 2, cy - size // 3),
        (cx - size // 3, cy + size),
        (cx, cy + size + size // 4),
        (cx + size // 3, cy + size),
        (cx + size // 2, cy - size // 3),
    ]
    draw.polygon(points, fill=fill_color, outline=outline)
    draw.line([points[0], points[2]], fill=outline, width=1)
    draw.line([points[0], points[4]], fill=outline, width=1)
    draw.line([points[1], points[3], points[5]], fill=outline, width=1)
    draw.polygon([(cx - size // 6, cy - size // 3), (cx, cy - size // 2),
                  (cx + size // 8, cy), (cx - size // 8, cy + size // 4)], fill=WHITE)


def draw_fancy_flower(draw, cx, cy, petal_color=PINK, size=18, pulse=0):
    """Draw a more ornate flower with layered petals."""
    petal_r = size + pulse
    inner_r = max(6, size // 2)
    for i in range(8):
        angle = math.radians(i * 45)
        px = cx + int(math.cos(angle) * petal_r)
        py = cy + int(math.sin(angle) * petal_r * 0.78)
        draw.ellipse([px - inner_r, py - inner_r, px + inner_r, py + inner_r], fill=petal_color, outline=WHITE)
    for i in range(4):
        angle = math.radians(i * 90 + 22)
        px = cx + int(math.cos(angle) * (petal_r // 2))
        py = cy + int(math.sin(angle) * (petal_r // 2))
        draw.ellipse([px - inner_r // 2, py - inner_r // 2, px + inner_r // 2, py + inner_r // 2],
                     fill=LIGHT_CORAL, outline=WHITE)
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=YELLOW, outline=ORANGE)
    draw.ellipse([cx - inner_r // 2, cy - inner_r // 2, cx + inner_r // 2, cy + inner_r // 2], fill=ORANGE)


def draw_spotlight(draw, cx, top_y, bottom_y, top_w=12, bottom_w=90, color=(255, 244, 190)):
    """Draw a stage-style spotlight cone using solid beam lines (GIF-safe)."""
    if len(color) == 4:
        color = color[:3]
    left_top = cx - top_w // 2
    right_top = cx + top_w // 2
    left_bottom = cx - bottom_w // 2
    right_bottom = cx + bottom_w // 2
    draw.line([left_top, top_y, left_bottom, bottom_y], fill=color, width=1)
    draw.line([right_top, top_y, right_bottom, bottom_y], fill=color, width=1)
    for i in range(1, 8):
        t = i / 8
        tx = int(left_top + (right_top - left_top) * t)
        bx = int(left_bottom + (right_bottom - left_bottom) * t)
        draw.line([tx, top_y, bx, bottom_y], fill=color, width=1)
    draw.arc([cx - bottom_w // 2, bottom_y - 14, cx + bottom_w // 2, bottom_y + 12], 200, 340, fill=color, width=1)


def draw_sigil_ring(draw, cx, cy, radius, color=PURPLE, frame=0, spokes=8):
    """Draw a simple arcane/scientific ring with ticks and orbit marks."""
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=color, width=2)
    inner_r = max(8, radius - 12)
    draw.arc([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
             frame * 18, frame * 18 + 240, fill=color, width=1)
    for i in range(spokes):
        angle = math.radians(frame * 10 + i * (360 / spokes))
        x0 = cx + int((radius - 8) * math.cos(angle))
        y0 = cy + int((radius - 8) * math.sin(angle))
        x1 = cx + int((radius + 4) * math.cos(angle))
        y1 = cy + int((radius + 4) * math.sin(angle))
        draw.line([x0, y0, x1, y1], fill=color, width=1)
        draw.rectangle([x1 - 1, y1 - 1, x1 + 1, y1 + 1], fill=YELLOW if i % 2 == 0 else color)


def draw_playing_card(draw, cx, cy, w=28, h=38, accent=RED, skew=0):
    """Draw a stylized playing card with a suit marker."""
    left = cx - w // 2
    right = cx + w // 2
    top = cy - h // 2
    bottom = cy + h // 2
    draw.polygon([(left + skew, top), (right + skew, top), (right - skew, bottom), (left - skew, bottom)],
                 fill=WHITE, outline=GRAY)
    draw.rectangle([left + 5 + skew // 2, top + 5, left + 11 + skew // 2, top + 11], fill=accent)
    draw.rectangle([right - 11 - skew // 2, bottom - 11, right - 5 - skew // 2, bottom - 5], fill=accent)
    draw.rectangle([cx - 5, cy - 8, cx + 5, cy + 8], fill=accent)
    draw.rectangle([cx - 2, cy - 14, cx + 2, cy + 14], fill=accent)


def draw_dancer_figure(draw, x, y, step=0, color=CORAL):
    """Draw a tiny dancer silhouette with a few expressive poses."""
    draw.ellipse([x - 5, y - 24, x + 5, y - 14], fill=color)
    draw.line([x, y - 14, x, y + 4], fill=color, width=3)
    arm_sets = [
        ((-10, -4), (10, 0)),
        ((-12, -10), (10, -2)),
        ((-8, -2), (12, -12)),
        ((-10, -12), (8, -4)),
    ]
    leg_sets = [
        ((-10, 14), (8, 10)),
        ((-6, 10), (12, 16)),
        ((-12, 16), (6, 10)),
        ((-8, 12), (10, 14)),
    ]
    left_arm, right_arm = arm_sets[step % len(arm_sets)]
    left_leg, right_leg = leg_sets[step % len(leg_sets)]
    draw.line([x, y - 8, x + left_arm[0], y + left_arm[1]], fill=color, width=3)
    draw.line([x, y - 8, x + right_arm[0], y + right_arm[1]], fill=color, width=3)
    draw.line([x, y + 4, x + left_leg[0], y + left_leg[1]], fill=color, width=3)
    draw.line([x, y + 4, x + right_leg[0], y + right_leg[1]], fill=color, width=3)


def frames_cerebrating():
    """Clawd centered with a more realistic pulsing brain icon above."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 120, 160
        draw_clawd(draw, cx, cy, g, blink=(f == 3))

        brain_cx = cx + 4 * g
        brain_cy = cy - 20
        draw_brain_icon(draw, brain_cx, brain_cy, pulse=1 if f in [1, 4] else 0)

        # Little neuron sparks around the brain.
        spark_positions = [
            (brain_cx - 52, brain_cy - 16),
            (brain_cx + 48, brain_cy - 10),
            (brain_cx - 42, brain_cy + 26),
            (brain_cx + 40, brain_cy + 24),
        ]
        for i, (sx, sy) in enumerate(spark_positions):
            if (f + i) % 2 == 0:
                draw_text(draw, "*", sx, sy, color=YELLOW, scale=3)

        draw_loading_label(draw, "Cerebrating", f)
        frames.append(img)
    return frames


def frames_channelling():
    """Clawd channeling ritual energy through circles, ribbons, and a focal orb."""
    frames = []
    num_frames = 8
    body_bob = [0, -1, 0, 1, -1, 1, 0, -1]
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = 13

        cx = 130
        cy = 144 + body_bob[f]
        sigil_cx = cx + 4 * g
        sigil_cy = 246

        for i, radius in enumerate([28, 44, 58]):
            if f >= i:
                draw_sigil_ring(
                    draw,
                    sigil_cx,
                    sigil_cy,
                    radius,
                    color=[TEAL, PURPLE, PINK][i],
                    frame=f + i,
                    spokes=8 + i * 2,
                )

        # Broad energy ribbons fan outward from the sigil instead of slicing through Clawd.
        column_specs = [
            (-98, BLUE, LIGHT_BLUE, 6, 5.5),
            (-66, PURPLE, WHITE, 5, 5.0),
            (66, PINK, WHITE, 5, 5.0),
            (98, TEAL, LIGHT_BLUE, 6, 5.5),
        ]
        for i, (base_offset, outer_color, inner_color, width, wave_amp) in enumerate(column_specs):
            direction = -1 if base_offset < 0 else 1
            for y_step in range(17):
                yy = sigil_cy - 10 - y_step * 9
                drift = int(y_step * 1.15) * direction
                wave = int(math.sin((y_step + f * 1.35 + i) * 0.7) * wave_amp)
                flare = max(2, width - y_step // 5)
                core = max(1, flare // 2)
                rx = sigil_cx + base_offset + drift + wave
                draw.rectangle([rx - flare, yy, rx + flare, yy + 8], fill=outer_color)
                draw.rectangle([rx - core, yy + 1, rx + core, yy + 7], fill=inner_color)
                if y_step % 4 == 0:
                    draw.rectangle([rx - 1, yy - 3, rx + 1, yy - 1], fill=WHITE)

        t = f / (num_frames - 1)
        orb_y = round(112 + (66 - 112) * t)
        orb_glow = round(14 + (36 - 14) * t)
        draw.ellipse([sigil_cx - orb_glow, orb_y - orb_glow, sigil_cx + orb_glow, orb_y + orb_glow], fill=(255, 236, 160))
        orb_core = round(10 + (14 - 10) * t)
        draw.ellipse([sigil_cx - orb_core, orb_y - orb_core, sigil_cx + orb_core, orb_y + orb_core], fill=WHITE)
        draw.ellipse([sigil_cx - 6, orb_y - 6, sigil_cx + 6, orb_y + 6], fill=YELLOW)

        if f >= 2:
            beam_targets = [
                (sigil_cx, cy - 8, LIGHT_BLUE, 2),
                (sigil_cx - 42, cy + 2, PURPLE, 2),
                (sigil_cx + 42, cy + 2, PINK, 2),
            ]
            for tx, ty, color, width in beam_targets:
                draw.line([sigil_cx, orb_y + orb_core - 1, tx, ty], fill=color, width=width)

        for i, (sx, sy) in enumerate([
            (sigil_cx - 94, cy - 34),
            (sigil_cx + 84, cy - 52),
            (sigil_cx - 28, cy - 96),
            (sigil_cx + 20, cy - 104),
            (sigil_cx + 98, cy + 8),
            (sigil_cx - 86, cy + 14),
        ]):
            if (f + i) % 2 == 0:
                draw_text(draw, "*", sx, sy - (f % 2) * 4, color=YELLOW, scale=3)

        draw_clawd(draw, cx, cy, g, blink=(f in (4, 5)))

        draw_loading_label(draw, "Channelling", f)
        frames.append(img)
    return frames


def frames_choreographing():
    """Clawd conducting a more theatrical stage performance."""
    frames = []
    num_frames = 8
    baton_dx = [28, 36, 24, 18, 26, 40, 30, 20]
    baton_dy = [-28, -18, -6, -16, -30, -22, -8, -20]
    dancer_1 = [(296, 196), (302, 188), (308, 198), (300, 208), (292, 202), (300, 190), (308, 194), (298, 206)]
    dancer_2 = [(344, 202), (336, 190), (330, 202), (338, 212), (346, 204), (338, 192), (330, 198), (340, 210)]
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        draw_spotlight(draw, 278, 16, 300, top_w=18, bottom_w=150, color=(255, 246, 200))
        draw_spotlight(draw, 344, 26, 304, top_w=18, bottom_w=140, color=(255, 230, 210))
        draw.rectangle([184, 268, 384, 308], fill=(48, 48, 60))
        draw.rectangle([184, 304, 384, 314], fill=DARK_GRAY)
        for i in range(6):
            light_x = 196 + i * 30
            light_color = YELLOW if (f + i) % 2 == 0 else PINK
            draw.rectangle([light_x, 308, light_x + 12, 312], fill=light_color)

        cx, cy = 20, 155
        draw_clawd(draw, cx, cy + [0, -2, -4, -2, 0, 2, 0, -2][f], g, blink=(f == 4))

        arm_y = cy + 2 * g + g // 2
        arm_x = cx + 10 * g
        bx = arm_x + baton_dx[f]
        by = arm_y + baton_dy[f]
        draw.line([arm_x, arm_y, bx, by], fill=DARK_BROWN, width=3)
        draw.rectangle([bx - 2, by - 2, bx + 2, by + 2], fill=WHITE)
        for trail in range(1, 4):
            tx = arm_x + int(baton_dx[f] * (1 - trail * 0.18))
            ty = arm_y + int(baton_dy[f] * (1 - trail * 0.18))
            draw.line([arm_x, arm_y, tx, ty], fill=LIGHT_BLUE if trail % 2 else PURPLE, width=1)

        draw_dancer_figure(draw, dancer_1[f][0], dancer_1[f][1], step=f, color=CORAL)
        draw_dancer_figure(draw, dancer_2[f][0], dancer_2[f][1], step=f + 1, color=LIGHT_CORAL)
        for x, y in [dancer_1[f], dancer_2[f]]:
            draw.arc([x - 22, y - 6, x + 22, y + 26], 200, 340, fill=WHITE, width=1)

        note_positions = [(232, 160), (260, 132), (300, 148), (332, 126)]
        for i, (nx, ny) in enumerate(note_positions):
            bob = ((f + i) % 4) * 7
            if (f + i) % 2 == 0:
                draw_music_note(draw, nx, ny - bob, [DARK_GRAY, PURPLE, PINK, TEAL][i])
        for sx, sy in [(250, 104), (316, 92), (364, 150)]:
            if (f + sx // 10) % 2 == 0:
                draw_text(draw, "*", sx, sy, color=YELLOW, scale=2)

        draw_loading_label(draw, "Choreographing", f)
        frames.append(img)
    return frames


def frames_churning():
    """Clawd beside an open churn with a rotating stirring motion."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 40, 150
        draw_clawd(draw, cx, cy, g)

        # Barrel body
        barrel_x, barrel_y = 235, 180
        bw, bh = 118, 108
        draw.rectangle([barrel_x, barrel_y, barrel_x + bw, barrel_y + bh], fill=BROWN)
        draw.ellipse([barrel_x - 4, barrel_y - 18, barrel_x + bw + 4, barrel_y + 18], fill=DARK_BROWN)
        draw.ellipse([barrel_x + 8, barrel_y - 10, barrel_x + bw - 8, barrel_y + 12], fill=(255, 246, 212))
        draw.ellipse([barrel_x, barrel_y + bh - 10, barrel_x + bw, barrel_y + bh + 12], outline=DARK_BROWN, width=2)
        for band_y in [barrel_y + 18, barrel_y + bh // 2, barrel_y + bh - 12]:
            draw.rectangle([barrel_x - 3, band_y - 3, barrel_x + bw + 3, band_y + 3], fill=DARK_BROWN)

        # Swirling cream on top.
        swirl_cx = barrel_x + bw // 2
        swirl_cy = barrel_y + 2
        swirl_specs = [
            (44, 16, WHITE, f * 55 + 10),
            (30, 11, (255, 238, 190), f * 55 + 110),
            (18, 7, YELLOW, f * 55 + 210),
        ]
        for rx, ry, color, start in swirl_specs:
            draw.arc([swirl_cx - rx, swirl_cy - ry, swirl_cx + rx, swirl_cy + ry],
                     start, start + 220, fill=color, width=3)

        # Rotating churn handle and dash.
        angle = math.radians([-55, -20, 20, 55, 18, -22][f])
        handle_top_x = swirl_cx + int(24 * math.cos(angle))
        handle_top_y = barrel_y - 40 + int(10 * math.sin(angle))
        dash_x = swirl_cx + int(10 * math.cos(angle + math.pi))
        dash_y = swirl_cy + int(6 * math.sin(angle + math.pi))
        draw.line([handle_top_x, handle_top_y, dash_x, dash_y + 18], fill=DARK_BROWN, width=4)
        draw.line([handle_top_x - 12, handle_top_y, handle_top_x + 12, handle_top_y], fill=DARK_BROWN, width=3)
        draw.rectangle([dash_x - 10, dash_y + 18, dash_x + 10, dash_y + 26], fill=DARK_BROWN)

        # Splashes and foam whipped by the motion.
        splash_points = [
            (barrel_x + 18, barrel_y - 8 - (f % 2) * 6),
            (barrel_x + 44, barrel_y - 14 + ((f + 1) % 3) * 3),
            (barrel_x + 82, barrel_y - 12 - ((f + 2) % 2) * 5),
            (barrel_x + 96, barrel_y - 6 + (f % 3) * 2),
        ]
        for sx, sy in splash_points:
            draw.ellipse([sx, sy, sx + 10, sy + 6], fill=WHITE)

        draw_loading_label(draw, "Churning", f)
        frames.append(img)
    return frames


def frames_coalescing():
    """Particles spiral together into a bright coalesced core."""
    import random
    rng = random.Random(42)
    target_cx, target_cy = 292, 136
    num_dots = 28
    colors = [CORAL, YELLOW, TEAL, LIGHT_BLUE]
    scattered = [(rng.randint(170, 380), rng.randint(25, 270)) for _ in range(num_dots)]
    targets = []
    for i in range(num_dots):
        ring = 18 + (i % 3) * 14
        angle = 2 * math.pi * i / num_dots
        targets.append((target_cx + int(ring * math.cos(angle)),
                        target_cy + int((ring - 4) * math.sin(angle))))

    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)

        # Clawd watching from bottom-left
        draw_clawd(draw, 30, 180, GRID)

        t = f / (NUM_FRAMES - 1)
        for i in range(num_dots):
            sx, sy = scattered[i]
            tx, ty = targets[i]
            base_x = sx + (tx - sx) * t
            base_y = sy + (ty - sy) * t
            swirl_r = (1 - t) * (26 + (i % 4) * 6)
            swirl_a = 0.9 * f + i * 0.55
            x = int(base_x + math.cos(swirl_a) * swirl_r)
            y = int(base_y + math.sin(swirl_a) * swirl_r * 0.65)
            prev_x = int(base_x + math.cos(swirl_a - 0.55) * swirl_r)
            prev_y = int(base_y + math.sin(swirl_a - 0.55) * swirl_r * 0.65)
            color = colors[i % len(colors)]
            draw.line([prev_x, prev_y, x, y], fill=color, width=2)
            dot_r = 3 + (i % 2)
            draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=color)

        if f >= 3:
            halo = 18 + (f - 3) * 8
            draw.ellipse([target_cx - halo, target_cy - halo, target_cx + halo, target_cy + halo], outline=YELLOW, width=2)
            draw.ellipse([target_cx - halo//2, target_cy - halo//2, target_cx + halo//2, target_cy + halo//2], fill=(255, 228, 160))
        if f >= 4:
            for sx, sy in [(target_cx - 46, target_cy - 10), (target_cx + 38, target_cy - 24), (target_cx + 24, target_cy + 30)]:
                draw_text(draw, "*", sx, sy, color=YELLOW, scale=3)

        draw_loading_label(draw, "Coalescing", f)
        frames.append(img)
    return frames


def frames_cogitating():
    """Clawd in thinker pose with thought bubble cycling content."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 120, 185
        draw_clawd(draw, cx, cy, g)

        # Thought bubble
        bubble_x = cx + 5 * g
        bubble_y = cy - 60
        bob = [0, -2, -4, -2, 0, 2][f]
        draw_thought_bubble(draw, bubble_x, bubble_y + bob, 70, 40)

        # Content cycles: gear, "?", "!", gear, "?", "!"
        content_phase = f % 3
        content_cx = bubble_x + 35
        content_cy = bubble_y + bob + 20
        if content_phase == 0:
            draw_gear(draw, content_cx, content_cy, 8, f)
        elif content_phase == 1:
            draw_text(draw, "?", content_cx - 10, content_cy - 14, color=TEAL, scale=5)
        else:
            draw_text(draw, "!", content_cx - 10, content_cy - 14, color=YELLOW, scale=5)

        draw_loading_label(draw, "Cogitating", f)
        frames.append(img)
    return frames


def frames_concocting():
    """Clawd with goggles, beaker + flask on table, bubbling liquid."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 20, 150
        draw_clawd(draw, cx, cy, g)

        # Goggles on Clawd
        gy_eye = cy + g
        draw.ellipse([cx + g - 2, gy_eye - 2, cx + 2 * g + 2, gy_eye + g + 2], outline=TEAL, width=2)
        draw.ellipse([cx + 6 * g - 2, gy_eye - 2, cx + 7 * g + 2, gy_eye + g + 2], outline=TEAL, width=2)
        draw.line([cx + 2 * g + 2, gy_eye + g // 2, cx + 6 * g - 2, gy_eye + g // 2], fill=TEAL, width=2)

        # Table surface
        table_y = 275
        draw.rectangle([210, table_y, 390, table_y + 8], fill=DARK_BROWN)

        # Flask (Erlenmeyer) — triangle
        flask_x = 240
        draw.polygon([(flask_x, table_y), (flask_x + 60, table_y),
                       (flask_x + 30, table_y - 70)], fill=(200, 220, 200))
        # Green liquid inside flask
        liq_h = 35
        draw.polygon([(flask_x + 8, table_y - 2), (flask_x + 52, table_y - 2),
                       (flask_x + 35, table_y - liq_h), (flask_x + 25, table_y - liq_h)], fill=GREEN)
        # Bubbles in flask
        for bi in range(3):
            bub_y = table_y - 10 - ((f * 8 + bi * 12) % liq_h)
            bub_x = flask_x + 20 + bi * 8
            draw.ellipse([bub_x, bub_y, bub_x + 5, bub_y + 5], fill=LIME)

        # Beaker — rectangle
        beaker_x = 330
        draw.rectangle([beaker_x, table_y - 55, beaker_x + 45, table_y], fill=(200, 200, 220))
        draw.rectangle([beaker_x + 5, table_y - 50, beaker_x + 40, table_y - 5], fill=PURPLE)
        # Bubbles in beaker
        for bi in range(2):
            bub_y = table_y - 15 - ((f * 7 + bi * 15) % 30)
            bub_x = beaker_x + 12 + bi * 14
            draw.ellipse([bub_x, bub_y, bub_x + 5, bub_y + 5], fill=PINK)

        # Smoke puffs alternating above
        smoke_colors = [GREEN, PURPLE]
        for si in range(3):
            sc = smoke_colors[(si + f) % 2]
            sx = 260 + si * 40
            sy = table_y - 80 - ((f + si) % 3) * 12
            r = 6 + (si % 2) * 3
            if (f + si) % 2 == 0:
                draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=sc)

        draw_loading_label(draw, "Concocting", f)
        frames.append(img)
    return frames


def frames_cascading():
    """Clawd watching a longer green codefall pile up into a data bank."""
    frames = []
    code_chars = "{}[]();<>/=+#01if"
    col_count = 11
    col_x_start = 196
    col_spacing = 16
    total_frames = 10

    for f in range(total_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)

        # Clawd (left)
        draw_clawd(draw, 30, 155, GRID)
        pool_top = 310 - (10 + f * 8)

        # Dense code waterfall (right)
        for col in range(col_count):
            col_x = col_x_start + col * col_spacing
            speed = 18 + col
            trail_len = 9 + (col % 4)
            head_y = (f * speed + col * 21) % 440 - 110
            for row in range(trail_len):
                char_y = head_y - row * 16
                if not 14 <= char_y <= pool_top - 10:
                    continue
                ch = code_chars[(col * 5 + row + f) % len(code_chars)]
                scale = 3 if row < 3 else 2
                if row == 0:
                    char_color = (220, 255, 225)
                elif row == 1:
                    char_color = (150, 235, 160)
                else:
                    char_color = (40, max(90, 190 - row * 9), 70)
                if ch in FONT_GLYPHS:
                    draw_text(draw, ch, col_x, int(char_y), color=char_color, scale=scale)
                if row < trail_len - 1:
                    draw.rectangle([col_x + 5, char_y + 9, col_x + 8, char_y + 15], fill=(30, 120, 50))

        # Accumulating data bank at the bottom.
        for x in range(188, 382, 8):
            height = (312 - pool_top) + ((x // 8 + f) % 3) * 4
            shade = (30, 110 + ((x // 8) % 4) * 18, 45)
            draw.rectangle([x, 310 - height, x + 6, 310], fill=shade)
        draw.line([188, pool_top, 382, pool_top], fill=(170, 255, 180), width=2)

        # Pixel spray where the code slams into the pile.
        for i in range(22):
            splash_x = 194 + (i * 9 + f * 5) % 184
            splash_y = pool_top - ((i * 7 + f * 11) % 34)
            splash_color = [(70, 205, 95), LIGHT_BLUE, YELLOW][i % 3]
            size = 3 if i % 4 else 4
            draw.rectangle([splash_x, splash_y, splash_x + size, splash_y + size], fill=splash_color)

        draw_loading_label(draw, "Cascading", f)
        frames.append(img)
    return frames


def frames_catapulting():
    """A playful catapult launch with setup, release, flight, and payoff."""
    frames = []
    num_frames = 8
    pivot_x, pivot_y = 132, 246
    arm_len = 86
    tail_len = 24
    arm_angles = [154, 148, 140, 100, 66, 62, 62, 62]
    flight_positions = [
        (138, 152),
        (190, 118),
        (244, 96),
        (282, 112),
        (286, 158),
    ]

    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)

        # Catapult base and wheels.
        draw.ellipse([68, 250, 100, 282], fill=GRAY, outline=DARK_BROWN)
        draw.ellipse([118, 250, 150, 282], fill=GRAY, outline=DARK_BROWN)
        draw.rectangle([72, 240, 146, 254], fill=BROWN)
        draw.line([84, 244, 132, 198], fill=DARK_BROWN, width=5)
        draw.line([132, 198, 142, 244], fill=DARK_BROWN, width=5)
        draw.line([80, 244, 142, 244], fill=DARK_BROWN, width=3)

        arm_angle = math.radians(arm_angles[f])
        arm_end_x = int(pivot_x + math.cos(arm_angle) * arm_len)
        arm_end_y = int(pivot_y - math.sin(arm_angle) * arm_len)
        tail_x = int(pivot_x - math.cos(arm_angle) * tail_len)
        tail_y = int(pivot_y + math.sin(arm_angle) * tail_len)

        draw.line([tail_x, tail_y, pivot_x, pivot_y, arm_end_x, arm_end_y], fill=DARK_BROWN, width=5)
        draw.rectangle([tail_x - 10, tail_y - 10, tail_x + 10, tail_y + 10], fill=DARK_GRAY)
        draw.ellipse([arm_end_x - 14, arm_end_y - 8, arm_end_x + 14, arm_end_y + 10], fill=BROWN, outline=DARK_BROWN)
        draw.line([pivot_x, 246, pivot_x, 264], fill=DARK_BROWN, width=3)

        if f <= 2:
            draw.line([94, 222, arm_end_x - 8, arm_end_y + 2], fill=GRAY, width=2)
            draw.line([106, 214, arm_end_x + 8, arm_end_y + 2], fill=GRAY, width=2)
            for i in range(3):
                draw.line([70 + i * 8, 224 + i * 4, 80 + i * 8, 220 + i * 4], fill=LIGHT_BLUE, width=1)
        else:
            for i in range(3):
                motion_x = pivot_x - 18 + i * 10
                motion_y = 168 + i * 10
                draw.line([motion_x, motion_y, motion_x + 12, motion_y - 10], fill=LIGHT_BLUE, width=1)

        if f <= 2:
            sling_grid = 9 + (1 if f == 2 else 0)
            clawd_x = max(28, arm_end_x - 4 * sling_grid + 8)
            clawd_y = arm_end_y - 2 * sling_grid + [6, 3, 0][f]
            draw_clawd(draw, clawd_x, clawd_y, sling_grid, blink=(f in (1, 2)))
            draw.line([arm_end_x - 10, arm_end_y + 2, clawd_x + 8, clawd_y + 20], fill=GRAY, width=2)
            draw.line([arm_end_x + 10, arm_end_y + 2, clawd_x + 52, clawd_y + 20], fill=GRAY, width=2)
        else:
            idx = f - 3
            clawd_x, clawd_y = flight_positions[idx]
            draw_clawd(draw, clawd_x, clawd_y, 10, blink=(f in (3, 7)))

            for i, (px, py) in enumerate(flight_positions[:idx]):
                arc_x = px + 38
                arc_y = py + 30
                size = 4 if i == idx - 1 else 3
                draw.rectangle([arc_x - size, arc_y - size, arc_x + size, arc_y + size], fill=YELLOW if i % 2 == 0 else PINK)

            for i in range(3):
                sx = clawd_x - 18 - i * 10
                sy = clawd_y + 18 + i * 6
                draw.line([sx, sy, sx + 16, sy - 2], fill=LIGHT_BLUE, width=2 if i == 0 else 1)
            for dx, dy, color in [(-18, 6, YELLOW), (-28, 14, PINK), (-8, 24, LIGHT_BLUE)]:
                if f < 7:
                    draw.rectangle([clawd_x + dx, clawd_y + dy, clawd_x + dx + 4, clawd_y + dy + 4], fill=color)

            if f == 7:
                puff_cx, puff_cy = 352, 214
                for ox, oy, r in [(-18, 12, 12), (-4, 0, 14), (14, 10, 11), (26, 2, 9)]:
                    draw.ellipse([puff_cx + ox - r, puff_cy + oy - r, puff_cx + ox + r, puff_cy + oy + r], fill=WHITE, outline=GRAY)
                draw_text(draw, "*", 334, 172, color=YELLOW, scale=4)
                draw_text(draw, "*", 360, 180, color=PINK, scale=3)

        draw_loading_label(draw, "Catapulting", f)
        frames.append(img)
    return frames


def frames_discombobulating():
    """Clawd spinning/dizzy, spiral eyes, question marks flying."""
    frames = []
    import math
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # Clawd with tilt
        tilt_x = [0, 4, 6, 4, 0, -4][f]
        cx, cy = 130 + tilt_x, 155
        draw_clawd(draw, cx, cy, g)

        # Replace eyes with spirals
        for eye_gx in [1, 6]:
            ex = cx + eye_gx * g + g // 2
            ey = cy + g + g // 2
            # Simple spiral: concentric partial arcs
            for r in range(2, 7, 2):
                start = (f * 60) % 360
                draw.arc([ex - r, ey - r, ex + r, ey + r], start, start + 270, fill=WHITE, width=1)

        # Question marks orbiting
        num_q = 4
        orbit_r = 100
        for i in range(num_q):
            angle = math.radians((f * 30 + i * 90) % 360)
            qx = cx + 4 * g + int(orbit_r * math.cos(angle))
            qy = cy + 3 * g + int(orbit_r * math.sin(angle)) - 20
            draw_text(draw, "?", qx, qy, color=YELLOW, scale=4)

        # Stars/dizzy marks
        star_pos = [(cx - 20, cy - 10), (cx + 10 * g + 10, cy + g)]
        for i, (sx, sy) in enumerate(star_pos):
            if (f + i) % 2 == 0:
                draw_text(draw, "*", sx, sy, color=YELLOW, scale=3)

        draw_loading_label(draw, "Discombobulating", f)
        frames.append(img)
    return frames


def frames_combobulating():
    """Refined knot on left resolves into a tidy stack on the right."""
    frames = []
    loops = [
        (-26, -10, 22, 14, RED),
        (-8, -24, 20, 14, ORANGE),
        (8, -8, 24, 16, PURPLE),
        (-20, 10, 26, 16, CORAL),
        (10, 12, 20, 14, YELLOW),
    ]
    ribbons = [
        [(-28, -4), (-6, -20), (18, -2), (-2, 16), (24, 18)],
        [(-22, 14), (-6, 2), (12, 18), (30, -6)],
        [(-18, -18), (0, 8), (20, -16), (30, 8)],
    ]

    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # Clawd in center
        cx, cy = 145, 155
        draw_clawd(draw, cx, cy, g)

        # Tidy-looking knot bundle (left, shrinks as order takes over).
        tangle_cx, tangle_cy = 60, 190
        shrink = 1.0 - f * 0.14
        if shrink > 0.1:
            for ox, oy, rx, ry, color in loops:
                draw.ellipse([tangle_cx + int((ox - rx) * shrink), tangle_cy + int((oy - ry) * shrink),
                              tangle_cx + int((ox + rx) * shrink), tangle_cy + int((oy + ry) * shrink)],
                             outline=color, width=3)
            ribbon_colors = [DARK_BROWN, PURPLE, DARK_GRAY]
            for pts, color in zip(ribbons, ribbon_colors):
                scaled = [(tangle_cx + int(px * shrink), tangle_cy + int(py * shrink)) for px, py in pts]
                draw.line(scaled, fill=color, width=3)
            for dx, dy in [(-10, -2), (6, 8), (20, -10)]:
                draw.ellipse([tangle_cx + int((dx - 3) * shrink), tangle_cy + int((dy - 3) * shrink),
                              tangle_cx + int((dx + 3) * shrink), tangle_cy + int((dy + 3) * shrink)], fill=YELLOW)

        # Neat stack (right, grows)
        stack_x = 330
        stack_base = 270
        num_blocks = min(f + 1, 5)
        block_colors = [BLUE, GREEN, YELLOW, CORAL, PURPLE]
        for bi in range(num_blocks):
            by = stack_base - bi * 22
            draw.rectangle([stack_x, by - 18, stack_x + 50, by], fill=block_colors[bi % 5])
            draw.rectangle([stack_x, by - 18, stack_x + 50, by], outline=BLACK, width=1)
            draw.rectangle([stack_x + 4, by - 14, stack_x + 46, by - 11], fill=WHITE)

        # Arrow from left to right
        arrow_y = 200
        draw.line([100, arrow_y, 135, arrow_y], fill=GRAY, width=2)
        draw.polygon([(135, arrow_y - 5), (145, arrow_y), (135, arrow_y + 5)], fill=GRAY)
        draw.line([cx + 10 * g + 5, arrow_y, 320, arrow_y], fill=GRAY, width=2)
        draw.polygon([(320, arrow_y - 5), (330, arrow_y), (320, arrow_y + 5)], fill=GRAY)
        if f >= 4:
            draw_text(draw, "*", 312, 176, color=YELLOW, scale=3)

        draw_loading_label(draw, "Combobulating", f)
        frames.append(img)
    return frames


def frames_conjuring():
    """Clawd with top hat, magic wand with sparkles."""
    frames = []
    import math
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 80, 160
        draw_clawd(draw, cx, cy, g)

        # Top hat on ground beside Clawd (right side)
        hat_x = 270
        hat_y = 230
        # Brim
        draw.rectangle([hat_x - 15, hat_y, hat_x + 65, hat_y + 10], fill=BLACK)
        # Hat body
        draw.rectangle([hat_x, hat_y - 60, hat_x + 50, hat_y], fill=BLACK)
        # Hat band
        draw.rectangle([hat_x, hat_y - 20, hat_x + 50, hat_y - 14], fill=PURPLE)

        # Wand from Clawd's right arm
        wand_base_x = cx + 10 * g
        wand_base_y = cy + 2 * g
        wand_angle = [30, 50, 70, 50, 30, 10][f]
        wand_len = 55
        wand_dx = int(wand_len * math.cos(math.radians(wand_angle)))
        wand_dy = -int(wand_len * math.sin(math.radians(wand_angle)))
        wand_tip_x = wand_base_x + wand_dx
        wand_tip_y = wand_base_y + wand_dy
        draw.line([wand_base_x, wand_base_y, wand_tip_x, wand_tip_y], fill=WHITE, width=3)
        # Star at wand tip
        draw_text(draw, "*", wand_tip_x - 6, wand_tip_y - 12, color=YELLOW, scale=4)

        # Sparkles burst from hat
        sparkle_patterns = [
            [(0, -10), (20, -25), (-15, -20)],
            [(10, -30), (-10, -15), (25, -10)],
            [(-5, -35), (15, -20), (30, -30)],
            [(5, -15), (-20, -30), (20, -25)],
            [(-10, -25), (25, -15), (0, -35)],
            [(15, -10), (-15, -35), (10, -20)],
        ]
        for sx, sy in sparkle_patterns[f]:
            sparkle_x = hat_x + 25 + sx
            sparkle_y = hat_y + sy
            draw.rectangle([sparkle_x - 2, sparkle_y - 2, sparkle_x + 2, sparkle_y + 2], fill=YELLOW)
            draw.rectangle([sparkle_x - 1, sparkle_y - 5, sparkle_x + 1, sparkle_y + 5], fill=PURPLE)
            draw.rectangle([sparkle_x - 5, sparkle_y - 1, sparkle_x + 5, sparkle_y + 1], fill=PURPLE)

        draw_loading_label(draw, "Conjuring", f)
        frames.append(img)
    return frames


def frames_contemplating():
    """Clawd in thinker pose with animated thought dots."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # Slight head bob
        bob = [0, -1, -2, -1, 0, 1][f]
        cx, cy = 120, 180 + bob
        draw_clawd(draw, cx, cy, g)

        # Arm to chin — block from right arm area toward head
        chin_x = cx + 7 * g
        chin_y = cy + g  # chin area
        draw.rectangle([chin_x, chin_y, chin_x + g, chin_y + g + g // 2], fill=CORAL)

        # Thought bubble with "..." dots
        bubble_x = cx + 2 * g
        bubble_y = cy - 65
        draw_thought_bubble(draw, bubble_x, bubble_y, 80, 40)

        # Animated dots: appear one by one over frames
        num_dots = ((f % 6) // 2) + 1  # cycles 1,1,2,2,3,3
        dot_y = bubble_y + 20
        for d in range(num_dots):
            dot_x = bubble_x + 22 + d * 16
            draw.ellipse([dot_x, dot_y, dot_x + 7, dot_y + 7], fill=DARK_GRAY)

        draw_loading_label(draw, "Contemplating", f)
        frames.append(img)
    return frames


def frames_crunching():
    """Clawd as/next to a CPU chip, binary digits streaming."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # CPU chip (center-right)
        cpu_x, cpu_y = 200, 140
        cpu_w, cpu_h = 90, 90
        draw.rectangle([cpu_x, cpu_y, cpu_x + cpu_w, cpu_y + cpu_h], fill=DARK_GRAY)
        draw.rectangle([cpu_x + 8, cpu_y + 8, cpu_x + cpu_w - 8, cpu_y + cpu_h - 8], fill=(50, 50, 50))
        # Pins around edges
        for p in range(5):
            px = cpu_x + 12 + p * 16
            draw.rectangle([px, cpu_y - 8, px + 6, cpu_y], fill=GRAY)  # top
            draw.rectangle([px, cpu_y + cpu_h, px + 6, cpu_y + cpu_h + 8], fill=GRAY)  # bottom
        for p in range(5):
            py = cpu_y + 12 + p * 16
            draw.rectangle([cpu_x - 8, py, cpu_x, py + 6], fill=GRAY)  # left
            draw.rectangle([cpu_x + cpu_w, py, cpu_x + cpu_w + 8, py + 6], fill=GRAY)  # right

        # Clawd next to CPU (left)
        draw_clawd(draw, 30, 155, GRID)

        # Binary streams flowing in from left
        binary = "10110010"
        for row in range(3):
            by = cpu_y + 15 + row * 28
            for ci in range(6):
                bx = 170 - ci * 22 - (f * 12) % 22
                if bx < 160 and bx > 25:
                    ch = binary[(ci + row + f) % len(binary)]
                    draw_text(draw, ch, bx, by, color=GREEN, scale=3)

        # Sparks flying out right side
        spark_colors = [YELLOW, ORANGE, YELLOW]
        for si in range(3):
            sx = cpu_x + cpu_w + 15 + ((f * 10 + si * 18) % 60)
            sy = cpu_y + 20 + si * 25 + ((f + si) % 3) * 5
            sc = spark_colors[si % 3]
            draw.rectangle([sx, sy, sx + 4, sy + 4], fill=sc)

        draw_loading_label(draw, "Crunching", f)
        frames.append(img)
    return frames


def frames_cultivating():
    """Clawd with watering can, plant growing from ground."""
    frames = []
    total_frames = 12
    for f in range(total_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID - 1

        cx, cy = 22, 162
        draw_clawd(draw, cx, cy, g)

        # Ground
        ground_y = 295
        draw.rectangle([215, ground_y, 382, ground_y + 15], fill=BROWN)

        # Watering can (held by Clawd, extending right)
        can_x = cx + 10 * g + 9
        can_y = cy + 2 * g + 2
        # Can body
        draw.rectangle([can_x, can_y, can_x + 35, can_y + 25], fill=GRAY)
        # Spout
        draw.line([can_x + 35, can_y + 5, can_x + 55, can_y - 10], fill=GRAY, width=3)
        # Handle
        draw.arc([can_x + 5, can_y - 15, can_x + 30, can_y + 5], 180, 360, fill=GRAY, width=2)

        # Water drops
        for di in range(3):
            drop_x = can_x + 50 + di * 6
            drop_y = can_y - 5 + ((f * 8 + di * 10) % 40)
            if (f + di) % 2 == 0:
                draw.ellipse([drop_x, drop_y, drop_x + 4, drop_y + 6], fill=BLUE)

        # Plant growth stages (extends into a much taller bloom).
        plant_x = 320
        plant_base = ground_y
        growth = f / (total_frames - 1)
        stem_h = 8 + int(170 * growth)
        stem_w = 4 + int(2 * growth)
        draw.rectangle([plant_x, plant_base - stem_h, plant_x + stem_w, plant_base], fill=GREEN)

        if f >= 2:
            leaf_y = plant_base - int(stem_h * 0.35)
            leaf_span = 10 + int(16 * growth)
            draw.polygon([(plant_x, leaf_y), (plant_x - leaf_span, leaf_y - 8), (plant_x, leaf_y - 4)], fill=LIME)
            draw.polygon([(plant_x + stem_w, leaf_y + 4), (plant_x + stem_w + leaf_span, leaf_y - 4),
                           (plant_x + stem_w, leaf_y)], fill=LIME)
        if f >= 5:
            leaf_y2 = plant_base - int(stem_h * 0.62)
            leaf_span2 = 14 + int(22 * growth)
            draw.polygon([(plant_x, leaf_y2), (plant_x - leaf_span2, leaf_y2 - 10), (plant_x, leaf_y2 - 4)], fill=GREEN)
            draw.polygon([(plant_x + stem_w, leaf_y2 + 4), (plant_x + stem_w + leaf_span2, leaf_y2 - 6),
                           (plant_x + stem_w, leaf_y2)], fill=GREEN)
        if f >= 7:
            flower_y = plant_base - stem_h - 12
            flower_cx = plant_x + stem_w // 2 + 1
            petal_radius = 8 + int(20 * growth)
            petal_size = 5 + int(8 * growth)
            for angle_i in range(8):
                a = math.radians(angle_i * 45)
                px = flower_cx + int(petal_radius * math.cos(a))
                py = flower_y + int(petal_radius * math.sin(a))
                draw.ellipse([px - petal_size, py - petal_size,
                              px + petal_size, py + petal_size], fill=PINK)
            center_r = 5 + int(8 * growth)
            draw.ellipse([flower_cx - center_r, flower_y - center_r,
                          flower_cx + center_r, flower_y + center_r], fill=YELLOW)

        draw_loading_label(draw, "Cultivating", f)
        frames.append(img)
    return frames


def frames_deciphering():
    """Clawd with magnifying glass over scrambled text."""
    frames = []
    import random as _rng
    rng = _rng.Random(77)
    # Pre-generate scrambled chars
    scramble_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    scrambled_grid = []
    for row in range(4):
        row_chars = [scramble_chars[rng.randint(0, len(scramble_chars) - 1)] for _ in range(8)]
        scrambled_grid.append(row_chars)

    decoded_text = ["C", "o", "d", "e", "H", "e", "r", "e"]

    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 20, 160
        draw_clawd(draw, cx, cy, g)

        # Scrambled text block (right side)
        text_start_x = 220
        text_start_y = 130
        col_spacing = 20
        row_spacing = 28

        # Magnifying glass position shifts each frame
        lens_col = f % 6  # which column the lens is over (0-5, wraps)
        lens_x = text_start_x + lens_col * col_spacing + 4
        lens_y = text_start_y + 30

        # Draw text grid
        for row in range(4):
            for col in range(min(6, len(scrambled_grid[row]))):
                tx = text_start_x + col * col_spacing
                ty = text_start_y + row * row_spacing
                # Is this under the lens?
                under_lens = (col == lens_col or col == lens_col + 1) and (1 <= row <= 2)
                if under_lens:
                    ch = decoded_text[(row * 4 + col) % len(decoded_text)]
                    draw_text(draw, ch, tx, ty, color=GREEN, scale=3)
                else:
                    ch = scrambled_grid[row][col % len(scrambled_grid[row])]
                    if ch in FONT_GLYPHS:
                        draw_text(draw, ch, tx, ty, color=GRAY, scale=3)

        # Magnifying glass
        lens_r = 22
        # Glass circle
        draw.ellipse([lens_x - lens_r, lens_y - lens_r, lens_x + lens_r, lens_y + lens_r],
                      outline=DARK_BROWN, width=3)
        # Handle
        draw.line([lens_x + lens_r - 4, lens_y + lens_r - 4,
                   lens_x + lens_r + 20, lens_y + lens_r + 20], fill=DARK_BROWN, width=4)

        draw_loading_label(draw, "Deciphering", f)
        frames.append(img)
    return frames


def frames_cooking():
    """Clawd with chef hat, pan on stove, food flipping."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 30, 150
        draw_clawd(draw, cx, cy, g, blink=(f == 4), accessories=[("chef_hat", {"tall": True})])

        # Stove (right)
        stove_x, stove_y = 210, 220
        draw.rectangle([stove_x, stove_y, stove_x + 120, stove_y + 40], fill=DARK_GRAY)
        # Burner glow
        glow = [(255, 80, 20), (255, 120, 40), (255, 80, 20)][f % 3]
        draw.ellipse([stove_x + 35, stove_y - 8, stove_x + 85, stove_y + 8], fill=glow)

        # Pan
        pan_y = stove_y - 20
        pan_left = stove_x + 35
        pan_right = stove_x + 115
        draw.rectangle([pan_left, pan_y, pan_right, pan_y + 12], fill=DARK_GRAY)
        # Pan handle points toward Clawd and meets the right paw.
        handle_left = stove_x - 20
        handle_right = pan_left
        handle_top = pan_y + 2
        draw.rectangle([handle_left, handle_top, handle_right, handle_top + 8], fill=BROWN)
        draw.rectangle([handle_left - 2, handle_top - 1, handle_left + 10, handle_top + 11], fill=CORAL)

        # Flipping food
        flip_h = [0, -15, -30, -30, -15, 0][f]
        food_x = stove_x + 75
        food_y = pan_y - 5 + flip_h
        draw.ellipse([food_x - 12, food_y - 8, food_x + 12, food_y + 8], fill=YELLOW)
        draw.ellipse([food_x - 8, food_y - 5, food_x + 8, food_y + 5], fill=ORANGE)

        # Steam
        draw_steam(draw, stove_x + 70, pan_y - 20, f)

        draw_loading_label(draw, "Cooking", f)
        frames.append(img)
    return frames


def frames_crafting():
    """Clawd at workbench with hammer, assembling blocks."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 30, 155
        draw_clawd(draw, cx, cy, g)

        # Workbench
        bench_x, bench_y = 220, 260
        draw.rectangle([bench_x, bench_y, bench_x + 150, bench_y + 12], fill=BROWN)
        # Legs
        draw.rectangle([bench_x + 10, bench_y + 12, bench_x + 20, bench_y + 45], fill=DARK_BROWN)
        draw.rectangle([bench_x + 130, bench_y + 12, bench_x + 140, bench_y + 45], fill=DARK_BROWN)

        # Blocks being assembled
        block_colors = [BLUE, GREEN, YELLOW, CORAL, PURPLE]
        num_blocks = min(f + 1, 5)
        for bi in range(num_blocks):
            bx = bench_x + 20 + bi * 25
            by = bench_y - 18
            draw.rectangle([bx, by, bx + 20, by + 16], fill=block_colors[bi])
            draw.rectangle([bx, by, bx + 20, by + 16], outline=BLACK, width=1)

        # Hammer motion from Clawd
        hammer_angles = [0, -15, -30, -15, 0, 10]
        import math
        angle = math.radians(hammer_angles[f])
        hammer_x = cx + 10 * g + 10
        hammer_y = cy + 2 * g
        hx2 = hammer_x + int(40 * math.cos(angle))
        hy2 = hammer_y + int(40 * math.sin(angle))
        draw.line([hammer_x, hammer_y, hx2, hy2], fill=DARK_BROWN, width=3)
        # Hammer head
        draw.rectangle([hx2 - 6, hy2 - 8, hx2 + 6, hy2 + 4], fill=GRAY)

        # Sparkles on impact
        if f in [2, 3]:
            for sx, sy in [(hx2 + 10, hy2 - 10), (hx2 - 8, hy2 + 8), (hx2 + 15, hy2 + 5)]:
                draw.rectangle([sx, sy, sx + 3, sy + 3], fill=YELLOW)

        draw_loading_label(draw, "Crafting", f)
        frames.append(img)
    return frames


def frames_deliberating():
    """Clawd with scales of justice, weighing options."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 120, 180
        draw_clawd(draw, cx, cy, g, blink=(f == 3))

        # Scales above head
        scale_cx = cx + 4 * g
        scale_top = cy - 50
        # Central post
        draw.rectangle([scale_cx - 2, scale_top, scale_cx + 2, scale_top + 30], fill=DARK_BROWN)
        # Beam (tilts)
        tilt = [-6, -3, 0, 3, 6, 3][f]
        beam_l = (scale_cx - 55, scale_top + tilt)
        beam_r = (scale_cx + 55, scale_top - tilt)
        draw.line([beam_l, beam_r], fill=DARK_BROWN, width=3)
        # Left pan
        draw.arc([beam_l[0] - 18, beam_l[1] + 5, beam_l[0] + 18, beam_l[1] + 30],
                 0, 180, fill=GRAY, width=2)
        draw.ellipse([beam_l[0] - 15, beam_l[1] + 22, beam_l[0] + 15, beam_l[1] + 32], fill=GRAY)
        # Right pan
        draw.arc([beam_r[0] - 18, beam_r[1] + 5, beam_r[0] + 18, beam_r[1] + 30],
                 0, 180, fill=GRAY, width=2)
        draw.ellipse([beam_r[0] - 15, beam_r[1] + 22, beam_r[0] + 15, beam_r[1] + 32], fill=GRAY)

        # Items in pans
        draw.rectangle([beam_l[0] - 6, beam_l[1] + 24, beam_l[0] + 6, beam_l[1] + 30], fill=BLUE)
        draw.rectangle([beam_r[0] - 6, beam_r[1] + 24, beam_r[0] + 6, beam_r[1] + 30], fill=GREEN)

        draw_loading_label(draw, "Deliberating", f)
        frames.append(img)
    return frames


def frames_divining():
    """Clawd gazing into a crystal ball with swirling mist."""
    frames = []
    import math
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 30, 155
        draw_clawd(draw, cx, cy, g)

        # Crystal ball (right)
        ball_cx, ball_cy = 300, 200
        ball_r = 45
        # Base
        draw.rectangle([ball_cx - 20, ball_cy + ball_r - 5, ball_cx + 20, ball_cy + ball_r + 12],
                       fill=DARK_GRAY)
        draw.rectangle([ball_cx - 28, ball_cy + ball_r + 12, ball_cx + 28, ball_cy + ball_r + 20],
                       fill=GRAY)
        # Ball outline
        draw.ellipse([ball_cx - ball_r, ball_cy - ball_r, ball_cx + ball_r, ball_cy + ball_r],
                     fill=(180, 160, 220))
        # Inner glow
        draw.ellipse([ball_cx - ball_r + 8, ball_cy - ball_r + 8,
                      ball_cx + ball_r - 8, ball_cy + ball_r - 8], fill=(200, 180, 240))
        # Swirling sparkles inside
        for i in range(5):
            angle = math.radians((f * 40 + i * 72) % 360)
            r = 20 + (i % 2) * 10
            sx = ball_cx + int(r * math.cos(angle))
            sy = ball_cy + int(r * math.sin(angle))
            sc = [YELLOW, WHITE, PURPLE, YELLOW, WHITE][i]
            draw.rectangle([sx - 2, sy - 2, sx + 2, sy + 2], fill=sc)

        # Sparkle highlight
        draw.ellipse([ball_cx - 15, ball_cy - 25, ball_cx - 8, ball_cy - 18], fill=WHITE)

        draw_loading_label(draw, "Divining", f)
        frames.append(img)
    return frames


def frames_elucidating():
    """Clawd with lightbulb above, illuminating an open book."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 120, 175
        draw_clawd(draw, cx, cy, g)

        # Lightbulb above head
        bulb_cx = cx + 4 * g
        bulb_y = cy - 45
        pulse = 3 if f % 2 == 0 else 0
        draw.ellipse([bulb_cx - 12 - pulse, bulb_y - 16 - pulse,
                      bulb_cx + 12 + pulse, bulb_y + 10 + pulse], fill=YELLOW)
        draw.rectangle([bulb_cx - 5, bulb_y + 10, bulb_cx + 5, bulb_y + 18], fill=GRAY)
        # Rays
        import math
        for i in range(6):
            angle = math.radians(i * 60 + f * 15)
            rx = bulb_cx + int(22 * math.cos(angle))
            ry = bulb_y - 3 + int(22 * math.sin(angle))
            draw.line([bulb_cx, bulb_y - 3, rx, ry], fill=YELLOW, width=1)

        # Open book below / to the side
        book_x, book_y = 250, 230
        # Left page
        draw.rectangle([book_x, book_y, book_x + 50, book_y + 60], fill=WHITE)
        # Right page
        draw.rectangle([book_x + 52, book_y, book_x + 102, book_y + 60], fill=WHITE)
        # Spine
        draw.rectangle([book_x + 49, book_y - 3, book_x + 53, book_y + 63], fill=DARK_BROWN)
        # Text lines on pages
        for line in range(4):
            ly = book_y + 10 + line * 12
            draw.rectangle([book_x + 5, ly, book_x + 45, ly + 3], fill=GRAY)
            draw.rectangle([book_x + 57, ly, book_x + 97, ly + 3], fill=GRAY)

        draw_loading_label(draw, "Elucidating", f)
        frames.append(img)
    return frames


def frames_embellishing():
    """Clawd turning a plain plaque into an ornate decorated piece."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 28, 160
        draw_clawd(draw, cx, cy, g)

        # Plaque on a stand (right)
        plaque_x, plaque_y = 248, 108
        pw, ph = 108, 126
        draw.rectangle([plaque_x + 48, plaque_y + ph, plaque_x + 60, plaque_y + ph + 52], fill=DARK_BROWN)
        draw.rectangle([plaque_x + 18, plaque_y + ph + 52, plaque_x + 90, plaque_y + ph + 62], fill=BROWN)
        draw.rectangle([plaque_x, plaque_y, plaque_x + pw, plaque_y + ph], fill=(252, 244, 226))
        draw.rectangle([plaque_x, plaque_y, plaque_x + pw, plaque_y + ph], outline=BROWN, width=2)

        if f >= 1:
            draw.rectangle([plaque_x + 10, plaque_y + 10, plaque_x + pw - 10, plaque_y + ph - 10], outline=YELLOW, width=3)
        if f >= 2:
            corner_specs = [
                (plaque_x + 16, plaque_y + 16),
                (plaque_x + pw - 26, plaque_y + 16),
                (plaque_x + 16, plaque_y + ph - 26),
                (plaque_x + pw - 26, plaque_y + ph - 26),
            ]
            for ox, oy in corner_specs:
                draw.ellipse([ox, oy, ox + 10, oy + 10], fill=PINK)
                draw.rectangle([ox + 4, oy - 4, ox + 6, oy + 14], fill=PINK)
                draw.rectangle([ox - 4, oy + 4, ox + 14, oy + 6], fill=PINK)
        if f >= 3:
            gem_cx = plaque_x + pw // 2
            gem_cy = plaque_y + ph // 2 - 6
            draw.polygon([(gem_cx, gem_cy - 16), (gem_cx + 18, gem_cy),
                          (gem_cx, gem_cy + 16), (gem_cx - 18, gem_cy)], fill=TEAL)
            draw.ellipse([gem_cx - 8, gem_cy - 8, gem_cx + 8, gem_cy + 8], fill=WHITE)
        if f >= 4:
            ribbon_y = plaque_y + ph - 36
            draw.rectangle([plaque_x + 18, ribbon_y, plaque_x + pw - 18, ribbon_y + 10], fill=PURPLE)
            draw.polygon([(plaque_x + 30, ribbon_y + 10), (plaque_x + 18, ribbon_y + 28), (plaque_x + 42, ribbon_y + 18)], fill=PURPLE)
            draw.polygon([(plaque_x + pw - 30, ribbon_y + 10), (plaque_x + pw - 18, ribbon_y + 28), (plaque_x + pw - 42, ribbon_y + 18)], fill=PURPLE)
        if f >= 5:
            sparkles = [(plaque_x + 26, plaque_y + 22), (plaque_x + 82, plaque_y + 28), (plaque_x + 88, plaque_y + 94)]
            for sx, sy in sparkles:
                draw_text(draw, "*", sx, sy, color=YELLOW, scale=3)

        # Brush and active embellishing motion from Clawd toward the plaque.
        brush_x = cx + 10 * g + 4
        brush_y = cy + 2 * g + 6
        tip_targets = [
            (plaque_x + 22, plaque_y + 24),
            (plaque_x + 84, plaque_y + 24),
            (plaque_x + 22, plaque_y + 98),
            (plaque_x + 84, plaque_y + 98),
            (plaque_x + pw // 2, plaque_y + ph - 28),
            (plaque_x + pw // 2 + 12, plaque_y + ph // 2),
        ]
        tip_x, tip_y = tip_targets[f]
        draw.line([brush_x, brush_y, tip_x, tip_y], fill=BROWN, width=2)
        draw.rectangle([tip_x - 4, tip_y - 4, tip_x + 4, tip_y + 4], fill=PINK)
        if f >= 2:
            draw_text(draw, "*", tip_x + 6, tip_y - 8, color=YELLOW, scale=2)

        draw_loading_label(draw, "Embellishing", f)
        frames.append(img)
    return frames


def frames_enchanting():
    """Clawd with magic wand, stars and sparkles spiral around."""
    frames = []
    import math
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 120, 175
        draw_clawd(draw, cx, cy, g)

        # Wand held up
        wand_x = cx + 8 * g
        wand_y = cy - 10
        draw.line([wand_x, cy + 2 * g, wand_x, wand_y], fill=WHITE, width=3)
        # Star at tip
        draw_text(draw, "*", wand_x - 8, wand_y - 18, color=YELLOW, scale=5)

        # Sparkle spiral
        num_sparkles = 8
        for i in range(num_sparkles):
            angle = math.radians((f * 30 + i * 45) % 360)
            r = 40 + i * 8
            sx = cx + 4 * g + int(r * math.cos(angle))
            sy = cy + 2 * g + int(r * math.sin(angle)) - 30
            if 10 < sx < 390 and 10 < sy < 340:
                colors = [YELLOW, PINK, PURPLE, WHITE, YELLOW, PINK, PURPLE, WHITE]
                s = 3 + (i % 2)
                draw.rectangle([sx - s, sy - s, sx + s, sy + s], fill=colors[i])

        draw_loading_label(draw, "Enchanting", f)
        frames.append(img)
    return frames


def frames_envisioning():
    """Clawd with thought bubble showing a blueprint/plan."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 50, 190
        draw_clawd(draw, cx, cy, g)

        # Large thought bubble
        bx, by = 200, 60
        bw, bh = 160, 110
        draw.ellipse([bx, by, bx + bw, by + bh], fill=WHITE)
        draw.ellipse([bx - 15, by + bh // 4, bx + bw // 3, by + bh - bh // 5], fill=WHITE)
        draw.ellipse([bx + bw - bw // 3, by + bh // 4, bx + bw + 15, by + bh - bh // 5], fill=WHITE)
        # Connector dots
        draw.ellipse([bx - 10, by + bh + 5, bx + 8, by + bh + 20], fill=WHITE)
        draw.ellipse([bx - 25, by + bh + 22, bx - 12, by + bh + 33], fill=WHITE)

        # Blueprint grid inside bubble (appears progressively)
        grid_x, grid_y = bx + 25, by + 20
        # Draw grid lines
        for gx in range(0, 120, 20):
            draw.line([grid_x + gx, grid_y, grid_x + gx, grid_y + 65], fill=LIGHT_BLUE, width=1)
        for gy_off in range(0, 70, 15):
            draw.line([grid_x, grid_y + gy_off, grid_x + 110, grid_y + gy_off],
                      fill=LIGHT_BLUE, width=1)

        # Elements appearing on blueprint
        if f >= 1:
            draw.rectangle([grid_x + 5, grid_y + 5, grid_x + 35, grid_y + 25], outline=TEAL, width=2)
        if f >= 2:
            draw.rectangle([grid_x + 45, grid_y + 5, grid_x + 85, grid_y + 25], outline=TEAL, width=2)
        if f >= 3:
            draw.line([grid_x + 35, grid_y + 15, grid_x + 45, grid_y + 15], fill=TEAL, width=2)
        if f >= 4:
            draw.rectangle([grid_x + 20, grid_y + 35, grid_x + 70, grid_y + 55],
                           outline=GREEN, width=2)
        if f >= 5:
            draw.line([grid_x + 45, grid_y + 25, grid_x + 45, grid_y + 35], fill=TEAL, width=2)
            draw_text(draw, "*", grid_x + 90, grid_y + 8, color=YELLOW, scale=3)

        draw_loading_label(draw, "Envisioning", f)
        frames.append(img)
    return frames


def frames_fiddle_faddling():
    """Clawd juggling small trinkets, some falling."""
    frames = []
    import math
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 120, 175
        draw_clawd(draw, cx, cy, g)

        # Trinkets in an arc above Clawd (juggling)
        trinket_colors = [RED, BLUE, GREEN, YELLOW, PURPLE]
        num_trinkets = 5
        arc_cx = cx + 4 * g
        arc_cy = cy - 20
        for i in range(num_trinkets):
            angle = math.radians(180 + (i * 36) + f * 20)
            tr = 60
            tx = arc_cx + int(tr * math.cos(angle))
            ty = arc_cy + int(tr * math.sin(angle) * 0.6) - 20
            s = 5 + (i % 2) * 2
            if ty < cy:  # only draw above
                draw.rectangle([tx - s, ty - s, tx + s, ty + s], fill=trinket_colors[i])

        # Hands up gesture — blocks above arms
        draw.rectangle([cx - 2 * g, cy + g, cx - 2 * g + g, cy + g + g], fill=CORAL)
        draw.rectangle([cx + 9 * g, cy + g, cx + 9 * g + g, cy + g + g], fill=CORAL)

        draw_loading_label(draw, "Fiddle-faddling", f)
        frames.append(img)
    return frames


def frames_finagling():
    """Clawd with wrench and puzzle pieces clicking together."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 30, 160
        draw_clawd(draw, cx, cy, g)

        # Two puzzle pieces coming together
        gap = max(0, (5 - f) * 8)  # pieces close over frames
        # Left piece
        lp_x = 230 - gap
        lp_y = 170
        draw.rectangle([lp_x, lp_y, lp_x + 40, lp_y + 40], fill=BLUE)
        draw.rectangle([lp_x + 35, lp_y + 12, lp_x + 48, lp_y + 28], fill=BLUE)  # tab

        # Right piece
        rp_x = 280 + gap
        rp_y = 170
        draw.rectangle([rp_x, rp_y, rp_x + 40, rp_y + 40], fill=GREEN)
        draw.rectangle([rp_x - 8, rp_y + 12, rp_x + 5, rp_y + 28], fill=GREEN)  # socket

        # Click sparkle when pieces meet
        if f >= 4:
            spark_x = (lp_x + 48 + rp_x) // 2
            spark_y = lp_y + 20
            draw_text(draw, "*", spark_x - 8, spark_y - 12, color=YELLOW, scale=4)

        # Wrench extending from Clawd
        wrench_x = cx + 10 * g + 5
        wrench_y = cy + 2 * g + g // 2
        draw.line([wrench_x, wrench_y, wrench_x + 30, wrench_y - 15], fill=GRAY, width=3)
        draw.ellipse([wrench_x + 25, wrench_y - 25, wrench_x + 40, wrench_y - 10], outline=GRAY, width=2)

        draw_loading_label(draw, "Finagling", f)
        frames.append(img)
    return frames


def frames_flibbertigibbeting():
    """Clawd with speech bubbles rapidly appearing."""
    frames = []
    chatter_pairs = [
        ("§$%", "&?!"),
        ("#@%", "§&!"),
        ("$?&", "@#%"),
        ("§@!", "%$?"),
        ("#§&", "?!$"),
        ("@%§", "&#!"),
    ]
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # Clawd talking (mouth animation via blink substitute)
        cx, cy = 60, 185
        draw_clawd(draw, cx, cy, g, blink=(f % 2 == 0))

        # Multiple speech bubbles appearing rapidly
        bubbles = [
            (200, 80, 80, 35),
            (260, 45, 90, 30),
            (180, 140, 70, 30),
            (300, 100, 65, 28),
            (240, 165, 75, 32),
            (310, 150, 60, 25),
        ]
        for i, (bx, by, bw, bh) in enumerate(bubbles):
            if i <= f:
                col = (255, 255, 255)
                draw.ellipse([bx, by, bx + bw, by + bh], fill=col)
                top_text, bottom_text = chatter_pairs[(i + f) % len(chatter_pairs)]
                text_scale = 2 if bw < 75 else 3
                draw_text(draw, top_text, bx + 11, by + 6, color=DARK_GRAY, scale=text_scale)
                draw_text(draw, bottom_text, bx + 15, by + 16, color=GRAY, scale=text_scale)
                # Pointer toward Clawd
                draw.polygon([(bx - 4, by + bh // 2),
                              (bx + 8, by + bh // 2 - 5),
                              (bx + 8, by + bh // 2 + 5)], fill=col)

        draw_loading_label(draw, "Flibbertigibbeting", f)
        frames.append(img)
    return frames


def frames_flowing():
    """Clawd meditating with flowing water/wave patterns."""
    frames = []
    import math
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 120, 155
        draw_clawd(draw, cx, cy, g)

        # Flowing wave lines around Clawd
        wave_colors = [BLUE, LIGHT_BLUE, TEAL]
        for wi, wc in enumerate(wave_colors):
            base_y = 120 + wi * 100
            for x in range(0, CANVAS, 4):
                wy = base_y + int(15 * math.sin((x + f * 20 + wi * 40) * 0.03))
                draw.rectangle([x, wy, x + 3, wy + 3], fill=wc)

        # Re-draw Clawd on top
        draw_clawd(draw, cx, cy, g)

        # Zen circle above
        zen_phase = f * 60
        draw.arc([cx + 2 * g, cy - 55, cx + 6 * g, cy - 15],
                 zen_phase, zen_phase + 300, fill=TEAL, width=2)

        draw_loading_label(draw, "Flowing", f)
        frames.append(img)
    return frames


def frames_forging():
    """Clawd swinging hammer on anvil with sparks."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 20, 155
        draw_clawd(draw, cx, cy, g)

        # Anvil (larger and closer to the hammer impact).
        anvil_x, anvil_y = 245, 242
        draw.rectangle([anvil_x, anvil_y, anvil_x + 110, anvil_y + 38], fill=DARK_GRAY)
        draw.rectangle([anvil_x - 14, anvil_y - 10, anvil_x + 124, anvil_y + 8], fill=GRAY)
        draw.polygon([(anvil_x - 14, anvil_y - 6), (anvil_x - 42, anvil_y + 6),
                       (anvil_x - 14, anvil_y + 6)], fill=GRAY)
        draw.rectangle([anvil_x + 24, anvil_y + 38, anvil_x + 86, anvil_y + 60], fill=DARK_GRAY)

        # Glowing hot metal on anvil
        glow = [(230, 80, 30), (255, 120, 40), (255, 160, 60)][f % 3]
        impact_x = anvil_x + 52
        impact_y = anvil_y - 16
        draw.rectangle([impact_x - 26, impact_y, impact_x + 26, impact_y + 10], fill=glow)

        # Hammer: Clawd holds the handle end and swings into the anvil.
        hand_x = cx + 10 * g - 2
        hand_y = cy + 2 * g + g // 2
        head_x = impact_x + [24, 16, 8, 0, 10, 20][f]
        head_y = impact_y - [54, 38, 20, 4, 28, 44][f]
        draw.line([hand_x, hand_y, head_x, head_y], fill=BROWN, width=7)
        draw.rectangle([head_x - 18, head_y - 10, head_x + 18, head_y + 10], fill=DARK_GRAY)

        # Sparks when hammer is down
        if f in [0, 3, 4, 5]:
            rng = random.Random(f * 7)
            for _ in range(7):
                sx = impact_x + rng.randint(-28, 36)
                sy = impact_y + rng.randint(-24, 10)
                sc = [YELLOW, ORANGE, RED][rng.randint(0, 2)]
                draw.rectangle([sx, sy, sx + 3, sy + 3], fill=sc)

        draw_loading_label(draw, "Forging", f)
        frames.append(img)
    return frames


def frames_frolicking():
    """Clawd jumping happily, flowers and butterflies around."""
    frames = []
    import math
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # Clawd bouncing
        bounce = [0, -10, -20, -20, -10, 0][f]
        cx, cy = 130, 170 + bounce
        draw_clawd(draw, cx, cy, g)

        # Ground with flowers
        ground_y = 305
        draw.rectangle([20, ground_y, 380, ground_y + 10], fill=GREEN)

        # Flowers
        flower_positions = [(50, ground_y - 15), (100, ground_y - 20),
                           (280, ground_y - 18), (340, ground_y - 12)]
        for i, (fx, fy) in enumerate(flower_positions):
            # Stem
            draw.rectangle([fx, fy, fx + 2, ground_y], fill=GREEN)
            # Petals
            fc = [PINK, YELLOW, RED, PURPLE][i]
            draw.ellipse([fx - 5, fy - 5, fx + 7, fy + 5], fill=fc)
            draw.ellipse([fx - 3, fy - 3, fx + 5, fy + 3], fill=YELLOW)

        # Butterflies
        for i in range(2):
            angle = math.radians((f * 30 + i * 180) % 360)
            bx = 200 + int(80 * math.cos(angle)) + i * 50
            by = 80 + int(30 * math.sin(angle * 2))
            wing_open = f % 2 == i % 2
            bc = [PINK, LIGHT_BLUE][i]
            if wing_open:
                draw.polygon([(bx, by), (bx - 8, by - 6), (bx - 4, by + 4)], fill=bc)
                draw.polygon([(bx, by), (bx + 8, by - 6), (bx + 4, by + 4)], fill=bc)
            else:
                draw.rectangle([bx - 1, by - 5, bx + 1, by + 3], fill=bc)
            draw.rectangle([bx - 1, by - 1, bx + 1, by + 1], fill=BLACK)

        draw_loading_label(draw, "Frolicking", f)
        frames.append(img)
    return frames


def frames_germinating():
    """Seed underground sprouting upward through soil."""
    frames = []
    total_frames = 12
    for f in range(total_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        # Clawd watching from left
        cx, cy = 20, 160
        draw_clawd(draw, cx, cy, g)

        # Ground/soil
        soil_y = 260
        draw.rectangle([180, soil_y, 380, soil_y + 80], fill=BROWN)
        draw.rectangle([180, soil_y, 380, soil_y + 8], fill=DARK_BROWN)

        # Sun stays present throughout the animation.
        sun_x, sun_y = 366, 34
        sun_glow = 24 + (f % 3)
        draw.ellipse([sun_x - sun_glow, sun_y - sun_glow, sun_x + sun_glow, sun_y + sun_glow], fill=YELLOW)
        for angle in range(0, 360, 45):
            ray_dx = int(34 * math.cos(math.radians(angle)))
            ray_dy = int(34 * math.sin(math.radians(angle)))
            draw.line([sun_x, sun_y, sun_x + ray_dx, sun_y + ray_dy], fill=YELLOW, width=2)

        # Seed / sprout (center of soil)
        seed_x = 286
        seed_rects = [
            (seed_x - 6, soil_y + 25, seed_x + 6, soil_y + 37),
            (seed_x - 8, soil_y + 24, seed_x + 8, soil_y + 38),
            (seed_x - 8, soil_y + 24, seed_x + 8, soil_y + 38),
        ]

        if f <= 2:
            sx0, sy0, sx1, sy1 = seed_rects[min(f, 2)]
            draw.ellipse([sx0, sy0, sx1, sy1], fill=DARK_BROWN)
            if f == 2:
                draw.line([seed_x, soil_y + 24, seed_x, soil_y + 16], fill=WHITE, width=2)

        if f >= 3:
            draw.ellipse([seed_x - 8, soil_y + 24, seed_x + 8, soil_y + 38], fill=DARK_BROWN)
            draw.line([seed_x, soil_y + 31, seed_x, soil_y + 48], fill=DARK_BROWN, width=3)

        stem_tops = {
            4: soil_y + 18,
            5: soil_y + 4,
            6: soil_y - 18,
            7: soil_y - 42,
            8: soil_y - 62,
            9: soil_y - 82,
            10: soil_y - 102,
            11: soil_y - 118,
        }
        if f >= 4:
            stem_top = stem_tops[f]
            draw.rectangle([seed_x - 3, stem_top, seed_x + 3, soil_y + 30], fill=GREEN)
            if f >= 6:
                leaf_y = stem_top + 22
                leaf_span = 14 + max(0, (f - 6) * 2)
                draw.polygon([(seed_x, leaf_y), (seed_x - leaf_span, leaf_y - 10),
                               (seed_x, leaf_y - 4)], fill=LIME)
            if f >= 8:
                leaf_y2 = stem_top + 38
                leaf_span2 = 14 + (f - 8) * 3
                draw.polygon([(seed_x + 2, leaf_y2 + 6), (seed_x + 2 + leaf_span2, leaf_y2 - 4),
                               (seed_x + 2, leaf_y2)], fill=LIME)
            if f >= 10:
                top_leaf_y = stem_top + 12
                draw.polygon([(seed_x, top_leaf_y), (seed_x - 12, top_leaf_y - 9),
                               (seed_x + 2, top_leaf_y - 2)], fill=GREEN)
                draw.polygon([(seed_x, top_leaf_y + 10), (seed_x + 13, top_leaf_y + 1),
                               (seed_x + 2, top_leaf_y + 4)], fill=GREEN)

        draw_loading_label(draw, "Germinating", f)
        frames.append(img)
    return frames


def frames_hashing():
    """Clawd chopping data, hash symbols and bits flying."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 30, 160
        draw_clawd(draw, cx, cy, g)

        # Cutting board (right)
        board_x, board_y = 230, 250
        draw.rectangle([board_x, board_y, board_x + 130, board_y + 15], fill=BROWN)

        # Data block being chopped
        block_w = max(5, 50 - f * 8)
        draw.rectangle([board_x + 20, board_y - 20, board_x + 20 + block_w, board_y],
                       fill=BLUE)

        # Chopped bits flying
        num_bits = min(f + 1, 5)
        for bi in range(num_bits):
            bx = board_x + 80 + bi * 18 + f * 3
            by = board_y - 15 - ((f + bi) % 3) * 12
            draw.rectangle([bx, by, bx + 10, by + 10], fill=GREEN)
            # Hash symbol on the bit
            draw_text(draw, "#", bx + 1, by + 1, color=WHITE, scale=2)

        # Cleaver motion
        cleaver_y = board_y - 25 + [-30, -15, 0, 0, -15, -30][f]
        cleaver_x = board_x + 55
        draw.rectangle([cleaver_x, cleaver_y, cleaver_x + 4, cleaver_y + 25], fill=BROWN)
        draw.polygon([(cleaver_x - 12, cleaver_y), (cleaver_x + 4, cleaver_y),
                       (cleaver_x + 4, cleaver_y + 22), (cleaver_x - 12, cleaver_y + 16)],
                      fill=GRAY)

        draw_loading_label(draw, "Hashing", f)
        frames.append(img)
    return frames


def frames_hatching():
    """Three oversized eggs hatch three baby Clawds with slight offsets."""
    frames = []
    hatch_starts = [2, 3, 2]
    num_frames = 10
    wobble_x = [0, -3, 0, -2, 0, 1, 0, -1, 0, 0]
    wobble_x_r = [0, 3, 0, 2, 0, -1, 0, 1, 0, 0]
    center_wobble = [0, 0, -2, 0, 2, 0, -1, 1, 0, 0]
    bounce_pattern = [0, -10, 0, -8, 0]
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        egg_specs = [
            (98 + wobble_x[f], 214, 72, 98),
            (200 + center_wobble[f], 206, 82, 112),
            (302 + wobble_x_r[f], 214, 72, 98),
        ]

        for i, (egg_cx, egg_cy, egg_w, egg_h) in enumerate(egg_specs):
            start = hatch_starts[i]
            if f < start:
                draw.ellipse([egg_cx - egg_w//2, egg_cy - egg_h//2,
                              egg_cx + egg_w//2, egg_cy + egg_h//2], fill=WHITE, outline=GRAY)
                if f >= 1:
                    draw.line([egg_cx - 6, egg_cy - 14, egg_cx + 8, egg_cy + 3], fill=GRAY, width=2)
                    draw.line([egg_cx + 4, egg_cy - 20, egg_cx - 5, egg_cy - 4], fill=GRAY, width=2)
            elif f == start:
                draw.ellipse([egg_cx - egg_w//2, egg_cy - egg_h//2,
                              egg_cx + egg_w//2, egg_cy + egg_h//2], fill=WHITE, outline=GRAY)
                draw.line([egg_cx - 10, egg_cy - 18, egg_cx + 10, egg_cy + 4], fill=GRAY, width=2)
                draw.line([egg_cx + 10, egg_cy - 20, egg_cx - 8, egg_cy - 2], fill=GRAY, width=2)
                draw.line([egg_cx - 2, egg_cy - 24, egg_cx + 2, egg_cy + 10], fill=GRAY, width=2)
            else:
                rel = f - start
                rise = min(18, rel * 9)
                extra_bounce = 0
                if rel >= 3:
                    extra_bounce = bounce_pattern[min(rel - 3, len(bounce_pattern) - 1)]
                # Bottom shell
                draw.ellipse([egg_cx - egg_w//2, egg_cy + 8, egg_cx + egg_w//2, egg_cy + egg_h//2], fill=WHITE, outline=GRAY)
                for jx in range(egg_cx - egg_w//2 + 6, egg_cx + egg_w//2 - 12, 10):
                    draw.polygon([(jx, egg_cy + 8), (jx + 5, egg_cy - 8), (jx + 10, egg_cy + 8)], fill=WHITE, outline=GRAY)
                # Top shell halves
                cap_lift = rel * 10
                draw.polygon([(egg_cx - 30, egg_cy - 22 - cap_lift), (egg_cx - 10, egg_cy - 40 - cap_lift),
                              (egg_cx + 2, egg_cy - 10 - cap_lift)], fill=WHITE, outline=GRAY)
                draw.polygon([(egg_cx + 12, egg_cy - 18 - cap_lift), (egg_cx + 34, egg_cy - 32 - cap_lift),
                              (egg_cx + 20, egg_cy - 2 - cap_lift)], fill=WHITE, outline=GRAY)
                baby_grid = 5
                baby_x = egg_cx - 4 * baby_grid
                baby_y = egg_cy - 10 - rise + extra_bounce
                draw_clawd(draw, baby_x, baby_y, grid=baby_grid, blink=(f == start + 1 or rel == 5))
                for sx, sy in [(egg_cx - 26, egg_cy - 40 - cap_lift // 2), (egg_cx + 18, egg_cy - 34 - cap_lift // 3)]:
                    draw.polygon([(sx, sy), (sx + 10, sy - 8), (sx + 15, sy + 4)], fill=WHITE, outline=GRAY)

        draw_loading_label(draw, "Hatching", f)
        frames.append(img)
    return frames


def frames_recombobulating():
    """Clawd's pixels reassembling, with a longer final settle."""
    frames = []
    num_frames = 8
    scatter_levels = [50, 40, 28, 18, 10, 4, 0, 0]
    settle_offsets = [0, 0, 0, 0, 0, -2, 0, -1]

    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        cx, cy = 130, 170 + settle_offsets[f]
        scatter = scatter_levels[f]
        rng = random.Random(42)

        def shifted_rect(x1, y1, x2, y2, color):
            ox2 = rng.randint(-scatter, scatter) if scatter else 0
            oy2 = rng.randint(-scatter, scatter) if scatter else 0
            draw.rectangle([x1 + ox2, y1 + oy2, x2 + ox2, y2 + oy2], fill=color)

        for gx2 in range(8):
            for gy2 in range(2):
                shifted_rect(cx + gx2*g, cy + gy2*g, cx + (gx2+1)*g - 1, cy + (gy2+1)*g - 1, CORAL)
        if scatter <= 10:
            eye_y = cy + g + (g // 2 if f == 6 else 0)
            if f == 6:
                draw.rectangle([cx + 1*g, eye_y, cx + 2*g - 1, eye_y + 2], fill=BLACK)
                draw.rectangle([cx + 6*g, eye_y, cx + 7*g - 1, eye_y + 2], fill=BLACK)
            else:
                draw.rectangle([cx + 1*g, cy + 1*g, cx + 2*g - 1, cy + 2*g - 1], fill=BLACK)
                draw.rectangle([cx + 6*g, cy + 1*g, cx + 7*g - 1, cy + 2*g - 1], fill=BLACK)
        for gx2 in range(-2, 10):
            for gy2 in range(2, 4):
                shifted_rect(cx + gx2*g, cy + gy2*g, cx + (gx2+1)*g - 1, cy + (gy2+1)*g - 1, CORAL)
        for gx2 in range(8):
            for gy2 in range(4, 6):
                shifted_rect(cx + gx2*g, cy + gy2*g, cx + (gx2+1)*g - 1, cy + (gy2+1)*g - 1, CORAL)
        for lc in [0, 2, 5, 7]:
            for gy2 in range(6, 8):
                shifted_rect(cx + lc*g, cy + gy2*g, cx + (lc+1)*g - 1, cy + (gy2+1)*g - 1, CORAL)

        if f >= 4:
            sparkle_sets = [
                [(cx - 26, cy + 6), (cx + 146, cy + 18), (cx + 54, cy - 24)],
                [(cx - 16, cy - 10), (cx + 132, cy + 12), (cx + 80, cy + 92)],
                [(cx - 8, cy + 28), (cx + 150, cy - 6), (cx + 94, cy + 82)],
                [(cx - 18, cy + 16), (cx + 136, cy + 6), (cx + 68, cy - 20)],
            ]
            for sx, sy in sparkle_sets[min(f - 4, len(sparkle_sets) - 1)]:
                draw_text(draw, "*", sx, sy, color=YELLOW, scale=3)

        draw_loading_label(draw, "Recombobulating", f)
        frames.append(img)
    return frames


def frames_herding():
    """Clawd with shepherd staff, small blocks/dots moving like sheep."""
    frames = []
    import math
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 30, 165
        draw_clawd(draw, cx, cy, g)

        # Shepherd crook extending from Clawd
        crook_x = cx + 10 * g + 5
        crook_y = cy
        draw.rectangle([crook_x, crook_y, crook_x + 3, crook_y + g * 4], fill=BROWN)
        draw.arc([crook_x - 8, crook_y - 15, crook_x + 14, crook_y + 8],
                 180, 360, fill=BROWN, width=2)

        # "Sheep" (small white blocks with legs)
        sheep_positions = [
            (230 + int(math.sin(f * 0.8) * 15), 250),
            (270 + int(math.sin(f * 0.8 + 1) * 12), 260),
            (310 + int(math.sin(f * 0.8 + 2) * 18), 245),
            (260 + int(math.sin(f * 0.8 + 3) * 10), 270),
            (340 + int(math.sin(f * 0.8 + 4) * 14), 255),
        ]
        for i, (sx, sy) in enumerate(sheep_positions):
            # Body
            draw.rectangle([sx, sy, sx + 18, sy + 12], fill=WHITE)
            # Head
            draw.rectangle([sx + 18, sy + 2, sx + 24, sy + 10], fill=WHITE)
            draw.rectangle([sx + 22, sy + 4, sx + 24, sy + 6], fill=BLACK)  # eye
            # Legs
            draw.rectangle([sx + 2, sy + 12, sx + 5, sy + 18], fill=DARK_GRAY)
            draw.rectangle([sx + 12, sy + 12, sx + 15, sy + 18], fill=DARK_GRAY)

        # Ground
        draw.rectangle([200, 285, 380, 290], fill=GREEN)

        draw_loading_label(draw, "Herding", f)
        frames.append(img)
    return frames


def frames_honking():
    """Clawd as a goose honking with sound waves."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 100, 160
        draw_clawd(draw, cx, cy, g)

        # Megaphone / horn extending from Clawd's right
        horn_x = cx + 10 * g
        horn_y = cy + g + g // 2
        # Horn body (expanding cone)
        draw.polygon([(horn_x, horn_y - 5), (horn_x, horn_y + 12),
                       (horn_x + 50, horn_y + 25), (horn_x + 50, horn_y - 18)],
                      fill=ORANGE)
        draw.polygon([(horn_x, horn_y - 3), (horn_x, horn_y + 10),
                       (horn_x + 45, horn_y + 20), (horn_x + 45, horn_y - 13)],
                      fill=YELLOW)

        # Sound waves
        wave_phase = f % 3
        for i in range(3):
            if i <= wave_phase + 1:
                wave_x = horn_x + 55 + i * 20
                wave_r = 10 + i * 8
                draw.arc([wave_x, horn_y - wave_r, wave_x + wave_r, horn_y + wave_r],
                         -45, 45, fill=ORANGE, width=3)

        # "HONK!" text bouncing
        if f % 2 == 0:
            draw_text(draw, "HONK!", horn_x + 20, horn_y - 40 - f * 3, color=RED, scale=3)

        draw_loading_label(draw, "Honking", f)
        frames.append(img)
    return frames


def frames_hullaballooing():
    """Clawd in a whirlwind of papers, books, and items flying."""
    frames = []
    import math
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        cx, cy = 120, 175
        draw_clawd(draw, cx, cy, g)

        # Whirlwind of objects orbiting
        items = [
            (WHITE, 6),    # paper
            (BLUE, 8),     # book
            (YELLOW, 5),   # note
            (GREEN, 7),    # folder
            (RED, 4),      # flag
            (PURPLE, 6),   # card
        ]
        orbit_cx = cx + 4 * g
        orbit_cy = cy + 2 * g
        for i, (color, size) in enumerate(items):
            angle = math.radians((f * 35 + i * 60) % 360)
            r = 70 + (i % 3) * 20
            ix = orbit_cx + int(r * math.cos(angle))
            iy = orbit_cy + int(r * math.sin(angle) * 0.7) - 30
            if 5 < ix < 395 and 5 < iy < 345:
                draw.rectangle([ix - size, iy - size, ix + size, iy + size], fill=color)
                # Add a little detail
                if size > 5:
                    draw.rectangle([ix - size + 2, iy - size + 2,
                                    ix + size - 2, iy], fill=GRAY)

        # Exclamation marks
        for i in range(3):
            ex = 60 + i * 140
            ey = 60 + ((f + i) % 3) * 15
            if (f + i) % 2 == 0:
                draw_text(draw, "!", ex, ey, color=RED, scale=4)

        draw_loading_label(draw, "Hullaballooing", f)
        frames.append(img)
    return frames


def frames_wrangling():
    """Clawd lassoing unruly data cards into order."""
    frames = []
    num_frames = 8
    start_positions = [(298, 106), (338, 158), (304, 248), (348, 212), (268, 182)]
    end_positions = [(286, 154), (301, 174), (316, 194), (296, 214), (311, 234)]
    progress_steps = [0.0, 0.08, 0.16, 0.28, 0.45, 0.65, 0.82, 1.0]
    accents = [BLUE, TEAL, GREEN, YELLOW, PURPLE]

    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        clawd_x = [34, 32, 28, 24, 20, 18, 22, 28][f]
        clawd_y = [168, 170, 174, 178, 176, 174, 172, 170][f]
        draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 2))

        hand_x = clawd_x + 10 * g + 4
        hand_y = clawd_y + 2 * g + g // 2
        progress = progress_steps[f]

        card_positions = []
        for i, (start_pos, end_pos) in enumerate(zip(start_positions, end_positions)):
            sx, sy = start_pos
            ex, ey = end_pos
            jitter_amp = int((1.0 - progress) * 16)
            x = int(sx + (ex - sx) * progress + math.sin(f * 1.4 + i * 0.9) * jitter_amp)
            y = int(sy + (ey - sy) * progress + math.cos(f * 1.2 + i * 1.1) * jitter_amp)
            card_positions.append((x, y))

        center_x = sum(x + 17 for x, _ in card_positions) // len(card_positions)
        center_y = sum(y + 20 for _, y in card_positions) // len(card_positions)
        loop_w = 132 - int(progress * 48)
        loop_h = 88 - int(progress * 28)
        rope_left = center_x - loop_w // 2
        rope_mid_y = center_y - loop_h // 6
        draw.line([hand_x, hand_y, rope_left, rope_mid_y], fill=BROWN, width=3)
        draw.ellipse([center_x - loop_w // 2, center_y - loop_h // 2,
                      center_x + loop_w // 2, center_y + loop_h // 2], outline=BROWN, width=3)

        for i, (card_x, card_y) in enumerate(card_positions):
            skew = [-5, 2, -3, 4, -1][i] if progress < 0.7 else [-1, 1, 0, -1, 1][i]
            draw_data_card(draw, card_x, card_y, accent=accents[i], skew=skew)
            if progress < 0.78:
                tug_x = card_x + 38
                tug_y = card_y + 20
                draw.line([tug_x + 8, tug_y - 8, tug_x + 18, tug_y - 16], fill=GRAY, width=1)
                draw.line([tug_x + 10, tug_y, tug_x + 24, tug_y], fill=GRAY, width=1)

        for i in range(3):
            skid_y = clawd_y + 6 * g + 8 + i * 8
            skid_len = 12 + min(f, 5) * 6 + i * 4
            draw.line([clawd_x - 10 - skid_len, skid_y, clawd_x - 10, skid_y], fill=GRAY, width=1)

        if 2 <= f <= 5:
            draw_sweat_drop(draw, clawd_x + 2 * g, clawd_y - 8, scale=2, color=LIGHT_BLUE)

        draw_loading_label(draw, "Wrangling", f)
        frames.append(img)
    return frames


def frames_whirlpooling():
    """Large layered whirlpool with foam, spray, and deep pull."""
    frames = []
    num_frames = 10
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        bob = [0, -2, -4, -2, 0, 2, 0, -2, 0, 2][f]
        draw_clawd(draw, 42, 126 + bob, g, blink=(f == 4))

        cx, cy = 246, 252
        pull = f / (num_frames - 1)
        colors = [BLUE, TEAL, LIGHT_BLUE, BLUE, TEAL, WHITE]
        for ring in range(6):
            rx = 120 - ring * 18 + int(pull * 10)
            ry = 72 - ring * 10 + int(pull * 6)
            start = (f * 24 + ring * 38) % 360
            span = 220 - ring * 16
            width = max(2, 8 - ring)
            draw.arc([cx - rx, cy - ry, cx + rx, cy + ry], start, start + span,
                     fill=colors[ring], width=width)
            draw.arc([cx - rx + 8, cy - ry + 6, cx + rx - 8, cy + ry - 6],
                     start + 52, start + 100, fill=WHITE, width=2)

        eye_rx = 18 + int(pull * 12)
        eye_ry = 10 + int(pull * 8)
        draw.ellipse([cx - 34, cy - 20, cx + 34, cy + 20], fill=(30, 70, 110))
        draw.ellipse([cx - eye_rx, cy - eye_ry, cx + eye_rx, cy + eye_ry], fill=(12, 26, 45))

        for i in range(12):
            angle = math.radians(f * 30 + i * 32)
            radius = 130 - i * 5 - int(pull * 18)
            px = cx + int(radius * math.cos(angle))
            py = cy - 18 + int(radius * math.sin(angle) * 0.45)
            if i % 3 == 0:
                draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=WHITE)
            elif i % 3 == 1:
                draw.rectangle([px - 2, py - 2, px + 2, py + 2], fill=LIGHT_BLUE)
            else:
                draw.ellipse([px - 4, py - 2, px + 4, py + 2], fill=TEAL)

        for i in range(6):
            sx = 148 + i * 34
            sy = 300 - ((f * 10 + i * 12) % 58)
            draw.ellipse([sx, sy, sx + 8, sy + 8], fill=LIGHT_BLUE)

        draw_loading_label(draw, "Whirlpooling", f)
        frames.append(img)
    return frames


def frames_unfurling():
    """A parchment ribbon unfurling into a delicate map-like scroll."""
    frames = []
    num_frames = 8
    open_steps = [24, 56, 92, 126, 158, 188, 210, 224]
    flutters = [0, -2, -5, -3, -1, 2, 4, 1]
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        clawd_x = 34 + [0, 2, 4, 6, 4, 2, 0, -2][f]
        clawd_y = 170 + [0, -2, -4, -2, 0, 2, 0, -2][f]
        draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 5))

        scroll_x = 218
        scroll_y = 126
        scroll_h = 96
        open_w = open_steps[f]
        flutter = flutters[f]
        parchment = (250, 236, 208)

        hand_x = clawd_x + 10 * g + 4
        hand_y = clawd_y + 2 * g + g // 2
        draw.line([hand_x, hand_y, scroll_x - 24, scroll_y + scroll_h // 2], fill=BROWN, width=2)

        draw.ellipse([scroll_x - 46, scroll_y + 8, scroll_x, scroll_y + scroll_h - 8],
                     fill=parchment, outline=DARK_BROWN)
        draw.ellipse([scroll_x - 34, scroll_y + 20, scroll_x - 8, scroll_y + scroll_h - 20],
                     outline=DARK_BROWN, width=2)
        draw.line([scroll_x - 28, scroll_y + 18, scroll_x - 28, scroll_y + scroll_h - 18], fill=(214, 184, 144), width=2)

        right_x = scroll_x + open_w
        draw.polygon([
            (scroll_x - 2, scroll_y + 4),
            (right_x, scroll_y + flutter),
            (right_x + 8, scroll_y + scroll_h - 10 + flutter),
            (scroll_x - 2, scroll_y + scroll_h - 4),
        ], fill=parchment, outline=DARK_BROWN)
        draw.polygon([
            (right_x, scroll_y + flutter),
            (right_x + 18, scroll_y + 10 + flutter),
            (right_x + 18, scroll_y + scroll_h - 18 + flutter),
            (right_x, scroll_y + scroll_h - 8),
        ], fill=parchment, outline=DARK_BROWN)
        draw.arc([right_x + 4, scroll_y + 14 + flutter, right_x + 30, scroll_y + 40 + flutter],
                 270, 90, fill=DARK_BROWN, width=2)
        draw.arc([right_x + 4, scroll_y + scroll_h - 38 + flutter, right_x + 30, scroll_y + scroll_h - 12 + flutter],
                 90, 270, fill=DARK_BROWN, width=2)

        if open_w > 44:
            draw.rectangle([scroll_x + 14, scroll_y + 10, right_x - 18, scroll_y + scroll_h - 10],
                           outline=(190, 150, 110), width=1)
            draw.line([scroll_x + 28, scroll_y + 58, right_x - 48, scroll_y + 72 + flutter // 2],
                      fill=TEAL, width=2)
            for px, py in [(scroll_x + 44, scroll_y + 34), (scroll_x + 82, scroll_y + 60),
                           (scroll_x + 122, scroll_y + 44)]:
                if px < right_x - 20:
                    draw_text(draw, "*", px, py, color=YELLOW, scale=2)
        if open_w > 92:
            compass_x = min(right_x - 46, scroll_x + 126)
            compass_y = scroll_y + 36
            draw.line([compass_x - 10, compass_y, compass_x + 10, compass_y], fill=DARK_BROWN, width=1)
            draw.line([compass_x, compass_y - 10, compass_x, compass_y + 10], fill=DARK_BROWN, width=1)
            draw_text(draw, "*", compass_x - 6, compass_y - 20, color=YELLOW, scale=2)

        draw_loading_label(draw, "Unfurling", f)
        frames.append(img)
    return frames


def frames_topsy_turvying():
    """A whole workspace whipping around into a new upside-down arrangement."""
    frames = []
    num_frames = 10

    def draw_panel(draw, x, y, inverted=False):
        draw.rectangle([x, y, x + 72, y + 50], fill=(32, 38, 60), outline=WHITE)
        bar_y = y + 40 if inverted else y + 4
        draw.rectangle([x + 6, bar_y, x + 66, bar_y + 8], fill=BLUE)
        for i in range(3):
            line_y = y + 12 + i * 10 if not inverted else y + 10 + i * 9
            draw.rectangle([x + 10, line_y, x + 56, line_y + 3], fill=GRAY)

    def draw_crate(draw, x, y, inverted=False):
        draw.rectangle([x, y, x + 44, y + 38], fill=BROWN, outline=DARK_BROWN)
        band_y = y + 28 if inverted else y + 8
        draw.rectangle([x + 4, band_y, x + 40, band_y + 6], fill=DARK_BROWN)
        draw.line([x + 10, y + 5, x + 34, y + 33], fill=DARK_BROWN, width=2)
        draw.line([x + 34, y + 5, x + 10, y + 33], fill=DARK_BROWN, width=2)

    def draw_arrow_icon(draw, x, y, direction):
        if direction == 0:
            pts = [(x, y + 10), (x + 26, y + 10), (x + 26, y + 2), (x + 42, y + 16),
                   (x + 26, y + 30), (x + 26, y + 22), (x, y + 22)]
        elif direction == 1:
            pts = [(x + 16, y), (x + 30, y + 16), (x + 22, y + 16), (x + 22, y + 42),
                   (x + 10, y + 42), (x + 10, y + 16), (x + 2, y + 16)]
        elif direction == 2:
            pts = [(x + 42, y + 10), (x + 16, y + 10), (x + 16, y + 2), (x, y + 16),
                   (x + 16, y + 30), (x + 16, y + 22), (x + 42, y + 22)]
        else:
            pts = [(x + 16, y + 42), (x + 30, y + 26), (x + 22, y + 26), (x + 22, y),
                   (x + 10, y), (x + 10, y + 26), (x + 2, y + 26)]
        draw.polygon(pts, fill=YELLOW)

    start_positions = {
        "panel": (232, 108),
        "gear": (330, 146),
        "crate": (242, 224),
        "arrow": (322, 238),
    }
    end_positions = {
        "panel": (286, 230),
        "gear": (244, 132),
        "crate": (320, 108),
        "arrow": (232, 250),
    }

    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        draw_clawd(draw, 40 + [0, -2, 3, -4, 2, 5, -1, 3, 0, -2][f],
                   168 + [0, 2, 0, -3, 4, -2, 3, 0, -1, 2][f], g, blink=(f == 4))

        progress = f / (num_frames - 1)
        chaos = math.sin(progress * math.pi)
        center_x, center_y = 292, 184

        for i, key in enumerate(["panel", "gear", "crate", "arrow"]):
            sx, sy = start_positions[key]
            ex, ey = end_positions[key]
            radius = 58 - i * 7
            x = int(sx + (ex - sx) * progress + math.cos(f * 0.9 + i) * chaos * radius)
            y = int(sy + (ey - sy) * progress + math.sin(f * 1.1 + i * 1.3) * chaos * (radius - 10))
            orientation = (f + i) % 4

            if key == "panel":
                draw_panel(draw, x, y, inverted=f >= 7)
            elif key == "gear":
                draw_gear(draw, x + 18, y + 18, 16, step=f + i)
            elif key == "crate":
                draw_crate(draw, x, y, inverted=f >= 6)
            elif key == "arrow":
                draw_arrow_icon(draw, x, y, orientation)

        for i in range(3):
            draw.arc([center_x - 80 + i * 20, center_y - 56 + i * 14,
                      center_x + 80 - i * 20, center_y + 56 - i * 14],
                     30 + f * 18 + i * 35, 150 + f * 18 + i * 35, fill=LIGHT_CORAL, width=2)
        if 2 <= f <= 7:
            for sx, sy in [(210, 96), (360, 124), (218, 280), (360, 260)]:
                draw_text(draw, "*", sx + (f % 2) * 4, sy, color=RED, scale=3)

        draw_loading_label(draw, "Topsy-turvying", f)
        frames.append(img)
    return frames


def frames_tomfoolering():
    """A playful, winking Clawd doing a more theatrical fool routine."""
    frames = []
    sway = [-8, 0, 10, 6, -4, 2]
    bounce = [0, -10, -16, -6, 0, 4]
    confetti = [
        [(94, 86), (250, 72), (306, 110)],
        [(84, 68), (258, 60), (320, 96)],
        [(78, 58), (270, 54), (334, 88)],
        [(92, 80), (280, 70), (324, 104)],
        [(108, 96), (264, 84), (308, 118)],
        [(118, 102), (248, 92), (286, 128)],
    ]
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        clawd_x = 118 + sway[f]
        clawd_y = 170 + bounce[f]
        wink = "both" if f in [1, 2, 4, 5] else None
        draw_clawd(draw, clawd_x, clawd_y, g, blink=False, wink=wink)

        hat_x = clawd_x + g
        hat_y = clawd_y - int(g * 1.8)
        draw.rectangle([hat_x - g // 2, hat_y + 2 * g, hat_x + 9 * g, hat_y + 2 * g + g // 3], fill=RED)
        draw.polygon([(hat_x, hat_y + 2 * g), (hat_x + 3 * g, hat_y - g), (hat_x + 4 * g, hat_y + g // 2)],
                     fill=RED)
        draw.polygon([(hat_x + 5 * g, hat_y + g // 2), (hat_x + 8 * g, hat_y - g), (hat_x + 9 * g, hat_y + 2 * g)],
                     fill=YELLOW)
        bell_bob = [-2, -4, -1, 2, 1, -2][f]
        draw.ellipse([hat_x + 3 * g - 5, hat_y - g - 5 + bell_bob, hat_x + 3 * g + 5, hat_y - g + 5 + bell_bob],
                     fill=GREEN)
        draw.ellipse([hat_x + 8 * g - 5, hat_y - g - 5 - bell_bob, hat_x + 8 * g + 5, hat_y - g + 5 - bell_bob],
                     fill=BLUE)

        wand_x = clawd_x + 10 * g
        wand_y = clawd_y + 2 * g + g // 2
        draw.line([wand_x, wand_y, wand_x + 36, wand_y - 18], fill=DARK_BROWN, width=3)
        draw_text(draw, "*", wand_x + 30, wand_y - 34, color=YELLOW, scale=3)
        draw.arc([wand_x + 10, wand_y - 46, wand_x + 72, wand_y + 6], 200, 330, fill=PURPLE, width=2)
        draw.arc([wand_x + 6, wand_y - 32, wand_x + 64, wand_y + 18], 200, 330, fill=TEAL, width=2)

        for i, (cx, cy) in enumerate(confetti[f]):
            color = [RED, YELLOW, GREEN, BLUE, PURPLE, PINK][(f + i) % 6]
            draw.rectangle([cx, cy, cx + 6, cy + 6], fill=color)
            draw.line([cx + 3, cy + 7, cx + 7, cy + 12], fill=color, width=1)

        draw_loading_label(draw, "Tomfoolering", f)
        frames.append(img)
    return frames


def frames_transmuting():
    """An alchemical ore-to-crystal transformation."""
    frames = []
    num_frames = 8
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        draw_clawd(draw, 34, 160, g, blink=(f == 3))

        hand_x = 34 + 10 * g + 4
        hand_y = 160 + 2 * g + g // 2
        cx, cy = 294, 210
        pulse = 4 + (f % 3) * 3
        draw.ellipse([cx - 58, cy - 58, cx + 58, cy + 58], outline=PURPLE, width=2)
        draw.ellipse([cx - 42, cy - 42, cx + 42, cy + 42], outline=PURPLE, width=1)
        for i in range(6):
            angle = math.radians(f * 20 + i * 60)
            rx = cx + int(52 * math.cos(angle))
            ry = cy + int(52 * math.sin(angle))
            draw.rectangle([rx - 2, ry - 2, rx + 2, ry + 2], fill=PURPLE if i % 2 == 0 else YELLOW)
        draw.line([hand_x, hand_y, cx - 56, cy - 16], fill=PURPLE, width=2)

        ore_scale = max(0.0, 1.0 - f / 5.0)
        if ore_scale > 0:
            ore_w = int(48 * ore_scale) + 20
            ore_h = int(34 * ore_scale) + 16
            ore_points = [
                (cx - ore_w // 2, cy + ore_h // 4),
                (cx - ore_w // 3, cy - ore_h // 2),
                (cx + ore_w // 5, cy - ore_h // 3),
                (cx + ore_w // 2, cy + ore_h // 8),
                (cx + ore_w // 4, cy + ore_h // 2),
                (cx - ore_w // 6, cy + ore_h // 2),
            ]
            draw.polygon(ore_points, fill=DARK_GRAY, outline=GRAY)
            if f >= 2:
                draw.line([cx - ore_w // 4, cy - 6, cx, cy + 8, cx + ore_w // 5, cy - 10],
                          fill=PURPLE, width=2)

        crystal_progress = max(0.0, (f - 2) / 5.0)
        if crystal_progress > 0:
            glow = int(26 * crystal_progress)
            draw.ellipse([cx - 34 - glow, cy - 34 - glow, cx + 34 + glow, cy + 34 + glow],
                         fill=(255, 235, 160))
            draw_crystal(draw, cx, cy, size=18 + int(18 * crystal_progress),
                         fill_color=(255, 226, 110), outline=ORANGE)

        if f >= 3:
            for i in range(5):
                fx = cx - 30 + i * 15 + int(math.sin(f + i) * 6)
                fy = cy - 30 - i * 5
                draw.rectangle([fx, fy, fx + 4, fy + 4], fill=YELLOW if i % 2 == 0 else WHITE)

        draw_loading_label(draw, "Transmuting", f)
        frames.append(img)
    return frames


def frames_tinkering():
    """Clawd tinkering with a small gadget on a workbench."""
    frames = []
    num_frames = 8
    tool_angles = [-20, -8, 6, 16, 8, -4, -12, -2]
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        clawd_x, clawd_y = 34, 158
        draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 5))

        bench_x, bench_y = 224, 248
        draw.rectangle([bench_x, bench_y, 382, bench_y + 18], fill=BROWN)
        draw.rectangle([bench_x + 8, bench_y + 18, bench_x + 22, bench_y + 68], fill=DARK_BROWN)
        draw.rectangle([bench_x + 128, bench_y + 18, bench_x + 142, bench_y + 68], fill=DARK_BROWN)
        draw.rectangle([bench_x + 12, bench_y - 24, bench_x + 46, bench_y - 14], fill=GRAY)
        draw.rectangle([bench_x + 56, bench_y - 24, bench_x + 74, bench_y - 14], fill=YELLOW)
        draw.rectangle([bench_x + 86, bench_y - 24, bench_x + 120, bench_y - 14], fill=BLUE)

        gadget_x, gadget_y = 286, 196
        draw.rectangle([gadget_x - 30, gadget_y, gadget_x + 28, gadget_y + 42], fill=DARK_GRAY, outline=WHITE)
        draw.rectangle([gadget_x - 24, gadget_y + 10, gadget_x + 22, gadget_y + 18], fill=GRAY)
        draw.rectangle([gadget_x - 20, gadget_y + 42, gadget_x - 12, gadget_y + 50], fill=DARK_GRAY)
        draw.rectangle([gadget_x + 10, gadget_y + 42, gadget_x + 18, gadget_y + 50], fill=DARK_GRAY)

        if f >= 1:
            draw_gear(draw, gadget_x - 12, gadget_y + 28, 8, step=f)
        if f >= 2:
            draw.rectangle([gadget_x + 2, gadget_y + 6, gadget_x + 18, gadget_y + 16], fill=BLUE)
        if f >= 3:
            draw.line([gadget_x + 24, gadget_y + 8, gadget_x + 36, gadget_y - 12], fill=GRAY, width=2)
            draw.ellipse([gadget_x + 32, gadget_y - 18, gadget_x + 44, gadget_y - 6], fill=YELLOW)
        if f >= 4:
            draw.rectangle([gadget_x - 6, gadget_y - 14, gadget_x + 6, gadget_y], fill=TEAL)
        if f >= 5 and f % 2 == 1:
            for sx, sy in [(gadget_x - 36, gadget_y + 6), (gadget_x + 30, gadget_y + 4), (gadget_x + 4, gadget_y - 22)]:
                draw_text(draw, "*", sx, sy, color=YELLOW, scale=2)
        if f >= 6:
            draw.ellipse([gadget_x + 12, gadget_y + 22, gadget_x + 22, gadget_y + 32], fill=RED if f % 2 == 0 else GREEN)

        hand_x = clawd_x + 10 * g + 2
        hand_y = clawd_y + 2 * g + g // 2
        tool_len = 42
        angle = math.radians(tool_angles[f])
        tip_x = hand_x + int(tool_len * math.cos(angle))
        tip_y = hand_y + int(tool_len * math.sin(angle))
        draw.line([hand_x, hand_y, tip_x, tip_y], fill=DARK_BROWN, width=3)
        draw.rectangle([tip_x - 4, tip_y - 4, tip_x + 4, tip_y + 4], fill=GRAY)

        for i in range(4):
            bx = 250 + i * 20 + (f * 3 + i * 5) % 10
            by = 214 - (f * 4 + i * 7) % 18
            draw.rectangle([bx, by, bx + 4, by + 4], fill=WHITE if i % 2 == 0 else GRAY)

        draw_loading_label(draw, "Tinkering", f)
        frames.append(img)
    return frames


def frames_thundering():
    """Transparent storm frames alternating with black lightning flashes."""
    frames = []
    num_frames = 8
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        flash = f % 2 == 1

        if flash:
            draw.rectangle([0, 0, CANVAS, CANVAS], fill=BLACK)

        cloud_color = (236, 236, 236) if flash else DARK_GRAY
        for idx, (cx, cy, scale) in enumerate([(92, 58, 1.0), (200, 42, 1.15), (314, 60, 1.0)]):
            draw_storm_cloud(draw, cx + (-4 if flash and idx == 1 else 0), cy, scale=scale, fill_color=cloud_color)

        if not flash:
            for i in range(12):
                rx = 48 + i * 28 + (f % 2) * 6
                ry = 120 + (i % 3) * 18
                draw.line([rx, ry, rx - 4, ry + 20], fill=LIGHT_BLUE, width=1)

        body_color = (245, 245, 245) if flash else CORAL
        eye_color = DARK_GRAY if flash else BLACK
        draw_clawd(draw, 120, 185, g, blink=(f == 4), body_color=body_color, eye_color=eye_color)

        if flash:
            draw_lightning_bolt(draw, 178 + (f == 5) * 10, 54, scale=1.0, color=(255, 244, 170))
            draw_lightning_bolt(draw, 262 - (f == 3) * 8, 76, scale=0.72, color=WHITE)
        else:
            draw.line([196, 82, 186, 118], fill=GRAY, width=1)
            draw.line([276, 92, 268, 126], fill=GRAY, width=1)

        draw_loading_label(draw, "Thundering", f)
        frames.append(img)
    return frames


def frames_nucleating():
    """Particles collapse into a glowing nucleus and seed-crystal cluster."""
    frames = []
    num_frames = 8
    particle_count = 18
    center_x, center_y = 292, 162
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        draw_clawd(draw, 34, 170, GRID, blink=(f == 4))

        progress = f / (num_frames - 1)
        for ring_idx, radius in enumerate([72, 50]):
            if f >= ring_idx + 2:
                draw_sigil_ring(draw, center_x, center_y, max(12, radius - int(progress * 18)),
                                color=[LIGHT_BLUE, TEAL][ring_idx], frame=f + ring_idx, spokes=8 + ring_idx * 2)

        for i in range(particle_count):
            angle = math.radians(f * 22 + i * (360 / particle_count))
            start_r = 88 - (i % 4) * 10
            end_r = 18 + (i % 3) * 6
            radius = start_r + (end_r - start_r) * progress
            px = center_x + int(radius * math.cos(angle))
            py = center_y + int(radius * math.sin(angle) * 0.72)
            color = [LIGHT_BLUE, TEAL, WHITE][i % 3]
            size = 3 if progress < 0.6 else 4
            draw.ellipse([px - size, py - size, px + size, py + size], fill=color)
            if f >= 3 and i % 5 == 0:
                draw.line([px, py, center_x, center_y], fill=TEAL, width=1)

        glow = 10 + f * 4
        draw.ellipse([center_x - glow, center_y - glow, center_x + glow, center_y + glow], fill=(220, 248, 255))
        draw.ellipse([center_x - 7 - f, center_y - 7 - f, center_x + 7 + f, center_y + 7 + f], fill=TEAL)
        if f >= 4:
            draw_crystal(draw, center_x, center_y - 2, size=10 + (f - 4) * 3, fill_color=(180, 248, 255), outline=TEAL)
        if f >= 5:
            draw_crystal(draw, center_x - 18, center_y + 14, size=8 + (f - 5) * 2, fill_color=LIGHT_BLUE, outline=BLUE)
            draw_crystal(draw, center_x + 18, center_y + 14, size=8 + (f - 5) * 2, fill_color=WHITE, outline=TEAL)
        if f >= 6:
            for sx, sy in [(center_x - 54, center_y - 42), (center_x + 42, center_y - 24), (center_x + 12, center_y + 54)]:
                draw_text(draw, "*", sx, sy, color=YELLOW, scale=3)

        draw_loading_label(draw, "Nucleating", f)
        frames.append(img)
    return frames


def frames_osmosing():
    """A dramatic osmosis scene with a glowing membrane and particle transfer."""
    frames = []
    num_frames = 8
    membrane_x = 250
    left_particles = [(188, 92), (208, 124), (176, 154), (214, 184), (182, 214), (204, 248), (168, 276), (220, 302)]
    right_particles = [(296, 110), (324, 166), (308, 234), (332, 286)]
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        draw_clawd(draw, 28, 160, GRID, blink=(f == 3))

        glow_w = 12 + (f % 3) * 4
        draw.rectangle([membrane_x - glow_w, 74, membrane_x + glow_w, 314], fill=LIGHT_BLUE)
        draw.rectangle([membrane_x - 3, 74, membrane_x + 3, 314], fill=WHITE)
        for y in range(84, 314, 18):
            draw.rectangle([membrane_x - 10, y, membrane_x + 10, y + 4], fill=LIGHT_BLUE if (y // 18 + f) % 2 == 0 else TEAL)

        balance = f / (num_frames - 1)
        for i, (sx, sy) in enumerate(left_particles):
            target_x = [228, 238, 246, 258, 270, 282, 292, 304][i]
            x = int(sx + (target_x - sx) * balance)
            y = sy + int(math.sin(f * 0.8 + i) * 4)
            draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=BLUE)
            if abs(x - membrane_x) < 18:
                draw.arc([membrane_x - 18, y - 10, membrane_x + 18, y + 10], 190, 350, fill=WHITE, width=1)

        for i, (sx, sy) in enumerate(right_particles):
            target_x = [284, 292, 300, 308][i]
            x = int(sx - (sx - target_x) * balance)
            y = sy + int(math.cos(f * 0.9 + i) * 5)
            draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=GREEN)

        for i in range(5):
            if f >= 2:
                t = ((f - 2) + i * 0.7) / 6.0
                if 0 <= t <= 1:
                    px = int(220 + 90 * t)
                    py = int(96 + i * 42 + math.sin((t + i) * math.pi) * 16)
                    draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=WHITE if i % 2 == 0 else LIGHT_BLUE)

        if f >= 4:
            for sy in [114, 186, 258]:
                draw.arc([membrane_x - 28, sy - 18, membrane_x + 28, sy + 18], 200, 340, fill=TEAL, width=2)

        draw_loading_label(draw, "Osmosing", f)
        frames.append(img)
    return frames


def frames_prestidigitating():
    """A more theatrical sleight-of-hand card flourish."""
    frames = []
    num_frames = 8
    flourish_center = (292, 166)
    card_colors = [RED, BLUE, GREEN, PURPLE]
    scarf_paths = [
        [(238, 172), (260, 140), (290, 124), (324, 132)],
        [(238, 170), (266, 132), (302, 118), (334, 132)],
        [(238, 168), (274, 126), (314, 116), (344, 134)],
        [(238, 170), (280, 132), (324, 126), (350, 146)],
    ]
    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        g = GRID

        draw_spotlight(draw, 86, 18, 318, top_w=18, bottom_w=170, color=(255, 238, 190))
        draw_spotlight(draw, 290, 12, 308, top_w=16, bottom_w=140, color=(255, 228, 210))
        draw.rectangle([0, 304, 400, 314], fill=DARK_GRAY)

        cx, cy = 42, 164 + [0, -2, -4, -2, 0, 2, 0, -2][f]
        draw_clawd(draw, cx, cy, g, blink=(f == 4))
        hand_x = cx + 10 * g + 4
        hand_y = cy + 2 * g + g // 2
        wand_tip_x = hand_x + 34
        wand_tip_y = hand_y - 18
        draw.line([hand_x, hand_y, wand_tip_x, wand_tip_y], fill=DARK_BROWN, width=3)
        draw.rectangle([wand_tip_x - 2, wand_tip_y - 2, wand_tip_x + 2, wand_tip_y + 2], fill=WHITE)

        trail = scarf_paths[min(f, len(scarf_paths) - 1)]
        if f >= 2:
            draw.line(trail, fill=PINK, width=5)
            draw.line([(x, y + 5) for x, y in trail], fill=ORANGE, width=3)

        if f <= 1:
            fan_specs = [(-22, 18, RED), (0, 0, BLUE), (22, 18, GREEN)]
            for dx, skew, color in fan_specs:
                draw_playing_card(draw, flourish_center[0] + dx, flourish_center[1], accent=color, skew=skew // 6)
        elif f == 2:
            draw_playing_card(draw, flourish_center[0] - 24, flourish_center[1] + 4, accent=RED, skew=-2)
            draw_playing_card(draw, flourish_center[0] + 24, flourish_center[1] + 4, accent=GREEN, skew=2)
            for sx, sy in [(flourish_center[0] - 6, flourish_center[1] - 18), (flourish_center[0] + 8, flourish_center[1] + 4),
                           (flourish_center[0] - 16, flourish_center[1] + 22)]:
                draw_text(draw, "*", sx, sy, color=YELLOW, scale=3)
        else:
            for i, color in enumerate(card_colors):
                angle = math.radians(f * 28 + i * 85)
                radius = 32 + (i % 2) * 18
                px = flourish_center[0] + int(radius * math.cos(angle))
                py = flourish_center[1] + int(radius * math.sin(angle) * 0.72)
                skew = int(math.sin(angle) * 6)
                if not (f == 3 and i == 1):
                    draw_playing_card(draw, px, py, accent=color, skew=skew)
            if f >= 4:
                draw_playing_card(draw, flourish_center[0] + 42, flourish_center[1] - 36, accent=YELLOW, skew=1)

        for i, (sx, sy) in enumerate([(246, 114), (284, 92), (334, 108), (360, 150), (320, 216)]):
            if (f + i) % 2 == 0:
                draw_text(draw, "*", sx, sy, color=YELLOW, scale=2 + (i % 2))

        draw_loading_label(draw, "Prestidigitating", f)
        frames.append(img)
    return frames


# ---------------------------------------------------------------------------
# Compact scene functions (draw scene for a single frame)
# Used via make_frames() wrapper
# ---------------------------------------------------------------------------
def make_frames(word, draw_scene_fn):
    """Wrap a scene-drawing function into a list of 6 RGBA frames with text."""
    frames = []
    for f in range(NUM_FRAMES):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)
        draw_scene_fn(draw, f, img)
        draw_loading_label(draw, word, f)
        frames.append(img)
    return frames


def sc_hustling(draw, f, img):
    draw_clawd(draw, 60, 155 + [-2, 0, 2, 0, -2, 0][f], g)
    bx, by = 260, 230
    draw.rectangle([bx, by, bx+60, by+45], fill=BROWN)
    draw.rectangle([bx+25, by-5, bx+35, by+5], fill=DARK_BROWN)
    for i in range(3):
        dx = 200 + i * 60
        dy = 80 + ((f + i * 2) % 4) * 15
        if (f + i) % 2 == 0:
            draw_text(draw, "$", dx, dy, color=GREEN, scale=4)
    for i in range(4):
        ly = 170 + i * 20
        draw.line([20, ly, 50 + (f % 3) * 10, ly], fill=GRAY, width=1)


def sc_gusting(draw, f, img):
    gg = 13
    ox = 136 + [0, -1, -2, -1, 0, 1][f]
    oy = 158 + [1, 0, -1, 0, 1, 0][f]
    row_offsets = [-10, -8, -4, -2, 0, 1, 3, 5]

    def gust_path(base_y, amp, drift, phase):
        points = []
        for step in range(12):
            x = 8 + step * 32 + ((f * 8 + phase) % 20)
            y = base_y + int(math.sin((step + f * 0.85 + phase * 0.2) * 0.8) * amp) + step * drift
            points.append((x, y))
        return points

    ribbon_specs = [
        (84, 16, 3, LIGHT_BLUE, WHITE, 4),
        (118, 20, 4, TEAL, WHITE, 5),
        (160, 14, 3, LIGHT_BLUE, WHITE, 4),
        (198, 18, 4, TEAL, WHITE, 4),
        (234, 12, 3, LIGHT_BLUE, WHITE, 3),
    ]
    for i, (base_y, amp, drift, outer_color, inner_color, width) in enumerate(ribbon_specs):
        points = gust_path(base_y, amp, drift, i * 2)
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            draw.line([x1, y1, x2, y2], fill=outer_color, width=width)
            draw.line([x1, y1, x2, y2], fill=inner_color, width=max(1, width - 2))

    debris = [
        (42, 96, "leaf"),
        (78, 150, "paper"),
        (132, 86, "leaf"),
        (182, 212, "paper"),
        (234, 126, "leaf"),
        (288, 176, "paper"),
        (324, 102, "leaf"),
    ]
    for i, (dx, dy, kind) in enumerate(debris):
        x = dx + ((f * 18 + i * 13) % 72)
        y = dy + int(math.sin((f + i) * 0.8) * 8)
        if kind == "leaf":
            draw.polygon([(x, y), (x + 10, y - 4), (x + 18, y + 2), (x + 10, y + 8)],
                         fill=GREEN, outline=DARK_BROWN)
            draw.line([x + 3, y + 1, x + 14, y + 3], fill=DARK_BROWN, width=1)
        else:
            draw.polygon([(x, y + 6), (x + 10, y), (x + 18, y + 8), (x + 8, y + 14)],
                         fill=WHITE, outline=GRAY)
            draw.line([x + 4, y + 7, x + 13, y + 3], fill=GRAY, width=1)

    body_color = CORAL
    blink = (f == 4)

    # Head rows
    for gy in range(2):
        x_off = row_offsets[gy]
        for gx in range(8):
            draw.rectangle([ox + x_off + gx * gg, oy + gy * gg,
                            ox + x_off + (gx + 1) * gg - 1, oy + (gy + 1) * gg - 1], fill=body_color)

    eye_row_off = row_offsets[1]
    if blink:
        eye_y = oy + gg + gg // 2
        draw.rectangle([ox + eye_row_off + 1 * gg, eye_y, ox + eye_row_off + 2 * gg - 1, eye_y + 2], fill=BLACK)
        draw.rectangle([ox + eye_row_off + 6 * gg, eye_y, ox + eye_row_off + 7 * gg - 1, eye_y + 2], fill=BLACK)
    else:
        draw.rectangle([ox + eye_row_off + 1 * gg, oy + gg, ox + eye_row_off + 2 * gg - 1, oy + 2 * gg - 1], fill=BLACK)
        draw.rectangle([ox + eye_row_off + 6 * gg, oy + gg, ox + eye_row_off + 7 * gg - 1, oy + 2 * gg - 1], fill=BLACK)

    # Body rows
    for gy in range(2, 4):
        x_off = row_offsets[gy]
        for gx in range(-2, 10):
            draw.rectangle([ox + x_off + gx * gg, oy + gy * gg,
                            ox + x_off + (gx + 1) * gg - 1, oy + (gy + 1) * gg - 1], fill=body_color)

    # Lower body rows
    for gy in range(4, 6):
        x_off = row_offsets[gy]
        for gx in range(8):
            draw.rectangle([ox + x_off + gx * gg, oy + gy * gg,
                            ox + x_off + (gx + 1) * gg - 1, oy + (gy + 1) * gg - 1], fill=body_color)

    # Legs
    for gy in range(6, 8):
        x_off = row_offsets[gy]
        for lc in [0, 2, 5, 7]:
            leg_shift = -2 if (lc in [0, 2] and gy == 7 and f in [1, 2, 3]) else 0
            draw.rectangle([ox + x_off + lc * gg + leg_shift, oy + gy * gg,
                            ox + x_off + (lc + 1) * gg - 1 + leg_shift, oy + (gy + 1) * gg - 1], fill=body_color)

    foot_y = oy + 8 * gg + 2
    for sx in [ox + row_offsets[7] + 2 * gg, ox + row_offsets[7] + 7 * gg]:
        draw.line([sx, foot_y, sx + 24, foot_y + 4], fill=GRAY, width=2)
        draw.line([sx - 6, foot_y + 6, sx + 16, foot_y + 8], fill=LIGHT_BLUE, width=1)


def sc_ideating(draw, f, img):
    draw_clawd(draw, 120, 185, g, blink=(f == 3))
    idea_cx = 120 + 4 * g
    idea_cy = 86
    bulb_starts = [(78, 82), (122, 38), (304, 74), (252, 42), (332, 118)]

    if f < 4:
        t = (f + 1) / 5
        for i, (sx, sy) in enumerate(bulb_starts):
            bx = int(sx + (idea_cx - sx) * t)
            by = int(sy + (idea_cy - sy) * t)
            bulb_size = 11 - min(4, f)
            draw_lightbulb(draw, bx, by, size=bulb_size, glow=1 if (f + i) % 2 == 0 else 0)
    if f >= 2:
        halo = 10 + (f - 2) * 6
        draw.ellipse([idea_cx - halo, idea_cy - halo - 4, idea_cx + halo, idea_cy + halo + 4],
                     outline=YELLOW, width=2)
    if f >= 4:
        draw_lightbulb(draw, idea_cx, idea_cy, size=26 + (f - 4) * 3, glow=8 + (f - 4) * 2)
        for sx, sy in [(idea_cx - 44, idea_cy - 6), (idea_cx + 34, idea_cy - 18), (idea_cx + 22, idea_cy + 34)]:
            draw_text(draw, "*", sx, sy, color=YELLOW, scale=3)


def sc_imagining(draw, f, img):
    draw_clawd(draw, 46, 190, g)
    bx, by, bw, bh = 188, 48, 164, 112
    draw_thought_bubble(draw, bx, by, bw, bh)

    # A small teal swirl starts the imagined scene.
    swirl_x = bx + 28
    swirl_y = by + 54
    draw.arc([swirl_x - 16, swirl_y - 14, swirl_x + 16, swirl_y + 14], 20, 330, fill=TEAL, width=2)
    draw.arc([swirl_x - 8, swirl_y - 7, swirl_x + 8, swirl_y + 7], 20, 320, fill=TEAL, width=2)

    if f >= 1:
        cloud_x, cloud_y = bx + 38, by + 28
        draw.ellipse([cloud_x, cloud_y + 10, cloud_x + 48, cloud_y + 32], fill=LIGHT_BLUE)
        draw.ellipse([cloud_x + 16, cloud_y, cloud_x + 58, cloud_y + 28], fill=LIGHT_BLUE)
        draw.ellipse([cloud_x + 34, cloud_y + 8, cloud_x + 74, cloud_y + 32], fill=LIGHT_BLUE)
    if f >= 2:
        moon_x, moon_y = bx + 114, by + 18
        draw.ellipse([moon_x, moon_y, moon_x + 28, moon_y + 28], fill=YELLOW)
        draw.ellipse([moon_x + 9, moon_y + 3, moon_x + 30, moon_y + 27], fill=WHITE)
    if f >= 3:
        draw_text(draw, "*", bx + 126, by + 56, color=YELLOW, scale=4)
    if f >= 4:
        hill_y = by + 86
        draw.arc([bx + 70, hill_y - 10, bx + 150, hill_y + 22], 180, 360, fill=GREEN, width=8)
        tower_x = bx + 102
        tower_y = by + 58
        draw.rectangle([tower_x, tower_y, tower_x + 26, tower_y + 34], fill=PURPLE)
        draw.rectangle([tower_x - 2, tower_y - 6, tower_x + 4, tower_y], fill=PURPLE)
        draw.rectangle([tower_x + 8, tower_y - 6, tower_x + 14, tower_y], fill=PURPLE)
        draw.rectangle([tower_x + 18, tower_y - 6, tower_x + 24, tower_y], fill=PURPLE)
        draw.rectangle([tower_x + 9, tower_y + 18, tower_x + 17, tower_y + 34], fill=WHITE)
    if f >= 5:
        for sx, sy, scale in [(bx + 92, by + 32, 2), (bx + 140, by + 72, 2), (bx + 58, by + 72, 3)]:
            draw_text(draw, "*", sx, sy, color=YELLOW, scale=scale)


def sc_incubating(draw, f, img):
    draw_clawd(draw, 30, 160, g)
    ix, iy = 240, 180
    draw.rectangle([ix, iy, ix+120, iy+80], fill=LIGHT_BLUE)
    draw.rectangle([ix, iy, ix+120, iy+10], fill=GRAY)
    glow = [(255, 200, 100), (255, 220, 130), (255, 200, 100)][f % 3]
    draw.rectangle([ix+10, iy+15, ix+110, iy+70], fill=glow)
    draw.ellipse([ix+40, iy+30, ix+80, iy+65], fill=WHITE)
    th = 20 + f * 5
    draw.rectangle([ix+100, iy+70-th, ix+108, iy+70], fill=RED)


def sc_jiving(draw, f, img):
    sway = [0, -8, -12, -8, 0, 8][f]
    draw_clawd(draw, 130 + sway, 165, g)
    draw_music_note(draw, 80, 80 + ((f * 8) % 30), PURPLE)
    draw_music_note(draw, 300, 60 + ((f * 10) % 40), PINK)
    draw_music_note(draw, 200, 50 + ((f * 6) % 35), ORANGE)
    draw.ellipse([280, 30, 330, 80], fill=GRAY)
    for i in range(4):
        a = math.radians(f * 30 + i * 90)
        rx = 305 + int(12 * math.cos(a))
        ry = 55 + int(12 * math.sin(a))
        draw.rectangle([rx-3, ry-3, rx+3, ry+3], fill=WHITE)


def sc_levitating(draw, f, img):
    hover = [0, -6, -12, -12, -6, 0][f]
    clawd_x = 130
    clawd_y = 126 + hover
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 3))
    rx = clawd_x + 4 * g
    for i in range(3):
        ry = 314 - i * 16 - f * 2
        draw.ellipse([rx-40-i*10, ry, rx+40+i*10, ry+8],
                      outline=[PURPLE, PINK, TEAL][i], width=2)
    for i in range(4):
        a = math.radians(f * 25 + i * 90)
        sx = rx + int(60 * math.cos(a))
        sy = 194 + int(48 * math.sin(a))
        if (f + i) % 2 == 0:
            draw.rectangle([sx-2, sy-2, sx+2, sy+2], fill=YELLOW)
    for i in range(4):
        a = math.radians(f * 35 + i * 90 + 45)
        sx = rx + int(42 * math.cos(a))
        sy = clawd_y + 138 + int(22 * math.sin(a))
        draw.rectangle([sx-2, sy-2, sx+2, sy+2], fill=WHITE if i % 2 == 0 else LIGHT_BLUE)


def sc_manifesting(draw, f, img):
    draw_clawd(draw, 34, 170, g)
    pedestal_x, pedestal_y = 252, 248
    draw.rectangle([pedestal_x, pedestal_y, pedestal_x + 86, pedestal_y + 14], fill=DARK_GRAY)
    draw.rectangle([pedestal_x + 22, pedestal_y - 40, pedestal_x + 64, pedestal_y], fill=GRAY)

    crystal_cx, crystal_cy = 295, 156
    outline = [
        (crystal_cx, crystal_cy - 42),
        (crystal_cx + 28, crystal_cy - 14),
        (crystal_cx + 18, crystal_cy + 26),
        (crystal_cx, crystal_cy + 44),
        (crystal_cx - 18, crystal_cy + 26),
        (crystal_cx - 28, crystal_cy - 14),
    ]
    inner = [
        (crystal_cx, crystal_cy - 28),
        (crystal_cx + 16, crystal_cy - 10),
        (crystal_cx + 10, crystal_cy + 18),
        (crystal_cx, crystal_cy + 30),
        (crystal_cx - 10, crystal_cy + 18),
        (crystal_cx - 16, crystal_cy - 10),
    ]

    if f >= 1:
        paw_x = 34 + 10 * g
        paw_y = 170 + 2 * g
        for dx, dy in [(crystal_cx - 18, crystal_cy + 6), (crystal_cx + 10, crystal_cy + 18)]:
            draw.line([paw_x, paw_y, dx, dy], fill=PURPLE, width=2)

    # Materializing particles.
    particles = [(218, 118), (232, 90), (356, 102), (340, 210), (250, 214), (370, 152)]
    for i, (px, py) in enumerate(particles):
        if f >= i // 2:
            t = min(1.0, (f + 1) / 6)
            x = int(px + (crystal_cx - px) * t)
            y = int(py + (crystal_cy - py) * t)
            draw.rectangle([x - 3, y - 3, x + 3, y + 3], fill=[PINK, TEAL, YELLOW][i % 3])

    if f >= 0:
        draw.polygon(outline, outline=TEAL, width=2)
    if f >= 1:
        draw.line([crystal_cx, crystal_cy - 42, crystal_cx, crystal_cy + 44], fill=LIGHT_BLUE, width=2)
        draw.line([crystal_cx - 28, crystal_cy - 14, crystal_cx + 18, crystal_cy + 26], fill=LIGHT_BLUE, width=2)
        draw.line([crystal_cx + 28, crystal_cy - 14, crystal_cx - 18, crystal_cy + 26], fill=LIGHT_BLUE, width=2)
    if f >= 2:
        draw.polygon(inner, fill=(176, 230, 230))
    if f >= 3:
        draw.polygon(outline, fill=(130, 215, 220))
        draw.polygon(inner, fill=(205, 245, 248))
    if f >= 4:
        draw.ellipse([crystal_cx - 48, crystal_cy - 48, crystal_cx + 48, crystal_cy + 48], outline=YELLOW, width=2)
    if f >= 5:
        for sx, sy in [(250, 118), (344, 114), (320, 210)]:
            draw_text(draw, "*", sx, sy, color=YELLOW, scale=3)


def sc_marinating(draw, f, img):
    draw_clawd_head_only(draw, 120, 135, g, blink=(f == 3))
    bx, by = 90, 190
    bw = 220
    draw.rectangle([bx, by, bx+bw, by+80], fill=GRAY)
    draw.rectangle([bx-8, by-6, bx+bw+8, by+10], fill=DARK_GRAY)
    draw.rectangle([bx+8, by+14, bx+bw-8, by+72], fill=(180, 120, 60))
    herbs = [(bx+30, by+25), (bx+80, by+35), (bx+140, by+20), (bx+180, by+40)]
    for i, (hx, hy) in enumerate(herbs):
        bob = ((f + i) % 3) * 3
        draw.ellipse([hx, hy+bob, hx+12, hy+6+bob], fill=GREEN)


def sc_meandering(draw, f, img):
    draw_clawd(draw, 40 + f * 10, 180, g)
    for x in range(30, 380, 5):
        py = 260 + int(20 * math.sin(x * 0.04))
        draw.rectangle([x, py, x+4, py+4], fill=BROWN)
    for i in range(3):
        qx = 100 + i * 100
        qy = 230 + int(15 * math.sin(qx * 0.04))
        if (f + i) % 3 == 0:
            draw_text(draw, "?", qx, qy, color=GRAY, scale=3)


def sc_metamorphosing(draw, f, img):
    draw_clawd(draw, 24, 166, g)
    branch_y = 86
    draw.line([208, branch_y, 360, branch_y], fill=DARK_BROWN, width=5)
    draw.line([278, branch_y, 262, branch_y + 26], fill=DARK_BROWN, width=3)
    draw.line([318, branch_y, 334, branch_y + 22], fill=DARK_BROWN, width=3)

    if f <= 1:
        # Caterpillar on a leaf.
        draw.polygon([(240, 244), (330, 214), (350, 248), (270, 274)], fill=GREEN)
        draw.line([296, 226, 280, 246], fill=LIME, width=2)
        body_y = 224 - f * 4
        for i in range(5):
            draw.ellipse([246 + i * 18, body_y - (i % 2) * 4, 266 + i * 18, body_y + 16 - (i % 2) * 4], fill=GREEN)
        draw.ellipse([334, body_y - 2, 356, body_y + 18], fill=LIME)
        draw.line([348, body_y, 356, body_y - 8], fill=BLACK, width=1)
        draw.line([346, body_y + 4, 354, body_y - 4], fill=BLACK, width=1)
    elif f == 2:
        # Hanging J-shape before chrysalis.
        draw.line([300, branch_y, 300, 132], fill=WHITE, width=2)
        for i in range(4):
            draw.ellipse([286, 130 + i * 16, 314, 150 + i * 16], fill=GREEN)
        draw.ellipse([274, 176, 306, 200], fill=GREEN)
    elif f == 3:
        # Chrysalis.
        draw.line([300, branch_y, 300, 132], fill=WHITE, width=2)
        draw.ellipse([282, 126, 318, 202], fill=DARK_BROWN)
        draw.arc([286, 136, 314, 198], 200, 340, fill=BROWN, width=2)
    elif f == 4:
        # Chrysalis opening with butterfly emerging.
        draw.line([300, branch_y, 300, 132], fill=WHITE, width=2)
        draw.polygon([(286, 128), (304, 136), (292, 196)], fill=DARK_BROWN)
        draw.polygon([(314, 128), (296, 136), (308, 196)], fill=DARK_BROWN)
        body_x, body_y = 300, 170
        draw.rectangle([body_x - 2, body_y - 18, body_x + 2, body_y + 20], fill=BLACK)
        draw.polygon([(body_x, body_y), (body_x - 26, body_y - 18), (body_x - 18, body_y + 14)], fill=PURPLE)
        draw.polygon([(body_x, body_y), (body_x + 26, body_y - 18), (body_x + 18, body_y + 14)], fill=PINK)
    else:
        # Fully transformed butterfly.
        body_x, body_y = 302, 176
        draw.rectangle([body_x - 2, body_y - 18, body_x + 2, body_y + 20], fill=BLACK)
        draw.line([body_x, body_y - 18, body_x - 8, body_y - 30], fill=BLACK, width=1)
        draw.line([body_x, body_y - 18, body_x + 8, body_y - 30], fill=BLACK, width=1)
        draw.polygon([(body_x, body_y), (body_x - 38, body_y - 26), (body_x - 28, body_y + 6), (body_x - 10, body_y + 16)], fill=PURPLE)
        draw.polygon([(body_x, body_y), (body_x + 38, body_y - 26), (body_x + 28, body_y + 6), (body_x + 10, body_y + 16)], fill=PINK)
        draw.polygon([(body_x, body_y + 8), (body_x - 28, body_y + 10), (body_x - 16, body_y + 34)], fill=YELLOW)
        draw.polygon([(body_x, body_y + 8), (body_x + 28, body_y + 10), (body_x + 16, body_y + 34)], fill=LIGHT_BLUE)
        for sx, sy in [(258, 142), (338, 146), (320, 228)]:
            draw_text(draw, "*", sx, sy, color=YELLOW, scale=3)


def sc_moseying(draw, f, img):
    walk_x = 60 + f * 12
    draw_clawd(draw, walk_x, 170, g)
    hx = walk_x - g
    hy = 170 - int(g * 1.6)
    draw.rectangle([hx-g, hy+g, hx+11*g, hy+g+g//3], fill=BROWN)
    draw.rectangle([hx+2*g, hy, hx+8*g, hy+g+g//2], fill=BROWN)
    draw.rectangle([hx+2*g, hy+g//2, hx+8*g, hy+g//2+g//4], fill=DARK_BROWN)
    for i in range(2):
        tx = 300 - f * 8 + i * 80
        ty = 280 + i * 10
        draw.ellipse([tx, ty, tx+20, ty+20], outline=BROWN, width=2)
    draw.rectangle([20, 305, 380, 310], fill=(200, 180, 100))


def sc_mulling(draw, f, img):
    draw_clawd(draw, 40, 160, g)
    mx, my = 270, 210
    draw.rectangle([mx, my, mx+50, my+55], fill=RED)
    draw.rectangle([mx+5, my+5, mx+45, my+50], fill=(150, 30, 30))
    draw.rectangle([mx+50, my+15, mx+62, my+35], fill=RED)
    draw.line([mx+15, my+8, mx+40, my+8], fill=BROWN, width=3)
    draw_steam(draw, mx+20, my-15, f)
    n = ((f % 6) // 2) + 1
    for d in range(n):
        draw.ellipse([180+d*15, 130, 187+d*15, 137], fill=DARK_GRAY)


def sc_mustering(draw, f, img):
    draw_clawd(draw, 30, 155, g)
    positions = [
        (220, 250), (245, 250), (270, 250), (295, 250), (320, 250),
        (230, 270), (255, 270), (280, 270), (305, 270),
    ]
    for i, (px, py) in enumerate(positions):
        if i <= f + 2:
            draw.rectangle([px, py, px+12, py+16], fill=CORAL)
            draw.rectangle([px+3, py+2, px+9, py+6], fill=BLACK)
    draw.rectangle([350, 200, 354, 260], fill=DARK_BROWN)
    draw.rectangle([354, 200, 380, 220], fill=RED)


def sc_musing(draw, f, img):
    bob = [0, -1, -2, -1, 0, 1][f]
    draw_clawd(draw, 120, 185 + bob, g, blink=(f == 4))
    shapes = [(80, 60, PINK), (200, 40, TEAL), (300, 80, PURPLE),
              (160, 70, YELLOW), (260, 50, ORANGE)]
    for i, (sx, sy, c) in enumerate(shapes):
        drift = ((f + i) % 3) * 5
        if (f + i) % 2 == 0:
            draw.ellipse([sx-6, sy-6+drift, sx+6, sy+6+drift], fill=c)
        else:
            draw.rectangle([sx-5, sy-5+drift, sx+5, sy+5+drift], fill=c)


def sc_nesting(draw, f, img):
    draw_clawd(draw, 30, 155, g)
    nx, ny = 260, 240
    draw.ellipse([nx, ny, nx+100, ny+40], fill=BROWN)
    draw.ellipse([nx+5, ny+5, nx+95, ny+35], fill=DARK_BROWN)
    for i in range(6):
        sx = nx + 10 + i * 14
        draw.line([sx, ny+8, sx+8, ny-3], fill=BROWN, width=2)
    eggs = min(f + 1, 4)
    for i in range(eggs):
        ex = nx + 20 + i * 18
        draw.ellipse([ex, ny+12, ex+12, ny+28], fill=WHITE)


def sc_noodling(draw, f, img):
    draw_clawd(draw, 30, 165, g)
    gx2, gy2 = 250, 170
    draw.ellipse([gx2, gy2, gx2+70, gy2+90], fill=BROWN)
    draw.ellipse([gx2+5, gy2+5, gx2+65, gy2+85], fill=DARK_BROWN)
    draw.ellipse([gx2+25, gy2+35, gx2+45, gy2+55], fill=BLACK)
    draw.rectangle([gx2+32, gy2-50, gx2+38, gy2+10], fill=BROWN)
    draw.rectangle([gx2+25, gy2-55, gx2+45, gy2-45], fill=DARK_BROWN)
    for i in range(3):
        ny2 = 100 + ((f * 10 + i * 20) % 80)
        nx2 = 200 + i * 40
        if (f + i) % 2 == 0:
            draw_music_note(draw, nx2, ny2, CORAL)


def sc_nucleating(draw, f, img):
    draw_clawd(draw, 30, 170, g)
    cx2, cy2 = 290, 180
    cr = 4 + f * 3
    draw.ellipse([cx2-cr, cy2-cr, cx2+cr, cy2+cr], fill=TEAL)
    for i in range(8):
        a = math.radians(i * 45 + f * 20)
        r = 60 - f * 6
        px = cx2 + int(r * math.cos(a))
        py = cy2 + int(r * math.sin(a))
        draw.ellipse([px-3, py-3, px+3, py+3], fill=LIGHT_BLUE)


def sc_osmosing(draw, f, img):
    draw_clawd(draw, 30, 160, g)
    mx = 250
    for y in range(80, 300, 12):
        draw.rectangle([mx, y, mx+3, y+6], fill=GRAY)
    for i in range(5):
        px = 220 - f * 6 + i * 4 if i % 2 == 0 else 280 + f * 6 - i * 4
        py = 100 + i * 35 + ((f + i) % 3) * 5
        c = BLUE if i % 2 == 0 else GREEN
        draw.ellipse([px-4, py-4, px+4, py+4], fill=c)


def sc_percolating(draw, f, img):
    draw_clawd(draw, 30, 155, g)
    px2, py2 = 260, 120
    pw, ph = 80, 140
    draw.rectangle([px2, py2, px2+pw, py2+ph], fill=GRAY)
    draw.rectangle([px2+pw, py2+30, px2+pw+15, py2+60], fill=GRAY)
    draw.rectangle([px2+10, py2+80, px2+pw-10, py2+ph-5], fill=DARK_BROWN)
    for i in range(4):
        bx = px2 + 20 + i * 15
        by = py2 + ph - 20 - ((f * 8 + i * 10) % 60)
        draw.ellipse([bx, by, bx+6, by+6], fill=LIGHT_BLUE)
    draw_steam(draw, px2+35, py2-15, f)


def sc_perusing(draw, f, img):
    draw_clawd(draw, 40, 165, g)
    bkx, bky = 240, 130
    draw.rectangle([bkx, bky, bkx+130, bky+160], fill=WHITE)
    draw.rectangle([bkx, bky, bkx+130, bky+160], outline=BROWN, width=2)
    for i in range(8):
        ly = bky + 15 + i * 17
        lw = 110 if i < 7 else 60
        draw.rectangle([bkx+10, ly, bkx+10+lw, ly+4], fill=GRAY)
    hl = bky + 15 + (f % 6) * 17
    draw.rectangle([bkx+8, hl-2, bkx+125, hl+8], fill=(255, 255, 200))


def sc_philosophising(draw, f, img):
    draw_clawd(draw, 120, 190, g)
    draw.rectangle([300, 120, 320, 300], fill=GRAY)
    draw.rectangle([295, 115, 325, 125], fill=DARK_GRAY)
    draw.rectangle([295, 295, 325, 305], fill=DARK_GRAY)
    draw_thought_bubble(draw, 160, 60, 90, 50)
    syms = ["?", "!", "*"]
    draw_text(draw, syms[f % 3], 195, 75, color=TEAL, scale=5)


def sc_pollinating(draw, f, img):
    draw_clawd(draw, 118, 170, g, blink=(f == 4))
    flowers = [
        (74, 272, PINK, 16),
        (194, 252, (255, 175, 95), 20),
        (324, 274, PURPLE, 18),
    ]
    for i, (fx2, fy2, fc, fs) in enumerate(flowers):
        sway = [-3, -1, 0, 1, 3, 1][(f + i) % 6]
        draw.line([fx2, fy2 + 8, fx2, fy2 + 58], fill=GREEN, width=3)
        draw.line([fx2, fy2 + 30, fx2 - 14, fy2 + 40], fill=GREEN, width=2)
        draw.line([fx2, fy2 + 38, fx2 + 14, fy2 + 50], fill=GREEN, width=2)
        draw_fancy_flower(draw, fx2 + sway, fy2, petal_color=fc, size=fs, pulse=1 if (f + i) % 2 == 0 else 0)
        if (f + i) % 2 == 0:
            draw_text(draw, "*", fx2 - 10, fy2 - 36, color=YELLOW, scale=2)

    pollen_routes = [
        (74, 268, 194, 252),
        (194, 252, 324, 274),
        (324, 274, 194, 252),
    ]
    for i, (sx, sy, ex, ey) in enumerate(pollen_routes):
        for step in range(4):
            t = ((f + step + i * 2) % 6) / 5.0
            px = int(sx + (ex - sx) * t)
            py = int(sy + (ey - sy) * t - math.sin(t * math.pi) * 30)
            draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=YELLOW)
            if step % 2 == 0:
                draw.ellipse([px - 1, py - 1, px + 1, py + 1], fill=WHITE)


def sc_pondering(draw, f, img):
    bob = [0, -1, -2, -1, 0, 1][f]
    draw_clawd(draw, 120, 185 + bob, g)
    draw.rectangle([120+7*g, 185+bob+g, 120+8*g, 185+bob+2*g], fill=CORAL)
    n = ((f % 6) // 2) + 1
    for d in range(n):
        dx = 200 + d * 18
        draw.ellipse([dx, 120, dx+8, 128], fill=DARK_GRAY)


def sc_pontificating(draw, f, img):
    draw_clawd(draw, 60, 175, g, blink=(f % 3 == 0))
    draw.rectangle([250, 220, 350, 300], fill=BROWN)
    draw.rectangle([245, 215, 355, 225], fill=DARK_BROWN)
    for i in range(min(f + 1, 4)):
        lx = 240 - i * 15
        ly = 150 + i * 20
        lw = 40 + i * 10
        draw.rectangle([lx, ly, lx+lw, ly+4], fill=GRAY)


def sc_precipitating(draw, f, img):
    draw_clawd(draw, 30, 155, g)
    bx2, by2 = 250, 140
    draw.rectangle([bx2, by2, bx2+80, by2+120], fill=(200, 200, 220))
    lh = 80 + f * 5
    draw.rectangle([bx2+5, by2+120-lh, bx2+75, by2+115], fill=LIGHT_BLUE)
    ph = f * 8
    draw.rectangle([bx2+10, by2+115-ph, bx2+70, by2+115], fill=WHITE)


def sc_prestidigitating(draw, f, img):
    draw_clawd(draw, 80, 170, g)
    for i in range(5):
        a = -20 + i * 10 + f * 3
        cx2, cy2 = 280, 200
        rx = cx2 + int(30 * math.cos(math.radians(a)))
        ry = cy2 + int(20 * math.sin(math.radians(a)))
        draw.rectangle([rx-8, ry-12, rx+8, ry+12], fill=WHITE)
        draw.rectangle([rx-6, ry-10, rx+6, ry+10], fill=[RED, BLUE, GREEN, YELLOW, PURPLE][i])
    for i in range(3):
        sx = 250 + ((f * 15 + i * 30) % 100)
        sy = 130 + ((f * 10 + i * 20) % 50)
        draw.rectangle([sx, sy, sx+3, sy+3], fill=YELLOW)


def sc_proofing(draw, f, img):
    draw_clawd(draw, 30, 155, g)
    dx, dy = 260, 200
    rise = f * 8
    draw.rectangle([dx-5, dy+50, dx+75, dy+60], fill=BROWN)
    draw.ellipse([dx, dy+40-rise, dx+70, dy+55], fill=(240, 220, 170))
    draw_steam(draw, dx+30, dy+20-rise, f)


def sc_propagating(draw, f, img):
    draw_clawd(draw, 30, 170, g)
    nodes = [(250, 180), (300, 140), (350, 200), (280, 240), (320, 100)]
    for i, (nx2, ny2) in enumerate(nodes):
        if i <= f:
            draw.ellipse([nx2-8, ny2-8, nx2+8, ny2+8], fill=TEAL)
            if i > 0:
                px, py = nodes[i-1]
                draw.line([px, py, nx2, ny2], fill=GRAY, width=2)


def sc_puttering(draw, f, img):
    walk = f * 8
    draw_clawd(draw, 50 + walk, 170, g)
    items = [(200, 260, GRAY, 15), (260, 255, BROWN, 12), (320, 260, GREEN, 10), (160, 265, BLUE, 11)]
    for ix, iy, ic, isz in items:
        draw.rectangle([ix, iy, ix+isz, iy+isz], fill=ic)


def sc_puzzling(draw, f, img):
    draw_clawd(draw, 30, 165, g)
    colors2 = [RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE]
    for i in range(min(f + 1, 6)):
        px = 200 + (i % 3) * 50
        py = 140 + (i // 3) * 55
        draw.rectangle([px, py, px+40, py+40], fill=colors2[i])
        draw.rectangle([px, py, px+40, py+40], outline=BLACK, width=1)
    if f < 4:
        draw_text(draw, "?", 320, 120, color=GRAY, scale=4)


def sc_quantumizing(draw, f, img):
    draw_clawd(draw, 120, 182, g, blink=(f == 3))
    cx2, cy2 = 120 + 4 * g, 94
    glow = 10 + (f % 3) * 4
    draw.ellipse([cx2 - glow, cy2 - glow, cx2 + glow, cy2 + glow], fill=(255, 210, 130))
    draw.ellipse([cx2 - 8, cy2 - 8, cx2 + 8, cy2 + 8], fill=RED)
    draw.ellipse([cx2 - 20, cy2 - 6, cx2 - 8, cy2 + 6], fill=BLUE)
    draw.ellipse([cx2 + 8, cy2 - 6, cx2 + 20, cy2 + 6], fill=PURPLE)
    draw.line([cx2 - 8, cy2, cx2 + 8, cy2], fill=WHITE, width=2)
    orbit_boxes = [
        (cx2 - 58, cy2 - 24, cx2 + 58, cy2 + 24, BLUE),
        (cx2 - 52, cy2 - 36, cx2 + 52, cy2 + 36, TEAL),
        (cx2 - 34, cy2 - 54, cx2 + 34, cy2 + 54, PURPLE),
        (cx2 - 70, cy2 - 12, cx2 + 70, cy2 + 12, LIGHT_BLUE),
    ]
    for i, (x0, y0, x1, y1, color) in enumerate(orbit_boxes):
        draw.arc([x0, y0, x1, y1], f * 24 + i * 28, f * 24 + i * 28 + 220, fill=color, width=2)
    for i in range(6):
        angle = math.radians(f * 30 + i * 60)
        rx = 62 if i % 2 == 0 else 46
        ry = 24 if i % 2 == 0 else 42
        px = cx2 + int(rx * math.cos(angle))
        py = cy2 + int(ry * math.sin(angle))
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=YELLOW if i % 2 == 0 else WHITE)
    for sx, sy in [(cx2 - 76, cy2 - 28), (cx2 + 68, cy2 - 36), (cx2 - 58, cy2 + 42), (cx2 + 58, cy2 + 34)]:
        if (sx + sy + f) % 2 == 0:
            draw_text(draw, "*", sx, sy, color=YELLOW, scale=2)


def sc_razzmatazzing(draw, f, img):
    draw_clawd(draw, 120, 170, g)
    for i in range(5):
        lx = 40 + i * 80
        c = [RED, YELLOW, BLUE, PINK, GREEN][i]
        if (f + i) % 2 == 0:
            draw.polygon([(lx, 20), (lx-20, 120), (lx+20, 120)], fill=c)
    rng = random.Random(f * 13)
    for _ in range(8):
        sx = rng.randint(20, 380)
        sy = rng.randint(20, 340)
        draw.rectangle([sx, sy, sx+3, sy+3], fill=YELLOW)


def sc_reticulating(draw, f, img):
    draw_clawd(draw, 30, 170, g)
    gx2, gy2 = 200, 100
    lines = min(f + 1, 6)
    for i in range(lines):
        draw.line([gx2, gy2+i*30, gx2+160, gy2+i*30], fill=TEAL, width=1)
        draw.line([gx2+i*32, gy2, gx2+i*32, gy2+150], fill=TEAL, width=1)
    for i in range(min(lines, 5)):
        for j in range(min(lines, 5)):
            draw.ellipse([gx2+i*32-2, gy2+j*30-2, gx2+i*32+2, gy2+j*30+2], fill=TEAL)


def sc_ruminating(draw, f, img):
    clawd_x, clawd_y = 48, 184
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 4))
    draw.rectangle([clawd_x + 7 * g, clawd_y + g + 6, clawd_x + 8 * g + 2, clawd_y + 2 * g + 8], fill=CORAL)
    bubble_x, bubble_y, bubble_w, bubble_h = 176, 56, 160, 104
    draw_thought_bubble(draw, bubble_x, bubble_y, bubble_w, bubble_h)
    loop_cx = bubble_x + bubble_w // 2
    loop_cy = bubble_y + 54
    draw.arc([loop_cx - 44, loop_cy - 32, loop_cx + 44, loop_cy + 32], 28, 328, fill=TEAL, width=2)
    draw.polygon([(loop_cx + 40, loop_cy - 8), (loop_cx + 54, loop_cy - 4), (loop_cx + 42, loop_cy + 8)], fill=TEAL)
    for i in range(3):
        angle = math.radians(f * 22 + i * 120)
        px = loop_cx + int(38 * math.cos(angle))
        py = loop_cy + int(24 * math.sin(angle))
        draw.rectangle([px - 10, py - 8, px + 10, py + 8], fill=WHITE, outline=GRAY)
        draw.rectangle([px - 6, py - 4, px + 6, py - 1], fill=YELLOW if i == f % 3 else GRAY)
    draw.ellipse([loop_cx - 8, loop_cy - 8, loop_cx + 8, loop_cy + 8], fill=DARK_GRAY)


def sc_scheming(draw, f, img):
    clawd_x, clawd_y = 38, 170
    draw_clawd(draw, clawd_x, clawd_y, g, blink=False, wink="right" if f in [1, 4] else None)
    if f % 2 == 0:
        draw.rectangle([clawd_x + 2 * g, clawd_y + g + 2, clawd_x + 2 * g + 5, clawd_y + g + 7], fill=RED)
    bx, by = 214, 86
    draw.rectangle([bx, by, 370, 236], fill=(125, 92, 58), outline=DARK_BROWN)
    notes = [
        (228, 102, 44, 30, (255, 245, 165)),
        (308, 96, 42, 28, (220, 240, 255)),
        (244, 166, 52, 32, (255, 220, 180)),
        (322, 174, 34, 30, (255, 235, 175)),
        (278, 132, 38, 26, (250, 250, 250)),
    ]
    for i, (nx2, ny2, nw, nh, nc) in enumerate(notes):
        draw.rectangle([nx2, ny2, nx2 + nw, ny2 + nh], fill=nc, outline=GRAY)
        draw.rectangle([nx2 + 10, ny2 - 4, nx2 + 16, ny2 + 2], fill=RED)
        for line in range(2):
            draw.rectangle([nx2 + 6, ny2 + 8 + line * 8, nx2 + nw - 6, ny2 + 10 + line * 8], fill=GRAY)
        if i == f % len(notes):
            draw.rectangle([nx2 + 4, ny2 + 4, nx2 + nw - 4, ny2 + nh - 4], outline=RED, width=1)
    connections = [
        ((250, 118), (327, 110)),
        ((246, 182), (295, 146)),
        ((331, 188), (295, 146)),
        ((250, 118), (246, 182)),
    ]
    for i, (start, end) in enumerate(connections):
        if i <= min(f, len(connections) - 1):
            draw.line([start, end], fill=RED, width=2)
    if f >= 3:
        draw_text(draw, "*", 354, 78 + (f % 2) * 4, color=YELLOW, scale=2)


def sc_schlepping(draw, f, img):
    walk = f * 6
    draw_clawd(draw, 40 + walk, 170, g)
    bx2 = 40 + walk + 2 * g
    by2 = 170 - g
    draw.rectangle([bx2, by2, bx2+5*g, by2+3*g], fill=BROWN)
    draw.rectangle([bx2, by2, bx2+5*g, by2+3*g], outline=DARK_BROWN, width=1)
    if f % 2 == 0:
        draw.ellipse([40+walk+8*g, 170-5, 40+walk+8*g+4, 170+3], fill=BLUE)


def sc_scurrying(draw, f, img):
    speed = f * 20
    draw_clawd(draw, 30 + speed, 170, g)
    sweat_x = 30 + speed + 3 * g
    sweat_y = 170 - 18 + [-2, -5, -2, 0, -2, 0][f]
    draw_sweat_drop(draw, sweat_x, sweat_y, scale=4 if f % 2 == 0 else 5, color=LIGHT_BLUE)
    for i in range(5):
        ly = 180 + i * 12
        lx = 20 + speed
        draw.line([lx-40, ly, lx-10, ly], fill=GRAY, width=1)
    if f > 0:
        for i in range(f):
            dx = 20 + i * 15
            draw.ellipse([dx, 280, dx+12, 292], fill=(200, 200, 200))


def sc_seasoning(draw, f, img):
    draw_clawd(draw, 30, 155, g)
    px2, py2 = 260, 230
    draw.ellipse([px2, py2, px2+90, py2+40], fill=WHITE)
    draw.ellipse([px2+10, py2+5, px2+80, py2+35], fill=(200, 180, 100))
    shx, shy = 240, 180
    draw.rectangle([shx, shy, shx+20, shy+35], fill=WHITE)
    draw.rectangle([shx+30, shy, shx+50, shy+35], fill=DARK_GRAY)
    for i in range(4):
        py3 = py2 - ((f * 6 + i * 8) % 40)
        px3 = px2 + 20 + i * 15
        c = WHITE if i % 2 == 0 else BLACK
        draw.rectangle([px3, py3, px3+2, py3+2], fill=c)


def sc_shimmying(draw, f, img):
    sway = [-6, -3, 0, 3, 6, 3][f]
    draw_clawd(draw, 130 + sway, 170, g)
    for i in range(3):
        ly = 185 + i * 15
        draw.line([80, ly, 110, ly], fill=CORAL, width=1)
        draw.line([290, ly, 320, ly], fill=CORAL, width=1)
    draw_music_note(draw, 100, 100 + ((f * 8) % 30), PINK)
    draw_music_note(draw, 280, 80 + ((f * 10) % 40), PURPLE)


def sc_shucking(draw, f, img):
    draw_clawd(draw, 34, 162, g, blink=(f == 4))
    cx2, cy2 = 292, 202
    spread = [12, 20, 28, 38, 48, 56][f]
    draw.line([34 + 10 * g, 162 + 2 * g + g // 2, cx2 - 30, cy2 + 6], fill=GREEN, width=2)
    draw.ellipse([cx2 - 20, cy2 - 52, cx2 + 20, cy2 + 54], fill=YELLOW, outline=ORANGE)
    for row in range(6):
        for col in range(3):
            kx = cx2 - 12 + col * 10 + (row % 2) * 2
            ky = cy2 - 38 + row * 15
            if f >= row // 2:
                draw.ellipse([kx - 3, ky - 4, kx + 3, ky + 4], fill=ORANGE)
    draw.polygon([(cx2 - 18, cy2 - 36), (cx2 - 34 - spread, cy2 - 18), (cx2 - 26 - spread, cy2 + 60), (cx2 - 4, cy2 + 30)],
                 fill=GREEN)
    draw.polygon([(cx2 + 18, cy2 - 36), (cx2 + 34 + spread, cy2 - 10), (cx2 + 28 + spread, cy2 + 64), (cx2 + 6, cy2 + 28)],
                 fill=LIME)
    draw.polygon([(cx2 - 8, cy2 + 30), (cx2 - 34, cy2 + 80), (cx2 + 10, cy2 + 54)], fill=GREEN)
    for i in range(5):
        silk_x = cx2 - 10 + i * 5
        draw.line([silk_x, cy2 - 54, silk_x - 8 + i, cy2 - 74 - (f % 2) * 4], fill=YELLOW, width=1)
    if f >= 3:
        for sx, sy in [(cx2 - 52, cy2 - 24), (cx2 + 44, cy2 - 10), (cx2 + 18, cy2 + 74)]:
            draw_text(draw, "*", sx, sy, color=YELLOW, scale=2)


def sc_simmering(draw, f, img):
    draw_clawd(draw, 30, 150, g)
    px2, py2 = 240, 190
    pw2 = 120
    draw.rectangle([px2, py2+60, px2+pw2, py2+75], fill=DARK_GRAY)
    draw.rectangle([px2+5, py2, px2+pw2-5, py2+60], fill=GRAY)
    draw.rectangle([px2-5, py2-5, px2+pw2+5, py2+8], fill=DARK_GRAY)
    draw.rectangle([px2+10, py2+12, px2+pw2-10, py2+55], fill=RED)
    draw_bubbles(draw, px2+20, py2+25, pw2-40, f, (255, 200, 200))
    draw_steam(draw, px2+50, py2-20, f)


def sc_slithering(draw, f, img):
    draw_clawd(draw, 120, 170, g)
    for x in range(0, CANVAS, 6):
        y2 = 250 + int(25 * math.sin((x + f * 30) * 0.04))
        c = GREEN if x % 12 < 6 else LIME
        draw.rectangle([x, y2, x+5, y2+8], fill=c)
    for i in range(5):
        bx = 50 + i * 70 + f * 5
        by = 250 + int(25 * math.sin((bx + f * 30) * 0.04))
        draw_text(draw, "0" if i % 2 == 0 else "1", bx, by-10, color=WHITE, scale=2)


def sc_smooshing(draw, f, img):
    draw_clawd(draw, 120, 175, g)
    squeeze = f * 4
    ox2, oy2 = 250, 180
    w2 = 50 + squeeze
    h2 = max(10, 50 - squeeze)
    draw.rectangle([ox2, oy2+25-h2//2, ox2+w2, oy2+25+h2//2], fill=BLUE)
    draw.polygon([(ox2-15, oy2+25), (ox2, oy2+15), (ox2, oy2+35)], fill=RED)
    draw.polygon([(ox2+w2+15, oy2+25), (ox2+w2, oy2+15), (ox2+w2, oy2+35)], fill=RED)


def sc_spelunking(draw, f, img):
    draw.polygon([(0, 100), (50, 50), (150, 80), (200, 40), (300, 70), (380, 50),
                  (400, 100), (400, 400), (0, 400)], fill=DARK_GRAY)
    draw.polygon([(0, 120), (70, 80), (160, 100), (220, 60), (310, 90),
                  (400, 70), (400, 400), (0, 400)], fill=(50, 50, 50))
    clawd_x, clawd_y = 100, 200
    draw_clawd(draw, clawd_x, clawd_y, g)

    light_y = clawd_y + 2 * g + g // 2 + [-2, 0, 1, 0, -1, 0][f]
    light_x = clawd_x + 10 * g - 6
    beam_tip_x = 360
    beam_top_y = 145 + [0, -4, 0, 2, 0, -2][f]
    beam_bottom_y = 235 + [0, -2, 0, 2, 0, 2][f]

    # Keep the cave scene intact, but move the flashlight beam to Clawd's hand.
    draw.rectangle([light_x-14, light_y-5, light_x-4, light_y+5], fill=DARK_BROWN)
    draw.rectangle([light_x-4, light_y-4, light_x+4, light_y+4], fill=YELLOW)
    draw.polygon([(light_x+4, light_y), (beam_tip_x, beam_top_y), (beam_tip_x, beam_bottom_y)],
                 fill=(255, 244, 170))
    for i in range(5):
        sx = 50 + i * 75
        draw.polygon([(sx, 120), (sx+8, 120), (sx+4, 160+i*5)], fill=GRAY)


def sc_spinning(draw, f, img):
    cx2, cy2 = 200, 178
    spin = f * 60
    pulse = [0, 4, 8, 4, 0, -2][f % NUM_FRAMES]

    ring_specs = [
        (102 + pulse // 2, 90 + pulse // 3, spin, 210, CORAL, 5),
        (88, 76, (330 - spin * 2) % 360, 150, PINK, 4),
        (72, 60, (spin * 3 + 30) % 360, 190, TEAL, 4),
        (56, 46, (300 - spin * 3) % 360, 118, YELLOW, 3),
    ]
    for rx, ry, start, span, color, width in ring_specs:
        draw.arc([cx2 - rx, cy2 - ry, cx2 + rx, cy2 + ry],
                 start, start + span, fill=color, width=width)
        accent_start = (start + span + 16) % 360
        draw.arc([cx2 - rx, cy2 - ry, cx2 + rx, cy2 + ry],
                 accent_start, accent_start + 52, fill=WHITE, width=max(1, width - 2))

    for i in range(10):
        angle = math.radians(spin * 2 + i * 36)
        inner_r = 36 + (i % 2) * 7
        outer_r = 52 + ((f + i) % 3) * 4
        x1 = cx2 + int(math.cos(angle) * inner_r)
        y1 = cy2 + int(math.sin(angle) * inner_r * 0.82)
        x2 = cx2 + int(math.cos(angle) * outer_r)
        y2 = cy2 + int(math.sin(angle) * outer_r * 0.82)
        draw.line([x1, y1, x2, y2], fill=WHITE if i % 2 else YELLOW, width=2)

    orbiters = [
        (116, 0.84, CORAL, 6, spin * 2 + 15),
        (108, 0.78, PINK, 5, spin * 2 + 105),
        (110, 0.82, TEAL, 6, spin * 2 + 195),
        (118, 0.80, YELLOW, 5, spin * 2 + 285),
    ]
    for orbit_r, squash, color, size, angle_deg in orbiters:
        angle = math.radians(angle_deg)
        px = cx2 + int(math.cos(angle) * orbit_r)
        py = cy2 + int(math.sin(angle) * orbit_r * squash)
        tail_x = cx2 + int(math.cos(angle - 0.35) * (orbit_r - 12))
        tail_y = cy2 + int(math.sin(angle - 0.35) * (orbit_r - 12) * squash)
        tail_color = LIGHT_BLUE if color == TEAL else LIGHT_CORAL
        draw.rectangle([tail_x - 2, tail_y - 2, tail_x + 2, tail_y + 2], fill=tail_color)
        draw.ellipse([px - size, py - size, px + size, py + size], fill=color)
        twinkle = max(2, size - 2)
        draw.rectangle([px - twinkle, py - 1, px + twinkle, py + 1], fill=WHITE)
        draw.rectangle([px - 1, py - twinkle, px + 1, py + twinkle], fill=WHITE)

    sparkle_specs = [
        (cx2 - 116, cy2 - 48, WHITE),
        (cx2 + 120, cy2 - 24, YELLOW),
        (cx2 - 104, cy2 + 54, LIGHT_BLUE),
        (cx2 + 110, cy2 + 66, PINK),
    ]
    for i, (sx, sy, color) in enumerate(sparkle_specs):
        arm = 5 + ((f + i) % 3) * 2
        draw.rectangle([sx - arm, sy - 1, sx + arm, sy + 1], fill=color)
        draw.rectangle([sx - 1, sy - arm, sx + 1, sy + arm], fill=color)
        draw.rectangle([sx - 2, sy - 2, sx + 2, sy + 2], fill=color)

    clawd_grid = 11
    bob = [0, -2, -4, -2, 0, 2][f % NUM_FRAMES]
    draw_clawd(draw, cx2 - 4 * clawd_grid, cy2 - 4 * clawd_grid + bob, grid=clawd_grid)


def sc_stewing(draw, f, img):
    draw_clawd_head_only(draw, 110, 140, g, blink=(f == 4))
    px2, py2 = 80, 195
    pw2 = 240
    draw.rectangle([px2, py2, px2+pw2, py2+80], fill=GRAY)
    draw.rectangle([px2-8, py2-6, px2+pw2+8, py2+10], fill=DARK_GRAY)
    draw.rectangle([px2+8, py2+14, px2+pw2-8, py2+72], fill=(150, 80, 30))
    items = [(ORANGE, px2+30), (GREEN, px2+80), (RED, px2+130), (YELLOW, px2+180)]
    for i, (c, ix) in enumerate(items):
        bob = ((f + i) % 3) * 4
        draw.ellipse([ix, py2+25+bob, ix+15, py2+40+bob], fill=c)
    draw_steam(draw, px2+pw2//2, py2-15, f)


def sc_sussing(draw, f, img):
    draw_clawd(draw, 40, 165, g)
    lens_x = 220 + f * 20
    lens_y = 190
    draw.ellipse([lens_x-20, lens_y-20, lens_x+20, lens_y+20], outline=DARK_BROWN, width=3)
    draw.line([lens_x+14, lens_y+14, lens_x+30, lens_y+30], fill=DARK_BROWN, width=4)
    if f >= 3:
        draw.rectangle([lens_x-8, lens_y-5, lens_x+8, lens_y+5], fill=YELLOW)
        draw_text(draw, "!", lens_x-4, lens_y-15, color=RED, scale=3)


def sc_swirling(draw, f, img):
    draw_clawd(draw, 120, 175, g)
    cx2, cy2 = 120 + 4 * g, 100
    for i in range(20):
        a = math.radians(i * 30 + f * 25)
        r = 10 + i * 4
        px = cx2 + int(r * math.cos(a))
        py = cy2 + int(r * math.sin(a))
        c = [CORAL, PINK, PURPLE, TEAL][i % 4]
        draw.rectangle([px-2, py-2, px+2, py+2], fill=c)


def sc_symbioting(draw, f, img):
    gap = [20, 15, 10, 5, 2, 0][f]
    draw_clawd(draw, 80 - gap, 170, g)
    dx = 220 + gap
    for gy2 in range(8):
        for gx2 in range(8):
            if (gx2 + gy2) % 2 == 0:
                draw.rectangle([dx+gx2*g, 170+gy2*g, dx+(gx2+1)*g-1, 170+(gy2+1)*g-1], fill=TEAL)
    if f >= 3:
        for i in range(3):
            ly = 185 + i * 15
            draw.line([80-gap+10*g, ly, dx, ly], fill=YELLOW, width=1)


def sc_synthesizing(draw, f, img):
    draw_clawd(draw, 30, 160, g)
    kx, ky = 220, 240
    draw.rectangle([kx, ky, kx+150, ky+40], fill=BLACK)
    for i in range(10):
        draw.rectangle([kx+5+i*14, ky+5, kx+15+i*14, ky+35], fill=WHITE)
    pk = f % 10
    draw.rectangle([kx+5+pk*14, ky+5, kx+15+pk*14, ky+35], fill=GRAY)
    for i in range(3):
        wy = ky - 30 - i * 25
        for x in range(kx, kx+150, 4):
            y2 = wy + int(8 * math.sin((x + f * 20 + i * 30) * 0.08))
            c = [GREEN, TEAL, PURPLE][i]
            draw.rectangle([x, y2, x+3, y2+2], fill=c)


def sc_thundering(draw, f, img):
    draw_clawd(draw, 120, 185, g)
    for cx2, cy2 in [(100, 40), (200, 30), (300, 45)]:
        draw.ellipse([cx2-30, cy2-15, cx2+30, cy2+15], fill=DARK_GRAY)
        draw.ellipse([cx2-20, cy2-25, cx2+20, cy2+5], fill=DARK_GRAY)
    if f % 2 == 0:
        lx = 200
        draw.polygon([(lx, 55), (lx-15, 100), (lx+5, 95), (lx-10, 140),
                       (lx+20, 85), (lx, 90)], fill=YELLOW)


def sc_tinkering(draw, f, img):
    draw_clawd(draw, 30, 160, g)
    draw.rectangle([220, 260, 380, 272], fill=BROWN)
    items = [(230, 240, GRAY), (270, 245, BLUE), (310, 242, GREEN), (350, 248, RED)]
    for ix, iy, ic in items:
        draw.rectangle([ix, iy, ix+20, iy+18], fill=ic)
    sa = [-20, -10, 0, 10, 0, -10][f]
    sx, sy = 280, 230
    draw.line([sx, sy, sx+int(20*math.cos(math.radians(sa))),
               sy+int(20*math.sin(math.radians(sa)))], fill=YELLOW, width=2)


def sc_tomfoolering(draw, f, img):
    bounce = [0, -10, -18, -10, 0, 5][f]
    draw_clawd(draw, 130, 170 + bounce, g)
    hx = 130 + g
    hy = 170 + bounce - g
    draw.polygon([(hx, hy), (hx+3*g, hy-2*g), (hx+g, hy)], fill=RED)
    draw.polygon([(hx+3*g, hy), (hx+5*g, hy-2*g), (hx+5*g, hy)], fill=YELLOW)
    draw.ellipse([hx+3*g-4, hy-2*g-4, hx+3*g+4, hy-2*g+4], fill=GREEN)
    draw.ellipse([hx+5*g-4, hy-2*g-4, hx+5*g+4, hy-2*g+4], fill=BLUE)


def sc_topsy_turvying(draw, f, img):
    flip = f * 30
    draw_clawd(draw, 130, 170, g)
    for i in range(4):
        a = math.radians(flip + i * 90)
        r = 80
        ox2 = 200 + int(r * math.cos(a))
        oy2 = 180 + int(r * math.sin(a))
        c = [BLUE, GREEN, RED, YELLOW][i]
        draw.rectangle([ox2-8, oy2-8, ox2+8, oy2+8], fill=c)


def sc_transmuting(draw, f, img):
    draw_clawd(draw, 30, 160, g)
    bx2, by2 = 260, 200
    lead_w = max(0, 50 - f * 10)
    gold_w = min(50, f * 10)
    if lead_w > 0:
        draw.rectangle([bx2, by2, bx2+lead_w, by2+40], fill=DARK_GRAY)
    if gold_w > 0:
        draw.rectangle([bx2+lead_w, by2, bx2+50, by2+40], fill=YELLOW)
    draw.ellipse([bx2-10, by2-40, bx2+60, by2+60], outline=PURPLE, width=1)
    for i in range(3):
        if (f + i) % 2 == 0:
            sx = bx2 + 10 + i * 15
            sy = by2 - 10 - ((f + i) % 3) * 8
            draw.rectangle([sx, sy, sx+3, sy+3], fill=YELLOW)


def sc_twisting(draw, f, img):
    draw_clawd(draw, 120, 175, g)
    cx2, cy2 = 300, 160
    sz = 15
    offset = f * 3
    colors2 = [RED, BLUE, GREEN, YELLOW, ORANGE, WHITE]
    for row in range(3):
        for col in range(3):
            ci = (row * 3 + col + f) % 6
            draw.rectangle([cx2+col*sz+offset, cy2+row*sz, cx2+(col+1)*sz-1+offset, cy2+(row+1)*sz-1],
                            fill=colors2[ci])


def sc_undulating(draw, f, img):
    """Clawd rises and falls with layered ribbon-like waves sweeping across the scene."""
    bob = [8, 2, -6, -10, -4, 4][f]
    clawd_x = 44
    clawd_y = 162 + bob
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 3))

    base_y = 162
    wave_specs = [
        (LIGHT_BLUE, 0, 0.18, 18),
        (TEAL, 18, 0.22, 16),
        (BLUE, 34, 0.20, 14),
    ]
    for color, y_off, freq, amp in wave_specs:
        points = []
        for x in range(136, 391, 10):
            y = base_y + y_off + int(math.sin((x + f * 26) * freq) * amp)
            points.append((x, y))
        for p1, p2 in zip(points, points[1:]):
            draw.line([p1, p2], fill=color, width=4)
        for x, y in points[::3]:
            draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=color)

    ribbon_points = []
    for x in range(180, 372, 12):
        y = 250 + int(math.sin((x + f * 32) * 0.17) * 10)
        ribbon_points.append((x, y))
    for p1, p2 in zip(ribbon_points, ribbon_points[1:]):
        draw.line([p1, p2], fill=WHITE, width=2)

    for i in range(5):
        sx = 180 + i * 36
        sy = 118 + ((f + i) % 3) * 10
        draw_text(draw, "*", sx, sy, color=YELLOW if i % 2 == 0 else WHITE, scale=2)
    for i in range(4):
        px = 148 + i * 54
        py = 286 + int(math.sin((i * 20 + f * 30) * 0.1) * 6)
        draw.arc([px - 14, py - 6, px + 14, py + 6], 180, 360, fill=LIGHT_BLUE, width=2)


def sc_unfurling(draw, f, img):
    draw_clawd(draw, 30, 160, g)
    sx2, sy2 = 230, 120
    unroll = f * 25
    draw.rectangle([sx2, sy2, sx2+8, sy2+150], fill=DARK_BROWN)
    draw.rectangle([sx2+8, sy2, sx2+8+unroll, sy2+100], fill=(255, 240, 220))
    if unroll > 0:
        draw.ellipse([sx2+8+unroll-5, sy2, sx2+8+unroll+10, sy2+15], fill=(255, 240, 220))
    if f >= 3:
        for i in range(min(f-2, 3)):
            draw.rectangle([sx2+15, sy2+15+i*20, sx2+15+min(unroll-10, 60), sy2+20+i*20], fill=GRAY)


def sc_unravelling(draw, f, img):
    draw_clawd(draw, 30, 160, g)
    bx2, by2 = 280, 200
    br = max(5, 30 - f * 5)
    draw.ellipse([bx2-br, by2-br, bx2+br, by2+br], fill=RED)
    thread_len = f * 20
    points = [(bx2+br, by2)]
    for i in range(thread_len // 10):
        px = bx2 + br + i * 12
        py = by2 + int(10 * math.sin(i * 1.5))
        points.append((px, py))
    if len(points) > 1:
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]], fill=RED, width=2)


def sc_vibing(draw, f, img):
    sway = [-3, 0, 3, 0, -3, 0][f]
    draw_clawd(draw, 130 + sway, 170, g)
    hx = 130 + sway
    hy = 170
    draw.arc([hx+g, hy-g, hx+7*g, hy+g], 180, 360, fill=DARK_GRAY, width=3)
    draw.rectangle([hx, hy, hx+g+2, hy+g], fill=DARK_GRAY)
    draw.rectangle([hx+7*g-2, hy, hx+8*g, hy+g], fill=DARK_GRAY)
    for i in range(3):
        wx = 80 + i * 120
        wy = 120
        for y2 in range(40):
            x2 = wx + int(8 * math.sin((y2 + f * 5 + i * 10) * 0.3))
            draw.rectangle([x2, wy+y2*3, x2+3, wy+y2*3+2], fill=[PINK, PURPLE, TEAL][i])


def sc_wandering(draw, f, img):
    wx = 30 + f * 15
    draw_clawd(draw, wx, 175, g)
    for i in range(8):
        dx = wx - 10 - i * 15
        if dx > 5:
            draw.ellipse([dx, 290, dx+6, 296], fill=GRAY)
    draw_text(draw, "?", wx+3*g, 175-g-15, color=GRAY, scale=3)
    draw.rectangle([340, 180, 345, 300], fill=BROWN)
    draw.rectangle([320, 175, 370, 195], fill=BROWN)
    draw.polygon([(370, 175), (385, 185), (370, 195)], fill=BROWN)


def sc_whirring(draw, f, img):
    draw_clawd(draw, 30, 160, g)
    draw_gear(draw, 260, 180, 25, f)
    draw_gear(draw, 320, 210, 18, f + 1)
    draw_gear(draw, 280, 240, 15, f + 2)
    for i in range(4):
        a = math.radians(f * 30 + i * 90)
        r = 45
        sx = 260 + int(r * math.cos(a))
        sy = 180 + int(r * math.sin(a))
        draw.line([sx, sy, sx+int(8*math.cos(a)), sy+int(8*math.sin(a))], fill=GRAY, width=1)


def sc_wibbling(draw, f, img):
    wobble = [0, 4, 6, 4, 0, -4][f]
    draw_clawd(draw, 130 + wobble, 170, g)
    for i in range(3):
        wy = 175 + i * g * 2
        wave = int(4 * math.sin((wy + f * 20) * 0.1))
        draw.rectangle([130+wobble-2*g-5+wave, wy, 130+wobble-2*g+wave, wy+3], fill=LIGHT_CORAL)
        draw.rectangle([130+wobble+10*g+wave, wy, 130+wobble+10*g+5+wave, wy+3], fill=LIGHT_CORAL)


def sc_wizarding(draw, f, img):
    clawd_x, clawd_y = 120, 175
    draw_clawd(draw, clawd_x, clawd_y, g)

    robe_left = clawd_x - 2 * g
    robe_right = clawd_x + 10 * g
    robe_top = clawd_y + 2 * g + g // 2
    robe_bottom = clawd_y + 8 * g + g // 2
    draw.rectangle([robe_left, robe_top, robe_right, robe_bottom], fill=DARK_GRAY)
    draw.polygon([
        (clawd_x + 4 * g - 4, robe_top),
        (clawd_x + 6 * g + 4, robe_top),
        (clawd_x + 5 * g, robe_top + g + 4),
    ], fill=BLACK)
    draw.rectangle([clawd_x + 4 * g, robe_top + g, clawd_x + 6 * g, robe_bottom], fill=BLACK)
    draw.rectangle([robe_left, robe_bottom - g // 2, robe_right, robe_bottom], fill=BLACK)

    hat_x = clawd_x - g
    hat_y = clawd_y - int(g * 2.2)
    draw.rectangle([hat_x - g // 2, hat_y + 2 * g, hat_x + 10 * g, hat_y + 2 * g + g // 3], fill=DARK_GRAY)
    draw.polygon([
        (hat_x + g // 2, hat_y + 2 * g),
        (hat_x + 2 * g, hat_y + g // 2),
        (hat_x + 4 * g, hat_y - g),
        (hat_x + 6 * g, hat_y - 2 * g),
        (hat_x + 8 * g, hat_y - g),
        (hat_x + 9 * g, hat_y + g // 2),
        (hat_x + 7 * g, hat_y + 2 * g),
    ], fill=DARK_GRAY)
    draw.rectangle([hat_x + 2 * g, hat_y + g + g // 2, hat_x + 7 * g, hat_y + g + g // 2 + 4], fill=BLACK)
    draw.rectangle([hat_x + 4 * g + 2, hat_y + g + g // 2 - 1, hat_x + 4 * g + g // 2, hat_y + g + g // 2 + 3], fill=YELLOW)

    draw_text(draw, "*", hat_x + 6 * g, hat_y - 2 * g, color=YELLOW, scale=3)
    for i in range(6):
        a = math.radians(f * 25 + i * 60)
        r = 60 + i * 10
        sx = clawd_x+4*g + int(r * math.cos(a))
        sy = clawd_y+3*g + int(r * math.sin(a)) - 30
        if 10 < sx < 390 and 10 < sy < 340:
            draw.rectangle([sx-2, sy-2, sx+2, sy+2], fill=[YELLOW, PINK, PURPLE, WHITE, TEAL, ORANGE][i])


def sc_wrangling(draw, f, img):
    draw_clawd(draw, 30, 165, g)
    lx = 30 + 10 * g + 5
    ly = 165 + g
    rope_r = 30 + f * 3
    draw.ellipse([lx+20, ly-rope_r, lx+20+rope_r*2, ly+rope_r], outline=BROWN, width=2)
    blocks = [(250, 200), (300, 180), (280, 240), (330, 220), (260, 160)]
    for i, (bx2, by2) in enumerate(blocks):
        jx = int(5 * math.sin(f * 1.2 + i))
        jy = int(5 * math.cos(f * 1.5 + i))
        draw.rectangle([bx2+jx, by2+jy, bx2+16+jx, by2+16+jy],
                        fill=[RED, BLUE, GREEN, YELLOW, PURPLE][i])


def sc_whirlpooling(draw, f, img):
    draw_clawd(draw, 120, 160, g)
    cx2, cy2 = 120 + 4 * g, 300
    for i in range(30):
        a = math.radians(i * 25 + f * 20)
        r = 5 + i * 3
        px = cx2 + int(r * math.cos(a))
        py = cy2 - 20 + int(r * math.sin(a) * 0.4)
        c = BLUE if i % 2 == 0 else TEAL
        draw.rectangle([px-2, py-2, px+2, py+2], fill=c)


def sc_recombobulating(draw, f, img):
    """Clawd's pixels reassembling — reverse of discombobulation."""
    cx, cy = 130, 170
    scatter = max(0, (5 - f) * 10)
    rng = random.Random(42)

    def shifted_rect(x1, y1, x2, y2, color):
        ox2 = rng.randint(-scatter, scatter)
        oy2 = rng.randint(-scatter, scatter)
        draw.rectangle([x1+ox2, y1+oy2, x2+ox2, y2+oy2], fill=color)

    for gx2 in range(8):
        for gy2 in range(2):
            shifted_rect(cx+gx2*g, cy+gy2*g, cx+(gx2+1)*g-1, cy+(gy2+1)*g-1, CORAL)
    if scatter < 15:
        draw.rectangle([cx+1*g, cy+1*g, cx+2*g-1, cy+2*g-1], fill=BLACK)
        draw.rectangle([cx+6*g, cy+1*g, cx+7*g-1, cy+2*g-1], fill=BLACK)
    for gx2 in range(-2, 10):
        for gy2 in range(2, 4):
            shifted_rect(cx+gx2*g, cy+gy2*g, cx+(gx2+1)*g-1, cy+(gy2+1)*g-1, CORAL)
    for gx2 in range(8):
        for gy2 in range(4, 6):
            shifted_rect(cx+gx2*g, cy+gy2*g, cx+(gx2+1)*g-1, cy+(gy2+1)*g-1, CORAL)
    for lc in [0, 2, 5, 7]:
        for gy2 in range(6, 8):
            shifted_rect(cx+lc*g, cy+gy2*g, cx+(lc+1)*g-1, cy+(gy2+1)*g-1, CORAL)
    if f >= 4:
        for i in range(5):
            sx = cx - 20 + i * 50
            sy = cy - 15 + (i % 2) * 10
            draw.rectangle([sx, sy, sx+4, sy+4], fill=YELLOW)


def sc_jitterbugging(draw, f, img):
    """Energetic swing dance with bouncing and a dance floor."""
    bounce = [0, -15, -5, 0, -15, -5][f]
    sway = [-10, 5, 10, -5, -10, 5][f]
    draw_clawd(draw, 120 + sway, 165 + bounce, g)
    # Checkered dance floor
    for i in range(8):
        for j in range(2):
            c = YELLOW if (i + j + f) % 2 == 0 else RED
            draw.rectangle([50+i*40, 300+j*20, 50+(i+1)*40-2, 300+(j+1)*20-2], fill=c)
    # Music notes
    draw_music_note(draw, 60, 80 + ((f * 12) % 40), PURPLE)
    draw_music_note(draw, 320, 60 + ((f * 8) % 50), PINK)
    # Lightning bolt energy
    if f % 2 == 0:
        lx = 300
        draw.polygon([(lx, 100), (lx-8, 130), (lx+4, 125), (lx-4, 155),
                       (lx+12, 118), (lx+2, 123)], fill=YELLOW)
    # Motion lines
    for i in range(3):
        ly = 180 + bounce + i * 12
        draw.line([70+sway, ly, 100+sway, ly], fill=GRAY, width=1)
        draw.line([320+sway, ly, 350+sway, ly], fill=GRAY, width=1)


# ---------------------------------------------------------------------------
# GIF saving with transparency
# ---------------------------------------------------------------------------
def save_gif(frames, filename, duration=170):
    """Save RGBA frames as animated GIF with transparency."""
    key_rgb = (255, 0, 255)
    composite_frames = []
    for frame in frames:
        bg = Image.new('RGBA', (CANVAS, CANVAS), key_rgb + (255,))
        composite_frames.append(Image.alpha_composite(bg, frame).convert('RGB'))

    # Build one palette for the whole GIF so every frame shares the same
    # transparency index instead of quantizing independently.
    palette_source = Image.new('RGB', (CANVAS, CANVAS * len(composite_frames)))
    for i, frame in enumerate(composite_frames):
        palette_source.paste(frame, (0, i * CANVAS))
    master = palette_source.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    master_palette = master.getpalette()

    trans_index = 0
    min_dist = float('inf')
    for i in range(len(master_palette) // 3):
        r, g, b = master_palette[i*3:i*3+3]
        dist = (r - key_rgb[0])**2 + (g - key_rgb[1])**2 + (b - key_rgb[2])**2
        if dist < min_dist:
            min_dist = dist
            trans_index = i

    palette_image = Image.new('P', (1, 1))
    palette_image.putpalette(master_palette)

    processed = []
    for frame in composite_frames:
        p_frame = frame.quantize(palette=palette_image, dither=Image.Dither.NONE)
        p_frame.info['transparency'] = trans_index
        processed.append(p_frame)

    processed[0].save(
        filename,
        save_all=True,
        append_images=processed[1:],
        duration=duration,
        loop=0,
        disposal=2,
        transparency=processed[0].info['transparency'],
    )
    print(f"  Saved: {filename}")


# ---------------------------------------------------------------------------
# New batch: Billowing, Bloviating, Burrowing, Flambéing, Flummoxing,
# Fluttering, Inferring, Infusing, Julienning, Sprouting, Swooping,
# Waddling, Warping, Sautéing, Scampering, Caramelizing, Gesticulating,
# plus later compact additions like Clauding, Composing, Dilly-dallying,
# Boondoggling, Undulating, and Zesting
# ---------------------------------------------------------------------------

def sc_billowing(draw, f, img):
    """Clawd amid rolling, layered plumes that swell and unfurl outward."""
    draw_clawd(draw, 34, 170, g, blink=(f == 3))

    drift = [-10, -4, 4, 12, 18, 10][f]
    swell = [0, 6, 12, 18, 12, 6][f]
    back = (210, 218, 230)
    mid = (236, 240, 246)
    front = WHITE

    plume_clusters = [
        (222 + drift, 138, 1.0),
        (282 + drift, 122, 1.1),
        (248 + drift, 206, 1.25),
    ]
    for fill, offset in [(back, 12), (mid, 6), (front, 0)]:
        for cx, cy, scale in plume_clusters:
            rx1 = int((38 + swell + offset) * scale)
            ry1 = int((24 + swell // 2 + offset // 2) * scale)
            rx2 = int((48 + swell + offset) * scale)
            ry2 = int((30 + swell // 2 + offset // 2) * scale)
            rx3 = int((34 + swell // 2 + offset) * scale)
            ry3 = int((20 + swell // 3 + offset // 2) * scale)
            draw.ellipse([cx - rx1, cy - ry1, cx + rx1, cy + ry1], fill=fill)
            draw.ellipse([cx - 16, cy - ry2 - 6, cx + rx2, cy + ry2 - 10], fill=fill)
            draw.ellipse([cx - rx3 - 26, cy + 2, cx + rx3 - 24, cy + ry3 + 8], fill=fill)
            draw.ellipse([cx - rx3 + 18, cy + 8, cx + rx3 + 20, cy + ry3 + 14], fill=fill)

    curl_specs = [
        (200 + drift, 124, 34, 22, LIGHT_BLUE),
        (250 + drift, 106, 44, 28, TEAL),
        (314 + drift, 154, 38, 24, LIGHT_BLUE),
        (224 + drift, 216, 40, 24, TEAL),
    ]
    for i, (cx, cy, rx, ry, color) in enumerate(curl_specs):
        draw.arc([cx - rx, cy - ry, cx + rx, cy + ry], 190 + i * 8, 10 + i * 8, fill=color, width=2)
        draw.arc([cx - rx // 2, cy - ry // 2, cx + rx // 2, cy + ry // 2], 210, 30, fill=color, width=2)

    for i in range(5):
        sx = 168 + i * 36 + drift // 2
        sy = 116 + (i % 2) * 42 - (f % 2) * 4
        draw.rectangle([sx, sy, sx + 4, sy + 4], fill=YELLOW if i % 2 == 0 else WHITE)


def sc_bloviating(draw, f, img):
    """Clawd loudly over-explaining into a megaphone as speech swells outward."""
    clawd_x, clawd_y = 34, 170
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 4))

    paw_x = clawd_x + 10 * g
    paw_y = clawd_y + 2 * g + g // 2
    horn_x = 192
    horn_y = 220
    draw.line([paw_x, paw_y, horn_x, horn_y], fill=GRAY, width=3)
    draw.rectangle([horn_x - 18, horn_y - 8, horn_x + 4, horn_y + 8], fill=DARK_GRAY)
    draw.polygon([
        (horn_x + 4, horn_y - 18),
        (horn_x + 56, horn_y - 32),
        (horn_x + 56, horn_y + 32),
        (horn_x + 4, horn_y + 18),
    ], fill=RED)
    draw.polygon([
        (horn_x + 10, horn_y - 12),
        (horn_x + 48, horn_y - 22),
        (horn_x + 48, horn_y + 22),
        (horn_x + 10, horn_y + 12),
    ], fill=LIGHT_CORAL)

    bubble_w = [82, 96, 118, 138, 154, 132][f]
    bubble_h = [46, 54, 64, 74, 82, 70][f]
    bx = 214
    by = 70 + [10, 6, 2, 0, -4, 2][f]
    draw.ellipse([bx, by, bx + bubble_w, by + bubble_h], fill=WHITE, outline=BLACK)
    draw.ellipse([bx + 18, by - 12, bx + bubble_w - 8, by + bubble_h - 6], fill=WHITE, outline=BLACK)
    draw.polygon([
        (bx + 14, by + bubble_h - 4),
        (bx - 14, by + bubble_h + 10),
        (bx + 28, by + bubble_h - 12),
    ], fill=WHITE, outline=BLACK)

    for i in range(3):
        sound_r = 20 + i * 16 + f * 2
        draw.arc([horn_x + 18 - sound_r, horn_y - sound_r, horn_x + 18 + sound_r, horn_y + sound_r],
                 310, 50, fill=[YELLOW, ORANGE, RED][i], width=2)

    draw_text(draw, "BLAH", bx + 18, by + 18, color=RED, scale=4 if f >= 2 else 3)
    if f >= 1:
        draw_text(draw, "BLAH", bx + 34, by + 46, color=ORANGE, scale=2 if f < 4 else 3)
    if f >= 3:
        draw_text(draw, "!?", bx + bubble_w - 42, by + 12, color=PURPLE, scale=3)
    if f >= 4:
        for sx, sy in [(bx + bubble_w - 18, by + 28), (bx + bubble_w - 44, by + bubble_h - 10)]:
            draw_text(draw, "*", sx, sy, color=YELLOW, scale=2)


def sc_boondoggling(draw, f, img):
    """Clawd fusses over an overcomplicated little machine that feels impressively pointless."""
    clawd_x = 26 + [-2, 0, 2, 0, -2, 1][f]
    clawd_y = 166 + [0, -2, 0, -2, 0, -1][f]
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 4), accessories=[("tool", {"tool": "wrench"})])

    base_x, base_y = 214, 252
    draw.rectangle([base_x, base_y, base_x + 132, base_y + 12], fill=DARK_BROWN)
    draw.rectangle([base_x + 8, base_y - 42, base_x + 22, base_y], fill=GRAY)
    draw.rectangle([base_x + 104, base_y - 54, base_x + 116, base_y], fill=GRAY)
    draw.line([base_x + 22, base_y - 36, base_x + 64, base_y - 70], fill=GRAY, width=3)
    draw.line([base_x + 64, base_y - 70, base_x + 108, base_y - 52], fill=GRAY, width=3)
    draw.arc([base_x + 28, base_y - 54, base_x + 74, base_y - 8], 200, 360, fill=LIGHT_BLUE, width=2)
    draw.arc([base_x + 56, base_y - 52, base_x + 102, base_y - 4], 180, 340, fill=TEAL, width=2)

    gear1_y = base_y - 16
    gear2_y = base_y - 24
    draw_gear(draw, base_x + 36, gear1_y, 14, f)
    draw_gear(draw, base_x + 72, gear2_y, 18, f + 2)
    draw_gear(draw, base_x + 108, gear1_y - 4, 10, f + 1)

    lever_pivot_x = base_x + 18
    lever_pivot_y = base_y - 42
    lever_tip_x = lever_pivot_x + [18, 10, 0, -8, 4, 14][f]
    lever_tip_y = lever_pivot_y + [-24, -30, -36, -28, -20, -26][f]
    draw.line([lever_pivot_x, lever_pivot_y, lever_tip_x, lever_tip_y], fill=BROWN, width=3)
    draw.ellipse([lever_pivot_x - 4, lever_pivot_y - 4, lever_pivot_x + 4, lever_pivot_y + 4], fill=DARK_GRAY)
    draw.ellipse([lever_tip_x - 6, lever_tip_y - 6, lever_tip_x + 6, lever_tip_y + 6], fill=RED)

    spring_x = base_x + 118
    spring_top = base_y - 48
    spring_bottom = base_y - 8
    zig = [0, 5, -4, 5, -4, 0][f]
    spring_pts = [
        (spring_x, spring_bottom),
        (spring_x - 8 + zig, spring_bottom - 8),
        (spring_x + 6 - zig, spring_bottom - 16),
        (spring_x - 8 + zig, spring_bottom - 24),
        (spring_x + 6 - zig, spring_bottom - 32),
        (spring_x, spring_top),
    ]
    for p1, p2 in zip(spring_pts, spring_pts[1:]):
        draw.line([p1, p2], fill=GRAY, width=2)

    doodad_x = base_x + 126 + [0, 3, 7, 10, 6, 2][f]
    doodad_y = base_y - 52 + [0, -6, -12, -6, 0, 4][f]
    draw.rectangle([doodad_x - 6, doodad_y - 6, doodad_x + 6, doodad_y + 6], fill=YELLOW, outline=ORANGE)
    draw.line([doodad_x, doodad_y + 6, doodad_x, doodad_y + 18], fill=GRAY, width=1)
    draw.rectangle([doodad_x - 10, doodad_y + 18, doodad_x + 10, doodad_y + 22], fill=WHITE, outline=GRAY)

    for i in range(3):
        bx = base_x + 40 + i * 28 + [0, 2, -1, 3, -2, 1][(f + i) % NUM_FRAMES]
        by = base_y - 78 - ((f + i * 2) % NUM_FRAMES) * 8
        draw.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill=LIGHT_BLUE if i != 1 else WHITE)
    draw_text(draw, "?", 166, 124 + (f % 2) * 4, color=PURPLE, scale=3)


def sc_clauding(draw, f, img):
    """Clawd enters a self-referential Claude-like reply loop at a tiny terminal."""
    clawd_x = 34 + [-2, 0, 2, 0, -2, 1][f]
    clawd_y = 170 + [0, -2, 0, -2, 0, -1][f]
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 4))

    term_x, term_y = 208, 98
    term_w, term_h = 146, 132
    draw.rectangle([term_x, term_y, term_x + term_w, term_y + term_h], fill=(246, 246, 250), outline=DARK_GRAY)
    draw.rectangle([term_x, term_y, term_x + term_w, term_y + 20], fill=DARK_GRAY)
    for i, color in enumerate([RED, YELLOW, GREEN]):
        dx = term_x + 10 + i * 12
        draw.ellipse([dx, term_y + 7, dx + 6, term_y + 13], fill=color)

    avatar_x = term_x + 12
    avatar_y = term_y + 34
    draw_mini_clawd(draw, avatar_x, avatar_y, grid=5, blink=(f == 2))
    bubble_x = term_x + 70
    bubble_y = term_y + 36
    bubble_w = [32, 46, 60, 74, 84, 76][f]
    bubble_h = [18, 22, 26, 30, 34, 30][f]
    draw.rectangle([bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h], fill=CLAWD_ACCENT_BLUE_LIGHT, outline=CLAWD_ACCENT_BLUE)
    for i in range(3):
        line_w = max(10, bubble_w - 16 - i * 10)
        ly = bubble_y + 6 + i * 8
        if ly + 3 < bubble_y + bubble_h - 2:
            draw.rectangle([bubble_x + 8, ly, bubble_x + 8 + line_w, ly + 3], fill=BLACK)

    if f >= 2:
        nested_x = term_x + 84
        nested_y = term_y + 84
        nested_w = 44 + (f - 2) * 8
        nested_h = 28 + (f - 2) * 4
        draw.rectangle([nested_x, nested_y, nested_x + nested_w, nested_y + nested_h], fill=WHITE, outline=GRAY)
        draw_mini_clawd(draw, nested_x + 6, nested_y + 6, grid=3, blink=(f == 5))
        draw.rectangle([nested_x + 20, nested_y + 10, nested_x + nested_w - 8, nested_y + 13], fill=CLAWD_ACCENT_BLUE)
        if f >= 4:
            draw.rectangle([nested_x + 20, nested_y + 18, nested_x + nested_w - 14, nested_y + 21], fill=BLACK)

    for i, (sx, sy) in enumerate([(176, 146), (188, 128), (198, 112)]):
        pulse = (f + i) % 3
        size = 2 + pulse
        draw.rectangle([sx - size, sy - size, sx + size, sy + size], fill=YELLOW if i != 1 else WHITE)


def sc_composing(draw, f, img):
    """Clawd writes a growing musical score on a stand, distinct from stage choreography."""
    clawd_x, clawd_y = 30, 166
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 3), accessories=["headphones"])

    stand_x, stand_y = 226, 112
    sheet_w, sheet_h = 110, 92
    draw.rectangle([stand_x, stand_y, stand_x + sheet_w, stand_y + sheet_h], fill=WHITE, outline=DARK_GRAY)
    draw.polygon([
        (stand_x + 10, stand_y + sheet_h),
        (stand_x + sheet_w - 10, stand_y + sheet_h),
        (stand_x + sheet_w - 18, stand_y + sheet_h + 16),
        (stand_x + 18, stand_y + sheet_h + 16),
    ], fill=(214, 214, 214), outline=DARK_GRAY)
    draw.line([stand_x + sheet_w // 2, stand_y + sheet_h + 16, stand_x + sheet_w // 2, 286], fill=DARK_GRAY, width=3)
    draw.line([stand_x + sheet_w // 2, 286, stand_x + sheet_w // 2 - 20, 308], fill=DARK_GRAY, width=2)
    draw.line([stand_x + sheet_w // 2, 286, stand_x + sheet_w // 2 + 20, 308], fill=DARK_GRAY, width=2)

    for i in range(5):
        ly = stand_y + 14 + i * 12
        draw.line([stand_x + 10, ly, stand_x + sheet_w - 10, ly], fill=GRAY, width=1)
    for i in range(3):
        mx = stand_x + 34 + i * 24
        draw.line([mx, stand_y + 8, mx, stand_y + sheet_h - 10], fill=(228, 228, 228), width=1)

    note_positions = [
        (stand_x + 24, stand_y + 54),
        (stand_x + 48, stand_y + 42),
        (stand_x + 72, stand_y + 60),
        (stand_x + 90, stand_y + 34),
    ]
    for i in range(min(f + 1, len(note_positions))):
        nx, ny = note_positions[i]
        draw_music_note(draw, nx, ny, color=[BLUE, PURPLE, TEAL, RED][i])
    if f >= 3:
        draw.line([stand_x + 18, stand_y + 26, stand_x + 28, stand_y + 26], fill=BLACK, width=2)
        draw.line([stand_x + 18, stand_y + 78, stand_x + 34, stand_y + 78], fill=BLACK, width=2)

    pen_tip_x = stand_x - 8 + f * 3
    pen_tip_y = stand_y + 42 + [2, -8, -16, -10, 0, -4][f]
    draw.line([clawd_x + 10 * g, clawd_y + 2 * g + g // 2, pen_tip_x - 12, pen_tip_y + 6], fill=GRAY, width=2)
    draw.polygon([
        (pen_tip_x - 14, pen_tip_y + 8),
        (pen_tip_x + 2, pen_tip_y),
        (pen_tip_x + 10, pen_tip_y + 6),
        (pen_tip_x - 6, pen_tip_y + 14),
    ], fill=(152, 116, 86), outline=DARK_BROWN)
    draw.polygon([
        (pen_tip_x + 2, pen_tip_y),
        (pen_tip_x + 14, pen_tip_y + 4),
        (pen_tip_x + 6, pen_tip_y + 10),
    ], fill=YELLOW, outline=ORANGE)
    if f >= 2:
        for sx, sy in [(118, 110), (152, 86), (178, 134)]:
            draw_music_note(draw, sx, sy + ((f + sx // 10) % 3) * 4, color=LIGHT_BLUE if sx != 152 else YELLOW)


def sc_dilly_dallying(draw, f, img):
    """Clawd shuffles forward in tiny indecisive steps with a meandering trail behind."""
    xs = [42, 50, 48, 58, 56, 68]
    ys = [178, 170, 178, 170, 178, 170]
    cx = xs[f]
    cy = ys[f]
    draw_clawd(draw, cx, cy, g, blink=(f == 2))

    trail_points = [(30, 292), (56, 284), (84, 292), (112, 284), (138, 292), (164, 286)]
    for i in range(len(trail_points) - 1):
        x1, y1 = trail_points[i]
        x2, y2 = trail_points[i + 1]
        color = LIGHT_BLUE if i < len(trail_points) - 2 else TEAL
        draw.line([x1, y1, x2, y2], fill=color, width=2)
        mx = (x1 + x2) // 2
        my = (y1 + y2) // 2
        draw.ellipse([mx - 2, my - 2, mx + 2, my + 2], fill=color)
    arrow_x, arrow_y = trail_points[-1]
    draw.polygon([(arrow_x, arrow_y - 6), (arrow_x + 14, arrow_y), (arrow_x, arrow_y + 6)], fill=TEAL)

    for i in range(f + 1):
        fx = 22 + i * 20
        lift = -4 if i % 2 == 0 else 1
        draw.ellipse([fx, 306 + lift, fx + 10, 312 + lift], fill=DARK_BROWN)
        draw.ellipse([fx + 12, 304 - lift // 2, fx + 22, 310 - lift // 2], fill=DARK_BROWN)
    for sx, sy in [(220, 124), (246, 140), (270, 120)]:
        if f in {1, 3, 5}:
            draw.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], fill=(238, 238, 238))
            draw.ellipse([sx + 8, sy - 2, sx + 14, sy + 4], fill=(230, 230, 230))


def sc_burrowing(draw, f, img):
    """Clawd pops through a deeper burrow while the tunnel and dirt rim read more clearly."""
    soil = (132, 96, 64)
    soil_mid = (150, 112, 78)
    soil_light = (170, 132, 94)
    soil_dark = (84, 58, 40)
    soil_deep = (54, 36, 24)
    shift = [0, 4, 12, 16, 10, 4][f]

    draw.rectangle([0, 236, CANVAS, 320], fill=soil)
    for i in range(6):
        mx = -6 + i * 72
        my = 222 + (i % 2) * 6
        fill = soil_light if i % 2 == 0 else soil_mid
        draw.ellipse([mx, my, mx + 108, my + 34], fill=fill)

    hole_box = [74 + shift, 186, 194 + shift, 268]
    inner_box = [96 + shift, 204, 172 + shift, 258]
    front_rim = [52 + shift, 236, 186 + shift, 286]
    draw.ellipse(hole_box, fill=soil_dark)
    draw.ellipse(inner_box, fill=soil_deep)

    clawd_x = 60 + shift
    clawd_y = 146 + [2, 0, -6, -10, -6, -2][f]
    draw_clawd_head_only(draw, clawd_x, clawd_y, g, blink=(f == 3))

    draw.ellipse(front_rim, fill=soil_mid, outline=soil_dark)
    draw.arc([front_rim[0] + 6, front_rim[1] - 4, front_rim[2] - 6, front_rim[3] - 8], 180, 340, fill=soil_light, width=2)
    draw.arc([214 + shift, 170, 350 + shift, 292], 180, 360, fill=soil_dark, width=4)
    draw.arc([232 + shift, 186, 332 + shift, 274], 180, 360, fill=soil_deep, width=3)
    draw.line([284 + shift, 236, 284 + shift, 288], fill=soil_dark, width=3)
    draw.arc([252 + shift, 204, 314 + shift, 254], 202, 344, fill=soil_mid, width=2)

    shovel_x = 214
    shovel_y = 158
    draw.line([shovel_x, shovel_y, shovel_x + 40, shovel_y + 92], fill=BROWN, width=3)
    draw.polygon([
        (shovel_x + 30, shovel_y + 86),
        (shovel_x + 60, shovel_y + 84),
        (shovel_x + 66, shovel_y + 114),
        (shovel_x + 24, shovel_y + 114),
    ], fill=GRAY, outline=DARK_GRAY)

    dirt_bursts = [
        [(176, 176, 9), (216, 162, 7), (256, 186, 8), (292, 198, 6)],
        [(168, 164, 8), (224, 148, 6), (268, 174, 9), (298, 188, 6)],
        [(156, 152, 8), (234, 140, 7), (278, 164, 8), (306, 182, 7)],
        [(170, 160, 9), (246, 148, 7), (290, 176, 8), (314, 194, 6)],
        [(184, 172, 8), (238, 162, 7), (286, 188, 8), (304, 204, 6)],
        [(196, 184, 7), (226, 174, 6), (272, 200, 8), (294, 214, 6)],
    ]
    for i, (dx, dy, size) in enumerate(dirt_bursts[f]):
        fill = soil_dark if i % 2 else soil
        draw.ellipse([dx, dy, dx + size, dy + size], fill=fill)
        draw.ellipse([dx + 2, dy + 1, dx + size // 2 + 2, dy + size // 2 + 1], fill=soil_light)
    for sx, sy in [(54 + shift, 216), (70 + shift, 208), (194 + shift, 210)]:
        draw.line([sx, sy, sx + 10, sy - 10], fill=soil_light, width=1)


def sc_flambeing(draw, f, img):
    """A richer skillet flambé with layered blue heat and orange tongues of fire."""
    clawd_x, clawd_y = 30, 160
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 4))

    pan_x, pan_y = 210, 236
    draw.arc([pan_x, pan_y, pan_x + 126, pan_y + 64], 0, 180, fill=DARK_GRAY, width=4)
    draw.rectangle([pan_x + 8, pan_y + 26, pan_x + 118, pan_y + 34], fill=DARK_GRAY)
    draw.arc([pan_x + 8, pan_y + 18, pan_x + 118, pan_y + 40], 190, 350, fill=GRAY, width=2)
    draw.rectangle([pan_x - 34, pan_y + 22, pan_x + 4, pan_y + 30], fill=BROWN)
    draw.rectangle([pan_x - 36, pan_y + 19, pan_x - 22, pan_y + 33], fill=CORAL)

    flame_heights = [92, 124, 166, 184, 148, 110]
    plume_w = [60, 70, 82, 88, 72, 62][f]
    base_x = pan_x + 58
    base_y = pan_y + 14
    blue = (70, 154, 255)
    pale_blue = (176, 222, 255)
    orange = (255, 132, 44)
    yellow = (255, 224, 96)
    sway = [-10, -4, 6, 12, 6, -2][f]

    draw.polygon([
        (base_x - plume_w // 2, base_y + 18),
        (base_x - plume_w // 2 - 10, base_y - flame_heights[f] // 4),
        (base_x - 20 + sway // 2, base_y - flame_heights[f] // 2),
        (base_x - 6 + sway, base_y - flame_heights[f]),
        (base_x + 12 + sway, base_y - flame_heights[f] * 4 // 5),
        (base_x + 26 + sway // 2, base_y - flame_heights[f] // 2),
        (base_x + plume_w // 2 + 10, base_y - flame_heights[f] // 5),
        (base_x + plume_w // 2, base_y + 18),
    ], fill=blue)
    draw.polygon([
        (base_x - plume_w // 3, base_y + 10),
        (base_x - 16, base_y - flame_heights[f] // 3),
        (base_x - 2 + sway // 2, base_y - flame_heights[f] + 18),
        (base_x + 18 + sway, base_y - flame_heights[f] // 3),
        (base_x + plume_w // 3, base_y + 10),
    ], fill=orange)
    draw.polygon([
        (base_x - 16, base_y + 4),
        (base_x - 4, base_y - flame_heights[f] // 2 + 16),
        (base_x, base_y - flame_heights[f] + 34),
        (base_x + 4, base_y - flame_heights[f] // 2 + 16),
        (base_x + 16, base_y + 4),
    ], fill=yellow)
    for side in (-1, 1):
        tongue_x = base_x + side * (plume_w // 3)
        tongue_y = base_y - flame_heights[f] // 3
        draw.arc([tongue_x - 18, tongue_y - 24, tongue_x + 18, tongue_y + 24], 210 if side < 0 else -30, 30 if side < 0 else 210, fill=orange, width=3)
        draw.arc([tongue_x - 10, tongue_y - 16, tongue_x + 10, tongue_y + 16], 210 if side < 0 else -30, 30 if side < 0 else 210, fill=yellow, width=2)
    draw.ellipse([base_x - 36, base_y + 2, base_x + 40, base_y + 26], outline=orange, width=2)

    for i in range(5):
        sx = pan_x + 20 + i * 18
        sy = pan_y - 12 - ((f * 8 + i * 10) % 44)
        draw.rectangle([sx, sy, sx + 4, sy + 4], fill=yellow if i % 2 == 0 else pale_blue)
        draw.ellipse([sx + 6, sy + 3, sx + 10, sy + 7], fill=orange if i % 2 == 0 else yellow)

    bottle_x = 166
    bottle_y = 176
    pour = [0, 1, 1, 1, 0, 0][f]
    draw.rectangle([bottle_x, bottle_y, bottle_x + 18, bottle_y + 34], fill=GREEN)
    draw.rectangle([bottle_x + 4, bottle_y - 8, bottle_x + 14, bottle_y], fill=DARK_GRAY)
    if pour:
        draw.line([bottle_x + 18, bottle_y + 10, pan_x + 40, pan_y - 2], fill=YELLOW, width=2)
    for sx, sy in [(base_x - 20, base_y - 28), (base_x + 34, base_y - 40), (base_x + 10, base_y - 64)]:
        draw_text(draw, "*", sx + (f % 2) * 3, sy - (f % 3) * 2, color=YELLOW, scale=2)


def sc_flummoxing(draw, f, img):
    """Clawd stares at a denser problem knot while punctuation orbits in confusion."""
    clawd_x, clawd_y = 42, 166
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 2))
    draw_sweat_drop(draw, clawd_x + 116, clawd_y - 10 + (f % 2) * 4, scale=2)

    knot_cx = 282
    knot_cy = 170
    wobble = [-8, 0, 10, 4, -4, 2][f]
    bubble_fill = (244, 242, 248)
    draw.ellipse([214, 108, 350, 230], fill=bubble_fill, outline=GRAY)
    draw.ellipse([230, 94, 330, 178], fill=bubble_fill, outline=GRAY)
    draw.ellipse([238, 182, 340, 248], fill=bubble_fill, outline=GRAY)

    loops = [
        (knot_cx - 56 + wobble, knot_cy - 32, knot_cx + 8 + wobble, knot_cy + 12),
        (knot_cx - 20 + wobble, knot_cy - 48, knot_cx + 54 + wobble, knot_cy + 2),
        (knot_cx - 46 + wobble, knot_cy - 4, knot_cx + 26 + wobble, knot_cy + 48),
        (knot_cx + 2 + wobble, knot_cy - 10, knot_cx + 74 + wobble, knot_cy + 44),
        (knot_cx - 12 + wobble, knot_cy + 6, knot_cx + 46 + wobble, knot_cy + 58),
    ]
    for i, box in enumerate(loops):
        color = PURPLE if i % 2 == 0 else RED
        draw.arc(box, 18 + i * 18, 330 - i * 16, fill=color, width=3)
    draw.line([250 + wobble, 184, 322 + wobble, 156], fill=PURPLE, width=2)
    draw.line([260 + wobble, 146, 322 + wobble, 204], fill=RED, width=2)

    orbiters = [
        ("?", 230 + wobble, 110, YELLOW, 4),
        ("!", 306 + wobble, 112, ORANGE, 4),
        ("?", 334 + wobble, 152, LIGHT_BLUE, 3),
        ("!", 246 + wobble, 206, RED, 3),
    ]
    for glyph, sx, sy, color, scale in orbiters:
        draw_text(draw, glyph, sx, sy + (f % 2) * 2, color=color, scale=scale)
    for sx, sy in [(214, 214), (322, 232), (356, 198)]:
        draw_text(draw, "*", sx + wobble // 3, sy, color=WHITE, scale=2)

    hand_x = clawd_x + 10 * g
    hand_y = clawd_y + 2 * g + g // 2
    draw.line([hand_x, hand_y, 214, 184], fill=GRAY, width=2)


def sc_fluttering(draw, f, img):
    """Larger butterflies and petals flutter on visibly softer looping currents."""
    def draw_butterfly(cx, cy, wing, color):
        draw.ellipse([cx - wing - 4, cy - wing, cx - 2, cy + wing - 2], fill=color, outline=BLACK)
        draw.ellipse([cx + 2, cy - wing, cx + wing + 4, cy + wing - 2], fill=color, outline=BLACK)
        draw.ellipse([cx - wing, cy, cx - 2, cy + wing + 4], fill=tint_color(color, 0.2), outline=BLACK)
        draw.ellipse([cx + 2, cy, cx + wing, cy + wing + 4], fill=tint_color(color, 0.2), outline=BLACK)
        draw.rectangle([cx - 2, cy - wing + 2, cx + 2, cy + wing + 4], fill=DARK_GRAY)
        draw.line([cx - 2, cy - wing + 2, cx - 8, cy - wing - 6], fill=GRAY, width=1)
        draw.line([cx + 2, cy - wing + 2, cx + 8, cy - wing - 6], fill=GRAY, width=1)

    def draw_petal(cx, cy, color, tilt):
        draw.polygon([
            (cx, cy - 10),
            (cx + 8 + tilt, cy - 2),
            (cx + 2, cy + 10),
            (cx - 8 + tilt, cy + 2),
        ], fill=color, outline=BLACK)

    clawd_x = 118 + [0, 2, 0, -2, 0, 2][f]
    clawd_y = 170 + [0, -3, 0, 3, 0, -2][f]
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 3))

    butterflies = [
        (86, 92, 12, PINK),
        (284, 84, 13, LIGHT_BLUE),
        (318, 152, 11, YELLOW),
    ]
    butterfly_paths = [
        [(-8, 0), (-2, -12), (12, -18), (20, -6), (8, 8), (-6, 4)],
        [(0, -8), (14, -18), (24, -6), (12, 10), (-4, 14), (-12, 2)],
        [(12, -6), (18, 6), (8, 18), (-8, 10), (-12, -6), (4, -14)],
    ]
    for (bx, by, wing, color), path in zip(butterflies, butterfly_paths):
        ox, oy = path[f]
        cx = bx + ox
        cy = by + oy
        draw_butterfly(cx, cy, wing, color)
        draw.arc([cx - 26, cy - 20, cx + 26, cy + 20], 220, 330, fill=GRAY, width=1)

    petals = [
        (92, 204, LIGHT_CORAL, [(-6, 8), (4, 16), (12, 6), (6, -8), (-6, -12), (-12, -2)]),
        (296, 224, WHITE, [(6, 0), (14, -12), (8, -20), (-6, -8), (-10, 8), (4, 14)]),
    ]
    for bx, by, color, path in petals:
        ox, oy = path[f]
        draw_petal(bx + ox, by + oy, color, tilt=(-2 if f % 2 else 2))


def sc_infusing(draw, f, img):
    """A glass vessel slowly darkens as the infusion swirls through it."""
    clawd_x, clawd_y = 34, 168
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 4))

    cup_x, cup_y = 224, 132
    cup_w, cup_h = 98, 130
    liquid_colors = [
        (220, 238, 255),
        (204, 230, 250),
        (190, 216, 240),
        (196, 202, 232),
        (212, 184, 222),
        (228, 170, 200),
    ]
    liquid_color = liquid_colors[f]
    liquid_top = 212

    draw.rectangle([cup_x + 10, cup_y + 10, cup_x + cup_w - 10, cup_y + cup_h - 14], outline=(210, 230, 255), width=2)
    draw.rounded_rectangle([cup_x, cup_y + 8, cup_x + cup_w, cup_y + cup_h], radius=16, outline=WHITE, width=3)
    draw.ellipse([cup_x + 4, cup_y, cup_x + cup_w - 4, cup_y + 18], outline=WHITE, width=2)
    draw.line([cup_x + 16, cup_y + 22, cup_x + 16, cup_y + cup_h - 22], fill=(230, 245, 255), width=2)

    draw.rectangle([cup_x + 10, liquid_top, cup_x + cup_w - 10, cup_y + cup_h - 12], fill=liquid_color)
    draw.ellipse([cup_x + 10, liquid_top - 8, cup_x + cup_w - 10, liquid_top + 10], fill=tint_color(liquid_color, 0.12))
    draw.arc([cup_x + cup_w - 8, cup_y + 30, cup_x + cup_w + 26, cup_y + 76], 270, 90, fill=WHITE, width=3)
    draw.arc([cup_x + cup_w - 2, cup_y + 36, cup_x + cup_w + 20, cup_y + 70], 270, 90, fill=(220, 240, 255), width=2)

    bag_y = 152 + [0, 10, 22, 30, 22, 12][f]
    tag_x = clawd_x + 10 * g
    tag_y = clawd_y + 2 * g + g // 2
    draw.line([tag_x, tag_y, cup_x + 22, cup_y + 10], fill=GRAY, width=2)
    draw.line([cup_x + 22, cup_y + 10, cup_x + 22, bag_y], fill=WHITE, width=2)
    draw.rectangle([cup_x + 10, bag_y, cup_x + 38, bag_y + 30], fill=LIGHT_CORAL, outline=RED)
    draw.rectangle([cup_x + 15, bag_y + 6, cup_x + 33, bag_y + 24], fill=tint_color(LIGHT_CORAL, 0.35), outline=RED)

    swirl_colors = [WHITE, LIGHT_BLUE, PURPLE]
    for i, color in enumerate(swirl_colors):
        sy = 220 - i * 22
        sway = (f * 9 + i * 14) % 32
        draw.arc([cup_x + 18 + sway // 3, sy - 18, cup_x + 56 + sway, sy + 12], 200, 20, fill=color, width=2)
        draw.arc([cup_x + 46 - sway // 4, sy - 8, cup_x + 78 - sway // 4, sy + 18], 180, 10, fill=color, width=2)
    for px, py in [(cup_x + 44, 192), (cup_x + 66, 226), (cup_x + 58, 248)]:
        draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=WHITE)
    draw_steam(draw, cup_x + 36, cup_y - 28, f, color=(225, 225, 225))


def sc_inferring(draw, f, img):
    """Clawd inspects clue cards as dotted connections converge on one inferred answer."""
    def draw_dotted_link(x1, y1, x2, y2, dots, color):
        for i in range(dots):
            t = i / max(1, dots - 1)
            px = int(x1 + (x2 - x1) * t)
            py = int(y1 + (y2 - y1) * t)
            draw.ellipse([px - 2, py - 2, px + 2, py + 2], fill=color)

    clawd_x, clawd_y = 32, 164
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 3), accessories=["magnifier"])

    board_x, board_y = 220, 110
    board_w, board_h = 126, 124
    draw.rectangle([board_x, board_y, board_x + board_w, board_y + board_h], fill=(244, 236, 214), outline=DARK_BROWN)
    draw.rectangle([board_x + 6, board_y + 6, board_x + board_w - 6, board_y + board_h - 6], outline=(200, 178, 138))

    cards = [
        (236, 126, RED, -3, "?"),
        (292, 132, BLUE, 2, "!"),
        (248, 188, YELLOW, -1, "#"),
        (304, 192, GREEN, 1, "*"),
    ]
    for cx, cy, accent, skew, glyph in cards:
        draw_data_card(draw, cx, cy, accent=accent, skew=skew)
        draw_text(draw, glyph, cx + 10, cy + 10, color=accent, scale=3)
        draw.ellipse([cx + 14, cy - 8, cx + 20, cy - 2], fill=RED)

    hub_x = 292
    hub_y = 186
    dots = 3 + f * 2
    for cx, cy, accent, skew, glyph in cards[:3]:
        draw_dotted_link(cx + 20, cy + 24, hub_x, hub_y, dots, accent)

    clue_card_x = 286
    clue_card_y = 178
    draw_data_card(draw, clue_card_x, clue_card_y, accent=LIGHT_BLUE, skew=-2)
    draw.rectangle([clue_card_x + 10, clue_card_y + 18, clue_card_x + 26, clue_card_y + 21], fill=BLACK)
    draw.rectangle([clue_card_x + 10, clue_card_y + 26, clue_card_x + 24, clue_card_y + 29], fill=BLACK)
    draw.rectangle([clue_card_x + 10, clue_card_y + 34, clue_card_x + 28, clue_card_y + 37], fill=BLACK)
    glow_r = [8, 12, 16, 22, 28, 22][f]
    draw.ellipse([hub_x - glow_r, hub_y - glow_r, hub_x + glow_r, hub_y + glow_r], outline=YELLOW, width=2)
    if f >= 3:
        for sx, sy in [(274, 158), (326, 166), (318, 214), (266, 214)]:
            draw_text(draw, "*", sx, sy, color=YELLOW, scale=2)


def sc_julienning(draw, f, img):
    """Clawd finely slices vegetables into precise matchsticks under a taller toque."""
    clawd_x, clawd_y = 28, 162
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 4), accessories=[("chef_hat", {"tall": True})])

    board_x, board_y = 202, 224
    draw.polygon([
        (board_x + 6, board_y),
        (board_x + 146, board_y),
        (board_x + 152, board_y + 34),
        (board_x, board_y + 34),
    ], fill=(216, 174, 118), outline=DARK_BROWN)
    draw.rectangle([board_x + 126, board_y + 10, board_x + 138, board_y + 22], outline=DARK_BROWN, width=2)

    carrot_len = [82, 72, 60, 48, 36, 26][f]
    carrot_top = board_y + 12
    draw.polygon([
        (board_x + 20, carrot_top + 2),
        (board_x + 20 + carrot_len, carrot_top),
        (board_x + 20 + carrot_len + 14, carrot_top + 9),
        (board_x + 20 + carrot_len, carrot_top + 20),
        (board_x + 20, carrot_top + 22),
    ], fill=ORANGE, outline=RED)
    draw.rectangle([board_x + 10, carrot_top + 4, board_x + 20, carrot_top + 18], fill=GREEN)

    strip_count = 5 + f
    for i in range(strip_count):
        sx = board_x + 92 + (i % 5) * 9
        sy = board_y + 5 + (i // 5) * 6
        length = 24 + (i % 3) * 3
        draw.rectangle([sx, sy, sx + length, sy + 3], fill=ORANGE if i % 2 == 0 else YELLOW)

    chop_lift = [4, -10, -20, -6, 6, -2][f]
    knife_tip_x = board_x + 68 + f * 7
    knife_tip_y = board_y + 12 + chop_lift
    draw.polygon([
        (knife_tip_x - 30, knife_tip_y + 8),
        (knife_tip_x + 2, knife_tip_y),
        (knife_tip_x + 20, knife_tip_y + 8),
        (knife_tip_x - 8, knife_tip_y + 16),
    ], fill=GRAY, outline=DARK_GRAY)
    draw.rectangle([knife_tip_x - 44, knife_tip_y + 5, knife_tip_x - 30, knife_tip_y + 13], fill=BROWN)
    draw.line([clawd_x + 10 * g, clawd_y + 2 * g + g // 2, knife_tip_x - 42, knife_tip_y + 9], fill=GRAY, width=2)
    for i in range(3):
        draw.line([knife_tip_x - 6 - i * 12, knife_tip_y - 8 - i * 6,
                   knife_tip_x + 6 - i * 8, knife_tip_y - 16 - i * 6], fill=WHITE, width=1)


def sc_sprouting(draw, f, img):
    """Fresh green shoots emerge with clearer seed, crack, and leaf progression."""
    draw_clawd(draw, 36, 170, g, blink=(f == 4))
    leaf_green = (150, 210, 110)
    seed_color = (110, 74, 42)
    soil_highlight = (184, 146, 108)
    soil_crack = DARK_BROWN

    soil_x, soil_y = 204, 232
    draw.rectangle([soil_x, soil_y, 354, 274], fill=(132, 94, 62))
    for i in range(4):
        draw.ellipse([soil_x + 8 + i * 34, soil_y - 10 + (i % 2) * 4, soil_x + 54 + i * 34, soil_y + 12 + (i % 2) * 4],
                     fill=(156, 114, 78))

    heights = [
        [0, 0, 0],
        [10, 4, 0],
        [24, 18, 10],
        [42, 34, 24],
        [66, 54, 42],
        [84, 72, 58],
    ][f]
    xs = [238, 280, 320]
    for i, (sx, h) in enumerate(zip(xs, heights)):
        if h <= 0:
            draw.ellipse([sx - 9, soil_y - 7, sx + 9, soil_y + 5], fill=seed_color)
            draw.arc([sx - 9, soil_y - 7, sx + 9, soil_y + 5], 210, 330, fill=soil_highlight, width=1)
            continue
        top = soil_y - h
        draw.line([sx, soil_y, sx, top], fill=GREEN, width=3)
        draw.line([sx - 8, soil_y - 2, sx - 2, soil_y - 10], fill=soil_crack, width=1)
        draw.line([sx + 8, soil_y - 2, sx + 2, soil_y - 10], fill=soil_crack, width=1)
        if h > 12:
            draw.polygon([(sx, top + 12), (sx - 18, top + 2), (sx - 5, top + 24)], fill=leaf_green, outline=GREEN)
        if h > 26:
            draw.polygon([(sx, top + 18), (sx + 18, top + 8), (sx + 5, top + 30)], fill=GREEN, outline=DARK_BROWN)
        if h > 54:
            draw.ellipse([sx - 5, top - 6, sx + 5, top + 4], fill=LIGHT_CORAL if i == 1 else YELLOW)
        else:
            draw.ellipse([sx - 4, top - 4, sx + 4, top + 4], fill=seed_color if i == 2 else YELLOW)

    if f >= 3:
        draw.polygon([(84, 154), (98, 142), (110, 154)], fill=GREEN)
        draw.line([96, 154, 96, 170], fill=GREEN, width=2)
    for sx, sy in [(258, 152), (308, 170)]:
        if f >= 4:
            draw_text(draw, "*", sx, sy, color=YELLOW, scale=2)


def sc_swooping(draw, f, img):
    """Clawd sweeps along a stronger curved flight path with clearer trailing motion."""
    xs = [46, 84, 144, 220, 294, 330]
    ys = [168, 128, 92, 100, 144, 188]
    cx = xs[f]
    cy = ys[f]
    path_arcs = [
        (34, 212, 140, 302),
        (98, 142, 236, 254),
        (186, 94, 316, 204),
    ]

    for i, (x1, y1, x2, y2) in enumerate(path_arcs):
        draw.arc([x1, y1, x2, y2], 198, 336, fill=LIGHT_BLUE if i < 2 else WHITE, width=2)
    for i in range(max(0, f - 2), f):
        tx = xs[i]
        ty = ys[i]
        tint = tint_color(CORAL, 0.34 + (f - i) * 0.08)
        draw.rectangle([tx + 20, ty + 24, tx + 74, ty + 30], fill=tint)
    draw_clawd(draw, cx, cy, g, blink=(f == 2))
    for i in range(4):
        line_y = cy + 18 + i * 10
        draw.line([cx - 42 - i * 16, line_y, cx - 8 - i * 10, line_y], fill=LIGHT_BLUE, width=2)

    for i in range(4):
        px = 68 + i * 72
        py = 252 - abs(2 - i) * 12
        draw.arc([px, py, px + 30, py + 14], 180, 360, fill=WHITE, width=2)
    for sx, sy in [(278, 82), (334, 116), (302, 176)]:
        draw_text(draw, "*", sx, sy + (f % 2) * 4, color=YELLOW, scale=2)


def sc_waddling(draw, f, img):
    """Clawd waddles with a bigger side sway and clearer alternating footprints."""
    xs = [40, 56, 70, 88, 104, 120]
    ys = [178, 168, 178, 168, 178, 168]
    cx = xs[f]
    cy = ys[f]
    draw_clawd(draw, cx, cy, g, blink=(f == 3))

    sway_arc = [(-18, 18), (14, -14), (-20, 16), (12, -12), (-16, 14), (18, -16)][f]
    draw.arc([cx - 34, cy - 34, cx + 84, cy + 50], 210, 324, fill=LIGHT_BLUE, width=2)
    draw.arc([cx - 22, cy - 24, cx + 72, cy + 42], 26, 148, fill=LIGHT_BLUE, width=2)
    draw.line([cx + 32, cy - 20, cx + 32 + sway_arc[0], cy - 30], fill=YELLOW, width=2)
    draw.line([cx + 32, cy - 20, cx + 32 + sway_arc[1], cy - 30], fill=YELLOW, width=2)
    draw.line([cx + 18, cy + 96, cx + 54, cy + 96], fill=(214, 214, 214), width=2)

    for i in range(f + 1):
        fx = 26 + i * 22
        rise = -4 if i % 2 == 0 else 2
        draw.ellipse([fx, 308 + rise, fx + 10, 314 + rise], fill=DARK_BROWN)
        draw.ellipse([fx + 14, 306 - rise // 2, fx + 24, 312 - rise // 2], fill=DARK_BROWN)
        if i >= 1:
            draw.arc([fx - 6, 292, fx + 24, 310], 200, 330, fill=GRAY, width=1)


def sc_warping(draw, f, img):
    """A code-grid tunnel bends and pulls data tiles through a warp corridor."""
    cx = 44 + [0, 8, 18, 28, 34, 22][f]
    cy = 168 + [0, -2, -6, -4, 0, 2][f]
    draw_clawd(draw, cx, cy, g, blink=(f == 3))

    vx, vy = 292, 180
    pull = [0.12, 0.24, 0.38, 0.52, 0.44, 0.28][f]
    for i in range(5):
        left = 178 + i * 16
        right = 376 - i * 18
        top = 94 + i * 18
        bottom = 270 - i * 14
        draw.arc([left, top, right, bottom], 110, 248, fill=LIGHT_BLUE if i < 3 else WHITE, width=2)
        draw.arc([left, top, right, bottom], 292, 70, fill=TEAL if i < 3 else LIGHT_BLUE, width=2)

    for i in range(6):
        base_x = 188 + i * 26
        bend = int((i - 2.5) * 24 * pull)
        draw.line([base_x, 102, base_x + bend, 138, vx + bend // 2, vy + 4, base_x + bend, 222, base_x, 262],
                  fill=GRAY if i % 2 else LIGHT_BLUE, width=1)
    for i in range(6):
        base_y = 108 + i * 24
        bend = int((i - 2.5) * 18 * pull)
        draw.line([186, base_y, 228, base_y + bend, vx, vy + bend, 344, base_y + bend, 376, base_y],
                  fill=GRAY if i % 2 else WHITE, width=1)

    cards = [
        (190 + int(12 * pull), 118, TEAL, -3 - f),
        (218 + int(26 * pull), 162, BLUE, -1 - f // 2),
        (238 + int(38 * pull), 210, PURPLE, 2 + f // 2),
    ]
    for card_x, card_y, accent, skew in cards:
        draw_data_card(draw, card_x, card_y, accent=accent, skew=skew)
    for i in range(4):
        line_y = cy + 18 + i * 10
        draw.line([cx + 112 + i * 6, line_y, cx + 150 + i * 14, line_y], fill=LIGHT_BLUE, width=2)


def sc_zesting(draw, f, img):
    """Clawd zesting citrus over a bowl while bright curls fall from the grater."""
    clawd_x, clawd_y = 26, 164
    draw_clawd(draw, clawd_x, clawd_y, g, blink=(f == 3), accessories=["chef_hat"])

    bowl_x, bowl_y = 258, 248
    draw.arc([bowl_x, bowl_y, bowl_x + 90, bowl_y + 40], 0, 180, fill=LIGHT_BLUE, width=4)
    draw.arc([bowl_x + 10, bowl_y + 10, bowl_x + 80, bowl_y + 34], 0, 180, fill=WHITE, width=2)

    grate_x1 = 218
    grate_y1 = 168 + [0, -2, -4, -2, 0, 2][f]
    grate_x2 = 302
    grate_y2 = 226
    draw.line([grate_x1, grate_y1, grate_x2, grate_y2], fill=GRAY, width=6)
    draw.line([grate_x1 - 10, grate_y1 - 4, grate_x1 + 10, grate_y1 + 10], fill=DARK_BROWN, width=5)
    for i in range(5):
        tx = grate_x1 + 18 + i * 12
        ty = grate_y1 + 12 + i * 10
        draw.line([tx, ty, tx + 10, ty + 8], fill=WHITE, width=1)
        draw.line([tx + 4, ty - 6, tx + 14, ty + 2], fill=WHITE, width=1)

    lemon_x = 286
    lemon_y = 150 + [2, 0, -4, -6, -2, 2][f]
    draw.ellipse([lemon_x - 24, lemon_y - 18, lemon_x + 24, lemon_y + 18], fill=YELLOW, outline=ORANGE)
    draw.arc([lemon_x - 16, lemon_y - 10, lemon_x + 16, lemon_y + 10], 210, 330, fill=WHITE, width=2)
    draw.ellipse([lemon_x + 18, lemon_y - 4, lemon_x + 32, lemon_y + 10], fill=ORANGE)

    draw.line([clawd_x + 10 * g, clawd_y + 2 * g + g // 2, grate_x1 - 6, grate_y1 + 4], fill=GRAY, width=2)
    curl_specs = [
        (268, 198), (286, 210), (304, 220), (278, 228), (296, 238), (318, 246)
    ]
    drop = [0, 4, 10, 18, 26, 34][f]
    for i, (zx, zy) in enumerate(curl_specs[:f + 2]):
        yy = zy + drop - i * 4
        draw.arc([zx - 8, yy - 6, zx + 8, yy + 6], 200, 30, fill=YELLOW if i % 2 == 0 else ORANGE, width=2)
    for sx, sy in [(328, 150), (338, 170), (316, 186)]:
        if f >= 2:
            draw_text(draw, "*", sx, sy + (f % 2) * 3, color=YELLOW, scale=2)


def sc_sauteing(draw, f, img):
    """Clawd tossing food in a hot wok with oil splashes and flame."""
    draw_clawd(draw, 30, 160, g)

    # Wok body
    wok_x, wok_y = 210, 235
    draw.arc([wok_x, wok_y, wok_x + 120, wok_y + 60], 0, 180, fill=DARK_GRAY, width=4)
    draw.rectangle([wok_x, wok_y + 28, wok_x + 120, wok_y + 32], fill=DARK_GRAY)
    # Wok handle toward Clawd's paw
    draw.rectangle([wok_x - 30, wok_y + 22, wok_x + 4, wok_y + 30], fill=BROWN)
    # Paw on handle
    draw.rectangle([wok_x - 32, wok_y + 19, wok_x - 20, wok_y + 33], fill=CORAL)

    # Flame under wok
    flame_bob = [0, -3, -1, 2, 0, -2][f]
    flame_colors = [RED, ORANGE, YELLOW]
    for i, fc in enumerate(flame_colors):
        fx = wok_x + 30 + i * 25
        fy = wok_y + 34 + flame_bob * (1 if i % 2 == 0 else -1)
        draw.polygon([(fx, fy + 16), (fx + 8, fy), (fx + 16, fy + 16)], fill=fc)

    # Food tossing in air
    toss_heights = [0, -18, -34, -38, -22, -6]
    food_items = [(wok_x + 25, ORANGE), (wok_x + 50, GREEN), (wok_x + 80, RED)]
    for i, (fx, fc) in enumerate(food_items):
        th = toss_heights[(f + i) % NUM_FRAMES]
        fy = wok_y + 10 + th
        draw.rectangle([fx, fy, fx + 14, fy + 10], fill=fc)

    # Oil splashes
    if f in [1, 2, 3]:
        for i in range(3):
            sx = wok_x + 20 + i * 35
            sy = wok_y - 5 - f * 6 - i * 4
            draw.rectangle([sx, sy, sx + 3, sy + 3], fill=YELLOW)


def sc_scampering(draw, f, img):
    """Clawd bouncing forward rapidly with dust puffs behind."""
    # Clawd moves right and bounces
    cx = 40 + f * 22
    bounce = [0, -14, -6, 0, -14, -6][f]
    draw_clawd(draw, cx, 175 + bounce, g)

    # Dust puffs trailing behind
    for i in range(min(f, 4)):
        age = f - i
        dx = 30 + i * 22
        dy = 290 + age * 2
        r = max(3, 12 - age * 3)
        alpha_grey = min(200, 80 + (4 - age) * 30)
        c = (alpha_grey, alpha_grey, alpha_grey)
        draw.ellipse([dx - r, dy - r, dx + r, dy + r], fill=c)

    # Speed lines
    for i in range(4):
        ly = 185 + i * 14 + bounce
        lx = cx - 10
        draw.line([lx - 30 - f * 3, ly, lx - 8, ly], fill=GRAY, width=1)

    # Tiny footprint marks on ground
    for i in range(min(f + 1, 5)):
        fpx = 50 + i * 28
        draw.rectangle([fpx, 308, fpx + 6, 312], fill=DARK_BROWN)
        draw.rectangle([fpx + 10, 306, fpx + 16, 310], fill=DARK_BROWN)


def sc_caramelizing(draw, f, img):
    """Sugar crystals melting into golden caramel in a pan, bubbling."""
    draw_clawd(draw, 30, 155, g)

    # Pan
    pan_x, pan_y = 200, 240
    draw.rectangle([pan_x, pan_y, pan_x + 140, pan_y + 16], fill=DARK_GRAY)
    draw.rectangle([pan_x + 140, pan_y + 2, pan_x + 185, pan_y + 12], fill=BROWN)

    # Caramel stages: white sugar → golden → deep amber
    stage = f / (NUM_FRAMES - 1)  # 0.0 to 1.0
    r = int(255 - stage * 55)
    gr = int(255 - stage * 105)
    b = int(255 - stage * 195)
    caramel_color = (r, gr, b)
    draw.rectangle([pan_x + 8, pan_y - 14, pan_x + 132, pan_y], fill=caramel_color)

    # Sugar crystals (fade out as melting progresses)
    if f < 4:
        for i in range(6 - f):
            sx = pan_x + 15 + i * 20
            sy = pan_y - 10
            draw.rectangle([sx, sy, sx + 5, sy + 5], fill=WHITE)

    # Bubbles rising from surface
    for i in range(3):
        bx = pan_x + 30 + i * 35
        by = pan_y - 18 - ((f * 5 + i * 8) % 30)
        br = 3 + (f + i) % 3
        draw.ellipse([bx, by, bx + br * 2, by + br * 2], outline=caramel_color, width=1)

    # Warm glow underneath pan
    glow_colors = [(255, 160, 60), (255, 130, 40), (255, 100, 20)]
    gc = glow_colors[f % 3]
    draw.rectangle([pan_x + 20, pan_y + 18, pan_x + 120, pan_y + 24], fill=gc)

    # Steam wisps
    draw_steam(draw, pan_x + 60, pan_y - 30, f)


def frames_gesticulating():
    """Clawd waving arms wildly with motion lines and punctuation symbols overhead."""
    frames = []
    num_frames = 8
    # Arm wave patterns: (left_arm_angle, right_arm_angle) in pixel offsets
    arm_poses = [
        (-20, 20), (-30, -10), (10, -30), (25, 15),
        (-15, -25), (-30, 20), (20, -20), (5, 25),
    ]
    symbols = ['!', '?', '#', '*', '!', '?', '#', '!']
    sym_colors = [RED, BLUE, PURPLE, YELLOW, ORANGE, GREEN, PINK, RED]

    for f in range(num_frames):
        set_current_frame(f)
        img = Image.new('RGBA', (CANVAS, CANVAS), TRANS)
        draw = ImageDraw.Draw(img)

        sway = [-3, 0, 4, 2, -4, 1, 3, -2][f]
        clawd_x = 130 + sway
        clawd_y = 175
        draw_clawd(draw, clawd_x, clawd_y, g)

        # Animated arm extensions (motion lines radiating from arm ends)
        la, ra = arm_poses[f]
        # Left arm motion lines
        lax = clawd_x - 2 * g
        lay = clawd_y + 2 * g + g // 2
        for i in range(3):
            ex = lax - 15 - i * 10 + la
            ey = lay - 10 + la // 2 + i * 6
            draw.line([lax - 4, lay, ex, ey], fill=GRAY, width=1)
        # Right arm motion lines
        rax = clawd_x + 8 * g + 2 * g
        ray = clawd_y + 2 * g + g // 2
        for i in range(3):
            ex = rax + 15 + i * 10 + ra
            ey = ray - 10 + ra // 2 + i * 6
            draw.line([rax + 4, ray, ex, ey], fill=GRAY, width=1)

        # Punctuation symbols floating above head
        for i in range(3):
            si = (f + i) % num_frames
            sx = clawd_x + g + i * 40 + [0, 5, -3, 2, -5, 3, 0, -2][si]
            sy = clawd_y - 40 - i * 18 + [-4, -8, -12, -8, -4, 0, -6, -10][si]
            draw_text(draw, symbols[si], sx, sy, color=sym_colors[si], scale=3)

        # Emphatic burst lines around body
        burst_len = 8 + (f % 3) * 4
        for angle_deg in range(0, 360, 45):
            rad = math.radians(angle_deg + f * 12)
            bcx = clawd_x + 4 * g
            bcy = clawd_y + 3 * g
            r_inner = 80 + (f % 2) * 4
            r_outer = r_inner + burst_len
            x1 = bcx + int(math.cos(rad) * r_inner)
            y1 = bcy + int(math.sin(rad) * r_inner)
            x2 = bcx + int(math.cos(rad) * r_outer)
            y2 = bcy + int(math.sin(rad) * r_outer)
            draw.line([x1, y1, x2, y2], fill=ORANGE, width=2)

        draw_loading_label(draw, "Gesticulating", f)
        frames.append(img)
    return frames


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated")
    os.makedirs(out_dir, exist_ok=True)

    # Hand-authored full-frame generators.
    generators = {
        "Baking": frames_baking,
        "Beaming": frames_beaming,
        "Blanching": frames_blanching,
        "Booping": frames_booping,
        "Brewing": frames_brewing,
        "Canoodling": frames_canoodling,
        "Cascading": frames_cascading,
        "Catapulting": frames_catapulting,
        "Cerebrating": frames_cerebrating,
        "Channelling": frames_channelling,
        "Choreographing": frames_choreographing,
        "Churning": frames_churning,
        "Coalescing": frames_coalescing,
        "Cogitating": frames_cogitating,
        "Combobulating": frames_combobulating,
        "Concocting": frames_concocting,
        "Conjuring": frames_conjuring,
        "Contemplating": frames_contemplating,
        "Cooking": frames_cooking,
        "Crafting": frames_crafting,
        "Crunching": frames_crunching,
        "Cultivating": frames_cultivating,
        "Deciphering": frames_deciphering,
        "Deliberating": frames_deliberating,
        "Discombobulating": frames_discombobulating,
        "Divining": frames_divining,
        "Elucidating": frames_elucidating,
        "Embellishing": frames_embellishing,
        "Enchanting": frames_enchanting,
        "Envisioning": frames_envisioning,
        "Fiddle-faddling": frames_fiddle_faddling,
        "Finagling": frames_finagling,
        "Flibbertigibbeting": frames_flibbertigibbeting,
        "Flowing": frames_flowing,
        "Forging": frames_forging,
        "Frolicking": frames_frolicking,
        "Germinating": frames_germinating,
        "Hashing": frames_hashing,
        "Hatching": frames_hatching,
        "Herding": frames_herding,
        "Honking": frames_honking,
        "Hullaballooing": frames_hullaballooing,
        "Gesticulating": frames_gesticulating,
        "Nucleating": frames_nucleating,
        "Osmosing": frames_osmosing,
        "Prestidigitating": frames_prestidigitating,
        "Recombobulating": frames_recombobulating,
        "Thundering": frames_thundering,
        "Tinkering": frames_tinkering,
        "Tomfoolering": frames_tomfoolering,
        "Topsy-turvying": frames_topsy_turvying,
        "Transmuting": frames_transmuting,
        "Unfurling": frames_unfurling,
        "Whirlpooling": frames_whirlpooling,
        "Wrangling": frames_wrangling,
    }

    # Compact scene generators rendered through make_frames().
    scene_generators = {
        "Billowing": sc_billowing,
        "Bloviating": sc_bloviating,
        "Boondoggling": sc_boondoggling,
        "Burrowing": sc_burrowing,
        "Clauding": sc_clauding,
        "Composing": sc_composing,
        "Dilly-dallying": sc_dilly_dallying,
        "Flambéing": sc_flambeing,
        "Flummoxing": sc_flummoxing,
        "Fluttering": sc_fluttering,
        "Gusting": sc_gusting,
        "Hustling": sc_hustling,
        "Ideating": sc_ideating,
        "Imagining": sc_imagining,
        "Incubating": sc_incubating,
        "Inferring": sc_inferring,
        "Infusing": sc_infusing,
        "Jitterbugging": sc_jitterbugging,
        "Jiving": sc_jiving,
        "Julienning": sc_julienning,
        "Levitating": sc_levitating,
        "Manifesting": sc_manifesting,
        "Marinating": sc_marinating,
        "Meandering": sc_meandering,
        "Metamorphosing": sc_metamorphosing,
        "Moseying": sc_moseying,
        "Mulling": sc_mulling,
        "Mustering": sc_mustering,
        "Musing": sc_musing,
        "Nesting": sc_nesting,
        "Noodling": sc_noodling,
        "Percolating": sc_percolating,
        "Perusing": sc_perusing,
        "Philosophising": sc_philosophising,
        "Pollinating": sc_pollinating,
        "Pondering": sc_pondering,
        "Pontificating": sc_pontificating,
        "Precipitating": sc_precipitating,
        "Proofing": sc_proofing,
        "Propagating": sc_propagating,
        "Puttering": sc_puttering,
        "Puzzling": sc_puzzling,
        "Quantumizing": sc_quantumizing,
        "Razzmatazzing": sc_razzmatazzing,
        "Reticulating": sc_reticulating,
        "Ruminating": sc_ruminating,
        "Scheming": sc_scheming,
        "Schlepping": sc_schlepping,
        "Scurrying": sc_scurrying,
        "Seasoning": sc_seasoning,
        "Shimmying": sc_shimmying,
        "Shucking": sc_shucking,
        "Simmering": sc_simmering,
        "Slithering": sc_slithering,
        "Smooshing": sc_smooshing,
        "Spelunking": sc_spelunking,
        "Spinning": sc_spinning,
        "Sprouting": sc_sprouting,
        "Stewing": sc_stewing,
        "Sussing": sc_sussing,
        "Swirling": sc_swirling,
        "Swooping": sc_swooping,
        "Symbioting": sc_symbioting,
        "Synthesizing": sc_synthesizing,
        "Twisting": sc_twisting,
        "Undulating": sc_undulating,
        "Unravelling": sc_unravelling,
        "Vibing": sc_vibing,
        "Waddling": sc_waddling,
        "Wandering": sc_wandering,
        "Warping": sc_warping,
        "Whirring": sc_whirring,
        "Wibbling": sc_wibbling,
        "Wizarding": sc_wizarding,
        "Zesting": sc_zesting,
        "Sautéing": sc_sauteing,
        "Scampering": sc_scampering,
        "Caramelizing": sc_caramelizing,
    }
    # Normalize both generator styles into one output registry.
    for word, scene_fn in scene_generators.items():
        generators[word] = (lambda w=word, fn=scene_fn: make_frames(w, fn))

    print(f"Generating {len(generators)} Clawd spinner GIFs...")
    for word, gen_func in sorted(generators.items()):
        filename = os.path.join(out_dir, f"Clawd-{word}.gif")
        print(f"  Generating {word}...")
        frames = gen_func()
        save_gif(frames, filename)

    print("Done! All GIFs generated.")


if __name__ == "__main__":
    main()
