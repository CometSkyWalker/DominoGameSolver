"""
Окно программы. Запуск: python3 gui.py

Здесь только внешний вид и обработка кнопок. Все вычисления вынесены в
solver.py, поле и ходы описаны в model.py — благодаря этому оформление можно
менять, не трогая решатель.

Нужны библиотеки customtkinter и pillow (pip install customtkinter pillow).
Если их ставить не нужно, есть версия для консоли — cli.py.
"""
import tkinter as tk
import customtkinter as ctk
from PIL import ImageTk

import theme as T
from model import EMPTY, Move, block_cells, describe_move, simulate
from solver import solve_mode1, solve_mode2, count_mode3, count_mode4

ctk.set_appearance_mode("dark")
ctk.set_widget_scaling(1.0)

FB = (T.FONT, 13, "bold")
FN = (T.FONT, 13)
FS = (T.FONT, 12)
FMONO = ("DejaVu Sans Mono", 12)

MODES = [
    ("1", "Набор доминошек", "по набору a₁,a₂,… восстановить ходы"),
    ("2", "Последовательность", "класть строго по заданному порядку"),
    ("3", "Счёт конфигураций · набор", "сколько разных итогов даёт набор"),
    ("4", "Счёт конфигураций · посл-ть", "сколько разных итогов даёт порядок"),
]


