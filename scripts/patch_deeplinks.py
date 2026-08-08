"""
patch_deeplinks.py
يُشغَّل من سير عمل GitHub Actions بعد npx cap add android.

يضيف intent-filter داخل AndroidManifest.xml لتفعيل Android App Links، بحيث
عند ضغط الزبون على رابط حجز مثل https://yoyako.cloud/#/b/xxx أو
https://yoyako.cloud/#/ticket/xxx وكان التطبيق مثبتاً على جهازه، يُفتح الرابط
مباشرة داخل التطبيق بدل المتصفح.

ملاحظة مهمة: هذا التصحيح وحده لا يكفي — نظام أندرويد يتحقق أيضاً من ملف
assetlinks.json يجب رفعه على: https://yoyako.cloud/.well-known/assetlinks.json
(راجعي مخرجات خطوة "Print signing SHA256 fingerprint" في سجل GitHub Actions
للحصول على محتوى هذا الملف جاهزاً).

آمن للتشغيل أكثر من مرة: لا يُدخل نفس الكتلة مرتين.
"""

import os
import re

MANIFEST_PATH = os.path.join("android", "app", "src", "main", "AndroidManifest.xml")
DEEPLINK_MARKER = "<!-- yoyako-app-links -->"

APP_LINKS_FILTER = f"""            {DEEPLINK_MARKER}
            <intent-filter android:autoVerify="true">
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="https" android:host="yoyako.cloud" />
            </intent-filter>
"""


def patch_manifest():
    if not os.path.exists(MANIFEST_PATH):
        raise SystemExit(f"لم يتم العثور على {MANIFEST_PATH}")

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        content = f.read()

    if DEEPLINK_MARKER in content:
        print("ℹ intent-filter الخاص بروابط https://yoyako.cloud موجود مسبقاً، تم التخطي.")
        return

    # يُدرج داخل أول <activity ...> (النشاط الرئيسي MainActivity) قبل </activity>
    match = re.search(r"(<activity\b[^>]*>)(.*?)(</activity>)", content, re.S)
    if not match:
        raise SystemExit("تعذر العثور على وسم <activity> داخل AndroidManifest.xml")

    new_activity = match.group(1) + match.group(2) + APP_LINKS_FILTER + match.group(3)
    content = content[:match.start()] + new_activity + content[match.end():]

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ تمت إضافة intent-filter الخاص بروابط https://yoyako.cloud (App Links) إلى AndroidManifest.xml")


if __name__ == "__main__":
    patch_manifest()
