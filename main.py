"""
Точка входа. Запуск:

    python main.py          консольная версия, ничего доустанавливать не нужно
    python main.py --gui    окно (нужны customtkinter и pillow)

Сама логика лежит в пакете dominoes и от способа запуска не зависит.
"""

import sys


def main():
    if "--gui" in sys.argv[1:]:
        try:
            from dominoes.ui.gui import main as gui_main
        except ImportError as ex:
            # Окно требует сторонних библиотек, консольная версия — нет.
            # Подсказываем, что доставить, вместо голого стека вызовов.
            print(f"Не удалось запустить окно: {ex}")
            print("Установите зависимости:  pip install -r requirements.txt")
            print("Консольная версия работает без них:  python main.py")
            return 1
        gui_main()
        return 0

    from dominoes.ui.cli import main as cli_main
    cli_main()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nВыход.")
