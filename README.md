# ✨ Text Fixer

**যেকোনো অ্যাপে এক ক্লিকে ইংরেজি ঠিক করুন, AI দিয়ে।** Windows এবং Android, দুটোতেই চলে।

*Fix your English in any app with one click, using free AI. Works on Windows and Android.*

Fiverr, Gmail, WhatsApp, Slack, যেখানেই লিখুন, Text Fixer আপনার লেখার গ্রামার ঠিক করে, মেসেজটাকে স্বাভাবিক আর প্রফেশনাল করে দেয়। ক্লায়েন্টের মেসেজের রিপ্লাইও লিখে দেয়, আর বাংলা থেকে ইংরেজিও করে।

---

## 📥 ডাউনলোড

[**Releases**](../../releases/latest) পেজ থেকে নামান:

| ফাইল | কিসের জন্য |
|---|---|
| `TextFixer.exe` | Windows 10 / 11 |
| `TextFixer-android.apk` | Android 7.0 বা তার পরের ভার্সন |

দুটোই ফ্রি। চালাতে একটা ফ্রি AI API key লাগবে (নিচে দেখুন কীভাবে পাবেন)।

---

## 🔑 ফ্রি API key কীভাবে পাবেন

Text Fixer ফ্রি AI সার্ভিস দিয়ে চলে। অন্তত একটা key লাগবে, **Groq** সবচেয়ে দ্রুত (প্রায় ১ সেকেন্ড):

1. <https://console.groq.com/keys> এ যান, Google দিয়ে সাইন ইন করুন।
2. **Create API Key** চাপুন, একটা নাম দিন।
3. key টা কপি করুন (`gsk_` দিয়ে শুরু)। এটা শুধু একবারই দেখায়, তাই কোথাও সেভ করে রাখুন।

ব্যাকআপ হিসেবে চাইলে আরও যোগ করতে পারেন। একটা কাজ না করলে Text Fixer নিজে থেকেই পরেরটা ব্যবহার করে:
- **Google Gemini:** <https://aistudio.google.com/app/apikey>
- **OpenRouter:** <https://openrouter.ai/keys>

> 🔒 আপনার key শুধু আপনার নিজের PC বা ফোনেই থাকে। কারো সাথে শেয়ার করবেন না।

---

## 💻 Windows

### ইনস্টল
1. `TextFixer.exe` ডাউনলোড করে ডাবল-ক্লিক করুন।
2. Windows যদি **"Windows protected your PC"** দেখায়: **More info → Run anyway** চাপুন। (অ্যাপটা নতুন বলে এটা দেখায়।)
3. প্রথমবার Settings খুলবে: **AI providers** ট্যাবে Groq key পেস্ট করুন → **Test** → **Save**।
4. Settings → **Behavior** → **Start Text Fixer when Windows starts** টিক দিলে কম্পিউটার চালু হলেই চলবে।

Text Fixer ঘড়ির পাশে **system tray** তে চলে (✨ আইকন)।

### ব্যবহার

| কী করতে চান | কীভাবে |
|---|---|
| লেখা ঠিক করা | যেকোনো টেক্সট বক্সে লিখুন, ১ সেকেন্ড থামুন। বক্সের উপরে **✨ Fix grammar** বাটন আসবে, ক্লিক করুন |
| বাটন ছাড়া | **Ctrl + Shift + G** চাপুন |
| আগে দেখে নেওয়া | একটা প্রিভিউ আসে, কী বদলেছে সবুজ রঙে দেখায়। পছন্দ হলে **Replace**, না হলে **Try again** |
| অন্য স্টাইল | বাটনে **রাইট-ক্লিক** করুন: More professional, Shorter, Friendlier, Translate Bangla → English |
| আগের লেখা ফেরত | **Ctrl + Z** |
| পেস্ট করে ঠিক করা | tray আইকনে **ডাবল-ক্লিক** → **Paste & fix** ট্যাব। লেখা পেস্ট করুন → **Fix** → **Copy result** |
| ক্লায়েন্টের রিপ্লাই লেখা | ক্লায়েন্টের মেসেজ সিলেক্ট করুন → **Ctrl + Shift + R**। চাইলে নোট দিন (যেমন "yes, $50, Friday"), টোন বেছে নিন → **Copy** বা **Insert into app** |
| আগের ২০টা লেখা দেখা | tray আইকনে রাইট-ক্লিক → **History** |
| কিছুক্ষণ বন্ধ রাখা | tray আইকনে রাইট-ক্লিক → **Pause** |

