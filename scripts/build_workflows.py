#!/usr/bin/env python3
"""
سازندهٔ ورک‌فلوهای بستهٔ n8n فارسی.
هر ورک‌فلو از یک ساختار کوتاه ساخته می‌شود تا شناسه‌ها یکتا و JSON تضمین‌شده معتبر باشد.
اجرا:  python3 scripts/build_workflows.py
خروجی: workflows/*.json
"""
import json
import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "workflows")

# ---------------------------------------------------------------- helpers ----

def node(name, ntype, version, params, x, y, **extra):
    n = {
        "parameters": params,
        "id": str(uuid.uuid4()),
        "name": name,
        "type": ntype,
        "typeVersion": version,
        "position": [x, y],
    }
    n.update(extra)
    return n


def chain(names):
    """زنجیرهٔ ساده: هر گره به گره بعدی وصل می‌شود (خروجی اصلی)."""
    conns = {}
    for i in range(len(names) - 1):
        conns[names[i]] = {"main": [[{"node": names[i + 1], "type": "main", "index": 0}]]}
    return conns


def multi(conns_list):
    """ادغام چند دیکشنری اتصال."""
    out = {}
    for c in conns_list:
        for k, v in c.items():
            out.setdefault(k, {"main": []})
            out[k]["main"].extend(v["main"])
    return out


def workflow(name, nodes, connections, tags=None, **settings):
    wf = {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "active": False,
        "settings": {"executionOrder": "v1", **settings},
        "versionId": str(uuid.uuid4()),
        "meta": {"templateCredsSetupCompleted": False},
        "tags": tags or [],
    }
    return wf


def write(filename, wf):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  ✓ {filename}  ({len(wf['nodes'])} nodes)")


# ------------------------------------------------------------- workflows ----

