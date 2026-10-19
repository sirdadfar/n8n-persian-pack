#!/usr/bin/env node
/**
 * اعتبارسنجی ساختاری ورک‌فلوهای n8n.
 *
 * بدون نیاز به نصب n8n، موارد زیر بررسی می‌شود:
 *   - JSON معتبر و کلیدهای ضروری (name / nodes / connections)
 *   - یکتا و معتبر بودن شناسهٔ هر گره (UUID v4)
 *   - قابل‌خوان بودن نوع گره و مسیر نصب‌شده (n8n-nodes-base.* یا بستهٔ اجتماعی)
 *   - اشارهٔ همهٔ اتصال‌ها به گره‌های موجود
 *   - نبود گره یتیم (گره‌ای که نه ورودی دارد نه خروجی)
 *   - پر بودن نام پارامترهای اجباری وب‌هوک (path)
 *
 * اجرا:  node scripts/validate.mjs
 */

import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const WORKFLOWS_DIR = join(ROOT, 'workflows');

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/** گره‌هایی که می‌توانند ورودی/خروجی نداشته باشند. */
const ENTRY_TYPES = new Set([
  'n8n-nodes-base.webhook',
  'n8n-nodes-base.scheduleTrigger',
  'n8n-nodes-base.wooCommerceTrigger',
  'n8n-nodes-base.telegramTrigger',
  'n8n-nodes-base.emailReadImap',
  'n8n-nodes-base.cron',
  'n8n-nodes-base.executeWorkflowTrigger',
]);
const TERMINAL_TYPES = new Set([
  'n8n-nodes-base.noOp',
  'n8n-nodes-base.respondToWebhook',
  'n8n-nodes-base.telegram',
  'n8n-nodes-base.slack',
  'n8n-nodes-base.gmail',
  'n8n-nodes-base.emailSend',
]);

/** گره‌های «اقدام نهایی»: درخواست‌های تغییردهنده که لازم نیست خروجی داشته باشند. */
function isFinalAction(n) {
  const method = String(n.parameters?.method ?? 'POST').toUpperCase();
  return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && !n.parameters?.disableOutput;
}

const errors = [];
const warnings = [];
let checked = 0;

function err(file, msg) {
  errors.push(`${file}: ${msg}`);
}
function warn(file, msg) {
  warnings.push(`${file}: ${msg}`);
}

for (const file of readdirSync(WORKFLOWS_DIR).filter((f) => f.endsWith('.json')).sort()) {
  checked++;

  let wf;
  try {
    wf = JSON.parse(readFileSync(join(WORKFLOWS_DIR, file), 'utf8'));
  } catch (e) {
    err(file, `JSON نامعتبر است — ${e.message}`);
    continue;
  }

  // ---------- کلیدهای سطح بالا ----------
  if (!wf.name || typeof wf.name !== 'string') err(file, '«name» ورک‌فلو خالی است');
  if (!Array.isArray(wf.nodes) || wf.nodes.length === 0) {
    err(file, '«nodes» خالی یا غیرآرایه است');
    continue;
  }
  if (typeof wf.connections !== 'object' || wf.connections === null) {
    err(file, '«connections» وجود ندارد');
  }

  // ---------- گره‌ها ----------
  const names = new Set();
  const ids = new Set();

  for (const n of wf.nodes) {
    const label = n?.name || '<بی‌نام>';

    if (!n.name) err(file, 'گره‌ای بدون «name»');
    if (names.has(n.name)) err(file, `نام تکراری گره: ${n.name}`);
    names.add(n.name);

    if (!n.id) {
      err(file, `گرهٔ «${label}» شناسه ندارد`);
    } else if (!UUID_V4.test(n.id)) {
      err(file, `شناسهٔ گره «${label}» قالب UUID v4 ندارد (${n.id})`);
    } else if (ids.has(n.id)) {
      err(file, `شناسهٔ تکراری: ${n.id}`);
    }
    ids.add(n.id);

    if (!n.type || typeof n.type !== 'string') {
      err(file, `گرهٔ «${label}» نوع (type) ندارد`);
    } else if (!n.type.startsWith('n8n-nodes-base.') && !n.type.startsWith('@')) {
      warn(file, `گرهٔ «${label}» از بستهٔ غیررسمی استفاده می‌کند: ${n.type}`);
    }

    if (typeof n.typeVersion !== 'number') {
      err(file, `گرهٔ «${label}» نسخه (typeVersion) ندارد`);
    }

    if (!Array.isArray(n.position) || n.position.length !== 2 ||
        !n.position.every((v) => typeof v === 'number')) {
      err(file, `موقعیت نامعتبر گره «${label}»`);
    }

    if (typeof n.parameters !== 'object' || n.parameters === null) {
      err(file, `پارامترهای گره «${label}» نامعتبر است`);
    }

    // وب‌هوک بدون path کار نمی‌کند
    if (n.type === 'n8n-nodes-base.webhook' && !n.parameters?.path) {
      err(file, `وب‌هوک «${label}» مسیر (path) ندارد`);
    }
  }

  // ---------- اتصال‌ها ----------
  const incoming = new Set();
  const outgoing = new Set();
  const loops = new Map(); // name -> number of times it appears as a target

  for (const [source, outputs] of Object.entries(wf.connections ?? {})) {
    if (!names.has(source)) {
      err(file, `اتصال از گرهٔ ناموجود «${source}»`);
      continue;
    }
    outgoing.add(source);

    if (!Array.isArray(outputs.main)) {
      err(file, `ساختار اتصال گرهٔ «${source}» نامعتبر است`);
      continue;
    }

    outputs.main.forEach((branch, branchIndex) => {
      if (!Array.isArray(branch)) {
        err(file, `شاخهٔ ${branchIndex} گرهٔ «${source}» آرایه نیست`);
        return;
      }
      for (const link of branch) {
        if (!link || !names.has(link.node)) {
          err(file, `اتصال به گرهٔ ناموجود «${link?.node}» از «${source}»`);
          continue;
        }
        incoming.add(link.node);
        loops.set(link.node, (loops.get(link.node) ?? 0) + 1);
        if (link.type !== 'main') {
          warn(file, `نوع اتصال غیر «main» از «${source}» → «${link.node}»`);
        }
      }
    });
  }

  for (const n of wf.nodes) {
    const isEntry = ENTRY_TYPES.has(n.type) || n.parameters?.triggerTimes !== undefined;
    const isTerminal = TERMINAL_TYPES.has(n.type);

    if (!isEntry && !incoming.has(n.name)) {
      err(file, `گرهٔ «${n.name}» نه ورودی دارد نه تریگر است (یتیم)`);
    }
    if (!isTerminal && !isFinalAction(n) && !outgoing.has(n.name)) {
      warn(file, `گرهٔ «${n.name}» خروجی متصل ندارد`);
    }
  }

  // ---------- فعال/غیرفعال ----------
  if (wf.active === true) {
    err(file, 'ورک‌فلو پابلیک نباید به‌صورت پیش‌فرض فعال باشد');
  }
}

console.log(`\nبررسی ${checked} ورک‌فلو انجام شد.`);
if (warnings.length) {
  console.log(`\n⚠️  ${warnings.length} هشدار:`);
  for (const w of warnings) console.log('   - ' + w);
}
if (errors.length) {
  console.error(`\n❌ ${errors.length} خطا:`);
  for (const e of errors) console.error('   - ' + e);
  process.exit(1);
}
console.log('✅ همهٔ ورک‌فلوها از نظر ساختاری معتبرند.\n');
