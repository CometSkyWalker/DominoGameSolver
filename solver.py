"""
Алгоритмы всех четырёх режимов.
"""

import random
from collections import Counter, namedtuple

from model import (
    EMPTY, WILDCARD, Move,
    all_placements, block_cells, empty_grid, to_lists, to_tuple,
)


class SearchLimit(Exception):
    """Сигнал о том, что перебор разросся и его пора прервать."""
    pass


def _colored_cells(grid):
    """Клетки, которые ещё не разобраны и показывают цвет."""
    n = len(grid)
    return [(i, j) for i in range(n) for j in range(n) if grid[i][j] >= 1]


def _isolated_reason(target):
    """
    Простая проверка на заведомо невозможную картинку.

    Если цветная клетка стоит одна, а вокруг неё пусто, накрыть её нечем:
    доминошка занимает две клетки, и вторая обязательно попала бы на пустое
    место. Возвращает текст с объяснением или None.
    """
    n = len(target)
    coverable = set()
    for (r, c, w, h) in all_placements(n):
        cells = block_cells(r, c, w, h)
        if all(target[i][j] != EMPTY for (i, j) in cells):
            coverable.update(cells)
    for (i, j) in _colored_cells(target):
        if (i, j) not in coverable:
            return (f"клетку (строка {i + 1}, столбец {j + 1}) невозможно накрыть "
                    f"доминошкой, не задев пустую клетку")
    return None


def _plural_domino(k):
    """Правильное окончание: 1 доминошка, 2 доминошки, 5 доминошек."""
    if 11 <= k % 100 <= 14:
        return "доминошек"
    last = k % 10
    if last == 1:
        return "доминошка"
    if last in (2, 3, 4):
        return "доминошки"
    return "доминошек"


def _counts_reason(target, counts):
    """
    Проверка по количеству доминошек — до всякого перебора.

    Клетка показывает цвет той доминошки, которая накрыла её последней.
    Значит у каждой клетки цвета c есть своя доминошка этого цвета, и одна
    доминошка может отвечать не больше чем за две клетки. Отсюда простое
    условие: клеток цвета c на картинке не бывает больше, чем 2 * a_c,
    где a_c — сколько доминошек цвета c выдано.

    Если условие нарушено, картинку не собрать, и это видно сразу.
    Возвращает текст с объяснением или None.
    """
    need = {}
    for row in target:
        for v in row:
            if v != EMPTY:
                need[v] = need.get(v, 0) + 1

    for color in sorted(need):
        cells = need[color]
        have = counts.get(color, 0)
        if have == 0:
            return (f"на картинке есть цвет {color}, "
                    f"а доминошек этого цвета не выдано ни одной")
        if cells > 2 * have:
            if have == 1:
                return (f"клеток цвета {color} на картинке {cells}, "
                        f"а доминошка этого цвета всего одна — "
                        f"она закроет не больше двух клеток")
            return (f"клеток цвета {color} на картинке {cells}, "
                    f"а {have} {_plural_domino(have)} этого цвета закроют "
                    f"не больше {2 * have} клеток")
    return None


def _valid_peels(grid_lists, places):
    """
    Какие доминошки сейчас можно убрать с картинки.

    Убрать можно, если в блоке нет пустых клеток, все ещё не разобранные
    клетки одного цвета и хотя бы одна такая клетка там есть.
    """
    result = []
    for (r, c, w, h) in places:
        colors = set()
        has_bg = False
        has_colored = False
        for (i, j) in block_cells(r, c, w, h):
            v = grid_lists[i][j]
            if v == EMPTY:
                has_bg = True
                break
            if v >= 1:
                colors.add(v)
                has_colored = True
        if has_bg:
            continue
        if has_colored and len(colors) == 1:
            result.append((r, c, w, h, next(iter(colors))))
    return result


def _feasible_ignoring_counts(target, places):
    """
    Проверка, собирается ли картинка вообще, если доминошек сколько угодно.

    Убирается всё, что убирается, пока это возможно. Если в конце цветных
    клеток не осталось, картинку собрать можно.
    """
    grid = to_lists(target)
    changed = True
    while changed:
        changed = False
        for (r, c, w, h) in places:
            cells = block_cells(r, c, w, h)
            colors = set()
            bg = False
            colored = False
            for (i, j) in cells:
                v = grid[i][j]
                if v == EMPTY:
                    bg = True
                    break
                if v >= 1:
                    colors.add(v)
                    colored = True
            if bg or not colored or len(colors) != 1:
                continue
            for (i, j) in cells:
                if grid[i][j] != WILDCARD:
                    grid[i][j] = WILDCARD
                    changed = True
    return len(_colored_cells(grid)) == 0, _colored_cells(grid)


