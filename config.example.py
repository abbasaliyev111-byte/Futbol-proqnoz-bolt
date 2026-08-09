# Bu faylı config.py adlandır və öz açarlarını daxil et.
# ƏSLA config.py-ni GitHub-a public repo-ya yükləmə (açarların oğurlanar)!

FOOTBALL_DATA_API_KEY = "BURAYA_FOOTBALL_DATA_ORG_ACARINI_YAZ"

TELEGRAM_BOT_TOKEN = "BURAYA_TELEGRAM_BOT_TOKEN_YAZ"
TELEGRAM_CHAT_ID = "BURAYA_CHAT_ID_YAZ"

# İzləmək istədiyin liqalar (data_fetcher.py-dəki LEAGUE_CODES-dən seç)
# Nə qədər çox liqa qatsan, bot arasından seçmək üçün bir o qədər çox
# matça baxacaq (deməli TOP_N seçim də bir az "keyfiyyətli" ola bilər)
LEAGUES_TO_TRACK = [
    "premier_league",
    "la_liga",
    "bundesliga",
    "serie_a",
    "ligue_1",
]

# Hər gün neçə "top" seçim göndərilsin
TOP_N = 5
