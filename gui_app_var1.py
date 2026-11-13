import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import time
import random
import asyncio
import database as db
from quiz import SOUNDS_LIST

class ReactionGuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Тест скорости реакции (Диплом)")
        self.root.geometry("450x550")
        self.root.configure(bg="#f0f2f5")

        # Имитируем Telegram ID для локальной базы данных
        self.user_id = 777777777
        self.username = "local_gui_user"
        self.first_name = "Испытуемый"

        # Переменные для логики теста
        self.current_sound_idx = 0
        self.target_sequence = []
        self.current_step = 0
        self.errors_count = 0
        self.start_time = 0

        # Инициализируем базу данных асинхронно
        asyncio.run(db.init_db())
        asyncio.run(db.add_user(self.user_id, self.username, self.first_name))

        # Запускаем первый экран (Опрос про авиацию)
        self.create_aviation_screen()

    def clear_screen(self):
        """Очищает окно перед сменой экрана."""
        for widget in self.root.winfo_children():
            widget.destroy()

    # --- ЭКРАН 1: ОПРОС ПРО АВИАЦИЮ ---
    def create_aviation_screen(self):
        self.clear_screen()

        label = tk.Label(
            self.root,
            text="Имеете ли вы какую-либо связь\nс авиацией или авиасимуляторами?",
            font=("Arial", 14, "bold"), bg="#f0f2f5", fg="#333333", pady=20
        )
        label.pack()

        options = [
            ("Да, я пилот / диспетчер", "Профессионал"),
            ("Да, активно летаю в авиасимуляторах", "Симмер"),
            ("Нет, никак не связан(а) с авиацией", "Нет связи")
        ]

        style = ttk.Style()
        style.configure("TButton", font=("Arial", 11), padding=10)

        for text, status in options:
            btn = ttk.Button(
                self.root, text=text,
                command=lambda s=status: self.save_aviation_status(s)
            )
            btn.pack(fill="x", padx=40, pady=10)

    def save_aviation_status(self, status):
        asyncio.run(db.update_user_aviation(self.user_id, status))
        self.create_calibration_screen()

    # --- ЭКРАН 2: КАЛИБРОВКА ЗВУКА ---
    def create_calibration_screen(self):
        self.clear_screen()

        label = tk.Label(
            self.root,
            text="Настройка аудио",
            font=("Arial", 16, "bold"), bg="#f0f2f5", fg="#333333", pady=20
        )
        label.pack()

        info = tk.Label(
            self.root,
            text="Пожалуйста, надевайте наушники.\nВ Telegram-боте здесь прозвучит технический звук\nдля настройки комфортной громкости.",
            font=("Arial", 11), bg="#f0f2f5", fg="#666666", justify="center"
        )
        info.pack(pady=20)

        start_btn = tk.Button(
            self.root, text="Громкость настроена.\nНачать тест ⏱",
            font=("Arial", 12, "bold"), bg="#31b545", fg="white",
            padx=20, pady=15, bd=0, cursor="hand2",
            command=self.start_main_test
        )
        start_btn.pack(pady=40)

    # --- ЭКРАН 3: ОСНОВНОЙ ТЕСТ (КНОПКИ 2х2) ---
    def start_main_test(self):
        self.current_sound_idx = 0
        self.next_sound_sequence()

    def next_sound_sequence(self):
        if self.current_sound_idx >= len(SOUNDS_LIST):
            self.show_finish_screen()
            return

        self.clear_screen()

        sound_name = SOUNDS_LIST[self.current_sound_idx]

        # Генерируем случайную комбинацию кнопок (3 шага)
        all_buttons = ['А', 'Б', 'В', 'Г']
        self.target_sequence = [random.choice(all_buttons) for _ in range(3)]
        self.current_step = 0
        self.errors_count = 0

        # Шапка экрана
        top_label = tk.Label(
            self.root, text=f"Стимул №{self.current_sound_idx + 1} из {len(SOUNDS_LIST)}",
            font=("Arial", 12), bg="#f0f2f5", fg="#666666"
        )
        top_label.pack(pady=5)

        sound_label = tk.Label(
            self.root, text=f"🔈 [Звучит файл: {sound_name}]",
            font=("Arial", 11, "italic"), bg="#f0f2f5", fg="#007bff"
        )
        sound_label.pack(pady=5)

        task_title = tk.Label(
            self.root, text="Как можно быстрее нажмите кнопки в порядке:",
            font=("Arial", 11), bg="#f0f2f5", fg="#333333"
        )
        task_title.pack(pady=10)

        # Отображение комбинации (например: Б -> А -> Г)
        seq_text = " ➡️ ".join(self.target_sequence)
        self.seq_label = tk.Label(
            self.root, text=seq_text,
            font=("Arial", 18, "bold"), bg="#e2e6ea", fg="#dc3545",
            padx=15, pady=10, relief="solid", bd=1
        )
        self.seq_label.pack(pady=10)

        # Подсказка текущего шага
        self.status_label = tk.Label(
            self.root, text=f"Ожидание нажатия: Кнопка {self.target_sequence[0]}",
            font=("Arial", 11, "bold"), bg="#f0f2f5", fg="#28a745"
        )
        self.status_label.pack(pady=10)

        # Контейнер для сетки кнопок 2х2
        grid_frame = tk.Frame(self.root, bg="#f0f2f5")
        grid_frame.pack(pady=20)

        # Стили кнопок пульта 2х2
        btn_opts = {"font": ("Arial", 12, "bold"), "width": 12, "height": 3, "bd": 2, "relief": "raised", "cursor": "hand2"}

        btn_A = tk.Button(grid_frame, text="Кнопка А", bg="#ffffff", fg="#333333", command=lambda: self.handle_click('А'), **btn_opts)
        btn_Б = tk.Button(grid_frame, text="Кнопка Б", bg="#ffffff", fg="#333333", command=lambda: self.handle_click('Б'), **btn_opts)
        btn_В = tk.Button(grid_frame, text="Кнопка В", bg="#ffffff", fg="#333333", command=lambda: self.handle_click('В'), **btn_opts)
        btn_Г = tk.Button(grid_frame, text="Кнопка Г", bg="#ffffff", fg="#333333", command=lambda: self.handle_click('Г'), **btn_opts)

        btn_A.grid(row=0, column=0, padx=10, pady=10)
        btn_Б.grid(row=0, column=1, padx=10, pady=10)
        btn_В.grid(row=1, column=0, padx=10, pady=10)
        btn_Г.grid(row=1, column=1, padx=10, pady=10)

        # Засекаем точное время вывода кнопок на экран
        self.start_time = time.time()

    def handle_click(self, letter):
        expected_letter = self.target_sequence[self.current_step]

        if letter == expected_letter:
            self.current_step += 1
            if self.current_step < len(self.target_sequence):
                # Обновляем текст подсказки следующего шага
                next_letter = self.target_sequence[self.current_step]
                self.status_label.config(text=f"Правильно! Ожидание: Кнопка {next_letter}", fg="#28a745")
            else:
                # Финал комбинации для текущего звука
                end_time = time.time()
                total_time = round(end_time - self.start_time, 2)

                sound_name = SOUNDS_LIST[self.current_sound_idx]

                # Записываем результаты в нашу SQLite базу данных!
                asyncio.run(db.save_reaction_results(self.user_id, sound_name, total_time, self.errors_count))

                # Слегка уведомляем об успехе и идем к следующему звуку
                messagebox.showinfo(
                    "Успех!",
                    f"Стимул выполнен!\nВремя: {total_time} сек.\nОшибок: {self.errors_count}"
                )

                self.current_sound_idx += 1
                self.next_sound_sequence()
        else:
            # Если игрок промахнулся или нажал не то
            self.errors_count += 1
            self.status_label.config(text=f"❌ ОШИБКА! Ждем Кнопку {expected_letter}", fg="#dc3545")

    # --- ЭКРАН 4: ЗАВЕРШЕНИЕ ---
    def show_finish_screen(self):
        self.clear_screen()
        label = tk.Label(
            self.root, text="🏆 Тест завершен!",
            font=("Arial", 18, "bold"), bg="#f0f2f5", fg="#28a745", pady=30
        )
        label.pack()

        info = tk.Label(
            self.root, text="Все замеры скорости и промахов\nуспешно занесены в базу данных\nreaction_results.db!",
            font=("Arial", 12), bg="#f0f2f5", fg="#333333"
        )
        info.pack(pady=20)

        exit_btn = ttk.Button(self.root, text="Выход", command=self.root.quit)
        exit_btn.pack(pady=30)

if __name__ == "__main__":
    window = tk.Tk()
    app = ReactionGuiApp(window)
    window.mainloop()
