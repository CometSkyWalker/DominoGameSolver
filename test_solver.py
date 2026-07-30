"""
Проверки решателя. Запуск: python3 test_solver.py

Сторонние библиотеки для тестов не используются: результат считается,
сравнивается с ожидаемым и печатается «ок» или «ошибка». Отдельно
проверяются каверзные случаи, где легко ошибиться.
"""

import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from collections import Counter
from model import simulate, Move
from solver import (
    solve_mode1, solve_mode2, count_mode3, count_mode4,
)

PASSED = 0


def check(name, condition):
    global PASSED
    assert condition, "ПРОВАЛ: " + name
    PASSED += 1
    print("  ok  :", name)


def counts_by_color(moves):
    return Counter(m.color for m in moves)


print("== Режим 1: восстановление по набору ==")

# Самый простой случай: одна доминошка легла горизонтально.
n = 2
target = ((1, 1),
          (0, 0))
ok, moves, reason = solve_mode1(n, {1: 3}, target)
check("простая доминошка достижима", ok)
check("итог совпадает", simulate(n, moves) == target)
check("не больше запаса", all(v <= 3 for v in counts_by_color(moves).values()))

# Здесь важен порядок разбора: в строке «1 2 2» единицу сразу не убрать,
# сначала убирается пара двоек.
n = 3
target = ((1, 2, 2),
          (0, 0, 0),
          (0, 0, 0))
ok, moves, reason = solve_mode1(n, {1: 1, 2: 1}, target)
check("1 2 2 достижимо", ok)
check("1 2 2 итог совпадает", simulate(n, moves) == target)
check("1 2 2 использует ровно 1+1", counts_by_color(moves) == Counter({1: 1, 2: 1}))

# Одна цветная клетка в углу, вокруг пусто — накрыть её нечем.
n = 3
target = ((1, 0, 0),
          (0, 0, 0),
          (0, 0, 0))
ok, moves, reason = solve_mode1(n, {1: 5}, target)
check("одинокая клетка невозможна", not ok)
check("есть обоснование", reason is not None and len(reason) > 0)

# Картинка собирается, но выданных доминошек не хватает.
n = 2
target = ((1, 1),
          (2, 2))
ok, moves, reason = solve_mode1(n, {1: 1, 2: 0}, target)
check("нехватка цвета 2 -> невозможно", not ok)

ok, moves, reason = solve_mode1(n, {1: 1, 2: 1}, target)
check("хватает 1+1 -> возможно", ok and simulate(n, moves) == target)

# Перекрытие: вторая доминошка легла сверху и закрасила часть первой.
n = 2
target = ((2, 2),
          (1, 1))
ok, moves, reason = solve_mode1(n, {1: 2, 2: 2}, target)
check("перекрытие достижимо", ok and simulate(n, moves) == target)

# Пустая картинка — ходов быть не должно.
n = 3
target = tuple(tuple(0 for _ in range(3)) for _ in range(3))
ok, moves, reason = solve_mode1(n, {1: 4}, target)
check("пустой итог -> нет ходов", ok and moves == [])

# Проверка по количеству: клеток цвета c не бывает больше, чем 2 * a_c.
# Такие случаи отсекаются сразу, без перебора.
n = 3
target = ((1, 1, 1),
          (0, 0, 0),
          (0, 0, 0))
ok, moves, reason = solve_mode1(n, {1: 1}, target)
check("3 клетки одного цвета против 1 доминошки -> невозможно", not ok)
check("причина названа по количеству", reason is not None and "клеток цвета" in reason)

# Цвет есть на картинке, а доминошек такого цвета не выдано вообще.
n = 2
target = ((1, 1),
          (2, 2))
ok, moves, reason = solve_mode1(n, {1: 2, 2: 0}, target)
check("цвет без единой доминошки -> невозможно", not ok and "не выдано" in reason)

# Впритык: 4 клетки и ровно 2 доминошки — должно решаться.
n = 2
target = ((1, 1),
          (1, 1))
