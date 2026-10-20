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

## ۷) احراز هویت وبهوک (ورک‌فلوهای ۰۴ و ۰۵)

وبهوک یک آدرس عمومی است: هر کسی که مسیر را بداند می‌تواند برای آن درخواست بفرستد. برای همین،
گره‌های وبهوک این بسته با `authentication: basicAuth` و یک ارجاع به Credential از پیش تعیین‌شده
(`Webhook Basic Auth (n8n Persian Pack)`) عرضه می‌شوند.

بعد از ایمپورت:

1. در n8n: **Credentials → New → Basic Auth**
2. نام را دقیقاً بگذارید: `Webhook Basic Auth (n8n Persian Pack)`
3. یک نام کاربری و رمز تصادفی و طولانی بسازید (مثلاً ۳۲ کاراکتر)
4. در گرهٔ وبهوک، همین Credential را انتخاب کنید (اگر n8n هشدار «credential not found» می‌دهد،
   یعنی مرحلهٔ ۲ انجام نشده است)
5. آدرس وبهوک را با همان نام کاربری/رمز به فرم سایت بدهید:

```bash
curl -u 'webhook-user:long-random-password' \
  -H 'Content-Type: application/json' \
  -d '{"name":"علی","phone":"09121234567"}' \
  https://n8n.example.com/webhook/lead
```

> مسیر وبهوک (`lead` و `invoice-scan`) داخل JSON عمومی است؛ «مخفی بودن مسیر» کنترل امنیتی
> حساب نمی‌شود. احراز هویت Basic Auth روی TLS انجام می‌شود، پس حتماً HTTPS داشته باشید.

---

## چک‌لیست امنیتی

- [ ] `N8N_ENCRYPTION_KEY` تصادفی و طولانی است
- [ ] `.env` در `.gitignore` هست (پیش‌فرض همین است)
- [ ] پنل n8n روی اینترنت با Basic Auth یا IP allowlist محافظت شده و پشت HTTPS است
- [ ] پورت ۵۶۷۸ روی `0.0.0.0` باز نیست (در `docker-compose.yml` روی loopback بسته شده)
- [ ] برای وبهوک‌های ۰۴ و ۰۵ حتماً Credential احراز هویت ساخته و وصل شده است
- [ ] کلید ووکامرس فقط Read/Write است، نه Admin
- [ ] توکن‌ها را هر چند ماه یک‌بار بچرخانید
- [ ] اجراهای ذخیره‌شدهٔ n8n (که ممکن است دادهٔ مشتری داشته باشند) پاک‌سازی/محدود شده‌اند