def wf1_order_to_accounting():
    """سفارش جدید ووکامرس → ثبت فاکتور در حسابداری → پیامک تأیید → هشدار تلگرام."""
    n_trigger = node(
        "سفارش جدید ووکامرس", "n8n-nodes-base.wooCommerceTrigger", 1,
        {"event": "order.created", "options": {}},
        -780, 300,
        webhookId=str(uuid.uuid4()),
    )
    n_prepare = node(
        "آماده‌سازی دادهٔ سفارش", "n8n-nodes-base.set", 3.4,
        {
            "mode": "manual",
            "includeOtherFields": False,
            "assignments": {
                "assignments": [
                    {"id": "1", "name": "order_id", "value": "={{ $json.id }}", "type": "number"},
                    {"id": "2", "name": "customer", "value": "={{ $json.billing.first_name }} {{ $json.billing.last_name }}", "type": "string"},
                    {"id": "3", "name": "mobile", "value": "={{ $json.billing.phone }}", "type": "string"},
                    {"id": "4", "name": "total", "value": "={{ $json.total }}", "type": "string"},
                    {"id": "5", "name": "items", "value": "={{ $json.line_items.map(i => i.name + ' x' + i.quantity).join(' | ') }}", "type": "string"},
                ]
            },
            "options": {},
        },
        -560, 300,
    )
    n_invoice = node(
        "ثبت فاکتور در حسابداری", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "POST",
            "url": "={{ $env.ACCOUNTING_API_URL }}/api/v1/invoices",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": "=Bearer {{ $env.ACCOUNTING_API_TOKEN }}"},
                {"name": "Content-Type", "value": "application/json"},
            ]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ external_id: $json.order_id, customer_name: $json.customer, mobile: $json.mobile, description: $json.items, amount: Number($json.total), type: 'sale' }) }}",
            "options": {"response": {"response": {"neverError": True, "fullResponse": True}}},
        },
        -340, 300,
    )
    n_check = node(
        "فاکتور ثبت شد؟", "n8n-nodes-base.if", 2,
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                "conditions": [{
                    "id": "c1",
                    "leftValue": "={{ $json.statusCode }}",
                    "rightValue": 201,
                    "operator": {"type": "number", "operation": "equals"},
                }],
                "combinator": "and",
            },
            "options": {},
        },
        -120, 300,
    )
    n_sms = node(
        "پیامک تأیید به مشتری", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "GET",
            "url": "={{ $env.KAVENEGAR_BASE_URL || 'https://api.kavenegar.com' }}/v1/{{ $env.KAVENEGAR_API_KEY }}/sms/send.json",
            "sendQuery": True,
            "queryParameters": {"parameters": [
                {"name": "receptor", "value": "={{ $('آماده‌سازی دادهٔ سفارش').item.json.mobile }}"},
                {"name": "message", "value": "=سفارش {{ $('آماده‌سازی دادهٔ سفارش').item.json.order_id }} ثبت شد. مبلغ: {{ $('آماده‌سازی دادهٔ سفارش').item.json.total }} تومان"},
            ]},
            "options": {"response": {"response": {"neverError": True}}},
        },
        100, 200,
    )
    n_alert = node(
        "هشدار به مدیر در تلگرام", "n8n-nodes-base.telegram", 1.2,
        {
            "chatId": "={{ $env.ADMIN_TELEGRAM_CHAT_ID }}",
            "text": "=⚠️ ثبت فاکتور سفارش {{ $('آماده‌سازی دادهٔ سفارش').item.json.order_id }} در حسابداری ناموفق بود.\nکد پاسخ: {{ $json.statusCode }}\nمشتری: {{ $('آماده‌سازی دادهٔ سفارش').item.json.customer }}",
            "additionalFields": {},
        },
        100, 420,
    )
    n_end = node("پایان", "n8n-nodes-base.noOp", 1, {}, 320, 300)

    conns = multi([
        chain(["سفارش جدید ووکامرس", "آماده‌سازی دادهٔ سفارش", "ثبت فاکتور در حسابداری", "فاکتور ثبت شد؟"]),
        {"فاکتور ثبت شد؟": {"main": [
            [{"node": "پیامک تأیید به مشتری", "type": "main", "index": 0}],
            [{"node": "هشدار به مدیر در تلگرام", "type": "main", "index": 0}],
        ]}},
        chain(["پیامک تأیید به مشتری", "پایان"]),
        chain(["هشدار به مدیر در تلگرام", "پایان"]),
    ])
    return workflow(
        "۰۱ — سفارش ووکامرس → حسابداری → پیامک",
        [n_trigger, n_prepare, n_invoice, n_check, n_sms, n_alert, n_end],
        conns,
        tags=["فروشگاه", "حسابداری", "پیامک"],
    )