ok, moves, reason = solve_mode1(n, {1: 2}, target)
check("ровно впритык -> решается", ok and simulate(n, moves) == target)

print("== Режим 2: восстановление по последовательности ==")

# Верный порядок для строки «1 2 2»: сначала цвет 1, потом цвет 2.
n = 3
target = ((1, 2, 2),
          (0, 0, 0),
          (0, 0, 0))
ok, moves, reason = solve_mode2(n, [1, 2], target)
check("послед-ть [1,2] воспроизводит '1 2 2'", ok and simulate(n, moves) == target)
check("порядок цветов сохранён", [m.color for m in moves] == [1, 2])

# При обратном порядке единица ляжет сверху и картинка не сойдётся.
ok, moves, reason = solve_mode2(n, [2, 1], target)
check("послед-ть [2,1] не воспроизводит '1 2 2'", not ok)

# Во втором режиме класть нужно все, лишнюю доминошку тоже надо разместить.
n = 2
target = ((1, 1),
          (0, 0))
ok, moves, reason = solve_mode2(n, [1], target)
check("одна доминошка кладётся ровно на строку", ok and simulate(n, moves) == target)

# Картинка пустая, а доминошки есть — девать их некуда.
n = 2
empty = ((0, 0), (0, 0))
ok, moves, reason = solve_mode2(n, [1], empty)
check("непустая послед-ть при пустом итоге невозможна", not ok)

# Первую доминошку полностью закрасили, и на картинке её не видно.
# Такое разрешено, программа должна это учитывать.
n = 2
target = ((2, 2),
          (2, 2))
# единица кладётся куда угодно, затем две двойки накрывают всё поле
ok, moves, reason = solve_mode2(n, [1, 2, 2], target)
check("полностью закрашенная доминошка допустима", ok and simulate(n, moves) == target)
check("выложены все 3", len(moves) == 3)

# В этом режиме набор берётся из самой последовательности, и проверка
# по количеству работает так же: одной доминошки на четыре клетки мало.
n = 2
target = ((1, 1),
          (1, 1))
ok, moves, reason = solve_mode2(n, [1], target)
check("послед-ть из одной доминошки на 4 клетки -> невозможно",
      not ok and "клеток цвета" in reason)

ok, moves, reason = solve_mode2(n, [1, 1], target)
check("двух доминошек хватает", ok and simulate(n, moves) == target)

print("== Режим 3: подсчёт конфигураций по набору ==")

# Одна доминошка на поле 2 на 2: четыре места — четыре разные картинки.
r = count_mode3(2, {1: 1})
check("одна доминошка на 2x2 -> 4 картинки", r.value == 4 and r.exact)

# Класть нечего, поэтому картинка ровно одна — пустая.
r = count_mode3(2, {1: 0})
check("ноль доминошек -> 1 картинка", r.value == 1 and r.exact)

print("== Режим 4: подсчёт по последовательности ==")

# То же самое, но порядок задан заранее.
r = count_mode4(2, [1])
check("[1] на 2x2 -> 4 конфигурации", r.value == 4 and r.exact)

# Две одинаковые доминошки на поле 2 на 2. Пересчёт вручную даёт девять
# разных картинок: вариантов 16, но часть из них совпадает.
r = count_mode4(2, [1, 1])
check("[1,1] на 2x2 -> 9 конфигураций", r.value == 9 and r.exact)


# Главная проверка подсчёта: быстрый способ сравнивается с перебором в лоб.
# На маленьких полях ответы обязаны совпасть.
def _ref_mode4(n, seq):
    from model import all_placements, block_cells, to_lists, to_tuple, empty_grid
    places = all_placements(n)
    finals = set()

    def rec(grid, i):
        if i == len(seq):
            finals.add(grid); return
        for (r, c, w, h) in places:
            g = to_lists(grid)
            for (a, b) in block_cells(r, c, w, h):
                g[a][b] = seq[i]
            rec(to_tuple(g), i + 1)
    rec(empty_grid(n), 0)
    return len(finals)

mism = 0
for seq in ([1], [1, 2], [2, 1], [1, 1, 2], [1, 2, 1]):
    if count_mode4(2, seq).value != _ref_mode4(2, seq):
        mism += 1
