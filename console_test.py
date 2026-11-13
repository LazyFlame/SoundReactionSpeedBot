import asyncio
import time
import random
import database as db
from quiz import SOUNDS_LIST

async def run_console_test():
    # 1. Инициализируем базу данных
    await db.init_db()
    print("=== КОНСОЛЬНЫЙ ЭМУЛЯТОР ТЕСТА СКОРОСТИ РЕАКЦИИ ===")

    # Имитируем Telegram ID (для теста используем фиксированный номер)
    user_id = 999999999
    username = "console_tester"
    first_name = "ЛокальныйТест"

    # Первичная регистрация
    await db.add_user(user_id, username, first_name)

    # 2. Вопрос про авиацию
    print("\nИмеете ли вы какую-либо связь с авиацией или авиасимуляторами?")
    print("1 — Да, я пилот / диспетчер")
    print("2 — Да, активно летаю в авиасимуляторах")
    print("3 — Нет, никак не связан(а) с авиацией")

    choice = input("Выберите вариант (1, 2 или 3): ").strip()
    status_map = {"1": "Да, я пилот / диспетчер", "2": "Да, активно летаю в авиасимуляторах", "3": "Нет, никак не связан(а) с авиацией"}
    aviation_status = status_map.get(choice, "Нет, никак не связан(а) с авиацией")

    # Обновляем статус в БД
    await db.update_user_aviation(user_id, aviation_status)
    print(f"✅ Статус '{aviation_status}' сохранен в базу данных.\n")

    print("Представьте, что звучит проверочный звук... Наушники настроены.")
    input("Нажмите Enter, чтобы начать основной тест скорости реакции...")

    # 3. Цикл по звуковым стимулам
    all_buttons = ['А', 'Б', 'В', 'Г']

    for idx, sound_name in enumerate(SOUNDS_LIST):
        print("\n" + "="*40)
        print(f"🔈 СТИМУЛ №{idx + 1}: {sound_name}")
        print("="*40)

        # Генерируем случайную комбинацию из 3 кнопок
        target_sequence = [random.choice(all_buttons) for _ in range(3)]
        seq_text = " ➡️ ".join(target_sequence)

        print(f"🚨 ЗАДАНИЕ: Как можно быстрее введите буквы в указанном порядке (без пробелов):")
        print(f"👉  {seq_text}  👈")
        print("Вводите по одной букве большими буквами (А, Б, В, Г) и нажимайте Enter.")

        errors_count = 0
        current_step = 0

        # Засекаем время старта
        start_time = time.time()

        while current_step < len(target_sequence):
            expected_letter = target_sequence[current_step]
            user_input = input(f"Шаг {current_step + 1} (Ждем {expected_letter}): ").strip().upper()

            if user_input == expected_letter:
                print("  🟢 Правильно!")
                current_step += 1
            else:
                print("  🔴 Ошибка! Попробуйте еще раз.")
                errors_count += 1

        # Засекаем время окончания комбинации
        end_time = time.time()
        total_time = round(end_time - start_time, 2)

        print(f"\n🎉 Стимул выполнен!")
        print(f"⏱ Время реакции: {total_time} сек.")
        print(f"❌ Количество ошибок: {errors_count}")

        # Записываем результаты замера в SQLite
        await db.save_reaction_results(user_id, sound_name, total_time, errors_count)
        print("💾 Данные успешно записаны в reaction_results.db!")

    print("\n🏆 Тестирование успешно завершено! Все данные в базе.")

if __name__ == "__main__":
    asyncio.run(run_console_test())
