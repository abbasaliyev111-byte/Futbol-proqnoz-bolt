"""
Futbol Proqnoz Telegram Botu
-----------------------------
Statistik (Poisson modeli) əsasında futbol matçları üçün proqnoz verir.
Mərc qəbul ETMİR — yalnız məlumat/proqnoz məqsədlidir.

Məlumat mənbəyi: football-data.org (pulsuz tier)
Telegram kitabxanası: python-telegram-bot v21+

Quraşdırma üçün README.md faylına bax.
"""

import os
import math
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
FOOTBALL_API_BASE = "https://api.football-data.org/v4"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Pulsuz tier-də mövcud olan əsas liqalar (football-data.org kodları)
LEAGUES = {
    "PL": "Premier Liqa (İngiltərə)",
    "PD": "La Liga (İspaniya)",
    "SA": "Serie A (İtaliya)",
    "BL1": "Bundesliga (Almaniya)",
    "FL1": "Ligue 1 (Fransa)",
    "CL": "Çempionlar Liqası",
    "DED": "Eredivisie (Niderland)",
    "PPL": "Primeira Liga (Portuqaliya)",
}

HEADERS = {"X-Auth-Token": FOOTBALL_API_KEY} if FOOTBALL_API_KEY else {}

# ---------- Keş (cache) ----------
# Bot arxa planda özü liqa matçlarını və proqnozları əvvəlcədən hesablayıb
# burada saxlayır. İstifadəçi /matches və ya /predict yazanda, əgər keşdə
# təzə məlumat varsa, birbaşa ordan (ani) cavab verilir — yenidən API-yə
# sorğu getmir. Bu, həm sürəti artırır, həm də pulsuz API-nin sorğu
# limitinə çatmamağa kömək edir.
CACHE = {
    "matches": {},       # {league_code: {"data": [...], "updated_at": datetime}}
    "predictions": {},   # {match_id: {"data": {...}, "updated_at": datetime}}
}
CACHE_TTL_HOURS = 6  # keş nə qədər müddət "təzə" sayılsın


def api_get(endpoint: str, params: dict = None):
    """football-data.org API-yə sorğu göndərir (pulsuz tier: dəqiqədə 10 sorğu)."""
    try:
        resp = requests.get(
            f"{FOOTBALL_API_BASE}{endpoint}", headers=HEADERS, params=params, timeout=15
        )
        if resp.status_code == 429:
            logger.warning("API rate limit aşıldı, bir az gözləyin.")
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"API xətası: {e}")
        return None


# ---------- Statistik hesablama (Poisson modeli) ----------

def poisson_pmf(k: int, lam: float) -> float:
    """Poisson ehtimal kütlə funksiyası: verilmiş orta (lam) üçün tam olaraq k qol ehtimalı."""
    if lam <= 0:
        lam = 0.1
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)


def get_team_recent_stats(team_id: int, n_matches: int = 10):
    """Komandanın son N matçındakı orta atdığı/buraxdığı qol sayını hesablayır."""
    data = api_get(
        f"/teams/{team_id}/matches",
        params={"status": "FINISHED", "limit": n_matches},
    )
    if not data or "matches" not in data or not data["matches"]:
        return None

    matches = data["matches"][-n_matches:]
    scored, conceded = [], []

    for m in matches:
        home_id = m["homeTeam"]["id"]
        home_goals = m["score"]["fullTime"]["home"]
        away_goals = m["score"]["fullTime"]["away"]
        if home_goals is None or away_goals is None:
            continue
        if home_id == team_id:
            scored.append(home_goals)
            conceded.append(away_goals)
        else:
            scored.append(away_goals)
            conceded.append(home_goals)

    if not scored:
        return None

    return {
        "avg_scored": sum(scored) / len(scored),
        "avg_conceded": sum(conceded) / len(conceded),
        "matches_used": len(scored),
    }


