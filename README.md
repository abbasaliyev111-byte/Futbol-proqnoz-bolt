# Futbol Proqnoz Telegram Botu

Statistik (Poisson modeli) əsasında futbol matçları üçün nəticə ehtimalları göstərən Telegram botu.

**Bu bot mərc qəbul etmir, pul əməliyyatı aparmır** — yalnız açıq statistik məlumat əsasında proqnoz göstərir. Tam leqaldır.

## Necə işləyir?

1. `football-data.org`-dan komandaların son matçlarındakı qol statistikası çəkilir
2. Hər komandanın hücum/müdafiə gücü hesablanır
3. Poisson ehtimal modeli ilə hər hesab kombinasiyasının (0-0, 1-0, 2-1 və s.) ehtimalı hesablanır
4. Ev qələbəsi / heç-heçə / qonaq qələbəsi faizləri və ən ehtimallı hesab göstərilir

## Quraşdırma addımları

### 1. Telegram Bot Token alın
- Telegram-da `@BotFather`-ə yazın
- `/newbot` əmrini göndərin, adını təyin edin
- Sizə verilən token-i saxlayın (məs: `123456:ABC-DEF...`)

### 2. Football-Data.org API açarı alın (pulsuz)
- https://www.football-data.org/client/register saytında qeydiyyatdan keçin
- Pulsuz plan: dəqiqədə 10 sorğu, 12 əsas liqaya çıxış (kifayət qədərdir)
- E-poçtunuza gələn API açarını saxlayın

### 3. Layihəni quraşdırın

```bash
cd football_predict_bot
python3 -m venv venv
source venv/bin/activate  # Windows-da: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Mühit dəyişənlərini təyin edin

`.env.example` faylını `.env` adı ilə kopyalayın və öz məlumatlarınızı daxil edin:

```bash
cp .env.example .env
```

`.env` faylını redaktə edin:
```
TELEGRAM_BOT_TOKEN=sizin_token
FOOTBALL_DATA_API_KEY=sizin_api_acar
```

### 5. Botu işə salın

```bash
python3 bot.py
```

Bot işə düşəcək və Telegram-da botunuza yazaraq test edə bilərsiniz.

## Bot əmrləri

| Əmr | Təsvir |
|---|---|
| `/start` | Salamlama və məlumat |
| `/leagues` | Mövcud liqaların siyahısı |
| `/matches PL` | Premier Liqada yaxın 7 gündəki matçlar |
| `/predict 12345` | Verilmiş match ID üçün proqnoz |

## Serverdə davamlı işlətmək

Bot açıq terminalda işləyir — kompüteri bağlasanız dayanar. Davamlı işləməsi üçün:

- **VPS (ucuz seçim):** DigitalOcean, Hetzner və ya oxşar serverlərdə `systemd` service və ya `screen`/`tmux` ilə arxa planda saxlayın
- **Docker:** İstəsəniz Dockerfile də hazırlaya bilərəm
- **Pulsuz hosting seçimləri:** Railway.app, Render.com kimi platformalar pulsuz/ucuz tier təklif edir

## Məhdudiyyətlər

- Pulsuz API tier-i dəqiqədə 10 sorğu ilə məhdudlaşır — çox istifadəçi eyni anda çox sorğu göndərərsə gecikmə ola bilər
- Model sadədir (yalnız son matçların qol ortalaması) — real bukmeker modelləri (xG, zədələr, motivasiya və s. daxil edən) daha mürəkkəbdir
- Bu, **maliyyə məsləhəti deyil** — istifadəçilərinizə bunu bildirməyi tövsiyə edirik

## Genişləndirmə ideyaları (istəsəniz kömək edə bilərəm)

- Ev/qonaq matçlarını ayrıca hesablamaq (dəqiqlik artırır)
- xG (expected goals) məlumatı əlavə etmək
- Zədəli oyunçu məlumatını nəzərə almaq
- Gündəlik avtomatik proqnoz siyahısı göndərmək (scheduled job)
- Nəticələri verilənlər bazasında saxlayıb modelin dəqiqliyini izləmək
