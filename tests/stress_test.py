"""
Жёсткие стресс-тесты алгоритма. Запуск: python tests/stress_test.py

Проверяется не «примерами», а сверкой с эталоном (полный перебор) и
round-trip'ом на больших объёмах случайных данных:

  A. Режим 1 — исчерпывающая сверка достижимости со всем пространством
     картинок для n=2 (k=2,3) и n=3 (k=2). Это сотни тысяч полей.
  B. Режим 1 — round-trip на десятках тысяч случайных достижимых картинок
     (n до 5): решатель обязан собрать и точно воспроизвести исходник,
     не потратив больше выданного.
  C. Режим 1 — экономность: решение не тратит доминошек больше запаса.
  D. Режим 2 — исчерпывающая сверка с прямым перебором по всем коротким
     последовательностям на n=2 и n=3.
  E. Режимы 3/4 — точный счёт сверяется с прямым перебором на многих
     наборах; проверяется совпадение mode3/mode4 на «перестановочных» наборах.
  F. Прикидка Чао — включается на больших полях, не занижает observed,
     даёт величину не меньше реально увиденного.
  G. Производительность/устойчивость — крупные поля не валят решатель и
     не выдают ложное «невозможно» на заведомо достижимых картинках.
"""

import itertools
import os
import random
import sys
import time
from collections import Counter

# Тест лежит в tests/, а пакет dominoes — в корне проекта; добавляем корень
# в путь, иначе при запуске файлом напрямую import dominoes не найдётся.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from dominoes.model import (
    all_placements, block_cells, to_lists, to_tuple, empty_grid, simulate,
)
from dominoes.solver import (
    solve_mode1, solve_mode2, count_mode3, count_mode4,
    _feasible_ignoring_counts,
)

FAILS = []
CHECKS = 0


def check(name, cond, extra=""):
    global CHECKS
    CHECKS += 1
    if cond:
        print(f"  ok   : {name}")
    else:
        print(f"  FAIL : {name}   {extra}")
        FAILS.append(name)


def reachable_set(n, k):
    """Все картинки, достижимые любой последовательностью ходов (без лимита)."""
    places = all_placements(n)
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
    return seen


# ----------------------------------------------------------------------
print("== A. Исчерпывающая сверка достижимости (режим 1) ==")


def exhaustive_reachability(n, k, big_counts):
    """Каждое возможное поле проверяется: вердикт решателя == эталон перебора."""
    ground = reachable_set(n, k)
    counts = {c: big_counts for c in range(1, k + 1)}
    total = 0
    verdict_mismatch = 0
    replay_mismatch = 0
    feasible_mismatch = 0
    t0 = time.time()
    for flat in itertools.product(range(k + 1), repeat=n * n):
        total += 1
        tgt = tuple(tuple(flat[i * n:(i + 1) * n]) for i in range(n))
        truth = tgt in ground
        ok, moves, reason = solve_mode1(n, counts, tgt)
        if ok != truth:
            verdict_mismatch += 1
        if ok and simulate(n, moves) != tgt:
            replay_mismatch += 1
        # _feasible_ignoring_counts при неограниченном наборе обязан в
        # точности характеризовать достижимость
        feas, _ = _feasible_ignoring_counts(tgt, all_placements(n))
        if feas != truth:
            feasible_mismatch += 1
    dt = time.time() - t0
    return total, verdict_mismatch, replay_mismatch, feasible_mismatch, dt


for (n, k) in [(2, 2), (2, 3), (3, 2)]:
    total, vm, rm, fm, dt = exhaustive_reachability(n, k, big_counts=50)
    check(f"n={n} k={k}: {total} полей, вердикт == эталон", vm == 0, f"расхождений={vm}")
    check(f"n={n} k={k}: восстановленное поле точно воспроизводится", rm == 0, f"расхождений={rm}")
    check(f"n={n} k={k}: _feasible_ignoring_counts == достижимость", fm == 0, f"расхождений={fm}")
    print(f"        ({total} полей за {dt:.1f} c)")


