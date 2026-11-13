import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import time
import random
import asyncio
import os
import database as db
from quiz import SOUNDS_LIST
import winsound
class ReactionGuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Тест скорости реакции и когнитивной нагрузки (Этап 2)")
        self.root.geometry("500x600")
        self.root.configure(bg="#f0f2f5")

        self.user_id = 777777777
        self.username = "local_gui_user"
        self.first_name = "Испытуемый"

        # Формируем общий пул испытаний: звук + тип условия
        # Создаем список словарей: {"sound": имя_файла, "type": "sound"/"silence"/"noise"}
        self.trials = []
        for s in SOUNDS_LIST:
            self.trials.append({"sound": s, "type": "sound"})
        # Добавляем 2 пробы тишины и 2 пробы фонового шума
        self.trials.append({"sound": "Контроль: Тишина 1", "type": "silence"})
        self.trials.append({"sound": "Контроль: Тишина 2", "type": "silence"})
        self.trials.append({"sound": "Контроль: Шум 1", "type": "noise"})
        self.trials.append({"sound": "Контроль: Шум 2", "type": "noise"})

        # Рандомизируем порядок предъявления всех проб для чистоты эксперимента
        random.shuffle(self.trials)

        self.current_trial_idx = 0
        self.current_target_seq = []   # Целевая последовательность (напр. [3, 1, 4, 2])
        self.current_step_idx = 0      # Индекс текущего шага респондента
        self.errors_count = 0
        self.start_time = 0
        self.buttons = []

        # Инициализация БД
        asyncio.run(db.init_db())
        asyncio.run(db.add_user(self.user_id, self.username, self.first_name))

        # Запускаем приветственный экран
        self.create_welcome_screen()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

