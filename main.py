"""
Точка входа. Запуск:

    python main.py          консольная версия, ничего доустанавливать не нужно
    python main.py --gui    окно (нужны customtkinter и pillow)

Двойным кликом удобнее через start_cli.bat и start_gui.bat.
Сама логика лежит в пакете dominoes и от способа запуска не зависит.
"""

import sys


def _show_error(title, text):
    """
    Показать сообщение об ошибке.

    Под pythonw (окно запускается без консоли) печатать некуда: print уходит
    в никуда, и человек видит просто молчание вместо причины. Поэтому сначала
    пробуем диалоговое окно и только потом — консоль.
    """
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(title, text)
        root.destroy()
        return
    except Exception:
        pass

    print(f"{title}\n\n{text}")
    from dominoes.ui.cli import pause
    pause()


def _run_gui():
    try:
        from dominoes.ui.gui import main as gui_main
    except ImportError as ex:
        # Окно требует сторонних библиотек, консольная версия — нет.
        # Подсказываем, что доставить, вместо голого стека вызовов.
        _show_error(
            "Не удалось открыть окно",
            f"{ex}\n\n"
            "Установите зависимости командой:\n"
            "    pip install -r requirements.txt\n\n"
            "Консольная версия работает без них: start_cli.bat")
        return 1
    gui_main()
    return 0


def _run_cli():
    from dominoes.ui.cli import main as cli_main, pause
    try:
        cli_main()
    except (KeyboardInterrupt, EOFError):
        print("\nВыход.")
    except Exception:
        # Без паузы окно закрылось бы вместе с текстом ошибки, и понять,
        # что произошло, было бы невозможно.
        import traceback
        traceback.print_exc()
        pause("\nПроизошла ошибка. Нажмите Enter, чтобы закрыть окно...")
        return 1
    return 0


def main():
    if "--gui" in sys.argv[1:]:
        return _run_gui()
    return _run_cli()


if __name__ == "__main__":
    sys.exit(main())
