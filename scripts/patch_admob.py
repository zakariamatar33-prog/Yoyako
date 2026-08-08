"""
patch_admob.py
يُشغَّل من سير عمل GitHub Actions بعد npx cap add android.

إضافة @capacitor-community/admob لا تُفعَّل تلقائياً من capacitor.config.json —
توثيق الحزمة نفسه يطلب تعديل يدوي في AndroidManifest.xml و strings.xml. بدون
هذا التعديل قد يتعطل التطبيق عند بدء التشغيل إن استُخدم AdMob.

يقرأ معرّف AdMob App ID من ملف admob.config.json في جذر المستودع (تُعدّلينه
مباشرة، ليس سراً حساساً). إن لم يوجد الملف، يُستخدم معرّف Google التجريبي
الرسمي تلقائياً (آمن دائماً أثناء التطوير، لا يخالف سياسات AdMob).
"""

import json
import os
import re

DEFAULT_TEST_APP_ID = "ca-app-pub-3940256099942544~3347511713"

MANIFEST_PATH = os.path.join("android", "app", "src", "main", "AndroidManifest.xml")
STRINGS_PATH = os.path.join("android", "app", "src", "main", "res", "values", "strings.xml")
CONFIG_PATH = "admob.config.json"


def get_app_id():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        app_id = (data or {}).get("appId")
        if app_id:
            print(f"ℹ استخدام AdMob App ID من admob.config.json: {app_id}")
            return app_id
    print(f"ℹ لا يوجد admob.config.json — استخدام معرّف Google التجريبي الرسمي مؤقتاً: {DEFAULT_TEST_APP_ID}")
    return DEFAULT_TEST_APP_ID


def patch_strings_xml(app_id):
    if not os.path.exists(STRINGS_PATH):
        raise SystemExit(f"لم يتم العثور على {STRINGS_PATH}")

    with open(STRINGS_PATH, encoding="utf-8") as f:
        content = f.read()

    if 'name="admob_app_id"' in content:
        content = re.sub(
            r'<string name="admob_app_id">[^<]*</string>',
            f'<string name="admob_app_id">{app_id}</string>',
            content,
        )
    else:
        content = content.replace(
            "</resources>",
            f'    <string name="admob_app_id">{app_id}</string>\n</resources>',
        )

    with open(STRINGS_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ تم تحديث strings.xml بمعرّف AdMob")


def patch_manifest_xml():
    if not os.path.exists(MANIFEST_PATH):
        raise SystemExit(f"لم يتم العثور على {MANIFEST_PATH}")

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        content = f.read()

    if "com.google.android.gms.ads.APPLICATION_ID" in content:
        print("ℹ meta-data الخاصة بـ AdMob موجودة مسبقاً، تم التخطي.")
        return

    meta_tag = '        <meta-data android:name="com.google.android.gms.ads.APPLICATION_ID" android:value="@string/admob_app_id"/>\n'
    content, n = re.subn(r"(<application[^>]*>)", r"\1\n" + meta_tag, content, count=1)
    if not n:
        raise SystemExit("تعذر العثور على وسم <application> داخل AndroidManifest.xml")

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ تمت إضافة meta-data الخاصة بـ AdMob إلى AndroidManifest.xml")


def main():
    app_id = get_app_id()
    patch_strings_xml(app_id)
    patch_manifest_xml()


if __name__ == "__main__":
    main()