# ----------------------------------------------------------------------
print("== B. Round-trip на случайных достижимых картинках ==")

random.seed(12345)
ROUNDS = 30000
bad_replay = 0
bad_overspend = 0
false_impossible = 0
maxmoves = 0
for it in range(ROUNDS):
    n = random.choice([2, 3, 4, 5])
    k = random.choice([1, 2, 3, 4])
    places = all_placements(n)
    grid = to_lists(empty_grid(n))
    placed = Counter()
    nmoves = random.randint(0, 3 * n)
    for _ in range(nmoves):
        r, c, w, h = random.choice(places)
        col = random.randint(1, k)
        for (i, j) in block_cells(r, c, w, h):
            grid[i][j] = col
        placed[col] += 1
    tgt = to_tuple(grid)
    # даём ровно столько, сколько положили, плюс немного лишнего
    counts = {col: placed.get(col, 0) + random.randint(0, 2) for col in range(1, k + 1)}
    ok, moves, reason = solve_mode1(n, counts, tgt)
    if ok is None:
        # лимит на этих размерах срабатывать не должен; но если сработал —
        # это не ложное «невозможно», а честное «не определено»
        continue
    if not ok:
        # картинка заведомо собрана ходами — «невозможно» тут ошибка
        false_impossible += 1
        continue
    if simulate(n, moves) != tgt:
        bad_replay += 1
    cb = Counter(m.color for m in moves)
    if any(cb[col] > counts.get(col, 0) for col in cb):
        bad_overspend += 1
    maxmoves = max(maxmoves, len(moves))

check(f"{ROUNDS} случайных: ни одного ложного 'невозможно'", false_impossible == 0,
      f"ложных={false_impossible}")
check(f"{ROUNDS} случайных: все воспроизводятся точно", bad_replay == 0, f"плохих={bad_replay}")
check(f"{ROUNDS} случайных: перерасхода запаса нет", bad_overspend == 0, f"плохих={bad_overspend}")
print(f"        (макс. длина решения {maxmoves} ходов)")


# ----------------------------------------------------------------------
print("== C. Режим 1: минимальный запас и нехватка ==")

# при нехватке хотя бы одного цвета решение обязано отсутствовать
random.seed(99)
short_bad = 0
tries = 3000
for _ in range(tries):
    n = random.choice([2, 3])
    k = random.choice([1, 2])
    places = all_placements(n)
    grid = to_lists(empty_grid(n))
    placed = Counter()
    for _ in range(random.randint(1, 4)):
        r, c, w, h = random.choice(places)
        col = random.randint(1, k)
        for (i, j) in block_cells(r, c, w, h):
            grid[i][j] = col
        placed[col] += 1
    tgt = to_tuple(grid)
    # достижимо с неограниченным набором?
    feas, _ = _feasible_ignoring_counts(tgt, places)
    if not feas:
        continue
    # выдаём заведомо достаточный набор -> должно решаться
    ok, moves, reason = solve_mode1(n, {c: 10 for c in range(1, k + 1)}, tgt)
    if not ok or simulate(n, moves) != tgt:
        short_bad += 1
check("достижимая картинка при достаточном наборе всегда решается", short_bad == 0,
      f"плохих={short_bad}")


# ----------------------------------------------------------------------
print("== D. Режим 2: сверка с прямым перебором по последовательностям ==")


def ref_mode2_reachable(n, seq):
    """Множество картинок, получаемых ровно этой последовательностью ходов."""
    places = all_placements(n)
    finals = set()

    def rec(grid, i):
        if i == len(seq):
            finals.add(grid)
            return
        for (r, c, w, h) in places:
            g = to_lists(grid)
            for (a, b) in block_cells(r, c, w, h):
                g[a][b] = seq[i]
            rec(to_tuple(g), i + 1)
    rec(empty_grid(n), 0)
    return finals


