#!/usr/bin/env bash
#
# آزمون ایمپورت واقعی: ورک‌فلوها را در یک نمونهٔ موقت n8n وارد می‌کند
# و وجودشان را از دیتابیس تأیید می‌کند.
#
# پیش‌نیاز: n8n نصب باشد (npm install -g n8n) و php با pdo_sqlite.
# اجرا:  bash scripts/import-test.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_FOLDER="${N8N_TEST_FOLDER:-/tmp/n8n-import-test}"
EXPECTED="${EXPECTED_WORKFLOWS:-6}"

export N8N_USER_FOLDER="$USER_FOLDER"
export N8N_ENCRYPTION_KEY="${N8N_ENCRYPTION_KEY:-import-test-key}"
export N8N_DIAGNOSTICS_ENABLED=false
export N8N_VERSION_NOTIFICATIONS_ENABLED=false

rm -rf "$USER_FOLDER"
mkdir -p "$USER_FOLDER"

cd "$ROOT"

echo "→ ایمپورت ورک‌فلوها در $USER_FOLDER"
n8n import:workflow --separate --input=workflows/ 2>&1 | tail -3

DB="$(find "$USER_FOLDER" -name 'database.sqlite' | head -1)"

if [ -z "$DB" ]; then
	echo "✗ دیتابیس n8n پیدا نشد" >&2
	exit 1
fi

echo "→ بررسی دیتابیس: $DB"
DB="$DB" EXPECTED="$EXPECTED" php -r '
$db = new PDO("sqlite:" . getenv("DB"));
$count = (int) $db->query("SELECT COUNT(*) FROM workflow_entity")->fetchColumn();
$expected = (int) getenv("EXPECTED");
printf("  ورک‌فلوهای واردشده: %d (انتظار: %d)\n", $count, $expected);
if ($count !== $expected) { fwrite(STDERR, "✗ تعداد ورک‌فلوها مطابق انتظار نیست\n"); exit(1); }

$rows = $db->query("SELECT name, nodes FROM workflow_entity")->fetchAll(PDO::FETCH_ASSOC);
$total = 0;
foreach ($rows as $row) {
    $nodes = json_decode($row["nodes"], true);
    $total += count($nodes);
    printf("  ✓ %s (%d گره)\n", $row["name"], count($nodes));
}
printf("  مجموع گره‌ها: %d\n", $total);
'

echo "✅ ایمپورت واقعی موفق بود."
