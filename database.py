import json
import aiosqlite
from quiz import generate_latin_playlist

DB_NAME = "reaction_results.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users_stage2 (
                participant_num INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                gender TEXT,
                age INTEGER,
                hearing_status TEXT,
                cockpit_familiarity TEXT,
                fatigue_level INTEGER,
                practice_count INTEGER DEFAULT 0,
                playlist_json TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                trial_index INTEGER,
                sound_id TEXT,
                target_sequence TEXT,
                execution_time REAL,
                errors_count INTEGER,
                timeouts_count INTEGER DEFAULT 0,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_stage2 (user_id)
            )
        """)

        await db.commit()


async def get_or_create_user_state(user_id: int, username: str = "", first_name: str = "") -> dict:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users_stage2 WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()

        if row is None:
            cursor = await db.execute(
                "INSERT INTO users_stage2 (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            participant_num = cursor.lastrowid
            playlist = generate_latin_playlist(participant_num - 1)
            await db.execute(
                "UPDATE users_stage2 SET playlist_json = ? WHERE user_id = ?",
                (json.dumps(playlist), user_id)
            )
            await db.commit()

            cursor = await db.execute("SELECT * FROM users_stage2 WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()

        playlist = json.loads(row["playlist_json"])
        res_cursor = await db.execute(
            "SELECT sound_id FROM reaction_results WHERE user_id = ? ORDER BY id ASC",
            (user_id,)
        )
        completed_sounds = [r["sound_id"] for r in await res_cursor.fetchall()]

        profile_completed = all([
            row["gender"] is not None,
            row["age"] is not None,
            row["hearing_status"] is not None,
            row["cockpit_familiarity"] is not None,
            row["fatigue_level"] is not None
        ])

        return {
            "user_id": row["user_id"],
            "profile_completed": profile_completed,
            "practice_count": row["practice_count"] or 0,
            "playlist": playlist,
            "completed_count": len(completed_sounds)
        }


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


async def save_reaction_results(
    user_id: int,
    trial_index: int,
    sound_id: str,
    target_sequence: str,
    execution_time: float,
    errors: int,
    timeouts: int = 0
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO reaction_results (user_id, trial_index, sound_id, target_sequence, execution_time, errors_count, timeouts_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, trial_index, sound_id, target_sequence, execution_time, errors, timeouts)
        )
        await db.commit()