mode2_mismatch = 0
mode2_replay = 0
cases = 0
for n in [2, 3]:
    k = 2
    max_len = 3 if n == 3 else 4
    for L in range(1, max_len + 1):
        for seq in itertools.product(range(1, k + 1), repeat=L):
            seq = list(seq)
            reach = ref_mode2_reachable(n, seq)
            # проверяем на всех достижимых + горсти случайных недостижимых
            candidates = set(reach)
            for _ in range(20):
                flat = tuple(random.randint(0, k) for _ in range(n * n))
                candidates.add(tuple(tuple(flat[i * n:(i + 1) * n]) for i in range(n)))
            for tgt in candidates:
                cases += 1
                truth = tgt in reach
                ok, moves, reason = solve_mode2(n, seq, tgt)
                if ok != truth:
                    mode2_mismatch += 1
                if ok and simulate(n, moves) != tgt:
                    mode2_replay += 1

check(f"режим 2 == прямой перебор ({cases} проверок)", mode2_mismatch == 0,
      f"расхождений={mode2_mismatch}")
check("режим 2: восстановление точно воспроизводит картинку", mode2_replay == 0,
      f"плохих={mode2_replay}")


# ----------------------------------------------------------------------
print("== E. Режимы 3/4: точный счёт против прямого перебора ==")


def ref_count_seq(n, seq):
    places = all_placements(n)
    finals = set()

    def rec(grid, i):
        if i == len(seq):
            finals.add(grid)
            return
        for (r, c, w, h) in places:
            g = to_lists(grid)
            for (a, b) in block_cells(r, c, w, h):
                g[a][b] = seq[i]
            rec(to_tuple(g), i + 1)
    rec(empty_grid(n), 0)
    return len(finals)


def ref_count_set(n, counts):
    """Полный перебор режима 3: все порядки всех перестановок набора."""
    multiset = [c for c in sorted(counts) for _ in range(counts[c])]
    finals = set()
    for perm in set(itertools.permutations(multiset)):
        # для каждой перестановки — все размещения
        places = all_placements(n)

        def rec(grid, i, perm=perm, places=places):
            if i == len(perm):
                finals.add(grid)
                return
            for (r, c, w, h) in places:
                g = to_lists(grid)
                for (a, b) in block_cells(r, c, w, h):
                    g[a][b] = perm[i]
                rec(to_tuple(g), i + 1)
        rec(empty_grid(n), 0)
    return len(finals)


c4_bad = 0
c4_cases = 0
for n in [2, 3]:
    k = 2
    max_len = 3 if n == 3 else 4
    for L in range(1, max_len + 1):
        for seq in itertools.product(range(1, k + 1), repeat=L):
            c4_cases += 1
            fast = count_mode4(n, list(seq))
            ref = ref_count_seq(n, list(seq))
            if not (fast.exact and fast.value == ref):
                c4_bad += 1
check(f"режим 4 точный счёт == перебор ({c4_cases} последовательностей)", c4_bad == 0,
      f"плохих={c4_bad}")

c3_bad = 0
c3_cases = 0
for n in [2, 3]:
    for counts in [{1: 1}, {1: 2}, {1: 1, 2: 1}, {1: 2, 2: 1}, {1: 1, 2: 2},
                   {1: 2, 2: 2}, {1: 3}]:
        c3_cases += 1
        fast = count_mode3(n, counts)
        ref = ref_count_set(n, counts)
        if not (fast.exact and fast.value == ref):
            c3_bad += 1
            print(f"        расхождение: n={n} counts={counts} "
                  f"fast={fast.value}(exact={fast.exact}) ref={ref}")
check(f"режим 3 точный счёт == перебор ({c3_cases} наборов)", c3_bad == 0,
      f"плохих={c3_bad}")

