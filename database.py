import aiosqlite

DB_NAME = "reaction_results.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users_stage2 (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                gender TEXT,
                age INTEGER,
                hearing_status TEXT,
                cockpit_familiarity TEXT,
                fatigue_level INTEGER,
                practice_count INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        new_cols = (
            "gender TEXT",
            "age INTEGER",
            "hearing_status TEXT",
            "cockpit_familiarity TEXT",
            "fatigue_level INTEGER",
            "practice_count INTEGER DEFAULT 0"
        )
        for col_def in new_cols:
            try:
                await db.execute(f"ALTER TABLE users_stage2 ADD COLUMN {col_def}")
            except Exception:
                pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                sound_id TEXT,
                condition_type TEXT,
                target_sequence TEXT,
                execution_time REAL,
                errors_count INTEGER,
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

async def update_user_profile(
    user_id: int,
    gender: str,
    age: int,
    hearing_status: str,
    cockpit_familiarity: str,
    fatigue_level: int
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            UPDATE users_stage2
            SET gender = ?, age = ?, hearing_status = ?, cockpit_familiarity = ?, fatigue_level = ?
            WHERE user_id = ?
            """,
            (gender, age, hearing_status, cockpit_familiarity, fatigue_level, user_id)
        )
        await db.commit()

async def update_user_practice_count(user_id: int, practice_count: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users_stage2 SET practice_count = ? WHERE user_id = ?",
            (practice_count, user_id)
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