# --- ЭКРАН 1: ПРИВЕТСТВИЕ И АНКЕТА ---
    def create_welcome_screen(self):
        self.clear_screen()

        tk.Label(
            self.root, text="Добро пожаловать во 2-й этап исследования!",
            font=("Arial", 14, "bold"), bg="#f0f2f5", fg="#333333", pady=15
        ).pack()

        # НОВЫЙ ВОПРОС ПРО СЛУХ
        tk.Label(
            self.root, text="Есть ли у вас сильная заложенность ушей в данный момент\nили диагностированные нарушения слуха?",
            font=("Arial", 11), bg="#f0f2f5", fg="#444444", pady=10
        ).pack()

        hearing_options = [
            ("Нет, слух в норме", "Слух в норме"),
            ("Есть легкие нарушения / небольшая заложенность", "Легкие нарушения"),
            ("Да, есть серьезные нарушения слуха", "Серьезные нарушения")
        ]

        style = ttk.Style()
        style.configure("TButton", font=("Arial", 10), padding=6)

        for text, status in hearing_options:
            btn = ttk.Button(
                self.root, text=text,
                command=lambda s=status: self.save_hearing_and_proceed(s)
            )
            btn.pack(fill="x", padx=40, pady=5)

    def save_hearing_and_proceed(self, hearing_status):
        # Сохраняем статус слуха (можем временно сохранить в память класса или сразу в БД, если добавим колонку)
        self.user_hearing_status = hearing_status

        # Переходим ко второму вопросу (про авиацию)
        self.create_aviation_question_screen()

    def create_aviation_question_screen(self):
        self.clear_screen()

        tk.Label(
            self.root, text="Имеете ли вы какую-либо связь\nс авиацией или авиасимуляторами?",
            font=("Arial", 12), bg="#f0f2f5", fg="#444444", pady=15
        ).pack()

        options = [
            ("Да, я пилот / диспетчер", "Профессионал"),
            ("Да, активно летаю в авиасимуляторах", "Симмер"),
            ("Нет, никак не связан(а) с авиацией", "Нет связи")
        ]

        for text, status in options:
            btn = ttk.Button(
                self.root, text=text,
                command=lambda s=status: self.save_aviation_and_continue(s)
            )
            btn.pack(fill="x", padx=50, pady=8)

    # --- ЭКРАН 2: ИНСТРУКЦИЯ ---
    def create_instruction_screen(self):
        self.clear_screen()

        tk.Label(
            self.root, text="Инструкция к когнитивной задаче",
            font=("Arial", 16, "bold"), bg="#f0f2f5", fg="#333333", pady=20
        ).pack()

        info_text = (
            "На экран будет выводиться заданная последовательность цифр (например: 3 → 1 → 4 → 2).\n\n"
            "Вам нужно нажать на кнопки с цифрами именно в этом порядке как можно быстрее.\n"
            "Расположение кнопок на экране каждый раз меняется случайным образом.\n\n"
            "Перед каждой задачей будет звучать аудиосигнал или контрольный фон.\n"
            "После каждого теста будет короткая пауза для отдыха."
        )

        tk.Label(
            self.root, text=info_text,
            font=("Arial", 11), bg="#f0f2f5", fg="#333333", justify="center", wraplength=420, pady=10
        ).pack(pady=10)

        start_btn = tk.Button(
            self.root, text="Начать тестирование",
            font=("Arial", 13, "bold"), bg="#007bff", fg="white",
            padx=30, pady=10, bd=0, cursor="hand2",
            command=self.run_next_trial
        )
        start_btn.pack(pady=20)

    # --- ЭКРАН 3: ОСНОВНАЯ ЗАДАЧА ---
    def run_next_trial(self):
        if self.current_trial_idx >= len(self.trials):
            self.show_finish_screen()
            return

        self.clear_screen()
        self.buttons = []
        self.errors_count = 0
        self.current_step_idx = 0

        trial = self.trials[self.current_trial_idx]
        condition_type = trial["type"]
        sound_name = trial["sound"]

        # Генерируем случайный целевой порядок нажатия цифр [1, 2, 3, 4]
        self.current_target_seq = [1, 2, 3, 4]
        random.shuffle(self.current_target_seq)

        # Шапка прогресса
        tk.Label(
            self.root, text=f"Испытание №{self.current_trial_idx + 1} из {len(self.trials)}",
            font=("Arial", 10), bg="#f0f2f5", fg="#666666"
        ).pack(pady=5)

