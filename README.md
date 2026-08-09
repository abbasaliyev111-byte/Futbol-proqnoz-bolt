# Futbol Proqnoz Botu (Poisson Modeli)

## Bu nədir?
Komandaların son matçlardakı qol statistikasına əsasən Poisson paylanması ilə
1X2, Over/Under 2.5 və BTTS ehtimallarını hesablayıb Telegram-a göndərən bot.

**Dürüst xəbərdarlıq:** Bu model elmi əsaslıdır, amma futbol nəticələrini
90% dəqiqliklə (və ya heç 70-80%) proqnozlaşdıra bilməz. 1X2 bazarında
real dünyada bu tip modellər adətən 50-55% arasında "tutur". Bunu əyləncə,
analiz və öz mərc qərarlarını daha məlumatlı vermək üçün istifadə et —
"zəmanətli qazanc aləti" kimi yox.

## Fayllar
- `predictor.py` — əsas Poisson riyaziyyatı (data mənbəyindən asılı deyil)
- `data_fetcher.py` — football-data.org API-dən real komanda statistikası çəkir
- `telegram_sender.py` — nəticələri Telegram bota göndərir
- `daily_run.py` — hər şeyi birləşdirən əsas script (bunu cron ilə işə salacaqsan)
- `config.example.py` — açarlarını yazacağın nümunə fayl

## Quraşdırma addımları

### 1. Python paketlərini quraşdır
```bash
pip install requests --break-system-packages
```

### 2. football-data.org açarı al (pulsuz)
https://www.football-data.org/client/register — qeydiyyatdan keç, emailinə
API açarı gələcək. Pulsuz tier: dəqiqədə 10 sorğu, əsas Avropa liqaları daxildir.

### 3. Telegram bot yarat
1. Telegram-da @BotFather-ə yaz
2. `/newbot` yaz, bot üçün ad seç
3. Sənə verəcəyi tokeni saxla (məs: `123456:ABC-DEF...`)
4. Öz botunla söhbətə başla (`/start` yaz və ya bir mesaj göndər)
5. Bu linki brauzerdə aç (TOKEN-i öz tokeninlə əvəz et):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. JSON cavabında `"chat":{"id": 123456789}` — bu rəqəm sənin chat_id-din

### 4. Config faylını doldur
```bash
cp config.example.py config.py
```
Sonra `config.py`-ni aç və 3 açarı + izləmək istədiyin liqaları yaz.

### 5. Sınaq üçün əl ilə işə sal
```bash
python3 daily_run.py
```
Telegram-a mesajlar gəlməlidir.

### 6. Avtomatlaşdırma (hər gün müəyyən saatda)

**Linux/Mac — cron ilə:**
```bash
crontab -e
```
Bu sətri əlavə et (məs. hər gün saat 09:00-da işə salmaq üçün):
```
0 9 * * * cd /path/to/football-bot && /usr/bin/python3 daily_run.py >> log.txt 2>&1
```

**Windows — Task Scheduler ilə:**
- Task Scheduler aç -> "Create Basic Task" -> gündəlik, saat seç
- Action: `python3.exe` -> Arguments: `daily_run.py` -> Start in: bot qovluğu

**Alternativ (server lazım deyil) — GitHub Actions:**
Əgər öz kompüterini daim açıq saxlamaq istəmirsənsə, `config.py`-dəki
məxfi açarları GitHub repo-nun "Secrets" bölməsinə yazıb, GitHub Actions
ilə cron-scheduled workflow qura bilərik — bunu da istəsən qururuq.

## Modeli inkişaf etdirmək
- Hazırkı model sadəcə "son 5 matç"a baxır — istəsən bunu ev/qonaq ayrı-ayrı
  (yalnız ev matçları / yalnız qonaq matçları) hesablamağa dəyişə bilərik,
  bu adətən dəqiqliyi bir az artırır
- Zədəli/cəzalı oyunçular, head-to-head tarixçə kimi əlavə faktorlar
  əl ilə əlavə edilə bilər, amma bunlar üçün əlavə API mənbələri lazımdır