def wf2_abandoned_cart():
    """یادآوری سبد خرید رها شده با پیامک، حداکثر دو بار."""
    n_sched = node(
        "هر ۳۰ دقیقه", "n8n-nodes-base.scheduleTrigger", 1.2,
        {"rule": {"interval": [{"field": "minutes", "minutesInterval": 30}]}},
        -760, 300,
    )
    n_fetch = node(
        "سفارش‌های در انتظار پرداخت", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "GET",
            "url": "={{ $env.WOO_BASE_URL }}/wp-json/wc/v3/orders",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpBasicAuth",
            "sendQuery": True,
            "queryParameters": {"parameters": [
                {"name": "status", "value": "pending"},
                {"name": "per_page", "value": "30"},
                {"name": "orderby", "value": "date"},
                {"name": "order", "value": "desc"},
            ]},
            "options": {},
        },
        -540, 300,
    )
    n_split = node(
        "دسته‌دسته", "n8n-nodes-base.splitInBatches", 3,
        {"batchSize": 5, "options": {}},
        -320, 300,
    )
    n_filter = node(
        "قابل یادآوری است؟", "n8n-nodes-base.if", 2,
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                "conditions": [
                    {"id": "c1", "leftValue": "={{ $json.billing.phone }}", "rightValue": "", "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}},
                    {"id": "c2", "leftValue": "={{ $json.meta_data.filter(m => m.key === 'reminder_sent').length }}", "rightValue": 1, "operator": {"type": "number", "operation": "smaller"}},
                ],
                "combinator": "and",
            },
            "options": {},
        },
        -100, 300,
    )
    n_sms = node(
        "پیامک یادآوری", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "GET",
            "url": "={{ $env.KAVENEGAR_BASE_URL || 'https://api.kavenegar.com' }}/v1/{{ $env.KAVENEGAR_API_KEY }}/sms/send.json",
            "sendQuery": True,
            "queryParameters": {"parameters": [
                {"name": "receptor", "value": "={{ $json.billing.phone }}"},
                {"name": "message", "value": "=سبد خرید شما آماده است 😊\n{{ ($json.line_items || []).map(i => i.name).slice(0,3).join('، ') }}\nبرای تکمیل: {{ $env.WOO_BASE_URL }}/checkout/"},
            ]},
            "options": {"response": {"response": {"neverError": True}}},
        },
        140, 220,
    )
    n_flag = node(
        "ثبت برچسب یادآوری", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "POST",
            "url": "={{ $env.WOO_BASE_URL }}/wp-json/wc/v3/orders/{{ $json.id }}",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpBasicAuth",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ meta_data: [ ...($json.meta_data || []).filter(m => m.key !== 'reminder_sent'), { key: 'reminder_sent', value: (($json.meta_data || []).find(m => m.key === 'reminder_sent')?.value || 0) + 1 } ] }) }}",
            "options": {"response": {"response": {"neverError": True}}},
        },
        360, 220,
    )
    n_wait = node("مکث", "n8n-nodes-base.wait", 1.1, {"amount": 2, "unit": "seconds"}, 580, 220)
    n_skip = node("رد شود", "n8n-nodes-base.noOp", 1, {}, 140, 420)

    conns = multi([
        chain(["هر ۳۰ دقیقه", "سفارش‌های در انتظار پرداخت", "دسته‌دسته"]),
        {"دسته‌دسته": {"main": [
            [{"node": "قابل یادآوری است؟", "type": "main", "index": 0}],
            [{"node": "دسته‌دسته", "type": "main", "index": 0}],
        ]}},
        {"قابل یادآوری است؟": {"main": [
            [{"node": "پیامک یادآوری", "type": "main", "index": 0}],
            [{"node": "رد شود", "type": "main", "index": 0}],
        ]}},
        {"پیامک یادآوری": {"main": [[{"node": "ثبت برچسب یادآوری", "type": "main", "index": 0}]]}},
        chain(["ثبت برچسب یادآوری", "مکث"]),
        {"مکث": {"main": [[{"node": "دسته‌دسته", "type": "main", "index": 0}]]}},
    ])
    return workflow(
        "۰۲ — یادآوری سبد خرید رها شده",
        [n_sched, n_fetch, n_split, n_filter, n_sms, n_flag, n_wait, n_skip],
        conns,
        tags=["فروشگاه", "پیامک", "بازیابی فروش"],
    )


