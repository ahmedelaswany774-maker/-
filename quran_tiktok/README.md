# Quran TikTok Channel Generator

مولّد Python ينشئ مقاطع قرآن عمودية مناسبة لـ TikTok من آيات عشوائية غير مكررة من المصحف كاملًا. يستخدم النص العربي، ترجمة إنجليزية، وتلاوة Mishari Rashid al-`Afasy، ثم ينتج MP4 بصيغة H.264 وبمقاس 1080×1920.

## ما تم تنفيذه

يختار السكريبت آية عشوائية من إجمالي 6236 آية، يجلب النص العربي والترجمة الإنجليزية والتلاوة، يبني بطاقة عمودية واضحة، يدمج البطاقة مع الصوت باستخدام FFmpeg، ويحفظ `state.json` لمنع إعادة استخدام الآية بعد نجاح التوليد. كل فيديو يصاحبه ملف JSON يحوي بيانات السورة والآية والمصادر والكابشن المقترح.

## التشغيل

```bash
cd /home/ubuntu/quran_tiktok_channel
python3 generate_quran_tiktok.py --count 1 --output output
```

لإنشاء خمسة مقاطع:

```bash
python3 generate_quran_tiktok.py --count 5 --output output
```

المقاطع الجاهزة للنشر ستظهر داخل:

```text
output/ready_to_post/
```

أما الملفات المؤقتة فتظهر داخل `output/work/`، وسجل الآيات المستخدمة في `output/state.json`.

## التشغيل الدوري

يمكن تشغيل الأمر مرة يوميًا عبر cron على جهاز Linux:

```cron
0 18 * * * cd /home/ubuntu/quran_tiktok_channel && /usr/bin/python3 generate_quran_tiktok.py --count 1 --output output >> output/generator.log 2>&1
```

لا تحذف `output/state.json` إلا إذا أردت إعادة استخدام الآيات من البداية.

## المصادقة والنشر

النسخة الحالية تولّد الملفات وتضعها في `ready_to_post` ولا تنشر علنًا تلقائيًا. عند ربط TikTok، يلزم إنشاء تطبيق Developer ومنحه صلاحية Content Posting API ثم مصادقة حساب القناة. بعد ذلك يمكن إضافة رفع الفيديوهات كمسودات للمراجعة داخل TikTok. يوصى بالإبقاء على مراجعة بشرية قبل النشر للتحقق من النص ورقم الآية.

## مصادر البيانات

- Quran Foundation API: https://api-docs.quran.foundation/
- Quran audio CDN: https://verses.quran.foundation/
- TikTok Content Posting API: https://developers.tiktok.com/doc/content-posting-api-get-started-upload-content?enter_method=left_navigation