পাসওয়ার্ড ফিল্ডে বাটন কখনো আসে না। কোনো অ্যাপে না চাইলে Settings → **Excluded apps** এ যোগ করুন।

---

## 📱 Android

### ইনস্টল
1. ফোনে `TextFixer-android.apk` ডাউনলোড করে খুলুন।
2. "Install unknown apps" অনুমতি চাইলে **Allow** দিন, তারপর **Install**।
   - Play Protect সতর্ক করলে **Install anyway** চাপুন।
   - **Xiaomi / Redmi / POCO:** File Manager থেকে APK খুলে ইনস্টল করুন। "security scan" এ **Install anyway** দিন।
3. **Text Fixer** অ্যাপ খুলুন → Groq key পেস্ট করুন → **Save** → **Test**।

### ব্যবহার
1. যেকোনো অ্যাপে (WhatsApp, Fiverr, Gmail…) লিখুন।
2. লেখাটা **সিলেক্ট** করুন → মেনুতে **Text Fixer** চাপুন। (না দেখলে **⋮** চাপুন।)
3. প্রিভিউ দেখে **Replace** চাপুন, লেখা বদলে যাবে।

**রিপ্লাই:** ক্লায়েন্টের মেসেজ সিলেক্ট করুন → **Text Fixer Reply** → চাইলে নোট দিন → **Copy reply** → রিপ্লাই বক্সে পেস্ট করুন।

### 🔋 ব্যাটারি
Text Fixer ব্যাকগ্রাউন্ডে **একদম চলে না**। কোনো সার্ভিস, নোটিফিকেশন বা অটো-চেক নেই। শুধু আপনি মেনু থেকে চাপলে চালু হয়, কাজ শেষে বন্ধ হয়ে যায়। অ্যাপের সাইজ মাত্র ~৫০ KB।

---

## ❓ সমস্যা ও সমাধান

| সমস্যা | সমাধান |
|---|---|
| "No API key set" | অ্যাপে Groq key পেস্ট করে **Save** করুন |
| "rate limit reached" | ফ্রি লিমিট শেষ। এক মিনিট পর চেষ্টা করুন, বা Gemini key যোগ করুন |
| কোনো অ্যাপে বাটন আসে না (Windows) | **Ctrl + Shift + G** ব্যবহার করুন |
| Replace কাজ করে না (Android) | কিছু অ্যাপ এটা সাপোর্ট করে না। **Copy instead** চেপে পেস্ট করুন |
| মডেল "unavailable" | Text Fixer নিজে থেকেই অন্য মডেল বেছে নেয়। Settings এ **↻ Load models** দিয়েও বাছতে পারেন |

---

## 🛠️ For developers

**Windows app:** Python 3.11+, PySide6, Windows UI Automation.

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python -m pip install -r requirements.txt
```

```bash
.venv\Scripts\python main.py
```

Build a single exe: `powershell -ExecutionPolicy Bypass -File build.ps1` → `dist\TextFixer.exe`. Install with desktop and Start menu icons: `install.ps1`.

**Android app** (`android/`): plain Java, no dependencies, uses Android's text-selection menu (`ACTION_PROCESS_TEXT`). Build: `powershell -ExecutionPolicy Bypass -File android\build.ps1` → `dist\TextFixer-android.apk`. Needs Android Studio's SDK.

**AI providers:** Groq (`openai/gpt-oss-120b`) → Gemini (`gemini-3.5-flash`) → OpenRouter (`:free` models), with automatic fallback and automatic replacement of retired models. To add a provider, see `providers/`.

```
main.py, config.py      Windows app: tray, hotkeys, settings, prompts
core/                   focus watcher (UI Automation), text replace, clipboard, history
providers/              AI provider chain (Groq, Gemini, OpenRouter)
ui/                     floating button, preview card, Paste & fix, reply, settings
android/                Android app (Java)
marketing/              LinkedIn images and promo video scripts
```

API keys are stored only on the user's device (`%APPDATA%\FixIt\config.json` on Windows, encrypted with the Android Keystore on Android) and are never part of this repository.