def wf3_daily_report():
    """گزارش فروش روزانه به تلگرام یا ایتا."""
    n_sched = node(
        "هر روز ۲۱:۰۰", "n8n-nodes-base.scheduleTrigger", 1.2,
        {"rule": {"interval": [{"field": "cronExpression", "expression": "0 21 * * *"}]}},
        -760, 300,
    )
    n_orders = node(
        "سفارش‌های امروز", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "GET",
            "url": "={{ $env.WOO_BASE_URL }}/wp-json/wc/v3/orders",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpBasicAuth",
            "sendQuery": True,
            "queryParameters": {"parameters": [
                {"name": "after", "value": "={{ $now.startOf('day').toISO() }}"},
                {"name": "per_page", "value": "100"},
                {"name": "status", "value": "processing,completed,on-hold"},
            ]},
            "options": {},
        },
        -540, 300,
    )
    n_report = node(
        "محاسبهٔ گزارش", "n8n-nodes-base.code", 2,
        {
            "jsCode": """// تجمیع سفارش‌های امروز به یک خلاصهٔ قابل خواندن
const orders = $input.all().map(i => i.json).filter(o => o && o.id);
const paid = orders.filter(o => ['processing', 'completed'].includes(o.status));

let revenue = 0;
const productCount = {};
const customerCount = {};

for (const o of paid) {
  revenue += Number(o.total || 0);
  const name = `${o.billing?.first_name || ''} ${o.billing?.last_name || ''}`.trim() || 'مشتری مهمان';
  customerCount[name] = (customerCount[name] || 0) + 1;
  for (const item of o.line_items || []) {
    productCount[item.name] = (productCount[item.name] || 0) + item.quantity;
  }
}

const topProducts = Object.entries(productCount)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 5)
  .map(([name, qty], i) => `${i + 1}. ${name} — ${qty} عدد`);

const repeatCustomers = Object.entries(customerCount).filter(([, n]) => n > 1);

const fmt = n => new Intl.NumberFormat('fa-IR').format(Math.round(n));

const text = [
  `📊 گزارش فروش ${$now.toFormat('yyyy/MM/dd')}`,
  '',
  `سفارش پرداخت‌شده: ${fmt(paid.length)}`,
  `درآمد: ${fmt(revenue)} تومان`,
  `میانگین سبد خرید: ${fmt(paid.length ? revenue / paid.length : 0)} تومان`,
  '',
  topProducts.length ? 'پرفروش‌ها:' : 'امروز فروشی ثبت نشده.',
  ...topProducts,
  repeatCustomers.length ? `\\nمشتری تکراری: ${repeatCustomers.length} نفر` : '',
].filter(Boolean).join('\\n');

return [{ json: { text, revenue, orders: paid.length, topProducts } }];
""",
        },
        -320, 300,
    )
    n_telegram = node(
        "ارسال به تلگرام", "n8n-nodes-base.telegram", 1.2,
        {"chatId": "={{ $env.ADMIN_TELEGRAM_CHAT_ID }}", "text": "={{ $json.text }}", "additionalFields": {}},
        -100, 220,
    )
    n_file = node(
        "ذخیرهٔ گزارش روی سرور", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "POST",
            "url": "={{ $env.REPORT_WEBHOOK_URL || 'https://example.com/api/reports' }}",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify($json) }}",
            "options": {"response": {"response": {"neverError": True}}},
        },
        -100, 420,
    )

    conns = multi([
        chain(["هر روز ۲۱:۰۰", "سفارش‌های امروز", "محاسبهٔ گزارش"]),
        {"محاسبهٔ گزارش": {"main": [[
            {"node": "ارسال به تلگرام", "type": "main", "index": 0},
            {"node": "ذخیرهٔ گزارش روی سرور", "type": "main", "index": 0},
        ]]}},
    ])
    return workflow(
        "۰۳ — گزارش فروش روزانه",
        [n_sched, n_orders, n_report, n_telegram, n_file],
        conns,
        tags=["گزارش", "مدیریت"],
    )