# Режим 1: задан набор доминошек по цветам и картинка.
# Принятое соглашение: «не больше, чем выдано» — лишние можно не класть.
def solve_mode1(n, counts, target, node_cap=300000):
    """
    counts — сколько доминошек какого цвета выдано, например {1: 2, 2: 1}.
    target — картинка, которую нужно собрать.

    Возвращает тройку (ok, moves, reason):
        ok is True  — решение найдено, moves — ходы в порядке выкладывания;
        ok is False — доказано, что картинку собрать нельзя, reason объясняет;
        ok is None  — перебор упёрся в лимит, ответ не определён (не «нельзя»,
                      а «не успели»), reason это поясняет.
    """
    target = to_tuple(target)
    places = all_placements(n)

    if not _colored_cells(target):
        return True, [], None  # картинка пустая, класть нечего

    # самая дешёвая проверка: хватает ли доминошек нужного цвета
    reason = _counts_reason(target, counts)
    if reason:
        return False, None, reason

    reason = _isolated_reason(target)
    if reason:
        return False, None, reason

    feasible, remaining = _feasible_ignoring_counts(target, places)
    if not feasible:
        i, j = remaining[0]
        return False, None, (
            f"конфигурация недостижима: клетку (строка {i + 1}, столбец {j + 1}) "
            f"нельзя получить никакой последовательностью ходов")

    kmax = max(counts) if counts else 0
    avail = tuple(counts.get(col, 0) for col in range(kmax + 1))
    memo = {}
    nodes = [0]

    def dfs(grid, used):
        """Перебор: что убрать следующим. used — сколько доминошек уже потрачено."""
        if not _colored_cells(grid):
            return []
        key = (grid, used)
        if key in memo:
            return memo[key]
        nodes[0] += 1
        if nodes[0] > node_cap:
            raise SearchLimit()

        glists = to_lists(grid)
        peels = _valid_peels(glists, places)

        # сначала идут варианты, закрывающие больше цветных клеток:
        # так решение находится быстрее
        def coverage(p):
            r, c, w, h, _ = p
            return sum(1 for (i, j) in block_cells(r, c, w, h) if glists[i][j] >= 1)
        peels.sort(key=lambda p: -coverage(p))

        result = None
        for (r, c, w, h, col) in peels:
            if used[col] >= avail[col]:
                continue
            ng = to_lists(grid)
            for (i, j) in block_cells(r, c, w, h):
                ng[i][j] = WILDCARD
            nused = list(used)
            nused[col] += 1
            sub = dfs(to_tuple(ng), tuple(nused))
            if sub is not None:
                result = [(r, c, w, h, col)] + sub
                break
        memo[key] = result
        return result

    try:
        peel_seq = dfs(target, tuple(0 for _ in avail))
    except SearchLimit:
        # Перебор упёрся в лимит узлов и не успел ни собрать картинку, ни
        # доказать её невозможность. Честный ответ — «не знаю», а не «нельзя».
        return None, None, (
            f"не удалось определить за отведённый бюджет перебора "
            f"({node_cap} состояний): картинка не разобрана до конца, но и "
            f"невозможность не доказана — попробуйте меньшее n, меньше "
            f"доминошек или увеличьте лимит")

    if peel_seq is None:
        return False, None, (
            "не хватает доминошек: такая картинка собирается в принципе, "
            "но не из выданного набора")

    # разбор шёл с конца, поэтому порядок выкладывания обратный
    moves = [Move(r, c, w, h, col) for (r, c, w, h, col) in reversed(peel_seq)]
    return True, moves, None


