"""
Перекрывающиеся доминошки — решение задачи.

Пакет собран из двух частей:
    model    поле, ход и раскладка ходов;
    solver   алгоритмы всех четырёх режимов.

Интерфейсы (консоль и окно) лежат отдельно, в dominoes.ui, и на решатель
только опираются — сама логика от способа ввода не зависит.
"""

from dominoes.model import (
    EMPTY, WILDCARD, Move,
    all_placements, block_cells, empty_grid,
    simulate, to_lists, to_tuple, describe_move,
)
from dominoes.solver import (
    solve_mode1, solve_mode2, count_mode3, count_mode4,
    CountResult, SearchLimit,
)

__all__ = [
    "EMPTY", "WILDCARD", "Move",
    "all_placements", "block_cells", "empty_grid",
    "simulate", "to_lists", "to_tuple", "describe_move",
    "solve_mode1", "solve_mode2", "count_mode3", "count_mode4",
    "CountResult", "SearchLimit",
]
