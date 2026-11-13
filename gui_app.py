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
        self.user_cockpit_familiarity = None
        self.user_gender = None
        self.user_age = None

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

    # --- ЭКРАН 1: ПРИВЕТСТВИЕ И СОГЛАСИЕ ---
    def create_welcome_screen(self):
        self.clear_screen()

        tk.Label(
            self.root, text="🎧 Исследование скорости реакции",
            font=("Arial", 16, "bold"), bg="#f0f2f5", fg="#1e293b", pady=16
        ).pack()

        card = tk.Frame(self.root, bg="#ffffff", padx=22, pady=18, relief="solid", bd=1)
        card.pack(pady=6, padx=35, fill="x")

        intro_text = (
            "Здравствуйте! Благодарим за готовность принять участие в исследовании.\n\n"
            "Вам предстоит выполнить серию из 20 коротких заданий. "
            "Вашей задачей будет нажимать на цифры в заданном порядке на фоне звуковых сигналов.\n\n"
            "Ориентировочная длительность исследования: 10–15 минут.\n\n"
            "Прохождение можно прервать в любой момент и продолжить позже с того же места. "
            "Все ответы записываются анонимно.\n\n"
            "Нажимая кнопку «Согласен(на)», вы подтверждаете своё согласие на участие."
        )

        tk.Label(
            card, text=intro_text,
            font=("Arial", 10), bg="#ffffff", fg="#334155",
            justify="left", wraplength=405
        ).pack(anchor="w")

        agree_btn = tk.Button(
            self.root, text="Согласен(на)",
            font=("Arial", 13, "bold"), bg="#28a745", fg="white",
            padx=30, pady=12, bd=0, cursor="hand2",
            command=self.create_demographics_screen
        )
        agree_btn.pack(pady=18, fill="x", padx=80)

    # --- ЭКРАН 1.2: ПОЛ И ВОЗРАСТ ---
    def create_demographics_screen(self):
        self.clear_screen()

        tk.Label(
            self.root, text="Несколько вопросов о вас",
            font=("Arial", 15, "bold"), bg="#f0f2f5", fg="#1e293b", pady=18
        ).pack()

        tk.Label(
            self.root, text="Укажите ваш пол:",
            font=("Arial", 11, "bold"), bg="#f0f2f5", fg="#334155"
        ).pack(pady=(5, 8))

        self.gender_var = tk.StringVar(value="")
        gender_frame = tk.Frame(self.root, bg="#f0f2f5")
        gender_frame.pack(pady=4)

        for label_text, val in [("Мужской", "М"), ("Женский", "Ж")]:
            rb = tk.Radiobutton(
                gender_frame, text=label_text, variable=self.gender_var, value=val,
                font=("Arial", 11), bg="#f0f2f5", fg="#1e293b",
                selectcolor="#ffffff", cursor="hand2", padx=15
            )
            rb.pack(side="left")

        tk.Label(
            self.root, text="Укажите ваш возраст (полных лет):",
            font=("Arial", 11, "bold"), bg="#f0f2f5", fg="#334155"
        ).pack(pady=(20, 8))

        self.age_entry = tk.Entry(
            self.root, font=("Arial", 14), width=8, justify="center", relief="solid", bd=1
        )
        self.age_entry.pack(pady=4)
        self.age_entry.focus_set()

        self.demo_error_label = tk.Label(
            self.root, text="", font=("Arial", 10), bg="#f0f2f5", fg="#dc2626"
        )
        self.demo_error_label.pack(pady=8)

        next_btn = tk.Button(
            self.root, text="Далее →",
            font=("Arial", 12, "bold"), bg="#007bff", fg="white",
            padx=25, pady=10, bd=0, cursor="hand2",
            command=self.validate_and_save_demographics
        )
        next_btn.pack(pady=15, fill="x", padx=90)

    def validate_and_save_demographics(self):
        gender = self.gender_var.get()
        age_str = self.age_entry.get().strip()

        if not gender:
            self.demo_error_label.config(text="Пожалуйста, выберите ваш пол.")
            return

        if not age_str.isdigit() or not (10 <= int(age_str) <= 99):
            self.demo_error_label.config(text="Введите корректный возраст (от 10 до 99 лет).")
            return

        self.user_gender = gender
        self.user_age = int(age_str)
        self.create_hearing_question_screen()

    # --- ЭКРАН 1.3: ВОПРОС ПРО СЛУХ (выровнен по левому краю) ---
    def create_hearing_question_screen(self):
        self.clear_screen()

        tk.Label(
            self.root, text="Есть ли у вас сейчас заложенность ушей\nили проблемы со слухом?",
            font=("Arial", 13, "bold"), bg="#f0f2f5", fg="#1e293b", pady=18
        ).pack()

        hearing_options = [
            ("Нет, слух в норме", "нет"),
            ("Есть лёгкие отклонения — небольшая заложенность или незначительное снижение слуха.", "легкое"),
            ("Есть выраженные нарушения — серьёзное снижение слуха или сильная заложенность.", "выраженное")
        ]

        for text, short_status in hearing_options:
            btn = tk.Button(
                self.root, text=text,
                font=("Arial", 10), bg="#ffffff", fg="#1e293b",
                activebackground="#e2e8f0", relief="solid", bd=1,
                anchor="w", justify="left", wraplength=400,
                padx=16, pady=12, cursor="hand2",
                command=lambda s=short_status: self.save_hearing_and_proceed(s)
            )
            btn.pack(fill="x", padx=35, pady=7)

    def save_hearing_and_proceed(self, hearing_status):
        self.user_hearing_status = hearing_status
        self.create_cockpit_question_screen()

    # --- ЭКРАН 1.4: ЗНАКОМСТВО С БОРТОВЫМИ СИСТЕМАМИ (выровнен по левому краю) ---
    def create_cockpit_question_screen(self):
        self.clear_screen()

        tk.Label(
            self.root,
            text="Насколько хорошо вы знакомы с бортовыми системами\nоповещения и звуками кабины самолёта?",
            font=("Arial", 12, "bold"), bg="#f0f2f5", fg="#1e293b", pady=16
        ).pack()

        cockpit_options = [
            ("Совсем не знаком(а)", "не_знаком"),
            ("Поверхностно знаком(а) — слышал(а) сигналы в фильмах, играх или видеороликах.", "поверхностно"),
            ("Знаком(а) как любитель — увлекаюсь авиацией, играю в авиасимуляторы.", "любитель"),
            ("Есть практический / учебный опыт — изучал(а) системы в ВУЗе, был(а) на тренажёрах или в кабине.", "практический_опыт")
        ]

        for text, short_code in cockpit_options:
            btn = tk.Button(
                self.root, text=text,
                font=("Arial", 10), bg="#ffffff", fg="#1e293b",
                activebackground="#e2e8f0", relief="solid", bd=1,
                anchor="w", justify="left", wraplength=405,
                padx=16, pady=10, cursor="hand2",
                command=lambda c=short_code: self.save_cockpit_and_proceed(c)
            )
            btn.pack(fill="x", padx=32, pady=6)

    def save_cockpit_and_proceed(self, cockpit_code):
        self.user_cockpit_familiarity = cockpit_code
        self.create_fatigue_question_screen()

    # --- ЭКРАН 1.5: ОЦЕНКА ТЕКУЩЕЙ УСТАЛОСТИ ---
    def create_fatigue_question_screen(self):
        self.clear_screen()

        tk.Label(
            self.root,
            text="Оцените ваш текущий уровень усталости",
            font=("Arial", 14, "bold"), bg="#f0f2f5", fg="#1e293b", pady=18
        ).pack()

        tk.Label(
            self.root,
            text="Выберите вариант, который точнее всего описывает ваше состояние прямо сейчас:",
            font=("Arial", 10), bg="#f0f2f5", fg="#475569", wraplength=420
        ).pack(pady=(0, 12))

        fatigue_options = [
            ("1 — Полон(на) сил и энергии, высокая концентрация", 1),
            ("2 — Бодрое состояние, чувствую себя хорошо", 2),
            ("3 — Нормальное, спокойное рабочее состояние", 3),
            ("4 — Ощущаю небольшую усталость или сонливость", 4),
            ("5 — Сильно устал(а), трудно удерживать внимание", 5)
        ]

        for text, level in fatigue_options:
            btn = tk.Button(
                self.root, text=text,
                font=("Arial", 10), bg="#ffffff", fg="#1e293b",
                activebackground="#e2e8f0", relief="solid", bd=1,
                anchor="w", justify="left", wraplength=405,
                padx=16, pady=10, cursor="hand2",
                command=lambda lvl=level: self.save_fatigue_and_continue(lvl)
            )
            btn.pack(fill="x", padx=35, pady=5)

    def save_fatigue_and_continue(self, fatigue_level):
        self.user_fatigue_level = fatigue_level
        asyncio.run(db.update_user_profile(
            self.user_id,
            self.user_gender,
            self.user_age,
            self.user_hearing_status,
            self.user_cockpit_familiarity,
            self.user_fatigue_level
        ))
        self.create_instruction_screen()

    # --- ЭКРАН 2: ИНСТРУКЦИЯ ---
    def create_instruction_screen(self):
        self.clear_screen()

        tk.Label(
            self.root, text="📋 Как проходить задание",
            font=("Arial", 16, "bold"), bg="#f0f2f5", fg="#1e293b", pady=16
        ).pack()

        card = tk.Frame(self.root, bg="#ffffff", padx=20, pady=16, relief="solid", bd=1)
        card.pack(pady=6, padx=35, fill="x")

        steps_text = (
            "1. Сверху появится строка с порядком из 4 цифр (например: 3 → 1 → 4 → 2).\n\n"
            "2. Нажмите кнопки с этими цифрами в указанном порядке как можно быстрее и точнее.\n\n"
            "3. Правильно нажатая цифра подсветится зелёным цветом в верхней строке.\n\n"
            "4. Сначала вы пройдёте 3 тренировочных задания без звука, затем настроите "
            "комфортную громкость в наушниках и перейдёте к основной серии."
        )

        tk.Label(
            card, text=steps_text,
            font=("Arial", 10), bg="#ffffff", fg="#334155",
            justify="left", wraplength=410
        ).pack(anchor="w")

        start_btn = tk.Button(
            self.root, text="Перейти к тренировке (0/3) →",
            font=("Arial", 12, "bold"), bg="#007bff", fg="white",
            padx=25, pady=12, bd=0, cursor="hand2",
            command=self.start_practice_trial
        )
        start_btn.pack(pady=20, fill="x", padx=65)


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
        self.seq_labels = []
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

        # Плашка с последовательностью и подсветкой пройденных цифр
        seq_frame = tk.Frame(self.root, bg="#e2e8f0", padx=20, pady=10, relief="solid", bd=1)
        seq_frame.pack(pady=12)

        tk.Label(
            seq_frame, text="Требуемый порядок:",
            font=("Arial", 10), bg="#e2e8f0", fg="#555555"
        ).pack()

        digits_row = tk.Frame(seq_frame, bg="#e2e8f0")
        digits_row.pack(pady=(4, 0))

        for idx, num in enumerate(self.current_target_seq):
            lbl = tk.Label(
                digits_row, text=str(num),
                font=("Arial", 18, "bold"), bg="#e2e8f0", fg="#1d4ed8"
            )
            lbl.pack(side="left")
            self.seq_labels.append(lbl)

            if idx < len(self.current_target_seq) - 1:
                tk.Label(
                    digits_row, text=" → ",
                    font=("Arial", 16, "bold"), bg="#e2e8f0", fg="#64748b"
                ).pack(side="left")

        # Сетка кнопок 2x2
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
            # Подсвечиваем выполненную цифру в верхней инструкции зеленым
            self.seq_labels[self.current_step_idx].configure(fg="#16a34a")
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
            # Ошибка: увеличиваем счетчик и коротко мигаем красным
            self.errors_count += 1
            btn.configure(bg="#f8d7da")
            self.root.after(
                150,
                lambda b=btn: b.configure(bg="#ffffff") if b.winfo_exists() else None
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
            self.root, text="🏆 Второй этап завершён!",
            font=("Arial", 18, "bold"), bg="#f0f2f5", fg="#28a745", pady=30
        ).pack()

        tk.Label(
            self.root,
            text="Спасибо за участие и внимание к заданиям!\n"
                 "Ваши ответы успешно сохранены.\n\n"
                 "Теперь вы можете закрыть это окно.",
            font=("Arial", 12), bg="#f0f2f5", fg="#334155", justify="center"
        ).pack(pady=20)

        exit_btn = ttk.Button(self.root, text="Закрыть приложение", command=self.root.quit)
        exit_btn.pack(pady=30)


if __name__ == "__main__":
    window = tk.Tk()
    app = ReactionGuiApp(window)
    window.mainloop()