# Режим 2: задана готовая последовательность цветов.
# Порядок менять нельзя, выложить нужно все доминошки.
def solve_mode2(n, sequence, target, node_cap=300000):
    """
    sequence — цвета в том порядке, в каком доминошки кладут.
    Результат такой же, как в первом режиме, включая тристейт ok:
    True — решено, False — доказано невозможно, None — не хватило бюджета
    перебора (ответ не определён).
    """
    target = to_tuple(target)
    places = all_placements(n)
    m = len(sequence)

    if m == 0:
        if _colored_cells(target):
            return False, None, "доминошек нет, а картинка не пустая"
        return True, [], None

    # в этом режиме набор известен из самой последовательности
    reason = _counts_reason(target, Counter(sequence))
    if reason:
        return False, None, reason

    reason = _isolated_reason(target)
    if reason:
        return False, None, reason

    memo = {}
    nodes = [0]

    def valid_positions(grid, col):
        """Куда сейчас можно поставить доминошку цвета col."""
        res = []
        for (r, c, w, h) in places:
            ok = True
            good = True
            for (i, j) in block_cells(r, c, w, h):
                v = grid[i][j]
                if v == EMPTY:
                    ok = False
                    break
                if v >= 1 and v != col:
                    good = False
            if ok and good:
                res.append((r, c, w, h))
        return res

    def dfs(grid, idx):
        """Разбор с конца: idx — номер убираемой доминошки в последовательности."""
        if idx < 0:
            return [] if not _colored_cells(grid) else None
        key = (grid, idx)
        if key in memo:
            return memo[key]
        nodes[0] += 1
        if nodes[0] > node_cap:
            raise SearchLimit()

        col = sequence[idx]
        glists = to_lists(grid)
        positions = valid_positions(glists, col)

        # сначала идут места, где действительно видны клетки этого цвета
        def coverage(p):
            r, c, w, h = p
            return sum(1 for (i, j) in block_cells(r, c, w, h) if glists[i][j] == col)
        positions.sort(key=lambda p: -coverage(p))

        result = None
        for (r, c, w, h) in positions:
            ng = to_lists(grid)
            for (i, j) in block_cells(r, c, w, h):
                ng[i][j] = WILDCARD
            sub = dfs(to_tuple(ng), idx - 1)
            if sub is not None:
                result = [(r, c, w, h, col)] + sub
                break
        memo[key] = result
        return result

    try:
        peel_seq = dfs(target, m - 1)
    except SearchLimit:
        # То же честное «не знаю»: бюджет исчерпан, вывод не доказан ни в одну
        # сторону.
        return None, None, (
            f"не удалось определить за отведённый бюджет перебора "
            f"({node_cap} состояний): вывод не доказан ни в одну сторону — "
            f"попробуйте меньшие параметры или увеличьте лимит")

    if peel_seq is None:
        return False, None, (
            "невозможно: такая последовательность не даёт эту картинку "
            "(какой-то доминошке нет места либо остаётся лишний цвет)")

    moves = [Move(r, c, w, h, col) for (r, c, w, h, col) in reversed(peel_seq)]
    return True, moves, None


# Режимы 3 и 4: сколько всего разных картинок может получиться.
#
# Подсчёт идёт в два шага.
# 1. Сначала точный перебор. Хранятся не ходы, а сами картинки: очередная
#    доминошка кладётся во все места ко всем уже полученным картинкам, а
#    одинаковые картинки отбрасываются. Пока их не слишком много, ответ точный.
# 2. Если картинок стало больше лимита, в память они не помещаются. Тогда
#    включается прикидка: доминошки много раз раскладываются наугад, и по
#    тому, часто ли повторяются одни и те же картинки, оценивается их общее
#    число. Редкие повторы означают, что разных картинок гораздо больше, чем
#    удалось увидеть.

CountResult = namedtuple("CountResult", ["value", "exact", "observed", "method"])
# value    — само число (точное или прикидка)
# exact    — True, если посчитано точно
# observed — сколько разных картинок реально встретилось (меньше уже не будет)
# method   — способ подсчёта, он показывается пользователю


def _cells_flat(n):
    """
    Заранее подготовленный список: какие клетки занимает доминошка в каждом
    из возможных мест.

    Клетки пронумерованы подряд одним числом (сначала первая строка, потом
    вторая и так далее) — в таком виде поле удобно хранить строкой байтов.
    """
    return [[i * n + j for (i, j) in block_cells(r, c, w, h)]
            for (r, c, w, h) in all_placements(n)]


def _round_sig(x, sig=3):
    """
    Округление прикидки до нескольких первых цифр.

    Число всё равно приблизительное, и показывать его целиком было бы
    обманом: понятнее вид «примерно 400 000 000».
    """
    if x <= 0:
        return 0
    import math
    d = sig - int(math.floor(math.log10(x))) - 1
    return int(round(x, min(0, d)))


