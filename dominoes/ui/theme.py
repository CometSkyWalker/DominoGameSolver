"""
Цвета интерфейса и мелочи оформления (градиенты, скругления).

Всё вынесено отдельно от окна, чтобы оформление правилось в одном месте,
а не искалось по всему коду.
"""
from PIL import Image, ImageDraw

BG        = "#0e0d16"   # фон окна
SIDEBAR   = "#151322"   # боковая панель
CARD      = "#1d1a2e"   # карточка
CARD_HI   = "#26223a"   # приподнятая карточка / поле ввода
INPUT     = "#2a2640"   # инпут
STROKE    = "#332f4a"   # тонкая граница
TEXT      = "#ECEAF6"   # основной текст
MUTED     = "#8b85a8"   # приглушённый текст
TEXT_DIM  = "#b7b2ce"

ACCENT    = "#7c3aed"    # фиолетовый
ACCENT_2  = "#ec4899"    # розовый (для градиента)
ACCENT_HI = "#9d5cff"
OK        = "#34d399"
BAD       = "#fb7185"
WARN      = "#fbbf24"   # янтарный — статус «не определено» (лимит перебора)

# Цвета клеток поля: нулевой — пустая клетка, дальше цвета доминошек.
CELLS = [
    "#272341",  # 0 пусто (чуть светлее карточки)
    "#f43f5e",  # 1 rose
    "#22d3ee",  # 2 cyan
    "#a78bfa",  # 3 violet
    "#fb923c",  # 4 orange
    "#34d399",  # 5 emerald
    "#f472b6",  # 6 pink
    "#facc15",  # 7 amber
    "#60a5fa",  # 8 blue
    "#c084fc",  # 9 purple
]

FONT = "DejaVu Sans"


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _lerp(a, b, t):
    return int(a + (b - a) * t)


def gradient(w, h, c1, c2, vertical=False, radius=0):
    """
    Картинка с плавным переходом от одного цвета к другому.

    Обычный tkinter так не умеет, поэтому изображение готовится через Pillow
    и затем кладётся на кнопку или на шапку.
    """
    w, h = max(1, int(w)), max(1, int(h))
    a, b = _hex(c1), _hex(c2)
    if vertical:
        data = [tuple(_lerp(a[k], b[k], y / max(1, h - 1)) for k in range(3)) for y in range(h)]
        strip = Image.new("RGB", (1, h)); strip.putdata(data)
        img = strip.resize((w, h))
    else:
        data = [tuple(_lerp(a[k], b[k], x / max(1, w - 1)) for k in range(3)) for x in range(w)]
        strip = Image.new("RGB", (w, 1)); strip.putdata(data)
        img = strip.resize((w, h))
    img = img.convert("RGBA")
    if radius > 0:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
        img.putalpha(mask)
    return img
