import asyncio
import os
import random
import time
import tkinter as tk
from tkinter import ttk
import database as db
from quiz import SOUNDS_LIST, TEST_SOUND_FILE

# Подключаем pygame для воспроизведения .mp3
try:
    import pygame
    pygame.mixer.init()
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    print("Внимание: библиотека pygame не установлена. Выполните: pip install pygame")


class ReactionGuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Тест скорости реакции и когнитивной нагрузки (Этап 2)")
        self.root.geometry("520x640")
        self.root.configure(bg="#f0f2f5")

        self.user_id = 777777777
        self.username = "local_gui_user"
        self.first_name = "Испытуемый"
        self.user_hearing_status = None
        self.user_aviation_status = None

        self.sounds_dir = "sounds_" if os.path.exists("sounds_") else "sounds"

        # Формируем общий пул испытаний (19 боевых звуков + 2 тишины + 2 шума = 23 пробы)
        self.trials = []
        for s in SOUNDS_LIST:
            self.trials.append({"sound": s, "type": "sound"})

        random.shuffle(self.trials)

        self.is_practice = True
        self.practice_count = 0
        self.current_trial_idx = 0
        self.current_target_seq = []
        self.current_step_idx = 0
        self.errors_count = 0
        self.start_time = 0
        self.buttons = {}

        asyncio.run(db.init_db())
        asyncio.run(db.add_user(self.user_id, self.username, self.first_name))

        self.create_welcome_screen()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def play_mp3(self, filename):
        if not HAS_PYGAME:
            print(f"[Имитация звука]: {filename}")
            return
        sound_path = os.path.join(self.sounds_dir, filename)
        try:
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Ошибка воспроизведения {sound_path}: {e}")

    def stop_audio(self):
        if HAS_PYGAME:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    # --- ЭКРАН 1: ПРИВЕТСТВИЕ И АНКЕТА ---
    def create_welcome_screen(self):
        self.clear_screen()

        tk.Label(
            self.root, text="Добро пожаловать во 2-й этап исследования!",
            font=("Arial", 14, "bold"), bg="#f0f2f5", fg="#333333", pady=15
        ).pack()

        tk.Label(
            self.root,
            text="Есть ли у вас сильная заложенность ушей в данный момент\nили диагностированные нарушения слуха?",
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
        self.user_hearing_status = hearing_status
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

    def save_aviation_and_continue(self, aviation_status):
        self.user_aviation_status = aviation_status
        asyncio.run(db.update_user_profile(
            self.user_id,
            self.user_hearing_status,
            self.user_aviation_status
        ))
        self.create_instruction_screen()

    # --- ЭКРАН 2: ИНСТРУКЦИЯ ---
    def create_instruction_screen(self):
        self.clear_screen()

        tk.Label(
            self.root, text="Инструкция к когнитивной задаче",
            font=("Arial", 16, "bold"), bg="#f0f2f5", fg="#333333", pady=15
        ).pack()

        info_text = (
            "На экран будет выводиться заданная последовательность цифр (например: 3 → 1 → 4 → 2).\n\n"
            "Вам нужно нажать на кнопки с цифрами именно в этом порядке как можно быстрее. "
            "Расположение кнопок каждый раз меняется случайным образом.\n\n"
            "Перед началом основной части вы пройдете 3 коротких тренировочных задания без звука, "
            "чтобы привыкнуть к управлению. После этого вы сможете настроить громкость и перейти к тесту."
        )

        tk.Label(
            self.root, text=info_text,
            font=("Arial", 11), bg="#f0f2f5", fg="#333333",
            justify="center", wraplength=440, pady=10
        ).pack(pady=10)

        start_btn = tk.Button(
            self.root, text="Начать тренировку (0/3)",
            font=("Arial", 12, "bold"), bg="#007bff", fg="white",
            padx=25, pady=10, bd=0, cursor="hand2",
            command=self.start_practice_trial
        )
        start_btn.pack(pady=20)

    def start_practice_trial(self):
        self.is_practice = True
        self.practice_count += 1
        self.run_next_trial()

    # --- ЭКРАН 3: ОСНОВНАЯ И ТРЕНИРОВОЧНАЯ ЗАДАЧА ---
    def run_next_trial(self):
        if not self.is_practice and self.current_trial_idx >= len(self.trials):
            self.show_finish_screen()
            return

        self.clear_screen()
        self.buttons = {}
        self.errors_count = 0
        self.current_step_idx = 0

        self.current_target_seq = [1, 2, 3, 4]
        random.shuffle(self.current_target_seq)

        if self.is_practice:
            header_text = f"🛠 Тренировочное задание №{self.practice_count}"
            audio_status = "🔇 [Тренировка: без звука — освойте нажатие кнопок]"
            color = "#6c757d"
        else:
            header_text = f"Испытание №{self.current_trial_idx + 1} из {len(self.trials)}"
            trial = self.trials[self.current_trial_idx]
            sound_name = trial["sound"]

            audio_status = f"🔈 [Звуковой стимул: {sound_name}]"
            color = "#007bff"
            self.play_mp3(sound_name)

        tk.Label(
            self.root, text=header_text,
            font=("Arial", 11, "bold"), bg="#f0f2f5", fg="#444444"
        ).pack(pady=(12, 4))

        tk.Label(
            self.root, text=audio_status,
            font=("Arial", 10, "italic"), bg="#f0f2f5", fg=color
        ).pack(pady=4)

        seq_str = " → ".join(map(str, self.current_target_seq))
        seq_frame = tk.Frame(self.root, bg="#e2e8f0", padx=20, pady=10, relief="solid", bd=1)
        seq_frame.pack(pady=12)

        tk.Label(
            seq_frame, text="Требуемый порядок:",
            font=("Arial", 10), bg="#e2e8f0", fg="#555555"
        ).pack()

        tk.Label(
            seq_frame, text=seq_str,
            font=("Arial", 18, "bold"), bg="#e2e8f0", fg="#1d4ed8"
        ).pack()

        grid_frame = tk.Frame(self.root, bg="#f0f2f5")
        grid_frame.pack(pady=20)

        button_labels = [1, 2, 3, 4]
        random.shuffle(button_labels)

        btn_opts = {
            "font": ("Arial", 18, "bold"),
            "width": 6,
            "height": 2,
            "bd": 2,
            "relief": "raised",
            "cursor": "hand2",
            "bg": "#ffffff",
            "fg": "#333333"
        }

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
                self.buttons[btn_num] = btn
                idx += 1

        self.start_time = time.perf_counter()


    def handle_click(self, clicked_num):
        expected_num = self.current_target_seq[self.current_step_idx]
        btn = self.buttons[clicked_num]

        if clicked_num == expected_num:
            btn.configure(bg="#d4edda", fg="#155724", state="disabled")
            self.current_step_idx += 1

            if self.current_step_idx >= len(self.current_target_seq):
                total_time = round(time.perf_counter() - self.start_time, 3)

                if self.is_practice:
                    self.show_practice_choice_screen(total_time, self.errors_count)
                else:
                    trial = self.trials[self.current_trial_idx]
                    seq_str_saved = ",".join(map(str, self.current_target_seq))
                    asyncio.run(db.save_reaction_results(
                        self.user_id,
                        trial["sound"],
                        trial["type"],
                        seq_str_saved,
                        total_time,
                        self.errors_count
                    ))
                    self.show_rest_screen()
        else:
            self.errors_count += 1
            btn.configure(bg="#f8d7da")
            self.root.after(
                150,
                lambda b=btn: b.configure(bg="#ffffff") if b.winfo_exists() and b["state"] != "disabled" else None
            )

    # --- ЭКРАН 3.5: ВЫБОР ПОСЛЕ ТРЕНИРОВКИ ---
    def show_practice_choice_screen(self, total_time, errors):
        self.clear_screen()
        min_practice = 3
        tk.Label(
            self.root, text=f"✅ Тренировка №{self.practice_count} выполнена!",
            font=("Arial", 15, "bold"), bg="#f0f2f5", fg="#28a745", pady=20
        ).pack()

        if self.practice_count < min_practice:
            remaining = min_practice - self.practice_count
            desc_text = (
                f"Чтобы привыкнуть к расположению кнопок и не терять время в основном тесте, "
                f"выполните еще {remaining} трен. задан. без звука."
            )
            tk.Label(
                self.root, text=desc_text,
                font=("Arial", 11), bg="#f0f2f5", fg="#4a5568",
                justify="center", wraplength=440, pady=15
            ).pack(pady=10)

            next_btn = tk.Button(
                self.root, text=f"Продолжить тренировку ({self.practice_count}/{min_practice})",
                font=("Arial", 12, "bold"), bg="#007bff", fg="white",
                padx=20, pady=12, bd=0, cursor="hand2",
                command=self.start_practice_trial
            )
            next_btn.pack(pady=10, fill="x", padx=60)
        else:
            desc_text = (
                "Обязательная тренировка пройдена!\n\n"
                "Вы можете сделать еще одну разминочную попытку или перейти к настройке звука "
                "перед основной частью исследования."
            )
            tk.Label(
                self.root, text=desc_text,
                font=("Arial", 11), bg="#f0f2f5", fg="#4a5568",
                justify="center", wraplength=440, pady=15
            ).pack(pady=10)

            retry_btn = tk.Button(
                self.root, text="Попробовать ещё тестовое задание",
                font=("Arial", 11, "bold"), bg="#6c757d", fg="white",
                padx=20, pady=10, bd=0, cursor="hand2",
                command=self.start_practice_trial
            )
            retry_btn.pack(pady=8, fill="x", padx=60)

            main_btn = tk.Button(
                self.root, text="Всё понятно, перейти к настройке звука →",
                font=("Arial", 12, "bold"), bg="#28a745", fg="white",
                padx=20, pady=12, bd=0, cursor="hand2",
                command=self.show_volume_calibration_screen
            )
            main_btn.pack(pady=8, fill="x", padx=60)

    # --- ЭКРАН 3.8: НАСТРОЙКА ГРОМКОСТИ (ТЕСТОВЫЙ ЗВУК) ---
    def show_volume_calibration_screen(self):
        asyncio.run(db.update_user_practice_count(self.user_id, self.practice_count))
        self.clear_screen()

        tk.Label(
            self.root, text="🔊 Настройка громкости",
            font=("Arial", 16, "bold"), bg="#f0f2f5", fg="#1e293b", pady=20
        ).pack()

        card = tk.Frame(self.root, bg="#ffffff", padx=22, pady=18, relief="solid", bd=1)
        card.pack(pady=10, padx=35, fill="x")

        checklist_text = (
            "🔹 Обязательно наденьте наушники.\n\n"
            "🔹 По возможности перейдите в тихое, спокойное место.\n\n"
            "🔹 Нажмите кнопку ниже и прослушайте тестовый сигнал.\n\n"
            "🔹 Отрегулируйте громкость устройства так, чтобы звук был "
            "хорошо различим, но не вызывал дискомфорта."
        )
        tk.Label(
            card, text=checklist_text,
            font=("Arial", 11), bg="#ffffff", fg="#334155",
            justify="left", wraplength=400
        ).pack(anchor="w")

        test_sound_btn = tk.Button(
            self.root, text="▶️ Прослушать тестовый сигнал",
            font=("Arial", 12, "bold"), bg="#007bff", fg="white",
            padx=20, pady=12, bd=0, cursor="hand2",
            command=lambda: self.play_mp3(TEST_SOUND_FILE)
        )
        test_sound_btn.pack(pady=(22, 10), fill="x", padx=55)

        start_main_btn = tk.Button(
            self.root, text="Громкость настроена, начать исследование →",
            font=("Arial", 12, "bold"), bg="#28a745", fg="white",
            padx=20, pady=12, bd=0, cursor="hand2",
            command=self.start_main_experiment
        )
        start_main_btn.pack(pady=8, fill="x", padx=55)

    def start_main_experiment(self):
        self.stop_audio()
        self.is_practice = False
        self.current_trial_idx = 0
        self.run_next_trial()

    # --- ЭКРАН 4: ПЕРЕДЫШКА МЕЖДУ ЗАДАЧАМИ ---
    def show_rest_screen(self):
        self.stop_audio()
        self.clear_screen()

        done_count = self.current_trial_idx + 1
        total_count = len(self.trials)

        # Прогресс сверху
        tk.Label(
            self.root, text=f"Прогресс: {done_count} из {total_count}",
            font=("Arial", 10, "bold"), bg="#f0f2f5", fg="#64748b", pady=15
        ).pack()

        # Аккуратная белая карточка по центру
        card = tk.Frame(self.root, bg="#ffffff", padx=30, pady=28, relief="solid", bd=1)
        card.pack(pady=25, padx=45, fill="x")

        tk.Label(
            card, text="⏸ Короткая пауза",
            font=("Arial", 16, "bold"), bg="#ffffff", fg="#1e293b"
        ).pack(pady=(0, 10))

        tk.Label(
            card, text="Переведите дух и нажмите кнопку,\nкогда будете готовы продолжить.",
            font=("Arial", 11), bg="#ffffff", fg="#475569", justify="center"
        ).pack()

        continue_btn = tk.Button(
            self.root, text="Дальше →",
            font=("Arial", 13, "bold"), bg="#007bff", fg="white",
            padx=30, pady=12, bd=0, cursor="hand2",
            command=self.next_trial_increment
        )
        continue_btn.pack(pady=20, fill="x", padx=80)

    def next_trial_increment(self):
        self.current_trial_idx += 1
        self.run_next_trial()


    # --- ЭКРАН 5: ЗАВЕРШЕНИЕ ---
    def show_finish_screen(self):
        self.stop_audio()
        self.clear_screen()

        tk.Label(
            self.root, text="🏆 Второй этап завершен!",
            font=("Arial", 18, "bold"), bg="#f0f2f5", fg="#28a745", pady=30
        ).pack()

        tk.Label(
            self.root,
            text="Все данные времени реакции, ошибок и контрольных условий\nуспешно сохранены в базу данных reaction_results.db!",
            font=("Arial", 11), bg="#f0f2f5", fg="#333333", justify="center"
        ).pack(pady=20)

        exit_btn = ttk.Button(self.root, text="Закрыть приложение", command=self.root.quit)
        exit_btn.pack(pady=30)


if __name__ == "__main__":
    window = tk.Tk()
    app = ReactionGuiApp(window)
    window.mainloop()