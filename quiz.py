from aiogram.fsm.state import State, StatesGroup
import random

SOUNDS_DICT = {
    "Test sound.mp3": "CQACAgIAAyEFAATuUsLvAAM_avXYiTDG3diEpm17ife-PiOKxZMAAluwAALQmKlLovBMf9hvRYQ9BA",

    # Аварийные
    "MW.mp3": "CQACAgIAAyEFAATuUsLvAAM5avXX8IL1S_KZksk4rNQTbuxx9TAAAkewAALQmKlLb5leZ7WD48c9BA",
    "SFT.mp3": "CQACAgIAAyEFAATuUsLvAAM-avXYiWhyz2lLPQJJmhxS0CVkxj8AAl2wAALQmKlLNAi9qpq-r5Y9BA",
    "CW.mp3": "CQACAgIAAyEFAATuUsLvAAMxavXXKi_SyQ0v2NLFSovcWD957LEAAjCwAALQmKlLCVgsNdwodTY9BA",
    "AG.mp3": "CQACAgIAAyEFAATuUsLvAAMvavXWt104hg-hOHUHBm6pVXp4K8wAAiSwAALQmKlLLNGrX438h389BA",
    "WD.mp3": "CQACAgIAAyEFAATuUsLvAANAavXYieGiJocAAb3w44YGLPXTwKmUAAJcsAAC0JipSzVqjdta0p7bPQQ",
    "OH.mp3": "CQACAgIAAyEFAATuUsLvAAM6avXYP7CPG3QtD7gmyGXwebX_W68AAlSwAALQmKlLcUVSFitcDfY9BA",

    # Предупреждающие
    "RD.mp3": "CQACAgIAAyEFAATuUsLvAAM7avXYP9QrlS7wdOMyCoHh1cmjTycAAlWwAALQmKlLWOGe3Hd7SJ89BA",
    "MPP.mp3": "CQACAgIAAyEFAATuUsLvAAM4avXX8JTcaA7K-QTSpG72ijAkywkAAkmwAALQmKlLMA_-Urrdqgs9BA",
    "IR.mp3": "CQACAgIAAyEFAATuUsLvAAM1avXXgaDftaOtYlCm_R2bgazFKPUAAj6wAALQmKlLlOIZhv1CI5s9BA",
    "ANLC.mp3": "CQACAgIAAyEFAATuUsLvAAMwavXXKqImJmjnQQABSrlD5kCXgZpmAAIxsAAC0JipS5ZGrPbxxWirPQQ",
    "WSGA.mp3": "CQACAgIAAyEFAATuUsLvAANCavXYtEuNzdgJyjS_2gypNqfdJ8IAAmCwAALQmKlL2v-FDqlswJI9BA",
    "WS.mp3": "CQACAgIAAyEFAATuUsLvAANBavXYtNaxgitqXqveBtwgtW2ImRsAAmGwAALQmKlLZRawt-UmT_Y9BA",
    "SBPL.mp3": "CQACAgIAAyEFAATuUsLvAAM9avXYP96P8rfh25kzvsXbYdPM5qMAAlOwAALQmKlLe6zZpbMZLIM9BA",

    # Уведомительные
    "SB.mp3": "CQACAgIAAyEFAATuUsLvAAM8avXYP4OBsXVw3tMDaDhvLs8xg-oAAlKwAALQmKlLIJwJmuK5e1c9BA",
    "LAR.mp3": "CQACAgIAAyEFAATuUsLvAAM2avXX8NGosNJwFD2mVx_faWdWFGUAAkawAALQmKlLsY7QqgYx_ps9BA",
    "AAA.mp3": "CQACAgIAAyEFAATuUsLvAAMuavXWt4xkPaFz3f8LQbs_5_-sAAGqAAIlsAAC0JipS3_8epHIi7iVPQQ",
    "HN.mp3": "CQACAgIAAyEFAATuUsLvAAM0avXXgczky2mHeiiy0h64IWvvBzQAAj2wAALQmKlLoxMmG1ZAr889BA",
    "GWR.mp3": "CQACAgIAAyEFAATuUsLvAAMzavXXgWTVzz6al0_OhEBsHNrsFy4AAjuwAALQmKlL0RGLt5Eb3Io9BA",
    "GWL.mp3": "CQACAgIAAyEFAATuUsLvAAMyavXXKrJeVxxiYUmL9CMxATSTA_MAAjKwAALQmKlLNEzJe70-JjI9BA",
    "LG.mp3": "CQACAgIAAyEFAATuUsLvAAM3avXX8IqlLPLLPt8wy8qJjv8OjgsAAkiwAALQmKlLusIXNKOk0FA9BA",
}
# Категории для контроля последовательности
CATEGORIES = {
    "emergency": ["MW.mp3", "SFT.mp3", "CW.mp3", "AG.mp3", "WD.mp3", "OH.mp3"],
    "warning": ["RD.mp3", "MPP.mp3", "IR.mp3", "ANLC.mp3", "WSGA.mp3", "WS.mp3", "SBPL.mp3"],
    "informative": ["SB.mp3", "LAR.mp3", "AAA.mp3", "HN.mp3", "GWR.mp3", "GWL.mp3", "LG.mp3"]
}

def generate_balanced_playlist():
    """
    Генерирует список звуков так, чтобы категории чередовались
    и не было ситуаций, когда подряд идут 3 звука одной категории.
    """
    em = CATEGORIES["emergency"][:]
    warn = CATEGORIES["warning"][:]
    info = CATEGORIES["informative"][:]

    random.shuffle(em)
    random.shuffle(warn)
    random.shuffle(info)

    playlist = []
    pools = [em, warn, info]

    last_cat_idx = -1
    while any(pools):
        # Выбираем пул, который не равен предыдущему (если в нем еще есть элементы)
        available_pools = [i for i, p in enumerate(pools) if p and i != last_cat_idx]
        if not available_pools:
            available_pools = [i for i, p in enumerate(pools) if p]

        chosen_pool_idx = random.choice(available_pools)
        sound = pools[chosen_pool_idx].pop(0)
        playlist.append(sound)
        last_cat_idx = chosen_pool_idx

    return playlist

# Готовый сбалансированный список для конкретного пользователя (можно вызывать при старте теста)
# SOUNDS_LIST = generate_balanced_playlist()

class QuizStates(StatesGroup):
    waiting_for_consent = State()
    survey_age = State()
    survey_gender = State()
    survey_hearing = State()
    survey_sleep = State()
    survey_aviation = State()
    survey_english = State()
    state_mood = State()
    state_tension = State()
    state_energy = State()
    waiting_for_test_sound = State()
    answering_anxiety = State()
    answering_action = State()
    answering_impulse = State()
    answering_irritation = State()
    answering_valence = State()
    answering_arousal = State()