def wf4_lead_to_crm():
    """لید از فرم سایت یا اینستاگرام → CRM + اعلان فوری."""
    n_hook = node(
        "دریافت لید", "n8n-nodes-base.webhook", 2,
        {
            "httpMethod": "POST",
            "path": "lead",
            "responseMode": "responseNode",
            "options": {},
        },
        -760, 300,
        webhookId=str(uuid.uuid4()),
    )
    n_normalize = node(
        "نرمال‌سازی", "n8n-nodes-base.set", 3.4,
        {
            "mode": "manual",
            "includeOtherFields": False,
            "assignments": {
                "assignments": [
                    {"id": "1", "name": "name", "value": "={{ $json.body.name || $json.body.full_name || 'بدون نام' }}", "type": "string"},
                    {"id": "2", "name": "phone", "value": "={{ ($json.body.phone || '').replace(/[^0-9+]/g, '') }}", "type": "string"},
                    {"id": "3", "name": "source", "value": "={{ $json.body.source || 'website' }}", "type": "string"},
                    {"id": "4", "name": "message", "value": "={{ $json.body.message || '' }}", "type": "string"},
                    {"id": "5", "name": "received_at", "value": "={{ $now.toISO() }}", "type": "string"},
                ]
            },
            "options": {},
        },
        -540, 300,
    )
    n_validate = node(
        "شماره معتبر است؟", "n8n-nodes-base.if", 2,
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                "conditions": [{
                    "id": "c1",
                    "leftValue": "={{ $json.phone }}",
                    "rightValue": "^09\\d{9}$",
                    "operator": {"type": "string", "operation": "regex"},
                }],
                "combinator": "and",
            },
            "options": {},
        },
        -320, 300,
    )
    n_crm = node(
        "ثبت در CRM", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "POST",
            "url": "={{ $env.CRM_API_URL }}/api/leads",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": "=Bearer {{ $env.CRM_API_TOKEN }}"},
            ]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify($json) }}",
            "options": {"response": {"response": {"neverError": True, "fullResponse": True}}},
        },
        -100, 220,
    )
    n_notify = node(
        "اعلان فوری به مدیر", "n8n-nodes-base.telegram", 1.2,
        {
            "chatId": "={{ $env.SALES_TELEGRAM_CHAT_ID }}",
            "text": "=🔔 لید جدید از {{ $('نرمال‌سازی').item.json.source }}\nنام: {{ $('نرمال‌سازی').item.json.name }}\nموبایل: {{ $('نرمال‌سازی').item.json.phone }}\nپیام: {{ $('نرمال‌سازی').item.json.message }}",
            "additionalFields": {},
        },
        140, 160,
    )
    n_reject = node(
        "پاسخ: شماره نامعتبر", "n8n-nodes-base.respondToWebhook", 1.1,
        {
            "respondWith": "json",
            "responseBody": "={{ JSON.stringify({ ok: false, error: 'invalid_phone' }) }}",
            "options": {"responseCode": 422},
        },
        140, 420,
    )
    n_ok = node(
        "پاسخ: ثبت شد", "n8n-nodes-base.respondToWebhook", 1.1,
        {
            "respondWith": "json",
            "responseBody": "={{ JSON.stringify({ ok: true }) }}",
            "options": {},
        },
        380, 160,
    )

    conns = multi([
        chain(["دریافت لید", "نرمال‌سازی", "شماره معتبر است؟"]),
        {"شماره معتبر است؟": {"main": [
            [{"node": "ثبت در CRM", "type": "main", "index": 0}],
            [{"node": "پاسخ: شماره نامعتبر", "type": "main", "index": 0}],
        ]}},
        {"ثبت در CRM": {"main": [[
            {"node": "اعلان فوری به مدیر", "type": "main", "index": 0},
            {"node": "پاسخ: ثبت شد", "type": "main", "index": 0},
        ]]}},
    ])
    return workflow(
        "۰۴ — لید → CRM + اعلان فوری",
        [n_hook, n_normalize, n_validate, n_crm, n_notify, n_reject, n_ok],
        conns,
        tags=["فروش", "CRM", "لید"],
    )