def predict_match(home_team_id: int, away_team_id: int, home_name: str, away_name: str):
    """İki komandanın statistikasına əsasən Poisson modeli ilə nəticə ehtimallarını hesablayır."""
    home_stats = get_team_recent_stats(home_team_id)
    away_stats = get_team_recent_stats(away_team_id)

    if not home_stats or not away_stats:
        return None

    # Gözlənilən qol sayı: hücum gücü * müdafiə zəifliyi ortalaması
    lig_orta_qol = 1.35  # təxmini liqa ortalaması (ev/qonaq üçün)

    home_attack = home_stats["avg_scored"] / lig_orta_qol
    home_defense = home_stats["avg_conceded"] / lig_orta_qol
    away_attack = away_stats["avg_scored"] / lig_orta_qol
    away_defense = away_stats["avg_conceded"] / lig_orta_qol

    exp_home_goals = home_attack * away_defense * lig_orta_qol
    exp_away_goals = away_attack * home_defense * lig_orta_qol

    max_goals = 6
    home_win = draw = away_win = 0.0
    score_probs = {}

    for h in range(max_goals):
        for a in range(max_goals):
            p = poisson_pmf(h, exp_home_goals) * poisson_pmf(a, exp_away_goals)
            score_probs[(h, a)] = p
            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p

    most_likely_score = max(score_probs, key=score_probs.get)

    total = home_win + draw + away_win
    return {
        "home_team": home_name,
        "away_team": away_name,
        "home_win_pct": round(home_win / total * 100, 1),
        "draw_pct": round(draw / total * 100, 1),
        "away_win_pct": round(away_win / total * 100, 1),
        "predicted_score": f"{most_likely_score[0]}-{most_likely_score[1]}",
        "exp_home_goals": round(exp_home_goals, 2),
        "exp_away_goals": round(exp_away_goals, 2),
        "sample_size": f"{home_stats['matches_used']} / {away_stats['matches_used']} son matç",
    }


MATCH_SEARCH_DAYS = 45  # fəsil arası dövrlərdə də yaxın matçları tapmaq üçün geniş pəncərə


def fetch_league_matches(code: str):
    """Verilmiş liqa kodunun yaxın MATCH_SEARCH_DAYS gündəki planlaşdırılan matçlarını API-dən çəkir."""
    date_from = datetime.utcnow().strftime("%Y-%m-%d")
    date_to = (datetime.utcnow() + timedelta(days=MATCH_SEARCH_DAYS)).strftime("%Y-%m-%d")

    data = api_get(
        f"/competitions/{code}/matches",
        params={"dateFrom": date_from, "dateTo": date_to, "status": "SCHEDULED"},
    )
    if not data or not data.get("matches"):
        return []
    return data["matches"]


def is_cache_fresh(entry: dict) -> bool:
    if not entry or "updated_at" not in entry:
        return False
    age = datetime.now(timezone.utc) - entry["updated_at"]
    return age < timedelta(hours=CACHE_TTL_HOURS)


async def refresh_cache_job(context: ContextTypes.DEFAULT_TYPE):
    """Arxa planda dövri işləyən tapşırıq: bütün liqaların matçlarını və
    yaxın matçların proqnozlarını əvvəlcədən hesablayıb keşə yazır."""
    logger.info("Keş yeniləməsi başladı...")

    for code in LEAGUES:
        try:
            match_list = await asyncio.to_thread(fetch_league_matches, code)
            CACHE["matches"][code] = {
                "data": match_list,
                "updated_at": datetime.now(timezone.utc),
            }
            logger.info(f"{code}: {len(match_list)} matç keşləndi.")

            # Hər liqadan ilk bir neçə matçın proqnozunu da əvvəlcədən hesablayaq
            for m in match_list[:3]:
                match_id = m["id"]
                home_team = m["homeTeam"]
                away_team = m["awayTeam"]
                result = await asyncio.to_thread(
                    predict_match,
                    home_team["id"], away_team["id"],
                    home_team["name"], away_team["name"],
                )
                if result:
                    CACHE["predictions"][match_id] = {
                        "data": result,
                        "updated_at": datetime.now(timezone.utc),
                    }
                await asyncio.sleep(2)  # API limitinə hörmət — sorğular arası kiçik fasilə

            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"{code} üçün keş yeniləmə xətası: {e}")

    logger.info("Keş yeniləməsi bitdi.")


# ---------- Telegram bot əmrləri ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚽ *Futbol Proqnoz Botu*\n\n"
        "Bu bot statistik model (Poisson) əsasında futbol matçları üçün "
        "*proqnoz ehtimalları* göstərir. Bu, mərc qəbul edən bukmeker botu DEYİL "
        "— yalnız məlumat məqsədi daşıyır.\n\n"
        "Bot arxa planda özü matçları və proqnozları əvvəlcədən hazırlayır ⚡ "
        "— bəzən ani cavab görəcəksiniz.\n\n"
        "Əmrlər:\n"
        "/leagues — mövcud liqaların siyahısı\n"
        "/matches <kod> — liqadakı yaxın matçlar (məs: /matches PL)\n"
        "/predict <matchId> — konkret matç üçün proqnoz\n\n"
        "⚠️ Proqnozlar statistik təxminlərdir, nəticə zəmanəti vermir."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def leagues(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📋 *Mövcud liqalar:*\n\n" + "\n".join(
        f"`{code}` — {name}" for code, name in LEAGUES.items()
    )
    text += "\n\nİstifadə: /matches PL"
    await update.message.reply_text(text, parse_mode="Markdown")