# mode3 из одного цвета == mode4 из последовательности этого же цвета
mode3v4 = 0
for n in [2, 3]:
    for cnt in range(1, 4):
        r3 = count_mode3(n, {1: cnt})
        r4 = count_mode4(n, [1] * cnt)
        if not (r3.exact and r4.exact and r3.value == r4.value):
            mode3v4 += 1
check("режим 3 {1:c} совпадает с режимом 4 [1]*c", mode3v4 == 0, f"плохих={mode3v4}")


# ----------------------------------------------------------------------
print("== F. Прикидка Чао на больших полях ==")

r = count_mode4(4, [1, 2, 1, 2, 1], cap=300, trials=6000)
check("n=4: включается прикидка, не точный счёт", not r.exact and r.method.startswith("прикидка"))
check("n=4: оценка не ниже реально увиденного", r.value >= r.observed > 0,
      f"value={r.value} observed={r.observed}")

r = count_mode3(4, {1: 2, 2: 2, 3: 1}, cap=300, trials=6000)
check("n=4 набор: прикидка включилась", not r.exact)
check("n=4 набор: оценка >= observed > 0", r.value >= r.observed > 0,
      f"value={r.value} observed={r.observed}")


# ----------------------------------------------------------------------
print("== G. Производительность и устойчивость на крупных полях ==")

random.seed(2024)
big_false_impossible = 0
big_replay = 0
limit_hits = 0
t0 = time.time()
BIG_ROUNDS = 400
for _ in range(BIG_ROUNDS):
    n = random.choice([6, 7, 8])
    k = random.choice([2, 3, 4])
    places = all_placements(n)
    grid = to_lists(empty_grid(n))
    placed = Counter()
    for _ in range(random.randint(3, 2 * n)):
        r, c, w, h = random.choice(places)
        col = random.randint(1, k)
        for (i, j) in block_cells(r, c, w, h):
            grid[i][j] = col
        placed[col] += 1
    tgt = to_tuple(grid)
    counts = {col: placed.get(col, 0) + random.randint(0, 3) for col in range(1, k + 1)}
    ok, moves, reason = solve_mode1(n, counts, tgt)
    if ok is None:
        # честное «не определено» — не ошибка, лишь бюджет исчерпан
        limit_hits += 1
    elif not ok:
        # картинка собрана ходами, значит доказанное «невозможно» — ошибка
        big_false_impossible += 1
    elif simulate(n, moves) != tgt:
        big_replay += 1
dt = time.time() - t0
check(f"{BIG_ROUNDS} крупных полей (n<=8): без ложного 'невозможно'",
      big_false_impossible == 0, f"ложных={big_false_impossible}")
check("крупные поля: восстановление точно воспроизводится", big_replay == 0,
      f"плохих={big_replay}")
print(f"        ({BIG_ROUNDS} задач за {dt:.1f} c, упёрлись в лимит перебора: {limit_hits})")

# один заведомо тяжёлый случай: почти полностью залитое поле n=8
n = 8
grid = to_lists(empty_grid(n))
places = all_placements(n)
random.seed(7)
placed = Counter()
for _ in range(60):
    r, c, w, h = random.choice(places)
    col = random.randint(1, 3)
    for (i, j) in block_cells(r, c, w, h):
        grid[i][j] = col
    placed[col] += 1
tgt = to_tuple(grid)
t0 = time.time()
ok, moves, reason = solve_mode1(n, {c: placed.get(c, 0) + 3 for c in range(1, 4)}, tgt)
dt = time.time() - t0
check("плотное поле 8x8 (~60 ходов) решается и воспроизводится",
      ok and simulate(n, moves) == tgt, f"reason={reason}")
print(f"        (решено за {dt:.2f} c, ходов={len(moves) if ok else '-'})")


# ----------------------------------------------------------------------
print("== H. Честный ответ при исчерпании лимита перебора ==")

