"""
Базовые вещи: игровое поле и ход.

Поле — квадрат n на n. В каждой клетке хранится число:
    0     пустая клетка, её никто не накрывал
    1..k  цвет доминошки, которая лежит сверху
   -1     служебная пометка «клетка уже разобрана», её видит только решатель

Доминошка занимает две соседние клетки и кладётся либо вдоль строки,
либо вдоль столбца. Размер по условию задачи фиксированный.
"""

from collections import namedtuple

EMPTY = 0        # пустая клетка
WILDCARD = -1    # клетка, разобранная решателем

# Ход — положить доминошку цвета color на поле.
# r, c — верхняя левая клетка; w — ширина, h — высота.
Move = namedtuple("Move", ["r", "c", "w", "h", "color"])

# Два положения доминошки: (ширина, высота).
ORIENTATIONS = ((2, 1), (1, 2))


def all_placements(n):
    """Все места, куда доминошка помещается на поле n на n."""
    result = []
    for (w, h) in ORIENTATIONS:
        # верхнюю левую клетку двигаем так, чтобы доминошка не вышла за край
        for r in range(n - h + 1):
            for c in range(n - w + 1):
                result.append((r, c, w, h))
    return result


def block_cells(r, c, w, h):
    """Клетки, которые накрывает доминошка с верхним левым углом (r, c)."""
    return [(i, j) for i in range(r, r + h) for j in range(c, c + w)]


def empty_grid(n):
    """Пустое поле. Собрано из кортежей, чтобы его можно было класть в множество."""
    return tuple(tuple(EMPTY for _ in range(n)) for _ in range(n))


def to_lists(grid):
    """Копия поля, которую можно менять."""
    return [list(row) for row in grid]


def to_tuple(grid):
    """Обратное превращение: такое поле сравнивается и хешируется."""
    return tuple(tuple(row) for row in grid)


def apply_move(grid_lists, move):
    """Закрасить клетки под доминошкой её цветом."""
    for (i, j) in block_cells(move.r, move.c, move.w, move.h):
        grid_lists[i][j] = move.color


def simulate(n, moves):
    """Разложить ходы по порядку на пустом поле и вернуть получившуюся картинку."""
    g = to_lists(empty_grid(n))
    for m in moves:
        apply_move(g, m)
    return to_tuple(g)


def orientation_name(w, h):
    """Название положения доминошки словами."""
    return "горизонтально" if h == 1 else "вертикально"


def describe_move(move, index=None):
    """Описание хода для вывода. Строки и столбцы нумеруются с единицы."""
    r, c, w, h, color = move
    rows = f"строка {r + 1}" if h == 1 else f"строки {r + 1}-{r + h}"
    cols = f"столбец {c + 1}" if w == 1 else f"столбцы {c + 1}-{c + w}"
    prefix = f"{index}) " if index is not None else ""
    return (f"{prefix}цвет {color} — {rows}, {cols} "
            f"({orientation_name(w, h)})")