# Кнопка с переходом цвета. В tkinter такой нет, поэтому она рисуется
# вручную: картинка готовится через Pillow и кладётся на холст.
class GradientButton(tk.Canvas):
    def __init__(self, master, text, command, width=260, height=50,
                 c1=T.ACCENT, c2=T.ACCENT_2, radius=16, bg=T.CARD, font=(T.FONT, 15, "bold")):
        super().__init__(master, width=width, height=height, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._cmd = command
        self._bw, self._bh = width, height
        self._normal = ImageTk.PhotoImage(T.gradient(width, height, c1, c2, radius=radius))
        self._hover = ImageTk.PhotoImage(T.gradient(width, height, T.ACCENT_HI, "#f472b6", radius=radius))
        self._img = self.create_image(0, 0, anchor="nw", image=self._normal)
        self._txt = self.create_text(width // 2, height // 2, text=text,
                                     fill="white", font=font)
        self.bind("<Enter>", lambda e: self.itemconfig(self._img, image=self._hover))
        self.bind("<Leave>", lambda e: self.itemconfig(self._img, image=self._normal))
        self.bind("<Button-1>", lambda e: self._cmd() if self._cmd else None)

    def set_text(self, text):
        self.itemconfig(self._txt, text=text)


# Игровое поле: клетки рисуются со скруглёнными углами.
class GridCanvas(tk.Canvas):
    def __init__(self, master, max_px=360, on_click=None, bg=T.CARD):
        super().__init__(master, width=max_px, height=max_px, bg=bg,
                         highlightthickness=0, bd=0)
        self.max_px = max_px
        self.on_click = on_click
        self.n = 3
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._click)

    def _geom(self, n):
        gap = 8 if n <= 6 else 5
        cell = int((self.max_px - gap * (n + 1)) / n)
        cell = max(14, cell)
        size = gap * (n + 1) + cell * n
        return gap, cell, size

    @staticmethod
    def _round(canvas, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return canvas.create_polygon(pts, smooth=True, **kw)

    def draw(self, grid, highlight=None):
        """Отрисовка поля. highlight — ход, который нужно обвести рамкой."""
        self.delete("all")
        n = len(grid)
        self.n = n
        gap, cell, size = self._geom(n)
        self.configure(width=size, height=size)
        for i in range(n):
            for j in range(n):
                x1 = gap + j * (cell + gap)
                y1 = gap + i * (cell + gap)
                x2, y1b, y2 = x1 + cell, y1, y1 + cell
                v = grid[i][j]
                color = T.CELLS[v] if 0 <= v < len(T.CELLS) else "#ffffff"
                r = max(6, cell // 6)
                if v == EMPTY:
                    self._round(self, x1, y1, x2, y2, r, fill=T.CELLS[0], outline=T.STROKE)
                else:
                    self._round(self, x1, y1, x2, y2, r, fill=color, outline="")
        # рамка вокруг последней положенной доминошки — видно, что изменилось
        if highlight is not None:
            cells = block_cells(highlight.r, highlight.c, highlight.w, highlight.h)
            (i0, j0) = min(cells); (i1, j1) = max(cells)
            x1 = gap + j0 * (cell + gap) - 3
            y1 = gap + i0 * (cell + gap) - 3
            x2 = gap + j1 * (cell + gap) + cell + 3
            y2 = gap + i1 * (cell + gap) + cell + 3
            self._round(self, x1, y1, x2, y2, max(8, cell // 6),
                        outline="#ffffff", width=3, fill="")

    def _click(self, e):
        if not self.on_click:
            return
        gap, cell, size = self._geom(self.n)
        j = int((e.x - gap) // (cell + gap))
        i = int((e.y - gap) // (cell + gap))
        if 0 <= i < self.n and 0 <= j < self.n:
            # проверка, что клик попал в клетку, а не в промежуток между ними
            x1 = gap + j * (cell + gap)
            y1 = gap + i * (cell + gap)
            if x1 <= e.x <= x1 + cell and y1 <= e.y <= y1 + cell:
                self.on_click(i, j)


# Маленький выбор числа кнопками «минус» и «плюс».
class Stepper(ctk.CTkFrame):
    def __init__(self, master, value=1, lo=0, hi=10, width=44):
        super().__init__(master, fg_color=T.INPUT, corner_radius=10)
        self.v = value; self.lo = lo; self.hi = hi
        self.minus = ctk.CTkButton(self, text="−", width=26, height=26, corner_radius=8,
                                   fg_color="transparent", hover_color=T.CARD_HI,
                                   text_color=T.TEXT_DIM, font=(T.FONT, 16, "bold"),
                                   command=lambda: self._step(-1))
        self.lbl = ctk.CTkLabel(self, text=str(value), width=width, font=FB, text_color=T.TEXT)
        self.plus = ctk.CTkButton(self, text="+", width=26, height=26, corner_radius=8,
                                  fg_color="transparent", hover_color=T.CARD_HI,
                                  text_color=T.TEXT_DIM, font=(T.FONT, 16, "bold"),
                                  command=lambda: self._step(+1))
        self.minus.grid(row=0, column=0, padx=(4, 0), pady=3)
        self.lbl.grid(row=0, column=1, padx=0, pady=3)
        self.plus.grid(row=0, column=2, padx=(0, 4), pady=3)

    def _step(self, d):
        self.v = max(self.lo, min(self.hi, self.v + d))
        self.lbl.configure(text=str(self.v))

    def get(self):
        return self.v

    def set(self, x):
        self.v = max(self.lo, min(self.hi, x))
        self.lbl.configure(text=str(self.v))


# Карточка с рамкой — из таких блоков собрано всё окно.
def card(master, **kw):
    return ctk.CTkFrame(master, fg_color=T.CARD, corner_radius=18,
                        border_width=1, border_color=T.STROKE, **kw)


def card_title(master, text, sub=None):
    box = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(box, text=text, font=(T.FONT, 16, "bold"), text_color=T.TEXT).pack(anchor="w")
    if sub:
        ctk.CTkLabel(box, text=sub, font=FS, text_color=T.MUTED).pack(anchor="w")
    return box


# Само окно программы.
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Перекрывающиеся доминошки")
        self.geometry("1240x860")
        self.minsize(1120, 780)
        self.configure(fg_color=T.BG)

        self.mode = "1"
        self.n = 3
        self.k = 3
        self.brush = 1
        self.target = [[EMPTY] * self.n for _ in range(self.n)]
        self.solution = []
        self.step = 0
        self.count_steppers = []
        self.chip_widgets = []
        self._playing = False
        self._play_after = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()
        self._select_mode("1")

    # Панель слева со списком режимов.
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=248, corner_radius=0, fg_color=T.SIDEBAR)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)

        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.pack(fill="x", padx=22, pady=(26, 8))
        dot = tk.Canvas(logo, width=38, height=38, bg=T.SIDEBAR, highlightthickness=0)
        dot._im = ImageTk.PhotoImage(T.gradient(38, 38, T.ACCENT, T.ACCENT_2, radius=12))
        dot.create_image(0, 0, anchor="nw", image=dot._im)
        dot.create_text(19, 19, text="▦", fill="white", font=(T.FONT, 17, "bold"))
        dot.pack(side="left")
        tx = ctk.CTkFrame(logo, fg_color="transparent"); tx.pack(side="left", padx=10)
        ctk.CTkLabel(tx, text="Доминошки", font=(T.FONT, 17, "bold"), text_color=T.TEXT).pack(anchor="w")
        ctk.CTkLabel(tx, text="перекрывающиеся доминошки", font=(T.FONT, 11), text_color=T.MUTED).pack(anchor="w")

        ctk.CTkLabel(sb, text="РЕЖИМЫ", font=(T.FONT, 11, "bold"),
                     text_color=T.MUTED).pack(anchor="w", padx=24, pady=(18, 6))

        self.nav_buttons = {}
        for key, title, sub in MODES:
            b = ctk.CTkButton(
                sb, text=f"  {key}   {title}", anchor="w", height=46, corner_radius=12,
                fg_color="transparent", hover_color=T.CARD_HI, text_color=T.TEXT_DIM,
                font=FN, command=lambda k=key: self._select_mode(k))
            b.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[key] = b


    # Всё, что справа от панели режимов.
    def _build_main(self):
        main = ctk.CTkScrollableFrame(self, fg_color=T.BG)
        main.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        main.grid_columnconfigure(0, weight=1)
        self.main = main

        # шапка с названием режима
        banner = tk.Canvas(main, height=104, bg=T.BG, highlightthickness=0)
        banner.pack(fill="x", padx=24, pady=(22, 0))
        self._banner = banner
        banner.bind("<Configure>", self._draw_banner)

        # строка сверху: размер поля и число цветов
        # (размер доминошки задан условием и не меняется)
        bar = card(main); bar.pack(fill="x", padx=24, pady=(16, 0))
        row = ctk.CTkFrame(bar, fg_color="transparent"); row.pack(fill="x", padx=18, pady=14)
        self._param(row, "Поле n", "n", 2, 10, 0)
        self._param(row, "Цветов k", "k", 1, 9, 1)

        # две колонки: слева картинка, справа настройки и ответ
        cols = ctk.CTkFrame(main, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=24, pady=16)
        cols.grid_columnconfigure(0, weight=0)
        cols.grid_columnconfigure(1, weight=1)

        # слева — поле, которое нужно собрать
        left = card(cols); left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        card_title(left, "Целевая конфигурация", "клик по клетке — покрасить выбранной кистью")\
            .pack(anchor="w", padx=20, pady=(18, 10))
        self.grid_canvas = GridCanvas(left, max_px=360, on_click=self._paint, bg=T.CARD)
        self.grid_canvas.pack(padx=20, pady=(0, 8))
        self.palette = ctk.CTkFrame(left, fg_color="transparent")
        self.palette.pack(fill="x", padx=20, pady=(4, 8))
        clr = ctk.CTkButton(left, text="Очистить поле", height=34, corner_radius=10,
                            fg_color=T.INPUT, hover_color=T.CARD_HI, text_color=T.TEXT_DIM,
                            font=FS, command=self._clear)
        clr.pack(anchor="w", padx=20, pady=(0, 18))

        # справа — параметры режима и результат
        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)

        pc = card(right); pc.grid(row=0, column=0, sticky="ew")
        self.param_header = card_title(pc, "Параметры режима", "")
        self.param_header.pack(anchor="w", padx=20, pady=(18, 8))
        self.mode_panel = ctk.CTkFrame(pc, fg_color="transparent")
        self.mode_panel.pack(fill="x", padx=20, pady=(0, 10))
        self.solve_btn = GradientButton(pc, "РЕШИТЬ", self._run, width=300, height=52, bg=T.CARD)
        self.solve_btn.pack(anchor="w", padx=20, pady=(4, 20))

        rc = card(right); rc.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        card_title(rc, "Результат", "последовательность ходов / вывод")\
            .pack(anchor="w", padx=20, pady=(18, 8))
        self.result = ctk.CTkTextbox(rc, height=190, fg_color=T.CARD_HI, corner_radius=12,
                                     text_color=T.TEXT_DIM, font=FMONO, border_width=0)
        self.result.pack(fill="x", padx=20, pady=(0, 20))
        self.result.insert("1.0", "Задайте параметры и нажмите «РЕШИТЬ».")
        self.result.configure(state="disabled")

        # внизу — показ решения по шагам
        play = card(main); play.pack(fill="x", padx=24, pady=(0, 26))
        head = ctk.CTkFrame(play, fg_color="transparent"); head.pack(fill="x", padx=20, pady=(18, 6))
        card_title(head, "Проигрывание решения", "как ходы накладываются один за другим")\
            .pack(side="left", anchor="w")
        self.step_lbl = ctk.CTkLabel(head, text="ход 0 / 0", font=FB, text_color=T.MUTED)
        self.step_lbl.pack(side="right")
        body = ctk.CTkFrame(play, fg_color="transparent"); body.pack(fill="x", padx=20, pady=(4, 20))
        self.replay_canvas = GridCanvas(body, max_px=300, on_click=None, bg=T.CARD)
        self.replay_canvas.pack(side="left")
        ctrl = ctk.CTkFrame(body, fg_color="transparent"); ctrl.pack(side="left", padx=24)
        ctk.CTkButton(ctrl, text="‹ шаг назад", width=140, height=40, corner_radius=10,
                      fg_color=T.INPUT, hover_color=T.CARD_HI, text_color=T.TEXT, font=FN,
                      command=lambda: self._step_manual(-1)).pack(pady=6)
        ctk.CTkButton(ctrl, text="шаг вперёд ›", width=140, height=40, corner_radius=10,
                      fg_color=T.INPUT, hover_color=T.CARD_HI, text_color=T.TEXT, font=FN,
                      command=lambda: self._step_manual(+1)).pack(pady=6)
        self.play_btn = GradientButton(ctrl, "▶  Проиграть", self._play_all,
                                       width=180, height=44, bg=T.CARD)
        self.play_btn.pack(pady=(10, 0))
        self.move_lbl = ctk.CTkLabel(body, text="", font=FN, text_color=T.TEXT_DIM,
                                     wraplength=280, justify="left")
        self.move_lbl.pack(side="left", padx=20, anchor="n")

        self._build_palette()
        self.grid_canvas.draw(self.target)
        self.replay_canvas.draw(self.target)

    def _param(self, parent, label, attr, lo, hi, col):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=0, column=col, padx=(0, 26))
        ctk.CTkLabel(box, text=label, font=FS, text_color=T.MUTED).pack(anchor="w", pady=(0, 4))
        st = Stepper(box, value=getattr(self, attr), lo=lo, hi=hi)
        st.pack()
        # подмена обработчика: при смене числа окно перестраивается
        orig = st._step
        def stepped(d, a=attr, s=st, o=orig):
            o(d); setattr(self, a, s.get()); self._on_param_change(a)
        st._step = stepped
        st.minus.configure(command=lambda s=st: s._step(-1))
        st.plus.configure(command=lambda s=st: s._step(+1))
        setattr(self, f"st_{attr}", st)

    # Реакция на изменение параметров сверху.
    def _on_param_change(self, attr):
        if attr == "n":
            new = self.st_n.get()
            old = self.target
            self.target = [[old[i][j] if i < len(old) and j < len(old) else EMPTY
                            for j in range(new)] for i in range(new)]
            self.n = new
            self.solution = []; self.step = 0
            self.grid_canvas.draw(self.target)
            self.replay_canvas.draw(self.target)
            self._reset_result()
        elif attr == "k":
            self.k = self.st_k.get()
            if self.brush > self.k:
                self.brush = self.k
            # если цветов стало меньше, лишние цвета с поля стираются
            self.target = [[v if v <= self.k else EMPTY for v in row] for row in self.target]
            self._build_palette()
            self._refresh_mode_panel()
            self.grid_canvas.draw(self.target)

    # Выбор цвета, которым рисуют по полю.
    def _build_palette(self):
        # Полная пересборка строки с кистями, нужна при смене числа цветов.
        # Подпись «Кисть:» тоже удаляется: иначе при каждом вызове она
        # добавляется заново и строка разъезжается.
        for w in self.palette.winfo_children():
            w.destroy()
        self.chip_widgets = []
        ctk.CTkLabel(self.palette, text="Кисть:", font=FS, text_color=T.MUTED)\
            .pack(side="left", padx=(0, 8))
        for v in range(0, self.k + 1):
            f = tk.Canvas(self.palette, width=30, height=30, bg=T.CARD,
                          highlightthickness=0, cursor="hand2")
            f.bind("<Button-1>", lambda e, val=v: self._set_brush(val))
            f.pack(side="left", padx=3)
            self.chip_widgets.append((f, v))
        self._draw_chips()

    def _draw_chips(self):
        # Перерисовка только рамки у выбранного цвета. Сами квадратики не
        # пересоздаются, иначе строка снова начнёт разъезжаться.
        for f, v in self.chip_widgets:
            f.delete("all")
            selected = (v == self.brush)
            ring = T.TEXT if selected else T.STROKE
            width = 2 if selected else 1
            if v == EMPTY:
                GridCanvas._round(f, 3, 3, 27, 27, 8, fill=T.CELLS[0], outline=ring, width=width)
                f.create_line(9, 21, 21, 9, fill=T.MUTED, width=2)
            else:
                GridCanvas._round(f, 3, 3, 27, 27, 8, fill=T.CELLS[v], outline=ring, width=width)

    def _set_brush(self, v):
        self.brush = v
        self._draw_chips()   # только обновить рамки, без пересборки строки

    def _paint(self, i, j):
        self.target[i][j] = self.brush
        self.grid_canvas.draw(self.target)

    def _clear(self):
        self.target = [[EMPTY] * self.n for _ in range(self.n)]
        self.solution = []; self.step = 0
        self.grid_canvas.draw(self.target)
        self.replay_canvas.draw(self.target)
        self._reset_result()

    # Переключение между четырьмя режимами.
    def _select_mode(self, key):
        self.mode = key
        for k, b in self.nav_buttons.items():
            if k == key:
                b.configure(fg_color=T.INPUT, text_color=T.TEXT)
            else:
                b.configure(fg_color="transparent", text_color=T.TEXT_DIM)
        self._draw_banner()
        self._refresh_mode_panel()
        self._reset_result()

    def _draw_banner(self, e=None):
        c = self._banner
        c.delete("all")
        w = c.winfo_width() or 900
        h = 104
        c._im = ImageTk.PhotoImage(T.gradient(max(2, w), h, "#3b1d6e", "#7c2d6b", radius=22))
        c.create_image(0, 0, anchor="nw", image=c._im)
        # подсветка активного режима
        c._im2 = ImageTk.PhotoImage(T.gradient(max(2, w // 2), h, T.ACCENT, "#3b1d6e", radius=22))
        title = next(t for k, t, s in MODES if k == self.mode)
        sub = next(s for k, t, s in MODES if k == self.mode)
        c.create_text(28, 40, anchor="w", text=f"Режим {self.mode} · {title}",
                      fill="white", font=(T.FONT, 22, "bold"))
        c.create_text(28, 72, anchor="w", text=sub, fill="#e6d9f5", font=(T.FONT, 13))

    # У каждого режима свои поля ввода, собираю их тут.
    def _refresh_mode_panel(self):
        for w in self.mode_panel.winfo_children():
            w.destroy()
        self.count_steppers = []
        if self.mode in ("1", "3"):
            self.param_header.winfo_children()[0].configure(
                text="Количество доминошек по цветам")
            grid = ctk.CTkFrame(self.mode_panel, fg_color="transparent")
            grid.pack(fill="x")
            for c in range(1, self.k + 1):
                rowf = ctk.CTkFrame(grid, fg_color="transparent")
                rowf.grid(row=(c - 1) // 3, column=(c - 1) % 3, padx=8, pady=6, sticky="w")
                chip = tk.Canvas(rowf, width=20, height=20, bg=T.CARD, highlightthickness=0)
                GridCanvas._round(chip, 2, 2, 18, 18, 6, fill=T.CELLS[c], outline="")
                chip.pack(side="left", padx=(0, 8))
                ctk.CTkLabel(rowf, text=f"цвет {c}", font=FS, text_color=T.TEXT_DIM)\
                    .pack(side="left", padx=(0, 8))
                st = Stepper(rowf, value=2, lo=0, hi=10, width=36)
                st.pack(side="left")
                self.count_steppers.append(st)
        else:
            self.param_header.winfo_children()[0].configure(text="Последовательность цветов")
            hint = "порядок выкладывания, например:  1 2 2 3" if self.mode == "2" \
                else "порядок выкладывания для подсчёта, например:  1 2 2"
            ctk.CTkLabel(self.mode_panel, text=hint, font=FS, text_color=T.MUTED)\
                .pack(anchor="w", pady=(0, 6))
            self.seq_entry = ctk.CTkEntry(self.mode_panel, height=42, corner_radius=12,
                                          fg_color=T.INPUT, border_color=T.STROKE,
                                          text_color=T.TEXT, font=FN,
                                          placeholder_text="1 2 2")
            self.seq_entry.pack(fill="x")
        # в режимах подсчёта добавляется ограничение: после него программа
        # перестаёт считать точно и переходит на прикидку
        if self.mode in ("3", "4"):
            lim = ctk.CTkFrame(self.mode_panel, fg_color="transparent"); lim.pack(fill="x", pady=(10, 0))
            ctk.CTkLabel(lim, text="лимит состояний:", font=FS, text_color=T.MUTED).pack(side="left")
            self.cap_entry = ctk.CTkEntry(lim, width=120, height=32, corner_radius=8,
                                          fg_color=T.INPUT, border_color=T.STROKE,
                                          text_color=T.TEXT, font=FS)
            self.cap_entry.insert(0, "200000")
            self.cap_entry.pack(side="left", padx=8)
        self.solve_btn.set_text("ПОСЧИТАТЬ" if self.mode in ("3", "4") else "РЕШИТЬ")

    # Запуск решателя и вывод ответа.
    def _reset_result(self, msg="Задайте параметры и нажмите кнопку."):
        self._stop_play()
        self.solution = []; self.step = 0
        self.step_lbl.configure(text="ход 0 / 0")
        self.move_lbl.configure(text="")
        self.replay_canvas.draw(self.target)
        self._show(msg, T.MUTED)

    def _show(self, text, color=T.TEXT_DIM):
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("1.0", text)
        self.result.configure(state="disabled", text_color=color)

    def _run(self):
        self._stop_play()
        try:
            if self.mode == "1":
                counts = {c + 1: self.count_steppers[c].get() for c in range(self.k)}
                ok, moves, reason = solve_mode1(self.n, counts, self.target)
                self._show_solution(ok, moves, reason)
            elif self.mode == "2":
                seq = self._parse_seq()
                if seq is None:
                    return
                ok, moves, reason = solve_mode2(self.n, seq, self.target)
                self._show_solution(ok, moves, reason)
            elif self.mode == "3":
                counts = {c + 1: self.count_steppers[c].get() for c in range(self.k)}
                cap = int(self.cap_entry.get() or "200000")
                res = count_mode3(self.n, counts, cap)
                self._show_count(res)
            else:
                seq = self._parse_seq()
                if seq is None:
                    return
                cap = int(self.cap_entry.get() or "200000")
                res = count_mode4(self.n, seq, cap)
                self._show_count(res)
        except Exception as ex:
            self._show(f"Ошибка: {ex}", T.BAD)

    def _parse_seq(self):
        raw = self.seq_entry.get().replace(",", " ").split()
        try:
            seq = [int(x) for x in raw]
        except ValueError:
            self._show("Последовательность должна состоять из чисел 1..k.", T.BAD)
            return None
        if any(c < 1 or c > self.k for c in seq):
            self._show(f"Цвета должны быть в диапазоне 1..{self.k}.", T.BAD)
            return None
        return seq

    def _show_solution(self, ok, moves, reason):
        if ok is None:
            # Бюджет перебора исчерпан — это не «невозможно», а «не определено».
            self._reset_result()
            self._show("НЕ ОПРЕДЕЛЕНО (не хватило бюджета перебора).\n\n"
                       "Это не значит «невозможно» — перебор просто не успел.\n\n"
                       "Пояснение: " + reason, T.WARN)
            return
        if not ok:
            self._reset_result()
            self._show("НЕВОЗМОЖНО (доказано).\n\nПричина: " + reason, T.BAD)
            return
        self.solution = moves
        self.step = 0
        lines = [f"РЕШЕНИЕ НАЙДЕНО.  Ходов: {len(moves)}", ""]
        for idx, m in enumerate(moves, 1):
            lines.append(describe_move(m, idx))
        if not moves:
            lines.append("(поле пустое — ходы не нужны)")
        lines += ["", "Смотрите проигрывание ниже (‹ / › / Проиграть)."]
        self._show("\n".join(lines), T.TEXT_DIM)
        self._replay(len(moves))

    def _show_count(self, res):
        self._reset_result("")
        if res.exact:
            self._show(f"Разных картинок: {res.value}\n\n"
                       f"({res.method})", T.OK)
        else:
            txt = (f"Примерно {res.value} разных картинок.\n\n"
                   f"Точно посчитать не получилось: картинок слишком много,\n"
                   f"они не помещаются в память. Поэтому программа разложила\n"
                   f"доминошки наугад много раз и прикинула ответ.\n\n"
                   f"Точно встретилось {res.observed} разных картинок — меньше\n"
                   f"этого числа быть не может.\n\n"
                   f"Чтобы посчитать точно, уменьшите поле или число\n"
                   f"доминошек, либо поднимите ограничение.")
            self._show(txt, T.TEXT)

    # Показ решения по шагам.
    def _replay(self, step):
        if not self.solution:
            return
        step = max(0, min(len(self.solution), step))
        self.step = step
        grid = simulate(self.n, self.solution[:step])
        grid = [list(r) for r in grid]
        hl = self.solution[step - 1] if step > 0 else None
        self.replay_canvas.draw(grid, highlight=hl)
        self.step_lbl.configure(text=f"ход {step} / {len(self.solution)}")
        if step > 0:
            self.move_lbl.configure(text="последний ход:\n" + describe_move(self.solution[step - 1]))
        else:
            self.move_lbl.configure(text="пустое поле (до первого хода)")

    def _step_manual(self, d):
        # ручное переключение шага останавливает автопоказ
        self._stop_play()
        self._replay(self.step + d)

    def _play_all(self):
        # одна кнопка на два действия: идёт показ — остановить, иначе запустить
        if self._playing:
            self._stop_play()
            return
        if not self.solution:
            return
        self._playing = True
        self.play_btn.set_text("■  Стоп")
        self._replay(0)

        def tick(s=1):
            if not self._playing or s > len(self.solution):
                self._stop_play()
                return
            self._replay(s)
            self._play_after = self.after(600, lambda: tick(s + 1))

        self._play_after = self.after(300, tick)

    def _stop_play(self):
        self._playing = False
        if getattr(self, "_play_after", None) is not None:
            try:
                self.after_cancel(self._play_after)
            except Exception:
                pass
            self._play_after = None
        if hasattr(self, "play_btn"):
            self.play_btn.set_text("▶  Проиграть")


if __name__ == "__main__":
    App().mainloop()