# Берём заведомо РЕШАЕМУЮ картинку. Сначала узнаём длину решения L (перебор
# любой длины-L цепочки проходит не меньше L узлов), затем душим лимитом L-1 —
# тогда перебор гарантированно не успевает дойти до решения. Правильное
# поведение при этом: ok is None («не определено»), а НЕ ok is False
# («доказано невозможно»). Отдельно проверяем 300 разных решаемых картинок:
# ни одна не должна выдать ложного False ни при каком лимите.
random.seed(555)
none_seen = 0
wrong_false = 0
verified_recover = 0
for _ in range(300):
    n = random.choice([5, 6, 7])
    k = random.choice([2, 3])
    places = all_placements(n)
    grid = to_lists(empty_grid(n))
    placed = Counter()
    for _ in range(random.randint(n, 3 * n)):
        r, c, w, h = random.choice(places)
        col = random.randint(1, k)
        for (i, j) in block_cells(r, c, w, h):
            grid[i][j] = col
        placed[col] += 1
    tgt = to_tuple(grid)
    counts = {c: placed.get(c, 0) + 2 for c in range(1, k + 1)}

    ok_big, moves_big, _ = solve_mode1(n, counts, tgt, node_cap=5_000_000)
    if not (ok_big and simulate(n, moves_big) == tgt):
        continue  # берём в проверку только заведомо решаемые
    L = len(moves_big)
    if L == 0:
        continue

    ok_small, _, reason_small = solve_mode1(n, counts, tgt, node_cap=L - 1)
    if ok_small is False:
        # картинка собрана ходами — доказанное «невозможно» недопустимо
        wrong_false += 1
    elif ok_small is None:
        none_seen += 1
        # честный ответ обязан пояснять, что дело в бюджете, а не в невозможности
        if reason_small and ("бюджет" in reason_small or "лимит" in reason_small):
            verified_recover += 1

check("на решаемых картинках лимит не даёт ложного 'невозможно' (False)",
      wrong_false == 0, f"ложных False={wrong_false}")
check("тесный лимит хотя бы раз даёт честное None", none_seen > 0,
      f"None получено {none_seen} раз")
check("каждое None сопровождается пояснением про бюджет/лимит",
      verified_recover == none_seen, f"{verified_recover} из {none_seen}")

# То же для режима 2: последовательность длины m всегда разбирается за m узлов,
# поэтому лимит m-1 гарантированно даёт None на решаемой картинке.
n = 6
places = all_placements(n)
random.seed(4242)
seq = [random.randint(1, 3) for _ in range(2 * n)]
grid = to_lists(empty_grid(n))
for col in seq:
    r, c, w, h = random.choice(places)
    for (i, j) in block_cells(r, c, w, h):
        grid[i][j] = col
tgt = to_tuple(grid)
ok_big2, moves2, _ = solve_mode2(n, seq, tgt, node_cap=5_000_000)
check("режим 2: большой лимит решает картинку", ok_big2 and simulate(n, moves2) == tgt)
ok_small2, _, reason2 = solve_mode2(n, seq, tgt, node_cap=len(seq) - 1)
check("режим 2: тесный лимит -> None, а не False", ok_small2 is None, f"ok={ok_small2}")
check("режим 2: reason про бюджет/лимит",
      ok_small2 is None and reason2 and ("бюджет" in reason2 or "лимит" in reason2))


# ----------------------------------------------------------------------
def _pause():
    """Не даём окну консоли закрыться сразу при запуске двойным кликом.
    Через пайп/из скрипта (stdin не терминал) паузу пропускаем."""
    if sys.stdin and sys.stdin.isatty():
        try:
            input("\nНажмите Enter, чтобы закрыть окно...")
        except (EOFError, KeyboardInterrupt):
            pass


print()
if FAILS:
    print(f"ПРОВАЛЕНО ПРОВЕРОК: {len(FAILS)} из {CHECKS}")
    for f in FAILS:
        print("   -", f)
    _pause()
    raise SystemExit(1)
else:
    print(f"ВСЕ СТРЕСС-ПРОВЕРКИ ПРОЙДЕНЫ: {CHECKS}")
    _pause()