# Воспроизведение аудио или фонового условия
        if condition_type == "sound":
            audio_status = f"🔈 [Звуковой стимул: {sound_name}]"
            color = "#007bff"
            try:
                sound_path = os.path.join("sounds", sound_name)
                # SND_ASYNC запускает звук асинхронно, чтобы не морозить интерфейс
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print(f"Не удалось воспроизвести файл {sound_name}: {e}")

        elif condition_type == "silence":
            audio_status = "🔇 [Контрольное условие: Тишина]"
            color = "#6c757d"
            # На всякий случай останавливаем предыдущий звук, если проигрался
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except:
                pass

        else:
            audio_status = "🔊 [Контрольное условие: Фоновый шум]"
            color = "#fd7e14"
            # Если появится файл с шумом, можно будет добавить путь сюда

        tk.Label(
            self.root, text=audio_status,
            font=("Arial", 11, "italic"), bg="#f0f2f5", fg=color
        ).pack(pady=5)

        # КЛЮЧ / ПОДСКАЗКА: В каком порядке нужно нажать кнопки
        seq_str = " → ".join(map(str, self.current_target_seq))
        seq_frame = tk.Frame(self.root, bg="#e2e8f0", padx=15, pady=8, relief="solid", bd=1)
        seq_frame.pack(pady=10)

        tk.Label(
            seq_frame, text="Требуемый порядок:",
            font=("Arial", 10), bg="#e2e8f0", fg="#555555"
        ).pack()

        tk.Label(
            seq_frame, text=seq_str,
            font=("Arial", 18, "bold"), bg="#e2e8f0", fg="#1d4ed8"
        ).pack()

        # Контейнер для кнопок 2x2
        grid_frame = tk.Frame(self.root, bg="#f0f2f5")
        grid_frame.pack(pady=20)

        # Расположение кнопок на экране (тоже рандомизируем физические цифры на кнопках)
        button_labels = [1, 2, 3, 4]
        random.shuffle(button_labels)

        btn_opts = {"font": ("Arial", 18, "bold"), "width": 6, "height": 2, "bd": 2, "relief": "raised", "cursor": "hand2", "bg": "#ffffff", "fg": "#333333"}

        idx = 0
        for row in range(2):
            for col in range(2):
                btn_num = button_labels[idx]
                btn = tk.Button(
                    grid_frame, text=str(btn_num),
                    command=lambda n=btn_num: self.handle_click(n),
                    **btn_opts
                )
                btn.grid(row=row, column=col, padx=12, pady=12)
                self.buttons.append(btn)
                idx += 1

        # Засекаем точное время старта задачи
        self.start_time = time.time()

    def handle_click(self, clicked_num):
        expected_num = self.current_target_seq[self.current_step_idx]

        if clicked_num == expected_num:
            # Правильный шаг
            self.current_step_idx += 1

            # Если прошли все 4 шага до конца
            if self.current_step_idx >= len(self.current_target_seq):
                end_time = time.time()
                total_time = round(end_time - self.start_time, 3)

                trial = self.trials[self.current_trial_idx]
                seq_str_saved = ",".join(map(str, self.current_target_seq))

                # Сохраняем в БД
                asyncio.run(db.save_reaction_results(
                    self.user_id,
                    trial["sound"],
                    trial["type"],
                    seq_str_saved,
                    total_time,
                    self.errors_count
                ))

                # Переходим к экрану передышки
                self.show_rest_screen()
        else:
            # Ошибка (нажали не ту цифру по порядку)
            self.errors_count += 1

# --- ЭКРАН 4: ПЕРЕДЫШКА МЕЖДУ ЗАДАЧАМИ ---
    def show_rest_screen(self):
        # Принудительно останавливаем воспроизведение звука при переходе на отдых
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

        self.clear_screen()

        tk.Label(
            self.root, text="⏸ Пауза для отдыха",
            font=("Arial", 16, "bold"), bg="#f0f2f5", fg="#2b6cb0", pady=30
        ).pack()

        tk.Label(
            self.root, text="Вы успешно завершили текущую пробу.\nНемного отдохните и нажмите кнопку ниже, когда будете готовы продолжить.",
            font=("Arial", 11), bg="#f0f2f5", fg="#4a5568", justify="center", pady=15
        ).pack()

        continue_btn = tk.Button(
            self.root, text="Продолжить тестирование",
            font=("Arial", 13, "bold"), bg="#28a745", fg="white",
            padx=25, pady=10, bd=0, cursor="hand2",
            command=self.next_trial_increment
        )
        continue_btn.pack(pady=30)

    def next_trial_increment(self):
        self.current_trial_idx += 1
        self.run_next_trial()

    # --- ЭКРАН 5: ЗАВЕРШЕНИЕ ---
    def show_finish_screen(self):
        self.clear_screen()

        tk.Label(
            self.root, text="🏆 Второй этап завершен!",
            font=("Arial", 18, "bold"), bg="#f0f2f5", fg="#28a745", pady=30
        ).pack()

        tk.Label(
            self.root, text="Все данные времени реакции, ошибок и контрольных условий\nуспешно сохранены в базу данных reaction_results.db!",
            font=("Arial", 11), bg="#f0f2f5", fg="#333333", justify="center"
        ).pack(pady=20)

        exit_btn = ttk.Button(self.root, text="Закрыть приложение", command=self.root.quit)
        exit_btn.pack(pady=30)

if __name__ == "__main__":
    window = tk.Tk()
    app = ReactionGuiApp(window)
    window.mainloop()