for seq in ([1], [1, 2], [1, 1]):
    if count_mode4(3, seq).value != _ref_mode4(3, seq):
        mism += 1
check("быстрый подсчёт == прямой перебор (мелкие случаи)", mism == 0)

# На большом поле точный счёт невозможен, должна включаться прикидка.
r = count_mode4(4, [1, 2, 1, 2], cap=200, trials=4000)
check("на большом поле включается прикидка, а не точный счёт",
      (not r.exact) and r.value >= r.observed > 0
      and r.method.startswith("прикидка"))

print("== Согласованность режима 1 (случайные разрешимые случаи) ==")
import random
random.seed(1)
ok_all = True
for _ in range(200):
    n = random.choice([2, 3])
    k = random.choice([1, 2, 3])
    # Картинка складывается случайными ходами. Раз она получена ходами,
    # решатель обязан её разобрать.
    from model import all_placements, block_cells, to_lists, to_tuple, empty_grid
    places = all_placements(n)
    grid = to_lists(empty_grid(n))
    placed = Counter()
    for _ in range(random.randint(0, 5)):
        r, c, w, h = random.choice(places)
        col = random.randint(1, k)
        for (i, j) in block_cells(r, c, w, h):
            grid[i][j] = col
        placed[col] += 1
    tgt = to_tuple(grid)
    counts = {col: placed.get(col, 0) + random.randint(0, 2) for col in range(1, k + 1)}
    ok, moves, reason = solve_mode1(n, counts, tgt)
    if ok:
        if simulate(n, moves) != tgt:
            ok_all = False
            break
        # заодно проверяется, что решатель не потратил больше, чем выдано
        cb = counts_by_color(moves)
        if any(cb[col] > counts.get(col, 0) for col in cb):
            ok_all = False
            break
    else:
        # сюда попадать нельзя: картинка заведомо собрана ходами
        ok_all = False
        break
check("200 случайных достижимых конфигураций восстановлены верно", ok_all)

print("== Исчерпывающая сверка достижимости (n=2, k=2: все 81 поле) ==")
# Сплошная проверка. На поле 2 на 2 с двумя цветами всего 81 картинка.
# Сначала перебором находится, какие из них вообще собираются, затем
# результат сверяется с ответом решателя.
from model import all_placements, block_cells, to_lists, to_tuple, empty_grid
import itertools

n, k = 2, 2
places = all_placements(n)


def reachable_set():
    start = empty_grid(n)
    seen = {start}
    frontier = [start]
    while frontier:
        nxt = []
        for g in frontier:
            for (r, c, w, h) in places:
                for col in range(1, k + 1):
                    ng = to_lists(g)
                    for (i, j) in block_cells(r, c, w, h):
                        ng[i][j] = col
                    t = to_tuple(ng)
                    if t not in seen:
                        seen.add(t)
                        nxt.append(t)
        frontier = nxt
    return seen  # каждое поле здесь достижимо и является допустимым итогом


ground = reachable_set()
mismatch = 0
for flat in itertools.product(range(k + 1), repeat=n * n):
    tgt = tuple(tuple(flat[i * n:(i + 1) * n]) for i in range(n))
    truth = tgt in ground
    ok, moves, reason = solve_mode1(n, {1: 10, 2: 10}, tgt)
    if ok != truth:
        mismatch += 1
    if ok and simulate(n, moves) != tgt:
        mismatch += 1
check("все 81 поле: вердикт достижимости совпал с эталоном", mismatch == 0)

print()
print(f"ВСЕ ТЕСТЫ ПРОЙДЕНЫ: {PASSED}")

# Не даём окну консоли закрыться сразу (запуск двойным кликом на Windows).
# При запуске через пайп/из скрипта stdin не терминал — тогда паузу пропускаем.
if sys.stdin and sys.stdin.isatty():
    try:
        input("\nНажмите Enter, чтобы закрыть окно...")
    except (EOFError, KeyboardInterrupt):
        pass
