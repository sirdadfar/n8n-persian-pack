# نصب و راه‌اندازی

## پیش‌نیاز

- n8n نسخهٔ **1.60 یا بالاتر** (ورک‌فلوها با `executionOrder: v1` ساخته شده‌اند)
- Node.js 18+ اگر بدون داکر نصب می‌کنید
- دسترسی به سرویس‌هایی که می‌خواهید وصل کنید (ووکامرس، پیامک، ...)

---

## روش ۱ — داکر (پیشنهادی برای سرور)

```bash
git clone https://github.com/sirdadfar/n8n-persian-pack.git
cd n8n-persian-pack
cp env.example .env
# .env را ویرایش کنید
docker compose up -d
docker compose logs -f n8n
```

بعد از بالا آمدن، `http://SERVER_IP:5678` را باز کنید و کاربر مدیر بسازید.

> روی سرور واقعی حتماً `N8N_ENCRYPTION_KEY` را یک رشتهٔ طولانی و تصادفی بگذارید. اگر این کلید عوض شود، همهٔ Credentialهای ذخیره‌شده غیرقابل خواندن می‌شوند.

> اگر پشت Nginx یا Caddy هستید، `WEBHOOK_URL` را برابر دامنهٔ عمومی بگذارید (مثلاً `https://automation.example.com/`) وگرنه وب‌هوک‌ها آدرس داخلی می‌گیرند.

---

## روش ۲ — نصب سراسری با npm

```bash
npm install -g n8n
export WOO_BASE_URL=https://shop.example.com
export ADMIN_TELEGRAM_CHAT_ID=123456789
# بقیهٔ متغیرها...
n8n start
```

در ویندوز، متغیرها را با `set` یا از طریق `System Properties → Environment Variables` تنظیم کنید.

---

## ایمپورت ورک‌فلوها

### از پنل

1. **Workflows → Add workflow → Import from File**
2. فایل JSON را انتخاب کنید
3. ذخیره کنید

### از خط فرمان (برای همه با هم)

```bash
for f in workflows/*.json; do
  n8n import:workflow --input="$f"
done
```

اگر با داکر اجرا می‌کنید:

```bash
docker compose exec n8n sh -c 'for f in /workflows/*.json; do n8n import:workflow --input="$f"; done'
```

---

## بعد از ایمپورت

1. **Credentials → New** برای هر سرویس یک Credential بسازید → [راهنما](credentials-fa.md)
2. در هر ورک‌فلو، روی گره‌های نارنجی (Credential ندارند) کلیک کنید و Credential مربوطه را انتخاب کنید
3. متغیرهای `$env` را در `.env` پر کنید (یا در تنظیمات سرور)
4. با دکمهٔ **Execute workflow** و یک دادهٔ تست، یک‌بار دستی اجرا کنید
5. اگر درست بود، ورک‌فلو را **Active** کنید

---

## عیب‌یابی

| نشانه | علت رایج | راه‌حل |
|---|---|---|
| `$env.X is not defined` | متغیر در محیط n8n نیست | `.env` را اصلاح و کانتینر را ری‌استارت کنید |
| وب‌هوک ۴۰۴ می‌دهد | `WEBHOOK_URL` اشتباه است یا ورک‌فلو Active نیست | `WEBHOOK_URL` را درست کنید و ورک‌فلو را فعال کنید |
| تلگرام `chat not found` | `chat_id` اشتباه یا ربات در گروه نیست | ربات را به گروه اضافه کنید و با `getUpdates` شناسه را بگیرید |
| پیامک نمی‌رود | شماره بدون `0` ابتدایی است یا اعتبار پنل تمام شده | `receptor` باید مثل `09121234567` باشد |
| ووکامرس ۴۰۱ می‌دهد | کلید REST با دسترسی Read/Write ساخته نشده | کلید را با دسترسی Write دوباره بسازید |

### دیدن لاگ اجرا

```bash
docker compose logs -f n8n
```

برای بررسی دقیق‌تر، در پنل **Executions** را باز کنید؛ ورودی و خروجی هر گره ذخیره می‌شود.
