"""
Версия для консоли, без окна. Запуск: python3 cli.py

Работает на голом Python, доустанавливать ничего не нужно. Программа
спрашивает режим и параметры, картинка вводится с клавиатуры.
"""

import sys

# Windows-консоль по умолчанию не в UTF-8, из-за чего кириллица выводится
# кракозябрами. Принудительно переключаем потоки на UTF-8 — на современных
# терминалах (Windows Terminal, VS Code, *nix) текст читается корректно.
for _stream in (sys.stdout, sys.stderr, sys.stdin):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from dominoes.model import simulate, describe_move, EMPTY
from dominoes.solver import solve_mode1, solve_mode2, count_mode3, count_mode4

CELL_CHARS = ".123456789"  # символ клетки: '.' = пусто, цифра = цвет


def pause(message="\nНажмите Enter, чтобы закрыть окно..."):
    """
    Задержать окно, пока ответ не прочитан.

    При запуске двойным кликом консоль закрывается сразу после последней
    строки, и ответ увидеть не успеваешь. Пауза это чинит.

    Если ввод идёт не с терминала (запуск через пайп, из скрипта, автотесты),
    паузы нет — иначе программа зависла бы, ожидая Enter, которого не будет.
    """
    if sys.stdin and sys.stdin.isatty():
        try:
            input(message)
        except (EOFError, KeyboardInterrupt):
            pass


def print_grid(grid):
    for row in grid:
        print("   " + " ".join(CELL_CHARS[v] if v != EMPTY else "." for v in row))


def ask_int(prompt, lo, hi, default=None):
    while True:
        raw = input(prompt).strip()
        if raw == "" and default is not None:
            return default
        try:
            v = int(raw)
            if lo <= v <= hi:
                return v
        except ValueError:
            pass
        print(f"   Введите целое число от {lo} до {hi}.")


def read_grid(n, k):
    print(f"Введите {n} строк по {n} символов. '.' или '0' — пусто, цифра 1..{k} — цвет.")
    grid = []
    for i in range(n):
        while True:
            raw = input(f"  строка {i + 1}: ").strip().replace(" ", "")
            if len(raw) != n:
                print(f"   Нужно ровно {n} символов.")
                continue
            row = []
            good = True
            for ch in raw:
                if ch in ".0":
                    row.append(0)
                elif ch.isdigit() and 1 <= int(ch) <= k:
                    row.append(int(ch))
                else:
                    good = False
                    break
            if not good:
                print(f"   Допустимы только '.', '0' и цифры 1..{k}.")
                continue
            grid.append(tuple(row))
            break
    return tuple(grid)


def read_sequence(k):
    while True:
        raw = input(f"Последовательность цветов через пробел (1..{k}): ").strip()
        parts = raw.split()
        try:
            seq = [int(x) for x in parts]
        except ValueError:
            print("   Только числа.")
            continue
        if all(1 <= x <= k for x in seq):
            return seq
        print(f"   Цвета должны быть от 1 до {k}.")


def read_counts(k):
    counts = {}
    print("Количество доминошек каждого цвета:")
    for col in range(1, k + 1):
        counts[col] = ask_int(f"  цвет {col} (0..10): ", 0, 10, default=0)
    return counts


def show_solution(n, ok, moves, reason):
    if ok is None:
        # Перебор не уложился в лимит: ни решения, ни доказательства невозможности.
        print("\n>>> НЕ ОПРЕДЕЛЕНО (не хватило бюджета перебора).")
        print("    Это не значит «невозможно» — перебор просто не успел.")
        print("    Пояснение:", reason)
        return
    if not ok:
        print("\n>>> НЕВОЗМОЖНО (доказано).")
        print("    Обоснование:", reason)
        return
    print(f"\n>>> РЕШЕНИЕ НАЙДЕНО. Ходов: {len(moves)}")
    for idx, m in enumerate(moves, 1):
        print("   " + describe_move(m, idx))
    print("\n   Пошаговое проигрывание:")
    for t in range(len(moves) + 1):
        print(f"   --- после {t} ходов ---")
        print_grid(simulate(n, moves[:t]))


def main():
    print("=" * 60)
    print("  ПЕРЕКРЫВАЮЩИЕСЯ ДОМИНОШКИ — консольная версия")
    print("=" * 60)
    print("Режимы:")
    print("  1 — восстановить ходы по НАБОРУ доминошек")
    print("  2 — восстановить ходы по ПОСЛЕДОВАТЕЛЬНОСТИ")
    print("  3 — посчитать число картинок (набор)")
    print("  4 — посчитать число картинок (последовательность)")
    mode = ask_int("Выберите режим (1-4): ", 1, 4)

    n = ask_int("Размер поля n (2..10): ", 2, 10)
    k = ask_int("Число цветов k (1..9): ", 1, 9)

    if mode == 1:
        counts = read_counts(k)
        target = read_grid(n, k)
        print("\nКартинка, которую нужно собрать:")
        print_grid(target)
        ok, moves, reason = solve_mode1(n, counts, target)
        show_solution(n, ok, moves, reason)

    elif mode == 2:
        seq = read_sequence(k)
        target = read_grid(n, k)
        print("\nКартинка, которую нужно собрать:")
        print_grid(target)
        ok, moves, reason = solve_mode2(n, seq, target)
        show_solution(n, ok, moves, reason)

    elif mode == 3:
        counts = read_counts(k)
        res = count_mode3(n, counts)
        if res.exact:
            print(f"\n>>> Разных картинок: {res.value}  (посчитано точно)")
        else:
            print(f"\n>>> Разных картинок: примерно {res.value}")
            print(f"    точно встретилось {res.observed} разных картинок, меньше не будет;")
            print(f"    картинок слишком много, чтобы сосчитать их все.")

    else:
        seq = read_sequence(k)
        res = count_mode4(n, seq)
        if res.exact:
            print(f"\n>>> Разных картинок: {res.value}  (посчитано точно)")
        else:
            print(f"\n>>> Разных картинок: примерно {res.value}")
            print(f"    точно встретилось {res.observed} разных картинок, меньше не будет;")
            print(f"    картинок слишком много, чтобы сосчитать их все.")

    # Ответ напечатан — держим окно, иначе при запуске кликом его не прочитать.
    pause()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nВыход.")