def _estimate_total(freq):
    """
    Прикидка общего числа разных картинок, когда видна только их часть.

    Приём тот же, что и при подсчёте рыбы в озере. Всю рыбу выловить нельзя,
    поэтому ловят сколько получится и смотрят на улов: если один и тот же вид
    попадается снова и снова, видов немного и почти все уже видны; если почти
    каждая рыба нового вида, значит в озере есть ещё много непойманного.

    Здесь так же:
        D  — сколько разных картинок встретилось;
        f1 — сколько из них встретились ровно один раз;
        f2 — сколько встретились ровно два раза.
    Расчёт по формуле D + f1*(f1-1) / (2*(f2+1)) — это готовая оценка Чао
    (Chao, 1984).

    Ниже D результат не опускается: эти картинки реально встретились, значит
    их точно не меньше.
    """
    D = len(freq)
    f1 = sum(1 for v in freq.values() if v == 1)
    f2 = sum(1 for v in freq.values() if v == 2)
    est = D + f1 * (f1 - 1) / (2 * (f2 + 1))
    return D, max(D, _round_sig(est, 3))


def count_mode4(n, sequence, cap=200000, trials=40000):
    """
    Режим 4: цвета кладут в заданном порядке. Нужно число разных картинок.
    """
    cells = _cells_flat(n)
    N = n * n
    # Сначала точный перебор. frontier — все разные картинки, полученные к
    # этому моменту. Очередной цвет кладётся во все места, а повторы
    # множество отбрасывает само.
    frontier = {bytes(N)}
    exact = True
    for col in sequence:
        nxt = set()
        for state in frontier:
            for pc in cells:
                b = bytearray(state)
                for idx in pc:
                    b[idx] = col
                nxt.add(bytes(b))
            if len(nxt) > cap:
                exact = False
                break
        if not exact:
            break
        frontier = nxt
    if exact:
        return CountResult(len(frontier), True, len(frontier), "посчитано точно")

    # Картинок слишком много для точного счёта. Дальше идут случайные
    # раскладки, и запоминается, что и сколько раз выпало.
    P = len(cells)
    freq = {}
    for _ in range(trials):
        arr = bytearray(N)
        for col in sequence:
            for idx in cells[random.randrange(P)]:
                arr[idx] = col
        key = bytes(arr)
        freq[key] = freq.get(key, 0) + 1
    D, est = _estimate_total(freq)
    return CountResult(est, False, D, "прикидка по случайным раскладкам")


def count_mode3(n, counts, cap=200000, trials=40000):
    """
    Режим 3: задан набор доминошек, а порядок выкладывания выбирается свободно.
    Порядок влияет на результат, потому что доминошка, положенная позже,
    закрашивает те, что лежали раньше. Поэтому перебираются и порядки.
    """
    cells = _cells_flat(n)
    N = n * n
    kmax = max(counts) if counts else 0
    full = tuple(counts.get(c, 0) for c in range(kmax + 1))
    m = sum(full)
    if m == 0:
        return CountResult(1, True, 1, "посчитано точно")  # класть нечего, картинка одна

    # То же, что в режиме 4, только рядом с картинкой хранится остаток набора:
    # «такая картинка получена, красных осталось 0, синих 1».
    frontier = {(bytes(N), full)}
    exact = True
    for _ in range(m):
        nxt = set()
        for (state, rem) in frontier:
            for col in range(1, kmax + 1):
                if rem[col] == 0:
                    continue
                nrem = list(rem); nrem[col] -= 1; nrem = tuple(nrem)
                for pc in cells:
                    b = bytearray(state)
                    for idx in pc:
                        b[idx] = col
                    nxt.add((bytes(b), nrem))
            if len(nxt) > cap:
                exact = False
                break
        if not exact:
            break
        frontier = nxt
    if exact:
        # набор израсходован, остаток больше не нужен — остаются картинки
        finals = {s for (s, rem) in frontier}
        return CountResult(len(finals), True, len(finals), "посчитано точно")

    # Точно посчитать не вышло: набор перемешивается и раскладывается наугад.
    multiset = [c for c in range(1, kmax + 1) for _ in range(full[c])]
    P = len(cells)
    freq = {}
    for _ in range(trials):
        order = multiset[:]
        random.shuffle(order)
        arr = bytearray(N)
        for col in order:
            for idx in cells[random.randrange(P)]:
                arr[idx] = col
        key = bytes(arr)
        freq[key] = freq.get(key, 0) + 1
    D, est = _estimate_total(freq)
    return CountResult(est, False, D, "прикидка по случайным раскладкам")

