"""
Gündəlik işə salınan əsas script.
Bütün izlənilən liqalardakı bugünkü matçları analiz edir, modelin ən yüksək
ehtimal verdiyi TOP_N matçı seçib Telegram-a göndərir.

VACIB: "Ən yüksək ehtimallı" ≠ "zəmanətli". 75-80% ehtimal olan matç da
uduzula bilər — bu normaldır, statistikanın təbiətidir.

Bu faylı hər gün müəyyən saatda avtomatik işlətmək üçün cron istifadə et
(README.md-də təlimat var). İşlətmədən əvvəl config.py faylında öz
açarlarını yaz.
"""

import time
from data_fetcher import FootballDataClient, LEAGUE_CODES
from predictor import predict_match
from telegram_sender import send_telegram_message, format_prediction_message, format_daily_top_message

try:
    from config import (
        FOOTBALL_DATA_API_KEY,
        TELEGRAM_BOT_TOKEN,
        TELEGRAM_CHAT_ID,
        LEAGUES_TO_TRACK,
        TOP_N,
    )
except ImportError:
    raise SystemExit(
        "config.py tapılmadı! config.example.py-ni config.py adlandır və "
        "öz açarlarını daxil et."
    )


def confidence_score(prediction: dict) -> float:
    """
    Bir proqnozun 'nə qədər aydın/ehtimallı' olduğunu ölçür.
    Sadəcə 1X2-dəki ən yüksək faizi götürürük (məs. ev sahibi 78% olsa, score=78).
    İstəsən buraya over/under, btts də qatıb daha mürəkkəb bal sistemi qura bilərik.
    """
    outcomes = prediction["1x2"]
    return max(outcomes["home_win"], outcomes["draw"], outcomes["away_win"])


def collect_all_predictions(client: FootballDataClient) -> list:
    """Bütün izlənilən liqalardakı bugünkü matçları analiz edib proqnoz siyahısı qaytarır"""
    all_predictions = []

    for league_key in LEAGUES_TO_TRACK:
        league_code = LEAGUE_CODES[league_key]
        print(f"--- {league_key} ({league_code}) yoxlanılır ---")

        try:
            matches = client.get_todays_matches(league_code)
        except Exception as e:
            print(f"Xəta ({league_key}): {e}")
            continue

        if not matches:
            print("Bugün matç yoxdur.")
            continue

        for m in matches:
            home_id, home_name = m["homeTeam"]["id"], m["homeTeam"]["name"]
            away_id, away_name = m["awayTeam"]["id"], m["awayTeam"]["name"]

            try:
                home_stats = client.build_team_stats(home_id, home_name)
                time.sleep(6)  # pulsuz tier: dəqiqədə 10 sorğu limiti
                away_stats = client.build_team_stats(away_id, away_name)
                time.sleep(6)
            except Exception as e:
                print(f"Statistika xətası ({home_name} vs {away_name}): {e}")
                continue

            prediction = predict_match(home_stats, away_stats)
            prediction["league"] = league_key
            prediction["confidence"] = confidence_score(prediction)
            all_predictions.append(prediction)

    return all_predictions


def run():
    client = FootballDataClient(FOOTBALL_DATA_API_KEY)

    all_predictions = collect_all_predictions(client)

    if not all_predictions:
        print("Heç bir matç tapılmadı, göndəriləcək şey yoxdur.")
        return

    # ən yüksək 'confidence'ə görə sırala, ilk TOP_N-i götür
    top_picks = sorted(all_predictions, key=lambda p: p["confidence"], reverse=True)[:TOP_N]

    message = format_daily_top_message(top_picks)
    print(message)

    sent = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
    if not sent:
        print("⚠️ Telegram-a göndərilmədi.")
    else:
        print(f"✅ {len(top_picks)} seçim Telegram-a göndərildi.")


if __name__ == "__main__":
    run()