def wf5_invoice_ocr():
    """عکس فاکتور → OCR → استخراج مبلغ → ثبت در دیتابیس + خلاصه در تلگرام."""
    n_hook = node(
        "دریافت عکس فاکتور", "n8n-nodes-base.webhook", 2,
        {"httpMethod": "POST", "path": "invoice-scan", "responseMode": "lastNode", "options": {}},
        -760, 300,
        webhookId=str(uuid.uuid4()),
    )
    n_ocr = node(
        "OCR فاکتور", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "POST",
            "url": "={{ $env.OCR_API_URL || 'https://api.ocr.space/parse/image' }}",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "apikey", "value": "={{ $env.OCR_API_KEY }}"},
            ]},
            "sendBody": True,
            "contentType": "multipart-form-data",
            "bodyParameters": {"parameters": [
                {"name": "language", "value": "fas"},
                {"name": "isOverlayRequired", "value": "false"},
                {"parameterType": "formBinaryData", "name": "file", "inputDataFieldName": "data"},
            ]},
            "options": {},
        },
        -540, 300,
    )
    n_parse = node(
        "استخراج مبلغ و تاریخ", "n8n-nodes-base.code", 2,
        {
            "jsCode": """// از متن خام فاکتور، مبلغ و تاریخ را بیرون می‌کشیم.
// ارقام فارسی/عربی به لاتین تبدیل می‌شوند تا محاسبات درست باشد.
const toLatin = s => String(s || '')
  .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
  .replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d));

const raw = ($json.ParsedResults?.[0]?.ParsedText) || $json.text || '';
const text = toLatin(raw).replace(/\\u200c/g, ' ');

const amountMatches = [...text.matchAll(/(?:مبلغ|جمع|قابل پرداخت|total)[^0-9]{0,20}([0-9][0-9,\\.]{3,})/gi)]
  .map(m => Number(m[1].replace(/[,\\.]/g, '')))
  .filter(n => n > 1000);

const amount = amountMatches.length ? Math.max(...amountMatches) : null;

const dateMatch = text.match(/(1[34]\\d{2}[\\/\\-]\\d{1,2}[\\/\\-]\\d{1,2})/) ||
                  new Date().toISOString().slice(0, 10);

const invoiceNo = (text.match(/(?:شماره|فاکتور)[^0-9]{0,10}([0-9]{3,})/) || [])[1] || null;

return [{
  json: {
    amount,
    jalali_or_gregorian_date: dateMatch[0] || dateMatch,
    invoice_no: invoiceNo,
    needs_review: amount === null,
    raw_text: text.slice(0, 1500),
  },
}];
""",
        },
        -320, 300,
    )
    n_db = node(
        "ثبت در دیتابیس", "n8n-nodes-base.postgres", 2.5,
        {
            "operation": "insert",
            "schema": {"value": "public"},
            "table": {"value": "invoices"},
            "columns": {
                "mappingMode": "defineBelow",
                "value": {
                    "invoice_no": "={{ $json.invoice_no }}",
                    "amount": "={{ $json.amount }}",
                    "issued_at": "={{ $json.jalali_or_gregorian_date }}",
                    "needs_review": "={{ $json.needs_review }}",
                    "created_at": "={{ $now.toISO() }}",
                },
                "matchingColumns": [],
                "schema": [],
            },
            "options": {},
        },
        -100, 300,
    )
    n_summary = node(
        "خلاصه در تلگرام", "n8n-nodes-base.telegram", 1.2,
        {
            "chatId": "={{ $env.ADMIN_TELEGRAM_CHAT_ID }}",
            "text": "=🧾 فاکتور پردازش شد\nشماره: {{ $json.invoice_no || '—' }}\nمبلغ: {{ $json.amount ? $json.amount.toLocaleString('fa-IR') : 'نیاز به بازبینی دستی' }} تومان\nتاریخ: {{ $json.jalali_or_gregorian_date }}",
            "additionalFields": {},
        },
        120, 300,
    )

    conns = chain(["دریافت عکس فاکتور", "OCR فاکتور", "استخراج مبلغ و تاریخ", "ثبت در دیتابیس", "خلاصه در تلگرام"])
    return workflow(
        "۰۵ — عکس فاکتور → OCR → ثبت خودکار",
        [n_hook, n_ocr, n_parse, n_db, n_summary],
        conns,
        tags=["حسابداری", "OCR", "هوش مصنوعی"],
    )


