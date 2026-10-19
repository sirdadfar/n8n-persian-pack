# ساخت Credentialها

هر ورک‌فلو به چند Credential نیاز دارد. این‌ها **در ریپو ذخیره نمی‌شوند** و باید در پنل n8n ساخته شوند (`Credentials → New`).

---

## ۱) ووکامرس (HTTP Basic Auth)

ورک‌فلوهای ۰۲ و ۰۳ از REST API ووکامرس استفاده می‌کنند.

1. در وردپرس: **WooCommerce → Settings → Advanced → REST API → Add key**
2. دسترسی را روی **Read/Write** بگذارید
3. `Consumer key` و `Consumer secret` را کپی کنید
4. در n8n یک Credential از نوع **Basic Auth** بسازید:
   - Username: `Consumer key` (با `ck_` شروع می‌شود)
   - Password: `Consumer secret` (با `cs_` شروع می‌شود)

> اگر ووکامرس روی HTTP (بدون SSL) است، بعضی هاست‌ها کلید را رد می‌کنند. حتماً HTTPS داشته باشید.

---

## ۲) تلگرام

1. در تلگرام به [@BotFather](https://t.me/BotFather) پیام بدهید: `/newbot`
2. توکن را کپی کنید (`123456:ABC-DEF...`)
3. ربات را به چت/گروه موردنظر اضافه کنید و یک پیام بفرستید
4. شناسهٔ چت را بگیرید:
   - چت شخصی: به [@userinfobot](https://t.me/userinfobot) پیام بدهید
   - گروه: ربات را ادمین کنید و `https://api.telegram.org/bot<TOKEN>/getUpdates` را باز کنید

در n8n: **Credentials → New → Telegram API** و توکن را وارد کنید. شناسهٔ چت را در متغیر `ADMIN_TELEGRAM_CHAT_ID` بگذارید.

---

## ۳) کاوه‌نگار (پیامک)

1. در [kavenegar.com](https://kavenegar.com) وارد شوید → **API Key** را از پنل بردارید
2. در `.env` مقدار `KAVENEGAR_API_KEY` را بگذارید

ورک‌فلوها از HTTP Request استفاده می‌کنند، پس Credential جدا لازم نیست؛ کلید از `$env` خوانده می‌شود.

> برای پنل‌های دیگر (فراز اس‌ام‌اس، ملی‌پیامک، SMS.ir) فقط آدرس و نام پارامترها را در گرهٔ «پیامک» عوض کنید.

---

## ۴) Postgres (ورک‌فلوی فاکتور)

جدول موردنیاز:

```sql
CREATE TABLE invoices (
  id           SERIAL PRIMARY KEY,
  invoice_no   TEXT,
  amount       BIGINT,
  issued_at    TEXT,
  needs_review BOOLEAN DEFAULT FALSE,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

در n8n: **Credentials → New → Postgres** و Host / Database / User / Password را وارد کنید.

---

## ۵) CRM (ورک‌فلوی لید)

ورک‌فلو با یک API فرضی صحبت می‌کند:

```
POST {CRM_API_URL}/api/leads
Authorization: Bearer {CRM_API_TOKEN}
```

اگر از CRM آماده استفاده می‌کنید (مثل دیدار، پیام‌گستر، HubSpot)، فقط آدرس و ساختار بدنه را در گرهٔ «ثبت در CRM» عوض کنید. اگر CRM ندارید، یک Google Sheet هم کافی است — گرهٔ Postgres/HTTP را با `Google Sheets → Append Row` جایگزین کنید.

---

## ۶) OCR فاکتور

پیش‌فرض `api.ocr.space` است (کلید رایگان دارد و فارسی را پشتیبانی می‌کند). برای دقت بیشتر روی فاکتورهای ایرانی، سرویس‌های محلی مثل «کاوه‌نگار OCR» یا مدل‌های خودمیزبان را جایگزین کنید؛ فقط خروجی باید فیلد `ParsedText` یا `text` داشته باشد تا گرهٔ بعدی بتواند بخواند.

---

## چک‌لیست امنیتی

- [ ] `N8N_ENCRYPTION_KEY` تصادفی و طولانی است
- [ ] `.env` در `.gitignore` هست (پیش‌فرض همین است)
- [ ] پنل n8n روی اینترنت با Basic Auth یا IP allowlist محافظت شده
- [ ] کلید ووکامرس فقط Read/Write است، نه Admin
- [ ] توکن‌ها را هر چند ماه یک‌بار بچرخانید
