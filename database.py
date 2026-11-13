import aiosqlite

DB_NAME = "reaction_results.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users_stage2 (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                aviation_status TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                sound_id TEXT,
                condition_type TEXT,        -- 'sound', 'silence', 'noise'
                target_sequence TEXT,       -- строка порядка (например, '3,1,4,2')
                execution_time REAL,        -- время выполнения в секундах
                errors_count INTEGER,       -- количество ошибок (неверных кликов)
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_stage2 (user_id)
            )
        """)
        await db.commit()

async def add_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users_stage2 (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        await db.commit()

async def update_user_aviation(user_id: int, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users_stage2 SET aviation_status = ? WHERE user_id = ?",
            (status, user_id)
        )
        await db.commit()

async def save_reaction_results(user_id: int, sound_id: str, condition_type: str, target_sequence: str, execution_time: float, errors: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO reaction_results (user_id, sound_id, condition_type, target_sequence, execution_time, errors_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, sound_id, condition_type, target_sequence, execution_time, errors)
        )
        await db.commit()