def wf6_uptime():
    """پایش آپتایم سایت و هشدار فوری (با تأیید دوباره برای جلوگیری از آلارم اشتباه)."""
    n_sched = node(
        "هر ۵ دقیقه", "n8n-nodes-base.scheduleTrigger", 1.2,
        {"rule": {"interval": [{"field": "minutes", "minutesInterval": 5}]}},
        -760, 300,
    )
    n_check = node(
        "بررسی سایت", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "GET",
            "url": "={{ $env.MONITOR_URL }}",
            "options": {
                "timeout": 15000,
                "response": {"response": {"neverError": True, "fullResponse": True}},
            },
        },
        -540, 300,
    )
    n_ok = node(
        "سایت سالم است؟", "n8n-nodes-base.if", 2,
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                "conditions": [{
                    "id": "c1",
                    "leftValue": "={{ $json.statusCode }}",
                    "rightValue": 400,
                    "operator": {"type": "number", "operation": "smaller"},
                }],
                "combinator": "and",
            },
            "options": {},
        },
        -320, 300,
    )
    n_recheck = node(
        "بررسی دوباره پس از ۳۰ ثانیه", "n8n-nodes-base.wait", 1.1,
        {"amount": 30, "unit": "seconds"},
        -100, 420,
    )
    n_second = node(
        "بررسی دوم", "n8n-nodes-base.httpRequest", 4.2,
        {
            "method": "GET",
            "url": "={{ $env.MONITOR_URL }}",
            "options": {
                "timeout": 15000,
                "response": {"response": {"neverError": True, "fullResponse": True}},
            },
        },
        140, 420,
    )
    n_confirm = node(
        "قطعی تأیید شد؟", "n8n-nodes-base.if", 2,
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                "conditions": [{
                    "id": "c1",
                    "leftValue": "={{ $json.statusCode }}",
                    "rightValue": 400,
                    "operator": {"type": "number", "operation": "largerEqual"},
                }],
                "combinator": "and",
            },
            "options": {},
        },
        380, 420,
    )
    n_alert = node(
        "هشدار قطعی", "n8n-nodes-base.telegram", 1.2,
        {
            "chatId": "={{ $env.ADMIN_TELEGRAM_CHAT_ID }}",
            "text": "=🚨 سایت از دسترس خارج شد\n{{ $env.MONITOR_URL }}\nکد وضعیت: {{ $json.statusCode }}\nزمان: {{ $now.toFormat('yyyy/MM/dd HH:mm') }}",
            "additionalFields": {},
        },
        620, 420,
    )
    n_ok_noop = node("همه‌چیز خوب است", "n8n-nodes-base.noOp", 1, {}, -100, 180)

    conns = multi([
        chain(["هر ۵ دقیقه", "بررسی سایت", "سایت سالم است؟"]),
        {"سایت سالم است؟": {"main": [
            [{"node": "همه‌چیز خوب است", "type": "main", "index": 0}],
            [{"node": "بررسی دوباره پس از ۳۰ ثانیه", "type": "main", "index": 0}],
        ]}},
        chain(["بررسی دوباره پس از ۳۰ ثانیه", "بررسی دوم", "قطعی تأیید شد؟"]),
        {"قطعی تأیید شد؟": {"main": [
            [{"node": "هشدار قطعی", "type": "main", "index": 0}],
            [{"node": "همه‌چیز خوب است", "type": "main", "index": 0}],
        ]}},
    ])
    return workflow(
        "۰۶ — پایش آپتایم و هشدار فوری",
        [n_sched, n_check, n_ok, n_recheck, n_second, n_confirm, n_alert, n_ok_noop],
        conns,
        tags=["زیرساخت", "مانیتورینگ", "پشتیبانی"],
    )


BUILDERS = [
    ("01-woocommerce-order-to-accounting.json", wf1_order_to_accounting),
    ("02-abandoned-cart-reminder.json", wf2_abandoned_cart),
    ("03-daily-sales-report.json", wf3_daily_report),
    ("04-lead-to-crm.json", wf4_lead_to_crm),
    ("05-invoice-ocr-to-accounting.json", wf5_invoice_ocr),
    ("06-site-uptime-alert.json", wf6_uptime),
]


def main():
    print("ساخت ورک‌فلوها:")
    for filename, builder in BUILDERS:
        write(filename, builder())
    print(f"\n{len(BUILDERS)} ورک‌فلو در {OUT} ساخته شد.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
