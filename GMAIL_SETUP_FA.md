# اتصال Gmail به AgentForge

1. در Google Cloud Console یک پروژه بساز و **Gmail API** را فعال کن.
2. صفحه OAuth consent screen را تنظیم کن. برای حالت Testing، آدرس Gmail خودت را در Test users اضافه کن.
3. یک OAuth Client ID از نوع **Desktop app** بساز و JSON آن را دانلود کن.
4. فایل JSON را در پوشه پروژه با نام `gmail_client_secret.json` قرار بده. آن را هرگز در Git یا برای دیگران منتشر نکن.
5. در محیط مجازی پروژه نصب کن: ` .\.venv\Scripts\python.exe -m pip install -r requirements_gmail.txt `
6. Streamlit را اجرا کن؛ در صفحه One-click Campaign تحقیق و پروپوزال را تولید کن؛ روی **Connect Gmail via Google OAuth** بزن و در مرورگر وارد Gmail شو.
7. گیرنده معتبر، عنوان، متن نهایی و مستند مجاز بودن تماس را وارد کن. بعد از تأیید صریح، **Send this email via Gmail** را بزن.

**مهم:** ارسال خودکار یا انبوه فعال نیست. وجود ایمیل عمومی یا GitHub Issue مجوز ارسال نیست. فقط Gmail API scope `gmail.send` درخواست می‌شود. توکن در `.agentforge_private/gmail_token.json` روی رایانه خودت ذخیره می‌شود؛ از آن محافظت کن. برای قطع دسترسی، در تنظیمات امنیتی حساب Google دسترسی اپ را لغو کن. فایل توکن و client secret را به Git اضافه نکن.
