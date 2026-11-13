import time
import random
from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile

from quiz import ReactionStates, SOUNDS_LIST
import database as db

router = Router()

# Кнопки пульта управления
def get_game_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Кнопка А", callback_data="btn_A"), InlineKeyboardButton(text="Кнопка Б", callback_data="btn_B")],
        [InlineKeyboardButton(text="Кнопка В", callback_data="btn_V"), InlineKeyboardButton(text="Кнопка Г", callback_data="btn_G")]
    ])

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    # Первым делом задаем вопрос про авиацию
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, пилот / учусь / связан профессионально", callback_data="exp_pro")],
        [InlineKeyboardButton(text="Да, увлекаюсь авиасимуляторами (MFS, X-Plane и др.)", callback_data="exp_sim")],
        [InlineKeyboardButton(text="Нет, никак не связан(а)", callback_data="exp_no")]
    ])

    await message.answer(
        f"Здравствуйте, {message.from_user.first_name}!\n"
        "Это вторая часть исследования. Прежде чем начать, ответьте на вопрос:\n\n"
        "**Связаны ли вы с авиацией или авиасимуляторами?**",
        reply_markup=kb
    )
    await state.set_state(ReactionStates.waiting_for_aviation)

@router.callback_query(ReactionStates.waiting_for_aviation)
async def handle_aviation_question(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    # Маппинг ответов для базы данных
    exp_map = {"exp_pro": "Профессионал", "exp_sim": "Симмер", "exp_no": "Нет связи"}
    user_exp = exp_map.get(callback.data, "Не указано")

    # Регистрируем в БД
    await db.add_user(callback.from_user.id, callback.from_user.first_name, user_exp)

    await callback.message.edit_text(
        "Данные приняты. Теперь настроим звук.\n"
        "Пожалуйста, наденьте наушники. Сейчас бот пришлет проверочный файл."
    )

    try:
        await callback.message.answer_audio(audio=FSInputFile("sounds/test_sound.mp3"), caption="Отрегулируйте громкость.")
    except Exception:
        pass

    ready_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Громкость настроена, начать тест", callback_data="start_speed_test")]
    ])
    await callback.message.answer("Как будете готовы, нажмите кнопку:", reply_markup=ready_kb)
    await state.set_state(ReactionStates.waiting_for_test_sound)

@router.callback_query(ReactionStates.waiting_for_test_sound, F.data == "start_speed_test")
async def start_speed_test(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(current_sound_index=0)
    await start_next_sequence(callback.message, state)

async def start_next_sequence(message: types.Message, state: FSMContext):
    """Генерация случайной комбинации кнопок и отправка звука."""
    data = await state.get_data()
    idx = data["current_sound_index"]

    if idx >= len(SOUNDS_LIST):
        await message.answer("🎉 Исследование успешно завершено! Огромное спасибо за участие.")
        await state.clear()
        return

    sound_name = SOUNDS_LIST[idx]

    # Генерируем случайную последовательность, например из 3 нажатий: ['A', 'B', 'G']
    all_buttons = ['A', 'B', 'V', 'G']
    target_sequence = [random.choice(all_buttons) for _ in range(3)]

    # Красивый текст для пользователя
    seq_text = " ➡️ ".join([f"Кнопка {x}" for x in target_sequence])

    await message.answer(f"🔈 **Тест №{idx + 1}**")
    try:
        await message.answer_audio(audio=FSInputFile(f"sounds/{sound_name}"))
    except Exception:
        await message.answer(f"*(Звучит файл: {sound_name})*")

    await message.answer(
        f"🚨 **ЗАДАНИЕ:** Как можно быстрее нажмите кнопки в указанном порядке:\n\n"
        f"👉 **{seq_text}** 👈",
        reply_markup=get_game_keyboard()
    )

    # Сохраняем эталонную цепочку, текущий шаг пользователя (0), счетчик ошибок (0) и время старта
    await state.update_data(
        target_sequence=target_sequence,
        current_step=0,
        errors_count=0,
        start_time=time.time() # Фиксируем время отправки задания
    )
    await state.set_state(ReactionStates.testing)

@router.callback_query(ReactionStates.testing, F.data.startswith("btn_"))
async def handle_game_click(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    # Какая кнопка была нажата ('A', 'B', 'V' или 'G')
    clicked_btn = callback.data.split("_")[1]

    data = await state.get_data()
    target_sequence = data["target_sequence"]
    current_step = data["current_step"]
    errors_count = data["errors_count"]

    # Какая кнопка ОЖИДАЛАСЬ на этом шаге
    expected_btn = target_sequence[current_step]

    if clicked_btn == expected_btn:
        # Правильно! Переходим к следующему шагу комбинации
        current_step += 1
        if current_step < len(target_sequence):
            # Если цепочка еще не закончена, обновляем шаг
            await state.update_data(current_step=current_step)
        else:
            # Цепочка завершена успешно! Считаем время
            end_time = time.time()
            total_time = round(end_time - data["start_time"], 2) # Время в секундах

            idx = data["current_sound_index"]
            sound_name = SOUNDS_LIST[idx]

            # Пишем результат в БД
            await db.save_reaction(
                user_id=callback.from_user.id,
                sound_id=sound_name,
                time_seconds=total_time,
                errors_count=errors_count
            )

            await callback.message.edit_text(
                f"✅ Задание выполнено!\n"
                f"⏱ Время: {total_time} сек.\n"
                f"❌ Ошибок: {errors_count}"
            )

            # Переходим к следующему звуку
            await state.update_data(current_sound_index=idx + 1)
            await start_next_sequence(callback.message, state)
    else:
        # Ошибка! Нажал не то
        errors_count += 1
        await state.update_data(errors_count=errors_count)
        # Можно слегка моргнуть текстом или просто продолжить ждать правильную кнопку
