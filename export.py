import sqlite3
import pandas as pd
from quiz import SOUND_TO_CAT

DB_NAME = "reaction_results.db"
OUTPUT_FILE = "research_export.xlsx"


def export_to_excel():
    conn = sqlite3.connect(DB_NAME)

    # 1. Таблица участников (без технического JSON-плейлиста)
    users_query = """
        SELECT
            u.participant_num AS "№ участника",
            u.user_id AS "Telegram ID",
            u.username AS "Username",
            u.first_name AS "Имя",
            u.gender AS "Пол",
            u.age AS "Возраст",
            u.hearing_status AS "Слух",
            u.cockpit_familiarity AS "Опыт в авиации",
            u.fatigue_level AS "Усталость (1-5)",
            u.practice_count AS "Кол-во тренировок",
            COUNT(r.id) AS "Пройдено проб (из 20)",
            u.registered_at AS "Дата регистрации"
        FROM users_stage2 u
        LEFT JOIN reaction_results r ON u.user_id = r.user_id
        GROUP BY u.user_id
        ORDER BY u.participant_num ASC
    """
    df_users = pd.read_sql_query(users_query, conn)

    # 2. Объединённая таблица замеров + данные анкеты для статистического анализа
    results_query = """
        SELECT
            r.id AS "ID записи",
            u.participant_num AS "№ участника",
            r.user_id AS "Telegram ID",
            u.gender AS "Пол",
            u.age AS "Возраст",
            u.hearing_status AS "Слух",
            u.cockpit_familiarity AS "Опыт в авиации",
            u.fatigue_level AS "Усталость (1-5)",
            r.trial_index AS "Порядковый номер пробы",
            r.sound_id AS "Звук",
            r.target_sequence AS "Последовательность",
            r.execution_time AS "Время реакции (сек)",
            r.errors_count AS "Ошибки",
            r.timeouts_count AS "Таймауты",
            r.answered_at AS "Время ответа"
        FROM reaction_results r
        LEFT JOIN users_stage2 u ON r.user_id = u.user_id
        ORDER BY u.participant_num ASC, r.trial_index ASC
    """
    df_results = pd.read_sql_query(results_query, conn)
    conn.close()

    # Добавляем категорию сигнала (emergency / warning / informative)
    if not df_results.empty:
        df_results.insert(
            10,
            "Категория звука",
            df_results["Звук"].map(SOUND_TO_CAT).fillna("unknown")
        )

        # 3. Сводная статистика по каждому звуку
        df_summary = (
            df_results.groupby(["Категория звука", "Звук"], as_index=False)
            .agg(
                Кол_во_замеров=("Время реакции (сек)", "count"),
                Среднее_время_сек=("Время реакции (сек)", lambda x: round(x.mean(), 3)),
                Медиана_времени_сек=("Время реакции (сек)", lambda x: round(x.median(), 3)),
                Среднее_ошибок=("Ошибки", lambda x: round(x.mean(), 2)),
                Всего_таймаутов=("Таймауты", "sum")
            )
            .sort_values(by=["Категория звука", "Среднее_время_сек"])
        )
    else:
        df_summary = pd.DataFrame(columns=["Категория звука", "Звук", "Замеров пока нет"])

    # Записываем в Excel с автоподбором ширины колонок
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        df_users.to_excel(writer, sheet_name="Анкета_участников", index=False)
        df_results.to_excel(writer, sheet_name="Результаты_замеров", index=False)
        df_summary.to_excel(writer, sheet_name="Сводка_по_звукам", index=False)

        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col) + 3
                ws.column_dimensions[col[0].column_letter].width = min(max_len, 40)

    print(f"✅ Экспорт завершён! Файл сохранён: {OUTPUT_FILE}")
    print(f"Участников в базе: {len(df_users)} | Записей замеров: {len(df_results)}")


if __name__ == "__main__":
    export_to_excel()
