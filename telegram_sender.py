"""
Hesablanmış proqnozları Telegram bota göndərir.

Quraşdırma:
1. @BotFather-ə yaz -> /newbot -> bot adı ver -> token alacaqsan
2. Botunla söhbətə başla (və ya kanala əlavə et), sonra chat_id tap:
   https://api.telegram.org/bot<TOKEN>/getUpdates
   (bir mesaj göndərdikdən sonra bu linkdə "chat":{"id": ...} görəcəksən)
"""

import requests


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=15)
    return resp.status_code == 200


def format_prediction_message(prediction: dict) -> str:
    """Proqnoz sözlüyünü Telegram üçün oxunaqlı mesaja çevirir"""
    p = prediction
    lines = [
        f"⚽ <b>{p['match']}</b>",
        f"📊 Gözlənilən qol: {p['expected_goals']['home']} - {p['expected_goals']['away']}",
        f"🎯 Ən ehtimallı skor: {p['most_likely_score']}",
        "",
        "<b>1X2:</b>",
        f"  Ev sahibi: {p['1x2']['home_win']}%",
        f"  Heç-heçə: {p['1x2']['draw']}%",
        f"  Qonaq: {p['1x2']['away_win']}%",
        "",
        f"<b>Over/Under 2.5:</b> {p['over_under_2_5']['over']}% / {p['over_under_2_5']['under']}%",
        f"<b>BTTS:</b> Bəli {p['btts']['yes']}% / Xeyr {p['btts']['no']}%",
    ]
    return "\n".join(lines)


def _pick_label(prediction: dict) -> str:
    """1X2 içindən ən yüksək faizli tərəfin adını qaytarır (mesajda göstərmək üçün)"""
    o = prediction["1x2"]
    best = max(o, key=o.get)
    labels = {"home_win": "Ev sahibi qalib", "draw": "Heç-heçə", "away_win": "Qonaq qalib"}
    return f"{labels[best]} ({o[best]}%)"


def format_daily_top_message(top_picks: list) -> str:
    """
    Günün ən yüksək ehtimallı N matçını tək mesajda formatlaşdırır.
    Başlıqda bilərəkdən 'zəmanətli deyil' xəbərdarlığı var - bu vacibdir,
    silmə.
    """
    lines = [
        f"📅 <b>Günün Top {len(top_picks)} Seçimi</b>",
        "<i>(Statistik modelin ən yüksək ehtimal verdiyi matçlar — zəmanət deyil, ehtimaldır)</i>",
        "",
    ]

    for i, p in enumerate(top_picks, start=1):
        lines.append(f"<b>{i}. {p['match']}</b> [{p.get('league', '')}]")
        lines.append(f"   👉 {_pick_label(p)}")
        lines.append(f"   Gözlənilən qol: {p['expected_goals']['home']}-{p['expected_goals']['away']} | Ən ehtimallı skor: {p['most_likely_score']}")
        lines.append(f"   O/U 2.5: {p['over_under_2_5']['over']}%/{p['over_under_2_5']['under']}% | BTTS: {p['btts']['yes']}%/{p['btts']['no']}%")
        lines.append("")

    lines.append("⚠️ Heç bir proqnoz 100% deyil. Məsuliyyətli oyna.")
    return "\n".join(lines)