async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("İstifadə: /matches PL (liqa kodu üçün /leagues bax)")
        return

    code = context.args[0].upper()
    if code not in LEAGUES:
        await update.message.reply_text(f"Naməlum liqa kodu. /leagues əmrinə bax.")
        return

    cache_entry = CACHE["matches"].get(code)
    if is_cache_fresh(cache_entry):
        match_list = cache_entry["data"]
        source_note = "⚡ (əvvəlcədən hazırlanmış məlumat)"
    else:
        match_list = fetch_league_matches(code)
        CACHE["matches"][code] = {"data": match_list, "updated_at": datetime.now(timezone.utc)}
        source_note = "🌐 (canlı sorğu)"

    if not match_list:
        await update.message.reply_text(
            f"Bu liqada yaxın {MATCH_SEARCH_DAYS} gündə planlaşdırılan matç tapılmadı "
            "(çox güman ki, fəsil hələ başlamayıb)."
        )
        return

    lines = [f"📅 *{LEAGUES[code]} — yaxın matçlar* {source_note}\n"]
    for m in match_list[:10]:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        date = m["utcDate"][:16].replace("T", " ")
        lines.append(f"`{m['id']}` — {home} vs {away}  ({date} UTC)")

    lines.append("\nProqnoz üçün: /predict <matchId>")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("İstifadə: /predict <matchId>  (/matches ilə ID tapın)")
        return

    try:
        match_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Match ID rəqəm olmalıdır.")
        return

    cache_entry = CACHE["predictions"].get(match_id)
    if is_cache_fresh(cache_entry):
        result = cache_entry["data"]
        source_note = "⚡ (əvvəlcədən hazırlanmış məlumat)"
    else:
        await update.message.reply_text("🔄 Hesablanır, bir az gözləyin...")

        match_data = api_get(f"/matches/{match_id}")
        if not match_data:
            await update.message.reply_text("Matç tapılmadı və ya API xətası.")
            return

        home_team = match_data["homeTeam"]
        away_team = match_data["awayTeam"]

        result = predict_match(
            home_team["id"], away_team["id"], home_team["name"], away_team["name"]
        )
        if result:
            CACHE["predictions"][match_id] = {"data": result, "updated_at": datetime.now(timezone.utc)}
        source_note = "🌐 (canlı hesablama)"

    if not result:
        await update.message.reply_text(
            "📊 Hələ proqnoz vermək mümkün deyil.\n\n"
            "Bu, statistik modelin hər komandanın *bu fəsildə oynadığı son matçlara* "
            "əsaslanmasından qaynaqlanır. Fəsil hələ başlamayıb (və ya komandalar "
            "kifayət qədər matç oynamayıb), ona görə hesablama üçün kifayət qədər "
            "məlumat yoxdur.\n\n"
            "⏳ Fəsil başlayıb hər komanda bir neçə (təxminən 3-4) matç oynadıqdan "
            "sonra proqnozlar avtomatik işləməyə başlayacaq — heç nə etmək lazım deyil, "
            "sadəcə bir az sonra yenidən sınayın.",
            parse_mode="Markdown",
        )
        return

    text = (
        f"⚽ *{result['home_team']} vs {result['away_team']}* {source_note}\n\n"
        f"🏠 Ev sahibi qələbəsi: *{result['home_win_pct']}%*\n"
        f"🤝 Heç-heçə: *{result['draw_pct']}%*\n"
        f"✈️ Qonaq qələbəsi: *{result['away_win_pct']}%*\n\n"
        f"📊 Ən ehtimallı hesab: *{result['predicted_score']}*\n"
        f"   (gözlənilən qol: {result['exp_home_goals']} — {result['exp_away_goals']})\n\n"
        f"_Əsas götürülən: {result['sample_size']}_\n\n"
        f"⚠️ Bu, statistik təxmindir — real nəticəni zəmanət etmir."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def main():
    if not BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN mühit dəyişəni tapılmadı. .env faylına bax.")
    if not FOOTBALL_API_KEY:
        raise SystemExit("FOOTBALL_DATA_API_KEY mühit dəyişəni tapılmadı. .env faylına bax.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leagues", leagues))
    app.add_handler(CommandHandler("matches", matches))
    app.add_handler(CommandHandler("predict", predict))

    # Bot işə düşəndən 15 saniyə sonra ilk dəfə, sonra hər 6 saatdan bir
    # arxa planda özü matçları və proqnozları əvvəlcədən hesablayıb keşləyir.
    app.job_queue.run_repeating(refresh_cache_job, interval=timedelta(hours=CACHE_TTL_HOURS), first=15)

    logger.info("Bot işə düşür...")
    app.run_polling()


if __name__ == "__main__":
    main()
