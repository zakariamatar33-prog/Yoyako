"""
patch_signing.py
يُشغَّل من سير عمل GitHub Actions فقط، بعد `npx cap add android`، وقبل
`./gradlew assembleDebug` / `bundleRelease`. يقوم بأمرين:

  1) يضيف مكوّن Google Services (com.google.gms.google-services) لملفي
     Gradle تلقائياً — فقط إذا كان android/app/google-services.json موجوداً
     فعلياً — وهذا ما يُفعّل FCM (الإشعارات) داخل التطبيق. بدون هذا التصحيح
     يبني المشروع بنجاح لكن دون أن يعمل تسجيل رمز الإشعارات (FCM token).

  2) يضيف إعدادات التوقيع (signingConfigs) لبناء نسخة release موقّعة،
     ويحدّث رقم/اسم الإصدار اختيارياً من متغيرات البيئة APP_VERSION_CODE /
     APP_VERSION_NAME — فقط إذا وُجدت أسرار التوقيع.

آمن للتشغيل أكثر من مرة: لا يُدخل نفس الكتلة مرتين.
"""

import os
import re

APP_GRADLE_PATH = os.path.join("android", "app", "build.gradle")
PROJECT_GRADLE_PATH = os.path.join("android", "build.gradle")
GOOGLE_SERVICES_JSON_PATH = os.path.join("android", "app", "google-services.json")

SIGNING_MARKER = "// yoyako-release-signing"
GMS_APP_MARKER = "// yoyako-google-services-plugin"
GMS_PROJECT_MARKER = "// yoyako-google-services-classpath"
GMS_CLASSPATH_LINE = "        classpath 'com.google.gms:google-services:4.4.2'"

SIGNING_BLOCK = f"""
    {SIGNING_MARKER}
    signingConfigs {{
        release {{
            def keystorePropertiesFile = rootProject.file("keystore.properties")
            def keystoreProperties = new Properties()
            if (keystorePropertiesFile.exists()) {{
                keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
                storeFile file(keystoreProperties['storeFile'])
                storePassword keystoreProperties['storePassword']
                keyAlias keystoreProperties['keyAlias']
                keyPassword keystoreProperties['keyPassword']
            }}
        }}
    }}
"""


def patch_release_signing(content: str) -> str:
    if SIGNING_MARKER not in content:
        content = content.replace("android {", "android {" + SIGNING_BLOCK, 1)
        content = re.sub(
            r"(buildTypes\s*\{\s*release\s*\{)",
            r"\1\n            signingConfig signingConfigs.release",
            content,
        )
        print("✓ تمت إضافة إعدادات التوقيع (signingConfigs) إلى build.gradle")
    else:
        print("ℹ إعدادات التوقيع موجودة مسبقاً، تم التخطي.")

    version_code = os.environ.get("APP_VERSION_CODE")
    version_name = os.environ.get("APP_VERSION_NAME")

    if version_code:
        content, n = re.subn(r"versionCode\s+\d+", f"versionCode {version_code}", content)
        if n:
            print(f"✓ تم تحديث versionCode إلى {version_code}")

    if version_name:
        content, n = re.subn(r'versionName\s+"[^"]*"', f'versionName "{version_name}"', content)
        if n:
            print(f"✓ تم تحديث versionName إلى {version_name}")

    return content


def patch_google_services(app_content: str, project_content: str):
    if not os.path.exists(GOOGLE_SERVICES_JSON_PATH):
        print("ℹ لا يوجد google-services.json — تم تخطي تفعيل مكوّن Google Services (الإشعارات لن تعمل حتى تُضيفيه).")
        return app_content, project_content

    if GMS_PROJECT_MARKER not in project_content:
        project_content = re.sub(
            r"(dependencies\s*\{)",
            r"\1\n" + GMS_PROJECT_MARKER + "\n" + GMS_CLASSPATH_LINE,
            project_content,
            count=1,
        )
        print("✓ تمت إضافة classpath الخاص بـ Google Services إلى android/build.gradle")
    else:
        print("ℹ classpath الخاص بـ Google Services موجود مسبقاً، تم التخطي.")

    if GMS_APP_MARKER not in app_content:
        app_content = app_content.rstrip() + f"\n\n{GMS_APP_MARKER}\napply plugin: 'com.google.gms.google-services'\n"
        print("✓ تمت إضافة مكوّن Google Services إلى android/app/build.gradle")
    else:
        print("ℹ مكوّن Google Services موجود مسبقاً، تم التخطي.")

    return app_content, project_content


def main():
    if not os.path.exists(APP_GRADLE_PATH):
        raise SystemExit(f"لم يتم العثور على {APP_GRADLE_PATH} — تأكدي من تشغيل npx cap add android أولاً.")

    with open(APP_GRADLE_PATH, encoding="utf-8") as f:
        app_content = f.read()
    with open(PROJECT_GRADLE_PATH, encoding="utf-8") as f:
        project_content = f.read()

    app_content = patch_release_signing(app_content)
    app_content, project_content = patch_google_services(app_content, project_content)

    with open(APP_GRADLE_PATH, "w", encoding="utf-8") as f:
        f.write(app_content)
    with open(PROJECT_GRADLE_PATH, "w", encoding="utf-8") as f:
        f.write(project_content)


if __name__ == "__main__":
    main()
