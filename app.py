#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yt-dlp GUI - واجهة رسومية شاملة لـ yt-dlp
- لصق الرابط فقط والتحميل
- كل خيارات التحميل
- تشخيص أخطاء ذكي بالعربية + حلول مقترحة
"""
import os, re, sys, json, threading, subprocess, queue, shutil
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_TITLE = "محمل الفيديو الشامل - yt-dlp GUI"
APP_VERSION = "1.1.0"
DEFAULT_OUTPUT = str(Path.home() / "Downloads" / "yt-dlp")
# مسار حفظ التفضيلات — يعمل للسكربت وللـ exe المجمد
def _config_path():
    try:
        # exe مجمد: بجانب الـ exe (قابل للكتابة)
        if getattr(sys, 'frozen', False):
            p = Path(sys.executable).parent / "settings.json"
            return p
        # سكربت: بجانب app.py
        p = Path(__file__).parent / "settings.json"
        # fallback: APPDATA
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            test = p.parent / ".write_test"
            test.touch(); test.unlink()
            return p
        except:
            return Path(os.environ.get("APPDATA", str(Path.home()))) / "yt-dlp-GUI" / "settings.json"
    except:
        return Path.home() / ".yt-dlp-gui.json"
CONFIG_FILE = _config_path()

# ---------- قاموس الأخطاء الشائعة وحلولها ----------
ERROR_SOLUTIONS = [
    {
        "pattern": r"Resolving timed out|Failed to resolve|Name or service not known|getaddrinfo failed",
        "title": "مشكلة DNS / انقطاع شبكة",
        "msg": "فشل في حل اسم النطاق (DNS). السبب شبكة محلية أو DNS بطيء.",
        "fix": "• غيّر DNS إلى 8.8.8.8 و 1.1.1.1\n• فعّل خيار --force-ipv4 في الواجهة\n• جرّب: ipconfig /flushdns\n• جرّب شبكة أخرى أو VPN إذا كان الموقع محجوب"
    },
    {
        "pattern": r"Unable to extract universal data|Unable to extract.*, rehydration|Extractor failed",
        "title": "تيك توك غيّر بنية الصفحة",
        "msg": "أداة yt-dlp قديمة والموقع غيّر الكود. هذا هو خطأك الحالي.",
        "fix": "• حدّث الأداة: yt-dlp -U  (أنت على 2026.02.21 وهي قديمة)\n• أو فعّل [استخدام الكوكيز] واختر ملف cookies.txt من المتصفح\n• أو جرّب خيار --extractor-args \"tiktok:api_hostname=api22-normal-c-useast2a.tiktokv.com\"\n• مؤقتاً استخدم موقع بديل مثل ssstik.io حتى يتم إصلاح المستخرج"
    },
    {
        "pattern": r"HTTP Error 403|Forbidden|HTTP Error 429|Too Many Requests",
        "title": "محجوب / كثرة طلبات",
        "msg": "الموقع حجب الطلب (حماية ضد البوتات أو حد تحميل).",
        "fix": "• فعّل [استخدام الكوكيز] وصدّرها من متصفحك (Extension: Get cookies.txt)\n• استخدم VPN / Proxy\n• قلل السرعة: --sleep-requests 1\n• انتظر دقائق ثم أعد المحاولة"
    },
    {
        "pattern": r"HTTP Error 404|video unavailable|Private video|Video not available",
        "title": "الفيديو غير متاح",
        "msg": "الفيديو محذوف أو خاص أو محجوب جغرافياً.",
        "fix": "• تأكد الرابط يفتح في المتصفح\n• إذا خاص: سجّل دخول وصدّر الكوكيز\n• إذا محجوب جغرافياً: استخدم VPN على بلد ناشر الفيديو"
    },
    {
        "pattern": r"ffmpeg.*not found|ffprobe.*not found",
        "title": "ffmpeg غير مثبت",
        "msg": "الدمج/التحويل يحتاج ffmpeg.",
        "fix": "• حمّل ffmpeg من gyan.dev وثبته\n• أو ضع ffmpeg.exe بجانب yt-dlp.exe\n• للأوديو MP3: يجب وجود ffmpeg"
    },
    {
        "pattern": r"No video formats found|Requested format not available",
        "title": "لا توجد صيغة مناسبة",
        "msg": "الصيغة المطلوبة غير متوفرة لهذا الفيديو.",
        "fix": "• اختر الجودة [الأفضل تلقائياً]\n• أو جرّب صيغة mp4 بدل webm\n• فعّل [السماح بأفضل بديل] (الافتراضي مفعل)"
    },
    {
        "pattern": r"SSL.*certificate|certificate verify failed|unable to get local issuer",
        "title": "مشكلة شهادة SSL",
        "msg": "فشل التحقق من الشهادة (ساعة النظام أو certifi قديم).",
        "fix": "• صحح تاريخ/وقت الويندوز\n• حدّث الشهادات: pip install -U certifi\n• مؤقتاً: أضف في الخيارات الإضافية: --no-check-certificate (غير آمن)"
    },
    {
        "pattern": r"Unsupported URL|No suitable extractor",
        "title": "رابط غير مدعوم",
        "msg": "yt-dlp لا يدعم هذا الرابط بهذا الشكل.",
        "fix": "• تأكد الرابط كامل يبدأ بـ https://\n• جرّب نسخ رابط المشاركة الأصلي بدون اختصار\n• حدّث yt-dlp لأحدث نسخة"
    },
    {
        "pattern": r"is older than 90 days",
        "title": "نسخة قديمة",
        "msg": "نسختك قديمة وستفشل مع مواقع كثيرة.",
        "fix": "• شغّل: yt-dlp -U\n• أو حمّل أحدث exe من github.com/yt-dlp/yt-dlp/releases"
    },
    {
        "pattern": r"Could not copy Chrome cookie database|Failed to read Chrome cookies|cookie database.*locked",
        "title": "Chrome مقفل — لا يمكن نسخ الكوكيز",
        "msg": "المتصفح Chrome مفتوح ويقفل قاعدة بيانات الكوكيز. yt-dlp لا يستطيع نسخها أثناء التشغيل.",
        "fix": "• الحل السريع: أغلق Chrome تماماً (X) ثم افتح Task Manager → أنهِ كل chrome.exe → اضغط التقاط مرة أخرى\n• أو: افتح الإعدادات → System → أوقف 'Continue running background apps when Chrome is closed'\n• أو: استخدم Firefox/Edge بدلاً من Chrome (أقل قفلاً)\n• أو: صدّر يدوياً: ثبّت إضافة 'Get cookies.txt LOCALLY' → افتح الموقع → Export → اختر الملف في خانة 'أو ملف cookies.txt'"
    },
    {
        "pattern": r"Failed to resolve.*googlevideo\.com|getaddrinfo failed.*googlevideo|rr\d+---sn-.*googlevideo",
        "title": "فشل DNS لمخدم الفيديو (googlevideo) — ليس بسبب الكوكيز",
        "msg": "yt-dlp استخرج معلومات الفيديو بنجاح (حتى مع الكوكيز الصحيحة)، لكن فشل في حل اسم مخدم الفيديو rr*---sn-*.googlevideo.com. هذه مشكلة شبكة/DNS محلية، وليست حجب كوكيز.",
        "fix": "• الكوكيز سليمة — لا تغيّرها. المشكلة شبكة فقط\n• جرّب: ipconfig /flushdns  ثم  netsh winsock reset  وأعد التشغيل\n• أوقف Force IPv4 في الواجهة وحاول، أو جرّبه مفعّل/معطّل بالتناوب\n• غيّر DNS إلى 1.1.1.1 و 8.8.8.8 (أنت عليه الآن لكن جرّب التبديل)\n• جرّب تحميل نفس الرابط على بيانات الجوال / VPN — إذا نجح فمزود الخدمة يحجب googlevideo\n• في الخيارات الإضافية أضف: --extractor-args \"youtube:player_client=android\"  أو جرّب جودة أقل (720p)\n• الملف الغريب C:/.../06c26081...txt في الأمر — احذفه من قائمة التحميل (سحب بالخطأ)"
    },
    {
        "pattern": r"Unable to extract og:title|Unable to extract.*Aparat",
        "title": "مستخرج Aparat معطّل — الموقع غيّر بنيته",
        "msg": "موقع aparat.com غيّر HTML ولم يعد يحتوي og:title. المستخرج الحالي يفشل (ليس مشكلة كوكيز أو شبكة).",
        "fix": "• حدّث yt-dlp فوراً: زر ⬆️ تحديث الآن أو yt-dlp -U — قد يكون الإصلاح في nightly\n• جرّب خياراً بديلاً في 'خيارات إضافية': --force-generic-extractor  أو  --impersonate chrome\n• أو حمّل عبر الرابط المضمن: https://www.aparat.com/embed/p511u4x  — الصقه في الواجهة\n• أبلغ المطورين: https://github.com/yt-dlp/yt-dlp/issues/new?template=extractor-bug.md  مع الرابط والـ log\n• مؤقتاً استخدم أدوات بديلة مثل gallery-dl أو JDownloader لموقع Aparat حتى يُصلح المستخرج"
    },
    {
        "pattern": r"Falling back on generic information extractor|Unsupported URL.*meyon|Unsupported URL.*generic",
        "title": "الموقع غير مدعوم (generic فشل)",
        "msg": "الموقع (meyon.com.ye وأمثاله) غير موجود في 1752 موقع مدعوم، والصفحات SPA تُحمّل الفيديو بـ JS — المستخرج العام لا يجد mp4 مباشر.",
        "fix": "• جرّب إضافتنا المستقلة: extension-standalone → افتح صفحة الفيديو → 🔍 فحص الفيديوهات → سيجد src المباشر بعد تحميل JS ثم ⬇️ تحميل\n• أو: افتح DevTools (F12) → Network → شغّل الفيديو → ابحث عن .mp4 أو m3u8 → انسخ الرابط المباشر والصقه في الواجهة مع --force-generic-extractor\n• أو اطلب منا بناء مستخرج مخصص: أرسل رابط API الظاهر في Network وسنضيفه"
    },
]

def diagnose_error(text):
    for item in ERROR_SOLUTIONS:
        if re.search(item["pattern"], text, re.I | re.S):
            return item
    return None

def find_ytdlp():
    # 1) إذا مجمّد كـ exe (PyInstaller onefile) → ابحث في _MEIPASS
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundled = Path(sys._MEIPASS) / "yt-dlp.exe"
        if bundled.exists():
            return str(bundled)
        bundled2 = Path(sys._MEIPASS) / "yt-dlp"
        if bundled2.exists():
            return str(bundled2)
    # 2) بجانب التطبيق (onedir أو script)
    try:
        local = Path(__file__).parent / "yt-dlp.exe"
        if local.exists():
            return str(local)
    except: pass
    # 3) بجانب الـ exe المجمد نفسه (onedir)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        for name in ["yt-dlp.exe", "yt-dlp"]:
            p = exe_dir / name
            if p.exists():
                return str(p)
    # 4) في PATH
    for c in ["yt-dlp", "yt-dlp.exe", shutil.which("yt-dlp")]:
        if c and shutil.which(c):
            return c
    # 5) مكتبة python المدمجة كـ fallback (ستُستخدم عبر python -m yt_dlp)
    try:
        import yt_dlp  # noqa
        return f"{sys.executable} -m yt_dlp"
    except: pass
    return "yt-dlp"

def find_js_runtime():
    """يكتشف محرك JS المتاح: deno > node"""
    for r in ["deno", "deno.exe", "node", "node.exe", "bun", "bun.exe"]:
        p = shutil.which(r)
        if p:
            # deno مفضل، لكن node يعمل إذا مُرر --js-runtimes node
            name = Path(p).stem.lower()
            return name, p
    return None, None

def find_ffmpeg():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        for n in ["ffmpeg.exe", "ffmpeg"]:
            p = Path(sys._MEIPASS) / n
            if p.exists():
                return True
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        for n in ["ffmpeg.exe", "ffmpeg"]:
            if (exe_dir / n).exists():
                return True
    return shutil.which("ffmpeg") is not None

def get_bundled_ffmpeg():
    """يرجع مسار ffmpeg المدمج إن وجد ليُمرر لـ yt-dlp عبر --ffmpeg-location"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        for n in ["ffmpeg.exe", "ffmpeg"]:
            p = Path(sys._MEIPASS) / n
            if p.exists():
                return str(p)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        for n in ["ffmpeg.exe", "ffmpeg"]:
            p = exe_dir / n
            if p.exists():
                return str(p)
    local = Path(__file__).parent / "ffmpeg.exe"
    if local.exists():
        return str(local)
    return None

def get_aparat_direct_url(aparat_url):
    """fallback لـ Aparat عبر API زر دانلود — يرجع رابط mp4 مباشر أو None"""
    try:
        m = re.search(r"/v/(?:#!)?([a-zA-Z0-9]+)", aparat_url)
        if not m:
            m = re.search(r"videohash/([a-zA-Z0-9]+)", aparat_url)
        if not m: return None
        vid = m.group(1)
        import urllib.request, ssl, json
        api = f"https://www.aparat.com/api/fa/v1/video/video/show/videohash/{vid}"
        ctx = ssl.create_default_context()
        req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0", "Referer": f"https://www.aparat.com/v/{vid}"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            data = json.loads(r.read().decode("utf-8"))
            attrs = data.get("data", {}).get("attributes", {})
            # file_link_all contains 144p-1080p
            fl = attrs.get("file_link_all")
            if fl and isinstance(fl, list) and fl:
                # اختر أعلى جودة (آخر عنصر 1080p)
                best = max(fl, key=lambda x: int(x.get("profile","0").replace("p","") or 0))
                urls = best.get("urls")
                if urls and urls[0]:
                    return urls[0]
            # fallback file_link
            if attrs.get("file_link"):
                return attrs["file_link"]
            if attrs.get("hls_link"):
                return attrs["hls_link"]
    except Exception:
        pass
    return None

def get_meyon_direct_url(meyon_url):
    """fallback لـ Meyon عبر embed API — يرجع HLS مباشر أو None"""
    try:
        # استخرج uuid من /videos/embed/UUID أو /w/shortUUID أو /shorts/xxx
        m = re.search(r"/videos/(?:embed|watch)/([a-f0-9\-]+)", meyon_url)
        if not m:
            m = re.search(r"/(?:shorts|w)/([A-Za-z0-9]+)", meyon_url)
            if m:
                # حاول جلب الصفحة لاستخراج embed uuid (shorts و /w/ يحتاجان تحويل)
                import urllib.request, ssl
                ctx = ssl.create_default_context()
                # Meyon يحتاج متابعة إعادة التوجيه لـ /w/
                req = urllib.request.Request(meyon_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
                    final_url = r.geturl()
                    html = r.read().decode("utf-8", errors="ignore")
                    # جرّب من الـ final URL نفسه
                    m2 = re.search(r"/videos/(?:embed|watch)/([a-f0-9\-]+)", final_url)
                    if not m2:
                        m2 = re.search(r"/videos/(?:embed|watch)/([a-f0-9\-]+)", html)
                    if m2:
                        m = m2
                    else:
                        # fallback: ابحث عن uuid في JSON المضمن
                        m3 = re.search(r'"uuid"\s*:\s*"([a-f0-9\-]+)"', html)
                        if m3:
                            m = m3
                        else:
                            # جرّب API shorts مباشرة
                            try:
                                api_short = f"https://meyon.com.ye/api/v1/videos/{m.group(1)}"
                                req2 = urllib.request.Request(api_short, headers={"User-Agent": "Mozilla/5.0"})
                                with urllib.request.urlopen(req2, timeout=10, context=ctx) as r2:
                                    data2 = r2.read().decode("utf-8", errors="ignore")
                                    m4 = re.search(r'"uuid"\s*:\s*"([a-f0-9\-]+)"', data2)
                                    if m4:
                                        m = m4
                                    else:
                                        return None
                            except: return None
            else:
                return None
        vid = m.group(1)
        import urllib.request, ssl, json
        api = f"https://meyon.com.ye/api/v1/videos/{vid}"
        ctx = ssl.create_default_context()
        req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            data = json.loads(r.read().decode("utf-8"))
            pls = data.get("streamingPlaylists", [])
            if pls and isinstance(pls, list) and pls[0].get("files"):
                files = pls[0]["files"]
                best = max(files, key=lambda x: int(x.get("resolution",{}).get("label","0").replace("p","") or 0))
                # fileDownloadUrl يعمل بدون Referer، fileUrl يحتاج Referer
                if best.get("fileDownloadUrl"):
                    return best["fileDownloadUrl"]
                if best.get("fileUrl"):
                    return best["fileUrl"]
            files = data.get("files", [])
            if files and files[0].get("fileUrl"):
                return files[0]["fileUrl"]
            if files and files[0].get("fileDownloadUrl"):
                return files[0]["fileDownloadUrl"]
    except Exception:
        pass
    return None

# ---------- خادم الإضافة (يستقبل روابط من المتصفح) ----------
EXTENSION_PORT = 8765
class _ExtensionHandler(BaseHTTPRequestHandler):
    app = None  # سيُعيّن عند التشغيل
    def _set_cors(self, code=200):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
    def do_OPTIONS(self):
        self._set_cors(204)
    def do_GET(self):
        if self.path in ("/ping", "/status"):
            self._set_cors(200)
            info = {"ok": True, "version": APP_VERSION, "port": EXTENSION_PORT}
            try:
                info["downloading"] = bool(self.app and self.app.downloading)
                info["yt_dlp"] = getattr(self.app, "current_version", "")
            except: pass
            self.wfile.write(json.dumps(info, ensure_ascii=False).encode("utf-8"))
        else:
            self._set_cors(404)
            self.wfile.write(json.dumps({"ok": False, "error": "not found"}).encode("utf-8"))
    def do_POST(self):
        if self.path != "/download":
            self._set_cors(404)
            self.wfile.write(json.dumps({"ok": False, "error": "not found"}).encode("utf-8"))
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            data = json.loads(body.decode("utf-8") or "{}")
            url = (data.get("url") or "").strip()
            if not url or not re.match(r"https?://", url):
                self._set_cors(400)
                self.wfile.write(json.dumps({"ok": False, "error": "رابط غير صالح"}).encode("utf-8"))
                return
            # أرسل للواجهة — أضف للقائمة المتوازية (لا يعلق)
            def _start():
                try:
                    self.app.add_url_to_queue_external(url)
                    # شغّل تلقائياً إذا لم يكن هناك تحميل نشط (تجربة سلسة)
                    def _auto():
                        try:
                            if self.app._active_downloads == 0:
                                # ابدأ فقط العناصر المنتظرة
                                pending = [iid for iid in self.app.queue_tree.get_children() if self.app.queue_tree.set(iid, "status") == "⏳ انتظار"]
                                if pending:
                                    self.app.after(300, self.app.start_parallel)
                        except: pass
                    self.app.after(400, _auto)
                    self.app.log_msg(f"🔗 رابط من الإضافة أضيف للقائمة: {url}", "ok")
                    self.app.status_var.set("رابط من الإضافة أضيف للقائمة")
                except Exception as e:
                    self.app.log_msg(f"فشل إضافة رابط الإضافة: {e}", "err")
            self.app.after(0, _start)
            self._set_cors(200)
            self.wfile.write(json.dumps({"ok": True, "url": url}).encode("utf-8"))
        except Exception as e:
            self._set_cors(500)
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
    def log_message(self, format, *args):
        # اكتم سجل http الافتراضي — نكتبه في سجل التطبيق فقط للأخطاء
        return

class YtDlpGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("900x860")
        self.minsize(900, 820)
        # أيقونة النافذة وشريط المهام — app.ico للـ bitmap + PNG للـ HiDPI
        try:
            import ctypes
            try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("yt-dlp.GUI.1.0")
            except: pass
            # ابحث عن ICO
            icon_ico = None
            candidates_ico = []
            if getattr(sys, 'frozen', False):
                if hasattr(sys, '_MEIPASS'):
                    candidates_ico += [Path(sys._MEIPASS)/"app.ico", Path(sys._MEIPASS)/"_internal"/"app.ico"]
                candidates_ico += [Path(sys.executable).parent/"app.ico", Path(sys.executable).parent/"_internal"/"app.ico"]
            candidates_ico.append(Path(__file__).parent/"app.ico")
            for c in candidates_ico:
                if c.exists():
                    icon_ico = c; break
            if icon_ico:
                try: self.iconbitmap(str(icon_ico))
                except: pass
            # PNG لـ iconphoto (يدعم HiDPI وشريط المهام أفضل)
            icon_png = None
            candidates_png = []
            if getattr(sys, 'frozen', False):
                if hasattr(sys, '_MEIPASS'):
                    candidates_png += [Path(sys._MEIPASS)/"icon.png", Path(sys._MEIPASS)/"_internal"/"icon.png", Path(sys._MEIPASS)/"yt-dlp-logo.png"]
                candidates_png += [Path(sys.executable).parent/"icon.png", Path(sys.executable).parent/"_internal"/"icon.png"]
            candidates_png += [Path(__file__).parent/"icon.png", Path(__file__).parent/"yt-dlp-logo.png"]
            for c in candidates_png:
                if c.exists():
                    icon_png = c; break
            if icon_png:
                try:
                    img = tk.PhotoImage(file=str(icon_png))
                    self.iconphoto(True, img)
                    self._icon_img = img
                except: pass
            if not icon_ico and not icon_png:
                self.iconbitmap(default="")
        except: pass

        self.proc = None
        self.q = queue.Queue()
        self.downloading = False
        self.current_version = ""
        self.latest_version = ""
        self._checking = False
        self._queue_counter = 0
        self._active_downloads = 0
        self._queue_lock = threading.Lock()
        self._active_procs = {}  # iid -> proc for parallel
        self._aparat_retry = False
        self._meyon_retry = False
        self._stop_all = False
        self._stop_ids = set()
        self.net_speed_var = tk.StringVar(value="--")
        self.size_var = tk.StringVar(value="")

        self.create_style()
        self.create_widgets()
        self.load_preferences()  # حمّل تفضيلات المستخدم المحفوظة
        self._bind_auto_save()   # حفظ تلقائي عند أي تغيير
        self.check_environment()
        self.start_extension_server()
        self.after(100, self.poll_queue)
        # فحص تلقائي للتحديث بعد 3 ثواني من التشغيل
        self.after(3000, lambda: self.check_for_update(auto=True))
        # حفظ تلقائي عند الإغلاق
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def create_style(self):
        style = ttk.Style(self)
        # نستخدم clam لأنه الوحيد الذي يحترم الألوان المخصصة على ويندوز
        try: style.theme_use("clam")
        except: pass
        style.configure("TButton", padding=6, font=("Segoe UI", 9))
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Hint.TLabel", foreground="#555", font=("Segoe UI", 8))

        # ---- ألوان معبرة حسب الوظيفة ----
        # أخضر = تحميل/نجاح، أحمر = إيقاف/خطر، أزرق = أساسي، برتقالي = تحديث، رمادي = ثانوي
        style.configure("Success.TButton", background="#16a34a", foreground="white", bordercolor="#15803d")
        style.map("Success.TButton", background=[("active","#15803d"),("disabled","#a7f3d0")], foreground=[("disabled","#555")])

        style.configure("Danger.TButton", background="#dc2626", foreground="white", bordercolor="#b91c1c")
        style.map("Danger.TButton", background=[("active","#b91c1c"),("disabled","#fecaca")], foreground=[("disabled","#555")])

        style.configure("Primary.TButton", background="#2563eb", foreground="white", bordercolor="#1d4ed8")
        style.map("Primary.TButton", background=[("active","#1d4ed8"),("disabled","#bfdbfe")], foreground=[("disabled","#555")])

        style.configure("Warning.TButton", background="#ea580c", foreground="white", bordercolor="#c2410c")
        style.map("Warning.TButton", background=[("active","#c2410c"),("disabled","#fed7aa")], foreground=[("disabled","#555")])

        style.configure("Secondary.TButton", background="#64748b", foreground="white", bordercolor="#475569")
        style.map("Secondary.TButton", background=[("active","#475569"),("disabled","#e2e8f0")], foreground=[("disabled","#555")])

        style.configure("Info.TButton", background="#0891b2", foreground="white", bordercolor="#0e7490")
        style.map("Info.TButton", background=[("active","#0e7490"),("disabled","#a5f3fc")], foreground=[("disabled","#555")])

    def create_widgets(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        # Header
        hdr = ttk.Frame(root)
        hdr.pack(fill="x", pady=(0,10))
        hdr_l = ttk.Frame(hdr); hdr_l.pack(side="left")
        ttk.Label(hdr_l, text="⬇️  محمل الفيديو الشامل", style="Title.TLabel").pack(side="left")
        ttk.Label(hdr_l, text=f"  yt-dlp GUI  •  {APP_VERSION}", foreground="#777").pack(side="left", padx=8)
        self.version_lbl = ttk.Label(hdr_l, text="…", foreground="#0a7", font=("Segoe UI", 8, "bold"))
        self.version_lbl.pack(side="left", padx=10)
        self.ext_status_lbl = ttk.Label(hdr_l, text="الإضافة: ...", foreground="#64748b", font=("Segoe UI", 7))
        self.ext_status_lbl.pack(side="left", padx=6)
        # سرعة الإنترنت في الأعلى
        ttk.Label(hdr_l, text="⚡ السرعة:", foreground="#555", font=("Segoe UI", 7)).pack(side="left", padx=(10,2))
        ttk.Label(hdr_l, textvariable=self.net_speed_var, foreground="#2563eb", font=("Segoe UI", 8, "bold")).pack(side="left")
        # أزرار التحديث - ألوان معبرة
        ttk.Button(hdr, text="⬆️ تحديث الآن", command=self.do_update, style="Warning.TButton").pack(side="right")
        ttk.Button(hdr, text="🔍 فحص التحديث", command=lambda: self.check_for_update(auto=False), style="Primary.TButton").pack(side="right", padx=4)
        ttk.Button(hdr, text="📂 فتح مجلد التحميل", command=self.open_output, style="Secondary.TButton").pack(side="right", padx=4)

        # Notebook - تبويبات
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, pady=4)
        tab_dl = ttk.Frame(nb, padding=8)
        tab_opt = ttk.Frame(nb, padding=8)
        nb.add(tab_dl, text="⬇️ التحميل")
        nb.add(tab_opt, text="⚙️ الإعدادات")

        # ===== تبويب التحميل =====
        # URL
        url_fr = ttk.LabelFrame(tab_dl, text=" 1- الرابط (الصق هنا) ", padding=10)
        url_fr.pack(fill="x", pady=4)
        self.url_var = tk.StringVar()
        ent = ttk.Entry(url_fr, textvariable=self.url_var, font=("Segoe UI", 11))
        ent.pack(side="left", fill="x", expand=True, padx=(0,6))
        ent.bind("<Control-v>", lambda e: self.after(100, self.auto_detect))
        ent.bind("<KeyRelease>", lambda e: self.auto_detect())
        ttk.Button(url_fr, text="📋 لصق", width=8, command=self.do_paste, style="Primary.TButton").pack(side="left", padx=2)
        ttk.Button(url_fr, text="✕ مسح", width=8, command=lambda: self.url_var.set(""), style="Secondary.TButton").pack(side="left", padx=2)
        self.detect_lbl = ttk.Label(url_fr, text="—", foreground="#0a7")
        self.detect_lbl.pack(side="left", padx=8)
        ttk.Label(url_fr, textvariable=self.size_var, foreground="#8e44ad", font=("Segoe UI", 8, "bold")).pack(side="left", padx=6)
        # أزرار سريعة للقائمة
        ttk.Button(url_fr, text="➕ إضافة للقائمة", width=14, command=self.add_to_queue, style="Success.TButton").pack(side="left", padx=4)

        # Queue - قائمة التحميل المتوازي
        q_fr = ttk.LabelFrame(tab_dl, text=" 1-ب: قائمة التحميل (متوازي - لا يعلق الواجهة) ", padding=8)
        q_fr.pack(fill="both", expand=False, pady=4)
        q_top = ttk.Frame(q_fr); q_top.pack(fill="x")
        ttk.Label(q_top, text="الروابط:").pack(side="left")
        self.parallel_var = tk.StringVar(value="3")
        ttk.Label(q_top, text="توازي:").pack(side="right", padx=(8,2))
        ttk.Spinbox(q_top, from_=1, to=5, textvariable=self.parallel_var, width=3, state="readonly").pack(side="right")
        ttk.Button(q_top, text="🗑️ مسح الكل", command=self.clear_queue, style="Secondary.TButton").pack(side="right", padx=4)
        ttk.Button(q_top, text="❌ حذف المحدد", command=self.remove_selected, style="Secondary.TButton").pack(side="right", padx=4)
        ttk.Button(q_top, text="▶️ تحميل الكل (متوازي)", command=self.start_parallel, style="Success.TButton").pack(side="right", padx=4)
        cols = ("url", "size", "status", "progress")
        self.queue_tree = ttk.Treeview(q_fr, columns=cols, show="headings", height=5, selectmode="extended")
        self.queue_tree.heading("url", text="الرابط")
        self.queue_tree.heading("size", text="الحجم")
        self.queue_tree.heading("status", text="الحالة")
        self.queue_tree.heading("progress", text="التقدم")
        self.queue_tree.column("url", width=340)
        self.queue_tree.column("size", width=90, anchor="center")
        self.queue_tree.column("status", width=110, anchor="center")
        self.queue_tree.column("progress", width=80, anchor="center")
        self.queue_tree.pack(fill="both", expand=True, pady=4)
        qb = ttk.Scrollbar(q_fr, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=qb.set)
        ttk.Label(q_fr, text="الصق عدة روابط (كل رابط في سطر) ثم ➕ إضافة | أو أرسل من الإضافة وسيُضاف تلقائياً", style="Hint.TLabel").pack(anchor="w")

        # Options في تبويب الإعدادات
        opt_fr = ttk.LabelFrame(tab_opt, text=" 2- خيارات التحميل ", padding=10)
        opt_fr.pack(fill="x", pady=4)

        # row 1
        r1 = ttk.Frame(opt_fr); r1.pack(fill="x", pady=3)
        ttk.Label(r1, text="الجودة:").pack(side="left")
        self.quality_var = tk.StringVar(value="الأفضل تلقائياً (best)")
        ttk.Combobox(r1, textvariable=self.quality_var, width=24, state="readonly",
                     values=["الأفضل تلقائياً (best)","1080p","720p","480p","360p","الأسوأ (worst)"]
                     ).pack(side="left", padx=6)
        ttk.Label(r1, text="الصيغة:").pack(side="left", padx=(14,0))
        self.format_var = tk.StringVar(value="mp4 (فيديو)")
        ttk.Combobox(r1, textvariable=self.format_var, width=20, state="readonly",
                     values=["mp4 (فيديو)","mkv","webm","mp3 (صوت فقط)","m4a (صوت)","wav"]
                     ).pack(side="left", padx=6)
        self.audio_only_var = tk.BooleanVar(value=False)
        # self kept but not shown

        # row 2 - output
        r2 = ttk.Frame(opt_fr); r2.pack(fill="x", pady=6)
        ttk.Label(r2, text="مجلد الحفظ:").pack(side="left")
        self.out_var = tk.StringVar(value=DEFAULT_OUTPUT)
        ttk.Entry(r2, textvariable=self.out_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(r2, text="📁 تصفح", command=self.browse_out, style="Secondary.TButton").pack(side="left")

        # filename template
        r2b = ttk.Frame(opt_fr); r2b.pack(fill="x", pady=3)
        ttk.Label(r2b, text="قالب الاسم:").pack(side="left")
        self.tmplate_var = tk.StringVar(value="%(title)s.%(ext)s")
        ttk.Entry(r2b, textvariable=self.tmplate_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Label(r2b, text='مثال: %(uploader)s - %(title)s', style="Hint.TLabel").pack(side="left")

        # checks row
        r3 = ttk.Frame(opt_fr); r3.pack(fill="x", pady=6)
        self.sub_var = tk.BooleanVar(value=False)
        self.sub_only_var = tk.BooleanVar(value=False)
        self.thumb_var = tk.BooleanVar(value=False)
        self.playlist_var = tk.BooleanVar(value=False)
        self.ipv4_var = tk.BooleanVar(value=True)
        self.sponsor_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r3, text="تحميل الترجمة", variable=self.sub_var, command=self._on_sub_toggle).pack(side="left", padx=6)
        ttk.Checkbutton(r3, text="📝 الترجمة فقط (بدون فيديو)", variable=self.sub_only_var, command=self._on_sub_only_toggle).pack(side="left", padx=6)
        ttk.Checkbutton(r3, text="تحميل الصورة المصغرة", variable=self.thumb_var).pack(side="left", padx=6)
        ttk.Checkbutton(r3, text="تحميل القائمة كاملة (playlist)", variable=self.playlist_var).pack(side="left", padx=6)
        ttk.Checkbutton(r3, text="Force IPv4 (يحل مشكلة DNS)", variable=self.ipv4_var).pack(side="left", padx=6)

        r3b = ttk.Frame(opt_fr); r3b.pack(fill="x")
        ttk.Checkbutton(r3b, text="حذف الإعلانات (SponsorBlock)", variable=self.sponsor_var).pack(side="left", padx=6)
        ttk.Label(r3b, text="Timeout:").pack(side="left", padx=(18,4))
        self.timeout_var = tk.StringVar(value="60")
        ttk.Spinbox(r3b, from_=10, to=300, increment=10, textvariable=self.timeout_var, width=5).pack(side="left")
        ttk.Label(r3b, text="ثانية").pack(side="left", padx=4)

        # صف خيارات الترجمة — يظهر عند تفعيل الترجمة
        r3c = ttk.Frame(opt_fr); r3c.pack(fill="x", pady=4)
        self.sub_opts_frame = r3c
        ttk.Label(r3c, text="لغة الترجمة:").pack(side="left", padx=(6,2))
        self.sub_langs_var = tk.StringVar(value="ar,en")
        self.sub_langs_combo = ttk.Combobox(r3c, textvariable=self.sub_langs_var, width=14,
                     values=["ar,en","ar","en","ar,en,fr","all","auto"], state="normal")
        self.sub_langs_combo.pack(side="left", padx=2)
        ttk.Label(r3c, text="صيغة:").pack(side="left", padx=(8,2))
        self.sub_format_var = tk.StringVar(value="vtt (افتراضي)")
        self.sub_format_combo = ttk.Combobox(r3c, textvariable=self.sub_format_var, width=14, state="readonly",
                     values=["vtt (افتراضي)","srt","ass","lrc"])
        self.sub_format_combo.pack(side="left", padx=2)
        self.convert_sub_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(r3c, text="تحويل لـ srt", variable=self.convert_sub_var).pack(side="left", padx=6)
        ttk.Label(r3c, text="(اتركه فارغ للتلقائي)", style="Hint.TLabel").pack(side="left", padx=4)

        # cookies — تلقائي من المتصفح + يدوي cookies.txt
        r4a = ttk.Frame(opt_fr); r4a.pack(fill="x", pady=4)
        ttk.Label(r4a, text="الكوكيز (للمحتوى الخاص):").pack(side="left")
        self.browser_var = tk.StringVar(value="بدون (يدوي)")
        self.browser_combo = ttk.Combobox(r4a, textvariable=self.browser_var, width=18, state="readonly",
                     values=["بدون (يدوي)","chrome","edge","firefox","brave","opera","vivaldi","chromium"])
        self.browser_combo.pack(side="left", padx=6)
        ttk.Button(r4a, text="🔑 التقاط من المتصفح", command=self.capture_browser_cookies, style="Primary.TButton").pack(side="left", padx=4)
        ttk.Button(r4a, text="اختبار", command=self.test_browser_cookies, style="Info.TButton").pack(side="left", padx=2)
        ttk.Label(r4a, text="يقرأ مباشرة من المتصفح المفتوح", style="Hint.TLabel").pack(side="left", padx=6)

        r4 = ttk.Frame(opt_fr); r4.pack(fill="x", pady=4)
        self.cookie_var = tk.StringVar(value="")
        ttk.Label(r4, text="أو ملف cookies.txt:").pack(side="left")
        ttk.Entry(r4, textvariable=self.cookie_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(r4, text="📁 اختيار", command=self.browse_cookie, style="Info.TButton").pack(side="left", padx=2)
        ttk.Label(r4, text="(بديل يدوي)", style="Hint.TLabel").pack(side="left", padx=4)

        # proxy + extra
        r5 = ttk.Frame(opt_fr); r5.pack(fill="x", pady=3)
        ttk.Label(r5, text="Proxy:").pack(side="left")
        self.proxy_var = tk.StringVar(value="")
        ttk.Entry(r5, textvariable=self.proxy_var, width=22).pack(side="left", padx=6)
        ttk.Label(r5, text="خيارات إضافية:").pack(side="left", padx=(10,4))
        self.extra_var = tk.StringVar(value="")
        ttk.Entry(r5, textvariable=self.extra_var).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Label(r5, text='مثال: --sleep-requests 1', style="Hint.TLabel").pack(side="left")

        # Progress + Buttons + Log في تبويب التحميل
        prog_fr = ttk.Frame(tab_dl); prog_fr.pack(fill="x", pady=6)
        self.progress = ttk.Progressbar(prog_fr, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=2)
        info = ttk.Frame(prog_fr); info.pack(fill="x")
        self.status_var = tk.StringVar(value="جاهز — الصق الرابط واضغط تحميل")
        ttk.Label(info, textvariable=self.status_var, foreground="#333", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.speed_var = tk.StringVar(value="")
        ttk.Label(info, textvariable=self.speed_var, foreground="#555").pack(side="right")

        btn_fr = ttk.Frame(tab_dl); btn_fr.pack(fill="x", pady=4)
        self.dl_btn = ttk.Button(btn_fr, text="⬇️  تحميل الآن", command=self.on_big_download, style="Success.TButton")
        self.dl_btn.pack(side="left", fill="x", expand=True, padx=(0,6), ipady=8)
        self.stop_btn = ttk.Button(btn_fr, text="⏹ إيقاف", command=self.stop_download, state="disabled", style="Danger.TButton")
        self.stop_btn.pack(side="left", padx=4, ipady=8)
        ttk.Button(btn_fr, text="🧹 مسح السجل", command=self.clear_log, style="Secondary.TButton").pack(side="left", padx=4)
        ttk.Button(btn_fr, text="📋 نسخ السجل", command=self.copy_log, style="Info.TButton").pack(side="left", padx=4)
        ttk.Button(btn_fr, text="↩️ استعادة الافتراضي", command=self.restore_defaults, style="Secondary.TButton").pack(side="left", padx=4)

        log_fr = ttk.LabelFrame(tab_dl, text=" السجل والتشخيص ", padding=6)
        log_fr.pack(fill="both", expand=True, pady=4)
        self.log = tk.Text(log_fr, height=10, wrap="word", font=("Consolas", 9), bg="#0f1117", fg="#d6deeb", insertbackground="white")
        self.log.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(log_fr, command=self.log.yview)
        sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=sb.set)
        self.log.tag_config("err", foreground="#ff6b6b")
        self.log.tag_config("ok", foreground="#51cf66")
        self.log.tag_config("warn", foreground="#fcc419")
        self.log.tag_config("info", foreground="#74c0fc")

        foot = ttk.Label(root, text="نصيحة: حدّث yt-dlp باستمرار — تيك توك يغيّر حمايته كل أسابيع.  •  github.com/yt-dlp/yt-dlp", style="Hint.TLabel")
        foot.pack(pady=(2,0))

        # إصلاح اختصارات الكيبورد مع التخطيط العربي + قائمة كليك يمين
        self._fix_arabic_shortcuts(root)
        # حالة خيارات الترجمة الابتدائية
        self.after(100, self._on_sub_toggle)

    # ---------- إصلاح تخطيط لوحة المفاتيح العربية ----------
    def _fix_arabic_shortcuts(self, root):
        """يجعل Ctrl+C/V/X/A/Z يعمل حتى لو التخطيط عربي (ر، ؤ، ء، ش، ئ)"""
        # ربط عام على مستوى keycode (يعمل مع كل اللغات)
        def on_ctrl_key(event):
            # تحقق أن Ctrl مضغوط (state bit 4 على ويندوز)
            is_ctrl = (event.state & 0x4) != 0
            # بعض الأنظمة ترسل state=12 مع Ctrl، لذا نتحقق أيضاً من keysym إذا كان Ctrl
            if not is_ctrl:
                # fallback: تحقق من أن الحدث جاء مع Control في مواصفات الربط
                # bind_all مع <Control-KeyPress> يضمن أصلاً أن Ctrl مضغوط، لذا نعتبره Ctrl
                is_ctrl = True
            kc = event.keycode
            # خريطة keycode الفيزيائية (ثابتة مهما كان التخطيط)
            # 86=V(ر) لصق، 67=C(ؤ) نسخ، 88=X(ء) قص، 65=A(ش) تحديد الكل، 90=Z(ئ) تراجع، 89=Y(غ) إعادة
            mapping = {86: "<<Paste>>", 67: "<<Copy>>", 88: "<<Cut>>", 65: "<<SelectAll>>", 90: "<<Undo>>", 89: "<<Redo>>"}
            virt = mapping.get(kc)
            # fallback إضافي عبر الحرف العربي نفسه (في حال keycode مختلف في بعض الأنظمة)
            if not virt:
                ch = event.char  # الحرف الناتج (ر، ؤ، ء، ش، ئ)
                char_map = {"ر": "<<Paste>>", "ؤ": "<<Copy>>", "ء": "<<Cut>>", "ش": "<<SelectAll>>", "ئ": "<<Undo>>", "غ": "<<Redo>>",
                            "ﻻ": "<<Paste>>"}  # بعض التخطيطات
                virt = char_map.get(ch)
            if virt:
                try:
                    w = event.widget
                    # فقط للحقول النصية
                    if isinstance(w, (tk.Entry, ttk.Entry, tk.Text)):
                        w.event_generate(virt)
                    else:
                        # حاول على الفوكس الحالي
                        foc = self.focus_get()
                        if isinstance(foc, (tk.Entry, ttk.Entry, tk.Text)):
                            foc.event_generate(virt)
                except: pass
                return "break"

        # bind_all يلتقط كل ضغطات Ctrl+حرف قبل المعالجة الافتراضية
        self.bind_all("<Control-KeyPress>", on_ctrl_key)

        # قائمة كليك يمين للصق (بديل بصري)
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="✂️ قص", command=lambda: self.focus_get() and self.focus_get().event_generate("<<Cut>>"))
        menu.add_command(label="📋 نسخ", command=lambda: self.focus_get() and self.focus_get().event_generate("<<Copy>>"))
        menu.add_command(label="📄 لصق", command=lambda: self.focus_get() and self.focus_get().event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="🔘 تحديد الكل", command=lambda: self.focus_get() and self.focus_get().event_generate("<<SelectAll>>"))
        def show_menu(e):
            try:
                if isinstance(e.widget, (tk.Entry, ttk.Entry, tk.Text)):
                    menu.tk_popup(e.x_root, e.y_root)
            finally:
                menu.grab_release()
        self.bind_all("<Button-3>", show_menu)
        # Shift+F10 و Menu key
        self.bind_all("<Shift-F10>", lambda e: show_menu(e))

    # ---------- helpers ----------
    def log_msg(self, msg, tag="info"):
        self.log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n", tag)
        self.log.see("end")

    def auto_detect(self):
        url = self.url_var.get().strip()
        if not url:
            self.detect_lbl.config(text="—")
            self.size_var.set("")
            return
        if "tiktok.com" in url: self.detect_lbl.config(text="🎵 TikTok")
        elif "youtube.com" in url or "youtu.be" in url: self.detect_lbl.config(text="▶️ YouTube")
        elif "instagram.com" in url: self.detect_lbl.config(text="📸 Instagram")
        elif "facebook.com" in url or "fb.watch" in url: self.detect_lbl.config(text="📘 Facebook")
        elif "twitter.com" in url or "x.com" in url: self.detect_lbl.config(text="🐦 X/Twitter")
        elif "soundcloud.com" in url: self.detect_lbl.config(text="🎧 SoundCloud")
        elif "aparat.com" in url: self.detect_lbl.config(text="🎬 Aparat")
        elif "meyon.com.ye" in url: self.detect_lbl.config(text="🎬 Meyon")
        else: self.detect_lbl.config(text="🌐 رابط عام")
        # جلب الحجم في الخلفية
        if re.match(r"https?://", url) and len(url) > 12:
            self.size_var.set("⏳ جاري الحساب...")
            threading.Thread(target=self._fetch_single_size, args=(url,), daemon=True).start()

    def do_paste(self):
        try:
            txt = self.clipboard_get()
            self.url_var.set(txt.strip())
            self.auto_detect()
        except: pass

    def browse_out(self):
        d = filedialog.askdirectory(initialdir=self.out_var.get() or str(Path.home()))
        if d: self.out_var.set(d)

    def browse_cookie(self):
        f = filedialog.askopenfilename(title="اختر cookies.txt", filetypes=[("Text","*.txt"),("All","*.*")])
        if f:
            self.cookie_var.set(f)
            self.browser_var.set("بدون (يدوي)")
            self.save_preferences()

    def capture_browser_cookies(self):
        br = self.browser_var.get()
        if br.startswith("بدون"):
            messagebox.showinfo("تنبيه", "اختر المتصفح أولاً (chrome / edge / firefox ...)")
            return
        y = find_ytdlp()
        self.log_msg(f"🔑 جاري التقاط الكوكيز من {br} ...", "info")
        self.status_var.set(f"جاري التقاط الكوكيز من {br}...")
        def run():
            try:
                test_cmd = y.split() if " -m " in y else [y]
                p = subprocess.run(test_cmd + ["--cookies-from-browser", br, "--skip-download", "--simulate", "https://www.youtube.com/watch?v=BaW_jenozKc"],
                                   capture_output=True, text=True, timeout=25)
                out = (p.stdout or "") + (p.stderr or "")
                low = out.lower()
                # نجاح — حتى لو 403 فالكوكيز قُرئت
                if "could not copy chrome cookie database" in low or "7271" in low:
                    # خطأ Chrome المقفل — تشخيص مخصص
                    diag = diagnose_error(out)
                    self.q.put(("log", f"❌ فشل نسخ كوكيز Chrome — المتصفح مفتوح ويقفل الملف", "err"))
                    if diag:
                        self.q.put(("log", f"الحل:\n{diag['fix']}", "warn"))
                    self.q.put(("log", out[:900], "info"))
                    self.q.put(("status", "Chrome مقفل — أغلقه وحاول"))
                    self.q.put(("show_cookie_help", br))
                    return
                if p.returncode == 0:
                    self.q.put(("log", f"✅ التقاط الكوكيز من {br} نجح — سيُستخدم في التحميل القادم", "ok"))
                    self.q.put(("status", f"الكوكيز من {br} جاهز ✅"))
                    self.q.put(("save_prefs", None))
                    return
                # حالات فشل أخرى
                if "not found" in low or "could not find" in low:
                    self.q.put(("log", f"❌ المتصفح {br} غير موجود أو لا توجد بيانات كوكيز\n{out[:700]}", "err"))
                elif "lock" in low or "cannot open" in low or "in use" in low:
                    self.q.put(("log", f"⚠️ أغلق المتصفح {br} تماماً ثم حاول مرة أخرى\n{out[:700]}", "warn"))
                    self.q.put(("show_cookie_help", br))
                else:
                    # حتى مع بعض الأخطاء قد تكون الكوكيز قُرئت جزئياً
                    if "extracting cookies" in low:
                        self.q.put(("log", f"✅ تم استخراج الكوكيز من {br} (مع تحذيرات)\n{out[:700]}", "ok"))
                        self.q.put(("status", f"الكوكيز من {br} جاهز ✅"))
                        self.q.put(("save_prefs", None))
                        return
                    self.q.put(("log", out[:900], "info"))
                self.q.put(("status", "فشل التقاط الكوكيز — راجع السجل"))
            except Exception as e:
                self.q.put(("log", f"فشل التقاط الكوكيز: {e}", "err"))
                self.q.put(("status", "فشل التقاط الكوكيز"))
        threading.Thread(target=run, daemon=True).start()

    def _show_cookie_help(self, br):
        win = tk.Toplevel(self)
        win.title("حل مشكلة كوكيز Chrome")
        win.geometry("620x420")
        win.transient(self); win.grab_set()
        frm = ttk.Frame(win, padding=14); frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="❌ فشل نسخ كوكيز Chrome — المتصفح مقفل", font=("Segoe UI", 11, "bold"), foreground="#c00").pack(anchor="w")
        ttk.Label(frm, text=f"السبب: {br} مفتوح ويقفل ملف Cookies. yt-dlp لا يستطيع نسخه أثناء التشغيل.\nاختر أحد الحلول التالية:", wraplength=580, justify="left").pack(anchor="w", pady=8)
        txt = tk.Text(frm, height=12, wrap="word", font=("Segoe UI", 9), bg="#fff8e1")
        txt.pack(fill="both", expand=True, pady=6)
        txt.insert("1.0",
            "1) الحل السريع (مستحسن):\n"
            "   • أغلق Chrome تماماً (X)\n"
            "   • افتح Task Manager (Ctrl+Shift+Esc) → أنهِ كل عمليات chrome.exe\n"
            "   • في التطبيق اضغط '🔑 التقاط من المتصفح' مرة أخرى\n\n"
            "2) عطّل التشغيل في الخلفية:\n"
            "   Chrome → Settings → System → أوقف 'Continue running background apps when Chrome is closed'\n\n"
            "3) استخدم متصفحاً آخر:\n"
            "   اختر 'firefox' أو 'edge' من القائمة (أقل قفلاً) ثم التقاط\n\n"
            "4) التصدير اليدوي (مضمون 100%):\n"
            "   • ثبّت إضافة 'Get cookies.txt LOCALLY' من Chrome Web Store\n"
            "   • افتح youtube.com / tiktok.com وسجّل دخولك\n"
            "   • اضغط الإضافة → Export → احفظ cookies.txt\n"
            "   • في التطبيق: 'أو ملف cookies.txt → 📁 اختيار' واختر الملف\n"
        )
        txt.config(state="disabled")
        btns = ttk.Frame(frm); btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="فتح Task Manager", command=lambda: subprocess.Popen("taskmgr", shell=True)).pack(side="left")
        ttk.Button(btns, text="فتح chrome://settings/system", command=lambda: webbrowser.open("chrome://settings/system")).pack(side="left", padx=6)
        ttk.Button(btns, text="إغلاق", command=win.destroy).pack(side="right")

    def test_browser_cookies(self):
        br = self.browser_var.get()
        if br.startswith("بدون"):
            messagebox.showinfo("تنبيه", "اختر المتصفح أولاً لاختباره")
            return
        self.capture_browser_cookies()

    def open_output(self):
        p = Path(self.out_var.get())
        p.mkdir(parents=True, exist_ok=True)
        try: os.startfile(str(p))
        except: webbrowser.open(str(p))

    def clear_log(self):
        self.log.delete("1.0","end")

    def copy_log(self):
        txt = self.log.get("1.0","end")
        self.clipboard_clear(); self.clipboard_append(txt)
        self.status_var.set("تم نسخ السجل ✅")

    def restore_defaults(self):
        """يعيد كل خيارات الواجهة للوضع الافتراضي"""
        if not messagebox.askyesno("تأكيد", "هل تريد استعادة الإعدادات الافتراضية؟\nسيتم إرجاع الجودة والصيغة والخيارات لوضعها الأصلي."):
            return
        self.quality_var.set("الأفضل تلقائياً (best)")
        self.format_var.set("mp4 (فيديو)")
        self.out_var.set(DEFAULT_OUTPUT)
        self.tmplate_var.set("%(title)s.%(ext)s")
        self.sub_var.set(False)
        self.sub_only_var.set(False)
        self.sub_langs_var.set("ar,en")
        self.sub_format_var.set("vtt (افتراضي)")
        self.convert_sub_var.set(False)
        self.thumb_var.set(False)
        self.playlist_var.set(False)
        self.ipv4_var.set(True)
        self.sponsor_var.set(False)
        self.timeout_var.set("60")
        self.cookie_var.set("")
        self.proxy_var.set("")
        self.extra_var.set("")
        self.browser_var.set("بدون (يدوي)")
        self._on_sub_toggle()
        self.save_preferences()
        # لا نمسح الرابط — يبقى كما هو
        self.log_msg("↩️ تمت استعادة الإعدادات الافتراضية ✅", "ok")
        self.status_var.set("تمت استعادة الافتراضي ✅")
        # إعادة إنشاء مجلد التحميل الافتراضي
        Path(DEFAULT_OUTPUT).mkdir(parents=True, exist_ok=True)

    def _on_sub_toggle(self):
        # إظهار/إخفاء خيارات الترجمة حسب الحاجة
        try:
            show = self.sub_var.get() or self.sub_only_var.get()
            for child in self.sub_opts_frame.winfo_children():
                child.configure(state="normal" if show else "disabled")
            # تمييز بصري
            self.sub_opts_frame.configure()
        except: pass

    def _on_sub_only_toggle(self):
        if self.sub_only_var.get():
            # الترجمة فقط تتطلب تفعيل الترجمة
            self.sub_var.set(True)
            self.log_msg("📝 وضع الترجمة فقط مفعّل — سيتم تنزيل .vtt/.srt فقط بدون الفيديو", "info")
        self._on_sub_toggle()
        self.save_preferences()

    # ---------- حفظ/تحميل التفضيلات ----------
    def save_preferences(self):
        try:
            data = {
                "out_dir": self.out_var.get(),
                "template": self.tmplate_var.get(),
                "quality": self.quality_var.get(),
                "format": self.format_var.get(),
                "sub": self.sub_var.get(),
                "sub_only": self.sub_only_var.get(),
                "sub_langs": self.sub_langs_var.get(),
                "sub_format": self.sub_format_var.get(),
                "convert_sub": self.convert_sub_var.get(),
                "thumb": self.thumb_var.get(),
                "playlist": self.playlist_var.get(),
                "ipv4": self.ipv4_var.get(),
                "sponsor": self.sponsor_var.get(),
                "timeout": self.timeout_var.get(),
                "cookie_file": self.cookie_var.get(),
                "browser": self.browser_var.get(),
                "proxy": self.proxy_var.get(),
                "extra": self.extra_var.get(),
            }
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("save prefs failed:", e)

    def load_preferences(self):
        try:
            if not CONFIG_FILE.exists():
                return
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            # طبّق فقط إن وجد
            if "out_dir" in d: self.out_var.set(d["out_dir"])
            if "template" in d: self.tmplate_var.set(d["template"])
            if "quality" in d: self.quality_var.set(d["quality"])
            if "format" in d: self.format_var.set(d["format"])
            if "sub" in d: self.sub_var.set(bool(d["sub"]))
            if "sub_only" in d: self.sub_only_var.set(bool(d["sub_only"]))
            if "sub_langs" in d: self.sub_langs_var.set(d["sub_langs"])
            if "sub_format" in d: self.sub_format_var.set(d["sub_format"])
            if "convert_sub" in d: self.convert_sub_var.set(bool(d["convert_sub"]))
            if "thumb" in d: self.thumb_var.set(bool(d["thumb"]))
            if "playlist" in d: self.playlist_var.set(bool(d["playlist"]))
            if "ipv4" in d: self.ipv4_var.set(bool(d["ipv4"]))
            if "sponsor" in d: self.sponsor_var.set(bool(d["sponsor"]))
            if "timeout" in d: self.timeout_var.set(str(d["timeout"]))
            if "cookie_file" in d: self.cookie_var.set(d["cookie_file"])
            if "browser" in d: self.browser_var.set(d["browser"])
            if "proxy" in d: self.proxy_var.set(d["proxy"])
            if "extra" in d: self.extra_var.set(d["extra"])
            self._on_sub_toggle()
            self.log_msg(f"✅ تم تحميل التفضيلات من {CONFIG_FILE}", "ok")
        except Exception as e:
            self.log_msg(f"تعذر تحميل التفضيلات: {e}", "warn")

    def _on_close(self):
        try: self.save_preferences()
        except: pass
        try:
            if hasattr(self, '_ext_server'):
                self._ext_server.shutdown()
        except: pass
        self.destroy()

    def _bind_auto_save(self):
        # حفظ تلقائي عند تغيير أي تفضيل
        vars_to_watch = [
            self.out_var, self.tmplate_var, self.quality_var, self.format_var,
            self.sub_var, self.sub_only_var, self.sub_langs_var, self.sub_format_var, self.convert_sub_var,
            self.thumb_var, self.playlist_var, self.ipv4_var, self.sponsor_var,
            self.timeout_var, self.cookie_var, self.browser_var, self.proxy_var, self.extra_var
        ]
        def _save(*_): 
            try: self.save_preferences()
            except: pass
        for v in vars_to_watch:
            try:
                v.trace_add("write", _save)
            except:
                try: v.trace("w", _save)
                except: pass

    def start_extension_server(self):
        """يشغّل خادم الإضافة على 127.0.0.1:8765"""
        try:
            _ExtensionHandler.app = self
            srv = ThreadingHTTPServer(("127.0.0.1", EXTENSION_PORT), _ExtensionHandler)
            srv.daemon_threads = True
            self._ext_server = srv
            t = threading.Thread(target=srv.serve_forever, daemon=True, name="ExtensionServer")
            t.start()
            self.log_msg(f"🔌 خادم الإضافة يعمل على http://127.0.0.1:{EXTENSION_PORT} — فعّل الإضافة في المتصفح", "ok")
            # تحديث حالة الإضافة في الواجهة إن وجدت
            try:
                if hasattr(self, 'ext_status_lbl'):
                    self.ext_status_lbl.config(text=f"الإضافة: متصل ✅ :{EXTENSION_PORT}", foreground="#16a34a")
            except: pass
        except Exception as e:
            self.log_msg(f"⚠️ فشل تشغيل خادم الإضافة: {e} — الإضافة لن تعمل", "warn")
            try:
                if hasattr(self, 'ext_status_lbl'):
                    self.ext_status_lbl.config(text="الإضافة: متوقف ❌", foreground="#dc2626")
            except: pass

    # ---------- قائمة التحميل المتوازي ----------
    def add_to_queue(self):
        raw = self.url_var.get().strip()
        if not raw:
            # جرّب قراءة الحافظة إذا كان الحقل فارغ
            try:
                raw = self.clipboard_get().strip()
            except: raw = ""
        if not raw:
            messagebox.showwarning("تنبيه", "الصق رابطاً أولاً")
            return
        # يدعم عدة روابط في سطور
        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        # إذا سطر واحد بدون أسطر، أضفه
        if not urls and raw:
            urls = [raw]
        # نظف و صحح
        added = 0
        for u in urls:
            if not re.match(r"https?://", u):
                u = "https://" + u
            # تجنب التكرار
            exists = False
            for iid in self.queue_tree.get_children():
                if self.queue_tree.set(iid, "url") == u:
                    exists = True; break
            if exists: continue
            self._queue_counter += 1
            iid = f"q{self._queue_counter}"
            self.queue_tree.insert("", "end", iid=iid, values=(u, "--", "⏳ انتظار", "0%"))
            # جلب الحجم في الخلفية
            threading.Thread(target=self._fetch_size_for_item, args=(iid, u), daemon=True).start()
            added += 1
        if added:
            self.log_msg(f"➕ أضيف {added} رابط للقائمة", "ok")
            self.url_var.set("")
            self.size_var.set("")
        else:
            self.log_msg("⚠️ لا روابط جديدة للإضافة (مكررة أو فارغة)", "warn")

    def add_url_to_queue_external(self, url):
        """لإضافة من الإضافة/الخادم بدون تجميد الواجهة"""
        def _do():
            if not re.match(r"https?://", url):
                url2 = "https://" + url
            else:
                url2 = url
            for iid in self.queue_tree.get_children():
                if self.queue_tree.set(iid, "url") == url2:
                    return
            self._queue_counter += 1
            iid = f"q{self._queue_counter}"
            self.queue_tree.insert("", "end", iid=iid, values=(url2, "--", "⏳ انتظار", "0%"))
            threading.Thread(target=self._fetch_size_for_item, args=(iid, url2), daemon=True).start()
            self.log_msg(f"🔗 من الإضافة: {url2}", "ok")
        self.after(0, _do)

    def remove_selected(self):
        sel = list(self.queue_tree.selection())
        if not sel:
            return
        # أوقف أولاً بدون تجميد الواجهة
        for iid in sel:
            proc = None
            with self._queue_lock:
                proc = self._active_procs.get(iid)
                if proc and proc.poll() is None:
                    self._stop_ids.add(iid)
                if hasattr(self, '_pending_queue') and iid in self._pending_queue:
                    try: self._pending_queue.remove(iid)
                    except: pass
            if proc and proc.poll() is None:
                # اقتل خارج القفل حتى لا يعلق الـ UI
                self._kill_proc(proc)
            # حدّث الحالة فوراً
            try: self._set_queue_status(iid, "⏹ ألغي")
            except: pass
        # احذف من الواجهة بعد التوقف
        for iid in sel:
            try:
                self.queue_tree.delete(iid)
                with self._queue_lock:
                    self._active_procs.pop(iid, None)
                self.log_msg(f"🗑️ حذف {iid}", "info")
            except: pass
        # نظّف العداد إذا لزم
        with self._queue_lock:
            if self._active_downloads < 0:
                self._active_downloads = 0
        self.after(150, self._launch_parallel_slots)
    def clear_queue(self):
        # أوقف كل شيء أولاً
        self.stop_download()
        for iid in list(self.queue_tree.get_children()):
            try: self.queue_tree.delete(iid)
            except: pass

    def _set_queue_status(self, iid, status, progress=None):
        try:
            vals = list(self.queue_tree.item(iid, "values"))
            # values: (url, size, status, progress)
            vals[2] = status
            if progress is not None:
                vals[3] = progress
            self.queue_tree.item(iid, values=tuple(vals))
        except: pass
    def _set_queue_size(self, iid, size_str):
        try:
            vals = list(self.queue_tree.item(iid, "values"))
            vals[1] = size_str
            self.queue_tree.item(iid, values=tuple(vals))
        except: pass
    def _fetch_size_for_item(self, iid, url):
        try:
            # حاول Aparat/Meyon مباشر أولاً
            direct = None
            if "aparat.com" in url.lower():
                direct = get_aparat_direct_url(url)
            elif "meyon.com.ye" in url.lower():
                direct = get_meyon_direct_url(url)
            check_url = direct if direct else url
            # استخدم yt-dlp --dump-json للحجم
            y = find_ytdlp()
            cmd = y.split() if " -m " in y else [y]
            # للروابط المباشرة استخدم --no-playlist وتجاوز الصيغة
            if direct or re.search(r"s3\.sohobcom\.ye|\.mp4(\?.*)?$", check_url, re.I):
                # رابط مباشر — حاول HEAD فقط
                import urllib.request, ssl
                ctx = ssl.create_default_context()
                req = urllib.request.Request(check_url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                    cl = r.headers.get("Content-Length")
                    if cl and cl.isdigit():
                        sz = int(cl)
                        hr = self._human_size(sz)
                        self.q.put(("queue_size", (iid, hr)))
                        return
            # fallback yt-dlp
            p = subprocess.run(cmd + ["--dump-json", "--no-download", "--no-playlist", "--socket-timeout", "15", check_url],
                               capture_output=True, text=True, timeout=20)
            if p.returncode == 0 and p.stdout.strip():
                import json as _json
                data = _json.loads(p.stdout.strip().splitlines()[0])
                sz = data.get("filesize") or data.get("filesize_approx") or 0
                # جرّب formats
                if not sz and data.get("formats"):
                    # اختر أفضل صيغة
                    best = max([f for f in data["formats"] if f.get("filesize")], key=lambda x: x.get("filesize",0), default=None)
                    if best: sz = best.get("filesize") or best.get("filesize_approx") or 0
                if sz:
                    self.q.put(("queue_size", (iid, self._human_size(sz))))
                else:
                    self.q.put(("queue_size", (iid, "--")))
            else:
                self.q.put(("queue_size", (iid, "--")))
        except Exception:
            self.q.put(("queue_size", (iid, "--")))
    def _human_size(self, n):
        try:
            n = int(n)
            for unit in ["B","KB","MB","GB"]:
                if n < 1024: return f"{n:.0f} {unit}" if unit=="B" else f"{n:.1f} {unit}"
                n/=1024
            return f"{n:.1f} TB"
        except: return "--"
    def _fetch_single_size(self, url):
        try:
            self.size_var.set("جاري حساب الحجم...")
            # نفس منطق _fetch_size_for_item لكن للنافذة المفردة
            direct = None
            if "aparat.com" in url.lower(): direct = get_aparat_direct_url(url)
            elif "meyon.com.ye" in url.lower(): direct = get_meyon_direct_url(url)
            check_url = direct if direct else url
            y = find_ytdlp()
            cmd = y.split() if " -m " in y else [y]
            p = subprocess.run(cmd + ["--dump-json", "--no-download", "--no-playlist", "--socket-timeout", "12", check_url],
                               capture_output=True, text=True, timeout=18)
            if p.returncode == 0 and p.stdout.strip():
                import json as _json
                data = _json.loads(p.stdout.strip().splitlines()[0])
                sz = data.get("filesize") or data.get("filesize_approx") or 0
                if not sz and data.get("duration"):
                    # لا حجم — اعرض المدة
                    dur = data.get("duration_string") or f"{int(data['duration']//60)}:{int(data['duration']%60):02d}"
                    self.q.put(("single_size", f"⏱ {dur}"))
                    return
                if sz:
                    self.q.put(("single_size", self._human_size(sz)))
                else:
                    self.q.put(("single_size", ""))
            else:
                self.q.put(("single_size", ""))
        except:
            self.q.put(("single_size", ""))

    def start_parallel(self):
        children = list(self.queue_tree.get_children())
        if not children:
            messagebox.showinfo("تنبيه", "القائمة فارغة — أضف روابط أولاً")
            return
        try:
            limit = int(self.parallel_var.get())
        except: limit = 3
        # عدّل فقط العناصر المنتظرة
        pending = [iid for iid in children if self.queue_tree.set(iid, "status") in ("⏳ انتظار", "❌ فشل", "⏹ ألغي")]
        if not pending:
            pending = [iid for iid in children if self.queue_tree.set(iid, "status") == "⏳ انتظار"]
            if not pending:
                messagebox.showinfo("تنبيه", "لا يوجد عناصر منتظرة")
                return
        self.log_msg(f"▶️ بدء التحميل المتوازي: {len(pending)} فيديو، توازي={limit}", "info")
        self._parallel_limit = limit
        self._pending_queue = pending
        self._stop_all = False
        self._stop_ids.clear()
        self.stop_btn.config(state="normal")
        self.dl_btn.config(state="disabled")
        self.status_var.set(f"متوازي: 0/{len(pending)} اكتمل — نشط: 0")
        self._launch_parallel_slots()

    def _launch_parallel_slots(self):
        with self._queue_lock:
            while self._active_downloads < self._parallel_limit and self._pending_queue:
                iid = self._pending_queue.pop(0)
                url = self.queue_tree.set(iid, "url")
                self._active_downloads += 1
                self._set_queue_status(iid, "⬇️ جاري", "0%")
                threading.Thread(target=self._queue_worker, args=(iid, url), daemon=True).start()

    def _queue_worker(self, iid, url):
        # يبني الأمر بنفس خيارات الواجهة ويحمّل
        try:
            cmd = self.build_command(url)
            kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True, "encoding": "utf-8", "errors": "replace", "bufsize": 1}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            proc = subprocess.Popen(cmd, **kwargs)
            with self._queue_lock:
                self._active_procs[iid] = proc
            for line in proc.stdout:
                if self._stop_all or iid in self._stop_ids:
                    self._kill_proc(proc)
                    break
                self.q.put(("log_line", line.rstrip("\n")))
                m = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%.*?at\s+([^\s]+).*?ETA\s+([^\s]+)", line)
                if m:
                    pct = m.group(1) + "%"
                    self.q.put(("queue_progress", (iid, pct)))
                    self.q.put(("queue_speed", (iid, f"{m.group(2)}")))
                    self.q.put(("net_speed", f"{m.group(2)}"))
                else:
                    m2 = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
                    if m2:
                        self.q.put(("queue_progress", (iid, m2.group(1)+"%")))
                if "ERROR" in line:
                    self.q.put(("queue_status", (iid, "❌ فشل")))
            proc.wait()
            rc = proc.returncode
            # إذا طُلب الإيقاف، لا تعتبره فشل
            if self._stop_all or iid in self._stop_ids:
                self.q.put(("queue_status", (iid, "⏹ ألغي")))
                return
            if rc == 0:
                self.q.put(("queue_status", (iid, "✅ اكتمل")))
                self.q.put(("queue_progress", (iid, "100%")))
            else:
                # محاولة fallback لـ Aparat / Meyon (لا تجرب إذا أُلغي)
                if self._stop_all or iid in self._stop_ids:
                    self.q.put(("queue_status", (iid, "⏹ ألغي")))
                    return
                direct = None
                if "aparat.com" in url.lower() or "og:title" in line or "Aparat" in line:
                    direct = get_aparat_direct_url(url)
                    if direct and direct != url:
                        self.q.put(("log", f"🔄 Aparat fallback: {direct[:80]}", "info"))
                elif "meyon.com.ye" in url.lower():
                    direct = get_meyon_direct_url(url)
                    if direct and direct != url:
                        self.q.put(("log", f"🔄 Meyon HLS fallback: {direct[:90]}", "info"))
                if direct and direct != url:
                    cmd2 = self.build_command(direct)
                    proc2 = subprocess.Popen(cmd2, **kwargs)
                    with self._queue_lock:
                        self._active_procs[iid] = proc2
                    for line2 in proc2.stdout:
                        if self._stop_all or iid in self._stop_ids:
                            self._kill_proc(proc2)
                            break
                        self.q.put(("log_line", line2.rstrip("\n")))
                        m2 = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line2)
                        if m2:
                            self.q.put(("queue_progress", (iid, m2.group(1)+"%")))
                    proc2.wait()
                    if self._stop_all or iid in self._stop_ids:
                        self.q.put(("queue_status", (iid, "⏹ ألغي")))
                    elif proc2.returncode == 0:
                        self.q.put(("queue_status", (iid, "✅ اكتمل")))
                        self.q.put(("queue_progress", (iid, "100%")))
                    else:
                        self.q.put(("queue_status", (iid, "❌ فشل")))
                else:
                    self.q.put(("queue_status", (iid, "❌ فشل")))
        except Exception as e:
            if not (self._stop_all or iid in self._stop_ids):
                self.q.put(("log", f"خطأ في {url}: {e}", "err"))
                self.q.put(("queue_status", (iid, "❌ فشل")))
            else:
                self.q.put(("queue_status", (iid, "⏹ ألغي")))
        finally:
            with self._queue_lock:
                self._active_downloads = max(0, self._active_downloads - 1)
                try: self._active_procs.pop(iid, None)
                except: pass
                try: self._stop_ids.discard(iid)
                except: pass
            self.q.put(("parallel_slot_free", None))

    def check_environment(self):
        y = find_ytdlp()
        self.log_msg(f"yt-dlp: {y}", "info")
        try:
            out = subprocess.run([y, "--version"], capture_output=True, text=True, timeout=8)
            ver = (out.stdout.strip() or out.stderr.strip()).splitlines()[0].strip()
            # نظف السطر: قد يكون "stable@2026.08.19" أو "2026.08.19"
            self.current_version = ver.replace("stable@", "").strip()
            self.version_lbl.config(text=f"yt-dlp {self.current_version}")
            self.log_msg(f"الإصدار الحالي: {ver}", "info")
        except Exception as e:
            self.log_msg(f"تعذر فحص الإصدار: {e}", "warn")
            self.current_version = ""
        if not find_ffmpeg():
            self.log_msg("⚠️ ffmpeg غير موجود — تحويل mp3/دمج الجودات لن يعمل. ثبّت ffmpeg.", "warn")
        else:
            self.log_msg("ffmpeg: متوفر ✅", "ok")
        # فحص محرك JS لليوتيوب
        js_name, js_path = find_js_runtime()
        if js_name is None:
            self.log_msg("⚠️ لا يوجد محرك JS (deno/node/bun) — يوتيوب قد يفقد بعض الصيغ. ثبّت Deno أو Node", "warn")
        elif js_name == "deno":
            self.log_msg(f"JS runtime: deno ✅ ({js_path})", "ok")
        else:
            self.log_msg(f"JS runtime: {js_name} ✅ ({js_path}) — سيُضاف --js-runtimes {js_name} تلقائياً", "ok")

    # ---------- نظام فحص وتثبيت التحديث ----------
    def fetch_latest_version(self):
        """يجلب آخر إصدار من GitHub API، ويرجع tag مثل 2026.08.19 أو None"""
        import urllib.request, ssl, json
        urls = [
            "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
            "https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/yt_dlp/version.py",
        ]
        # 1) GitHub API
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(urls[0], headers={"User-Agent": "yt-dlp-gui/1.0", "Accept": "application/vnd.github.v3+json"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                data = json.loads(r.read().decode("utf-8"))
                tag = data.get("tag_name", "").strip()
                if tag:
                    return tag.replace("stable@", "").strip()
        except Exception as e:
            self.q.put(("log", f"فشل GitHub API: {e}", "warn"))
        # 2) fallback: version.py
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(urls[1], headers={"User-Agent": "yt-dlp-gui/1.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                txt = r.read().decode("utf-8")
                m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", txt)
                if m: return m.group(1).strip()
        except Exception:
            pass
        # 3) fallback: yt-dlp -U يحاول جلب Latest
        try:
            y = find_ytdlp()
            p = subprocess.run([y, "-U"], capture_output=True, text=True, timeout=60)
            out = p.stdout + p.stderr
            m = re.search(r"Latest version:\s*stable@([0-9.]+)", out)
            if m: return m.group(1).strip()
            m2 = re.search(r"Updated yt-dlp to stable@([0-9.]+)", out)
            if m2: return m2.group(1).strip()
        except Exception:
            pass
        return None

    def check_for_update(self, auto=False):
        """يفحص التحديث؛ إذا auto=False يعرض نتيجة دائماً، إذا auto=True يعرض فقط عند وجود تحديث"""
        if getattr(self, "_checking", False):
            return
        self._checking = True
        self.log_msg("🔍 جاري فحص تحديث yt-dlp ...", "info")
        self.status_var.set("جاري فحص التحديث...")
        if not auto:
            self.version_lbl.config(text="جاري الفحص…")
        def run():
            try:
                # تأكد أن current_version محدث
                if not getattr(self, "current_version", ""):
                    try:
                        y = find_ytdlp()
                        out = subprocess.run([y, "--version"], capture_output=True, text=True, timeout=8)
                        self.current_version = (out.stdout.strip() or out.stderr.strip()).splitlines()[0].replace("stable@", "").strip()
                    except: self.current_version = ""
                latest = self.fetch_latest_version()
                if not latest:
                    self.q.put(("log", "تعذر جلب آخر إصدار — تحقق من الاتصال", "warn"))
                    self.q.put(("status", "تعذر فحص التحديث"))
                    if not auto: self.q.put(("update_result", ("error", latest)))
                    else: self.q.put(("update_result", ("auto_fail", latest)))
                    return
                self.latest_version = latest
                cur = (self.current_version or "").strip()
                # مقارنة بسيطة
                is_newer = (cur != latest) and (cur < latest or True)  # نصياً؛ yt-dlp إصداراته تاريخية لذا كافية
                # مقارنة أدق كتواريخ
                try:
                    def to_tuple(v): return tuple(int(x) for x in re.findall(r"\d+", v))
                    is_newer = to_tuple(latest) > to_tuple(cur) if cur else True
                except: pass
                if is_newer:
                    self.q.put(("log", f"✅ يتوفر تحديث جديد: {latest}  (حالي: {cur})", "ok"))
                    self.q.put(("status", f"يتوفر تحديث {latest} ⬆️"))
                    self.q.put(("update_result", ("available", latest, cur)))
                else:
                    self.q.put(("log", f"أنت على أحدث إصدار ✅  ({cur})", "ok"))
                    self.q.put(("status", f"أحدث إصدار ✅ {cur}"))
                    if not auto:
                        self.q.put(("update_result", ("uptodate", latest, cur)))
                    else:
                        # في الوضع التلقائي لا نزعج المستخدم إذا محدث
                        pass
            finally:
                self._checking = False
        threading.Thread(target=run, daemon=True).start()

    def do_update(self):
        """يثبت التحديث فوراً عبر yt-dlp -U"""
        self.log_msg("⬆️ جاري تنزيل وتثبيت تحديث yt-dlp ...", "info")
        self.status_var.set("جاري التحديث...")
        self.version_lbl.config(text="جاري التحديث…")
        def run():
            y = find_ytdlp()
            # حالة exe مجمد: لا يمكن لـ -U تحديث الملف داخل _MEIPASS، نحدّث النسخة الخارجية بجانب الـ exe
            is_frozen = getattr(sys, 'frozen', False)
            if is_frozen:
                try:
                    import urllib.request, ssl
                    latest = self.latest_version or self.fetch_latest_version() or "2026.08.19"
                    exe_dir = Path(sys.executable).parent
                    target = exe_dir / "yt-dlp.exe"
                    url = f"https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
                    # جرّب الرابط المباشر للإصدار
                    if latest:
                        url_ver = f"https://github.com/yt-dlp/yt-dlp/releases/download/{latest}/yt-dlp.exe"
                    else:
                        url_ver = url
                    self.q.put(("log", f"تنزيل التحديث من: {url_ver}", "info"))
                    ctx = ssl.create_default_context()
                    req = urllib.request.Request(url_ver, headers={"User-Agent": "yt-dlp-gui/1.0"})
                    with urllib.request.urlopen(req, timeout=120, context=ctx) as r, open(str(target)+".new", "wb") as out:
                        shutil.copyfileobj(r, out)
                    # استبدال
                    try:
                        if target.exists():
                            backup = exe_dir / "yt-dlp.exe.bak"
                            if backup.exists(): backup.unlink()
                            target.rename(backup)
                    except: pass
                    Path(str(target)+".new").rename(target)
                    self.q.put(("log", f"تم تنزيل yt-dlp.exe الجديد إلى {target}", "ok"))
                    # تحديث current_version
                    self.current_version = latest or self.current_version
                    self.q.put(("status", f"تم التحديث ✅ {self.current_version}"))
                    self.q.put(("version_update", self.current_version))
                    self.q.put(("update_done", True))
                    return
                except Exception as e:
                    self.q.put(("log", f"فشل تحديث الـ exe المجمد: {e} — نحاول -U كاحتياط", "warn"))
                    # fallback إلى المحاولة العادية
            try:
                # yt-dlp.exe يحتاج -U، و pip يحتاج pip install -U yt-dlp
                # إذا y هو "python -m yt_dlp" نحتاج تشغيل pip
                if " -m " in y:
                    p = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], capture_output=True, text=True, timeout=180)
                else:
                    p = subprocess.run([y, "-U"], capture_output=True, text=True, timeout=180)
                out = (p.stdout or "") + "\n" + (p.stderr or "")
                ok = p.returncode == 0 and ("Updated" in out or "is up to date" in out or "Latest version" in out)
                # حتى لو returncode !=0 لكن فيه Updated يعتبر نجاح
                if "Updated yt-dlp to" in out:
                    ok = True
                self.q.put(("log", out.strip(), "ok" if ok else "err"))
                if ok:
                    # حدث رقم الإصدار
                    m = re.search(r"stable@([0-9.]+)", out)
                    if m: self.current_version = m.group(1)
                    else:
                        try:
                            out2 = subprocess.run([y, "--version"], capture_output=True, text=True, timeout=8)
                            self.current_version = (out2.stdout.strip() or "").replace("stable@", "").splitlines()[0].strip()
                        except: pass
                    self.q.put(("status", f"تم التحديث ✅ {self.current_version}"))
                    self.q.put(("version_update", self.current_version))
                    self.q.put(("update_done", True))
                else:
                    self.q.put(("status", "فشل التحديث ❌ — راجع السجل"))
                    self.q.put(("update_done", False))
            except Exception as e:
                self.q.put(("log", f"فشل التحديث: {e}", "err"))
                self.q.put(("status", "فشل التحديث ❌"))
                self.q.put(("update_done", False))
        threading.Thread(target=run, daemon=True).start()

    def build_command(self, url):
        y = find_ytdlp()
        out_dir = Path(self.out_var.get() or DEFAULT_OUTPUT)
        out_dir.mkdir(parents=True, exist_ok=True)
        tmpl = self.tmplate_var.get().strip() or "%(title)s.%(ext)s"
        # output template
        out_tmpl = str(out_dir / tmpl)

        # إذا y هو "python -m yt_dlp" نقسمه
        if " -m " in y:
            y_parts = y.split()
            cmd = y_parts + ["--no-update", "--newline", "--progress", "--no-mtime", "-o", out_tmpl]
        else:
            cmd = [y, "--no-update", "--newline", "--progress", "--no-mtime", "-o", out_tmpl]

        # ffmpeg المدمج (مهم للـ exe المستقل)
        ff = get_bundled_ffmpeg()
        if ff and not shutil.which("ffmpeg"):
            cmd += ["--ffmpeg-location", str(Path(ff).parent)]

        # محرك JS لليوتيوب — يزيل تحذير "No supported JS runtime"
        js_name, _ = find_js_runtime()
        if js_name and js_name != "deno":
            cmd += ["--js-runtimes", js_name]
        # تخفيف 429 للترجمة/يوتيوب
        cmd += ["--retries", "10", "--fragment-retries", "10", "--retry-sleep", "2"]
        # أسماء ملفات آمنة للويندوز مع العربية
        cmd += ["--windows-filenames"]

        # timeout
        try:
            t = int(self.timeout_var.get())
            cmd += ["--socket-timeout", str(t)]
        except: pass
        if self.ipv4_var.get():
            cmd += ["--force-ipv4"]
        if not self.playlist_var.get():
            cmd += ["--no-playlist"]
        # الترجمة
        langs = (self.sub_langs_var.get() or "ar,en").strip()
        # تنظيف صيغة الترجمة
        fmt_sub = self.sub_format_var.get() or "vtt (افتراضي)"
        sub_ext = "vtt"
        if "srt" in fmt_sub: sub_ext = "srt"
        elif "ass" in fmt_sub: sub_ext = "ass"
        elif "lrc" in fmt_sub: sub_ext = "lrc"

        if self.sub_only_var.get():
            # 📝 الترجمة فقط — بدون فيديو
            cmd += ["--skip-download", "--write-sub", "--write-auto-sub", "--sub-langs", langs]
            if sub_ext != "vtt":
                cmd += ["--convert-subs", sub_ext]
            elif self.convert_sub_var.get():
                cmd += ["--convert-subs", "srt"]
            # لا ندمج الترجمة في الفيديو لأنه لن ينزل
        elif self.sub_var.get():
            cmd += ["--write-auto-sub", "--write-sub", "--sub-langs", langs, "--embed-subs"]
            if self.convert_sub_var.get() and sub_ext == "srt":
                cmd += ["--convert-subs", "srt"]
            elif sub_ext != "vtt":
                cmd += ["--convert-subs", sub_ext]

        if self.thumb_var.get():
            cmd += ["--embed-thumbnail"]
        if self.sponsor_var.get():
            cmd += ["--sponsorblock-remove", "all"]

        # Meyon/Aparat direct file (s3) — لا يحتاج اختيار صيغة
        is_direct_file = bool(re.search(r"s3\.sohobcom\.ye|download/streaming-playlists|\.mp4(\?.*)?$|\.webm(\?.*)?$", url, re.I))
        # quality / format — تخطى للروابط المباشرة
        if is_direct_file:
            # رابط مباشر — حمّله كملف بدون -f
            pass
        else:
            q = self.quality_var.get()
            fmt = self.format_var.get()
            is_audio = "صوت" in fmt or fmt.startswith("mp3") or fmt.startswith("m4a") or fmt.startswith("wav")
            if is_audio:
                ext = "mp3" if "mp3" in fmt else ("m4a" if "m4a" in fmt else "wav")
                cmd += ["-x", "--audio-format", ext, "--audio-quality", "0"]
            else:
                # video format
                if "الأفضل" in q:
                    sel = "bv*+ba/b"
                elif "1080" in q:
                    sel = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
                elif "720" in q:
                    sel = "bestvideo[height<=720]+bestaudio/best[height<=720]"
                elif "480" in q:
                    sel = "bestvideo[height<=480]+bestaudio/best[height<=480]"
                elif "360" in q:
                    sel = "bestvideo[height<=360]+bestaudio/best[height<=360]"
                else:
                    sel = "worst"
                # map container
                container = "mp4"
                if "mkv" in fmt: container = "mkv"
                elif "webm" in fmt: container = "webm"
                cmd += ["-f", sel, "--merge-output-format", container]

        # cookies / proxy — المتصفح له أولوية على الملف
        br = self.browser_var.get() if hasattr(self, 'browser_var') else "بدون (يدوي)"
        if not br.startswith("بدون"):
            # yt-dlp يقرأ مباشرة من المتصفح (حتى وهو مفتوح في الإصدارات الحديثة)
            # ملاحظة: قد يحتاج إغلاق المتصفح إذا كان مقفلاً
            cmd += ["--cookies-from-browser", br]
        elif self.cookie_var.get().strip():
            cmd += ["--cookies", self.cookie_var.get().strip()]
        if self.proxy_var.get().strip():
            cmd += ["--proxy", self.proxy_var.get().strip()]

        # extra
        extra = self.extra_var.get().strip()
        if extra:
            import shlex
            # shlex on windows: posix False
            try: cmd += shlex.split(extra, posix=False)
            except: cmd += extra.split()

        cmd += [url]
        return cmd

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("تنبيه", "الصق الرابط أولاً")
            return
        if not re.match(r"https?://", url):
            url = "https://" + url
        if self.downloading:
            return
        cmd = self.build_command(url)
        self.log_msg("الأمر: " + " ".join(f'"{c}"' if " " in c else c for c in cmd), "info")
        self.progress.config(value=0)
        self.speed_var.set("")
        self.status_var.set("جاري التحميل...")
        self.dl_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.downloading = True
        self.log_msg("— بدأ التحميل —", "info")
        threading.Thread(target=self.run_proc, args=(cmd,), daemon=True).start()

    def on_big_download(self):
        """الزر الكبير الذكي: يحمل من الحقل العلوي أو المحدد في القائمة"""
        url = self.url_var.get().strip()
        sel = list(self.queue_tree.selection())
        # 1) إذا كان الحقل العلوي فيه رابط — أضفه وحمّل هذا فقط
        if url:
            # نظف
            urls = [u.strip() for u in url.splitlines() if u.strip()]
            if not urls:
                urls = [url]
            # أضف للقائمة
            added_ids = []
            for u in urls:
                if not re.match(r"https?://", u):
                    u = "https://" + u
                exists = False
                for iid in self.queue_tree.get_children():
                    if self.queue_tree.set(iid, "url") == u:
                        exists = True
                        added_ids.append(iid)
                        break
                if exists:
                    continue
                self._queue_counter += 1
                iid = f"q{self._queue_counter}"
                self.queue_tree.insert("", "end", iid=iid, values=(u, "--", "⏳ انتظار", "0%"))
                threading.Thread(target=self._fetch_size_for_item, args=(iid, u), daemon=True).start()
                added_ids.append(iid)
            if not added_ids:
                # مكرر — حمّل الموجود
                for iid in self.queue_tree.get_children():
                    if self.queue_tree.set(iid, "url") in [url if re.match(r"https?://", url) else "https://"+url]:
                        added_ids = [iid]
                        break
            if added_ids:
                self.url_var.set("")
                self.size_var.set("")
                # حمّل فقط هذا/هذه
                for iid in added_ids:
                    self._set_queue_status(iid, "⏳ انتظار", "0%")
                self._pending_queue = added_ids
                try: self._parallel_limit = int(self.parallel_var.get())
                except: self._parallel_limit = 3
                self._stop_all = False
                self._stop_ids.clear()
                self.stop_btn.config(state="normal")
                self.dl_btn.config(state="disabled")
                self.log_msg(f"▶️ تحميل من الحقل: {len(added_ids)} فيديو", "info")
                self._launch_parallel_slots()
            return
        # 2) إذا لا يوجد رابط علوي لكن هناك تحديد في القائمة — حمّل المحدد فقط
        if sel:
            to_start = [iid for iid in sel if self.queue_tree.set(iid, "status") in ("⏳ انتظار", "❌ فشل", "⏹ ألغي", "⬇️ جاري")]
            if not to_start:
                to_start = sel
            for iid in to_start:
                self._set_queue_status(iid, "⏳ انتظار", "0%")
            self._pending_queue = to_start
            try: self._parallel_limit = int(self.parallel_var.get())
            except: self._parallel_limit = 3
            self._stop_all = False
            self._stop_ids.clear()
            self.stop_btn.config(state="normal")
            self.dl_btn.config(state="disabled")
            self.log_msg(f"▶️ تحميل المحدد: {len(to_start)} فيديو", "info")
            self._launch_parallel_slots()
            return
        # 3) لا حقل ولا تحديد — جرّب القائمة كلها
        all_children = list(self.queue_tree.get_children())
        if all_children:
            pending = [iid for iid in all_children if self.queue_tree.set(iid, "status") in ("⏳ انتظار", "❌ فشل", "⏹ ألغي")]
            if pending:
                self._pending_queue = pending
                try: self._parallel_limit = int(self.parallel_var.get())
                except: self._parallel_limit = 3
                self._stop_all = False
                self._stop_ids.clear()
                self.stop_btn.config(state="normal")
                self.dl_btn.config(state="disabled")
                self.log_msg(f"▶️ تحميل الكل: {len(pending)} فيديو", "info")
                self._launch_parallel_slots()
                return
        messagebox.showwarning("تنبيه", "الصق رابطاً في الحقل العلوي أو حدد فيديو من القائمة")

    def run_proc(self, cmd):
        try:
            # CREATE_NO_WINDOW لإخفاء نافذة الكونسول على ويندوز
            kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True, "encoding": "utf-8", "errors": "replace", "bufsize": 1}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            self.proc = subprocess.Popen(cmd, **kwargs)
            full_log = ""
            for line in self.proc.stdout:
                if self._stop_all:
                    self._kill_proc(self.proc)
                    break
                full_log += line
                self.q.put(("log_line", line.rstrip("\n")))
                m = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%.*?at\s+([^\s]+).*?ETA\s+([^\s]+)", line)
                if m:
                    try:
                        pct = float(m.group(1))
                        self.q.put(("progress", pct))
                        self.q.put(("speed", f"{m.group(2)}  •  ETA {m.group(3)}"))
                    except: pass
                else:
                    m2 = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
                    if m2:
                        try: self.q.put(("progress", float(m2.group(1))))
                        except: pass
            self.proc.wait()
            rc = self.proc.returncode
            if self._stop_all:
                self.q.put(("done_err", "STOPPED_BY_USER"))
            elif rc == 0:
                self.q.put(("done_ok", full_log))
            else:
                self.q.put(("done_err", full_log))
        except Exception as e:
            self.q.put(("done_err", str(e)))
        finally:
            self.proc = None

    def _kill_proc(self, proc):
        try:
            if proc.poll() is None:
                try: proc.stdout.close()
                except: pass
                proc.kill()
                try: proc.wait(timeout=1)
                except: pass
                try:
                    if sys.platform == "win32":
                        subprocess.run(f'taskkill /PID {proc.pid} /T /F', shell=True, capture_output=True, timeout=2)
                except: pass
        except: pass

    def stop_download(self):
        self._stop_all = True
        stopped = 0
        if self.proc and self.proc.poll() is None:
            self._kill_proc(self.proc)
            stopped += 1
        with self._queue_lock:
            for iid, proc in list(self._active_procs.items()):
                self._stop_ids.add(iid)
                if proc and proc.poll() is None:
                    self._kill_proc(proc)
                    stopped += 1
                self._set_queue_status(iid, "⏹ ألغي")
            # ألغِ المعلق
            if hasattr(self, '_pending_queue'):
                for iid in list(getattr(self, '_pending_queue', [])):
                    try:
                        self._set_queue_status(iid, "⏹ ألغي")
                        self._stop_ids.add(iid)
                    except: pass
                self._pending_queue.clear()
            # أي عنصر لا يزال ⏳ انتظار → ألغه
            try:
                for iid in self.queue_tree.get_children():
                    if self.queue_tree.set(iid, "status") in ("⏳ انتظار", "⬇️ جاري"):
                        self._set_queue_status(iid, "⏹ ألغي")
                        self._stop_ids.add(iid)
            except: pass
            self._active_downloads = 0
        if stopped or self.downloading:
            self.log_msg(f"⏹ تم إيقاف {stopped} تحميل بواسطة المستخدم", "warn")
        self.downloading = False
        self.dl_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("تم الإيقاف ⏹")
        self.net_speed_var.set("--")
        self.speed_var.set("")
        self.after(1500, lambda: setattr(self, '_stop_all', False))

    def poll_queue(self):
        try:
            while True:
                item = self.q.get_nowait()
                kind = item[0]
                if kind == "log":
                    _, txt, tag = item
                    self.log_msg(txt, tag)
                elif kind == "log_line":
                    _, line = item
                    # تلوين
                    tag = "info"
                    if "ERROR" in line or "error" in line.lower(): tag="err"
                    elif "WARNING" in line: tag="warn"
                    elif "[download]" in line: tag="ok"
                    self.log.insert("end", line + "\n", tag)
                    self.log.see("end")
                elif kind == "progress":
                    _, v = item
                    self.progress.config(value=v)
                elif kind == "speed":
                    _, s = item
                    self.speed_var.set(s)
                    self.net_speed_var.set(s.split("•")[0].strip() if "•" in s else s)
                elif kind == "status":
                    _, s = item
                    self.status_var.set(s)
                elif kind == "version_update":
                    _, ver = item
                    self.version_lbl.config(text=f"yt-dlp {ver}")
                elif kind == "update_result":
                    # ("update_result", (status, latest, cur)) أو ("error", ...)
                    payload = item[1]
                    status = payload[0] if len(payload)>0 else ""
                    if status == "available":
                        _, latest, cur = payload
                        self.version_lbl.config(text=f"تحديث {latest} متاح!")
                        # في الوضع اليدوي: اسأل المستخدم
                        if messagebox.askyesno("يتوفر تحديث", f"يتوفر إصدار جديد من yt-dlp:\n\nالحالي: {cur}\nالجديد: {latest}\n\nهل تريد تنزيله وتثبيته الآن؟\n(يحل مشاكل تيك توك والمواقع الأخرى)"):
                            self.do_update()
                    elif status == "uptodate":
                        _, latest, cur = payload
                        messagebox.showinfo("محدّث", f"أنت على أحدث إصدار ✅\n\nالإصدار: {cur}")
                        self.version_lbl.config(text=f"yt-dlp {cur} ✅")
                    elif status == "error":
                        messagebox.showwarning("تعذر الفحص", "تعذر جلب آخر إصدار — تحقق من الاتصال وحاول مرة أخرى.")
                        self.version_lbl.config(text=f"yt-dlp {self.current_version or '?'}")
                    elif status == "auto_fail":
                        self.version_lbl.config(text=f"yt-dlp {self.current_version or '?'}")
                elif kind == "update_done":
                    _, ok = item
                    if ok:
                        messagebox.showinfo("تم التحديث", f"تم تحديث yt-dlp بنجاح ✅\nالإصدار الجديد: {self.current_version}")
                    else:
                        messagebox.showerror("فشل التحديث", "فشل التحديث — راجع السجل.\nجرب تشغيل الواجهة كمسؤول أو حدّث يدوياً: yt-dlp -U")
                elif kind == "save_prefs":
                    try: self.save_preferences()
                    except: pass
                elif kind == "show_cookie_help":
                    _, br = item
                    self._show_cookie_help(br)
                elif kind == "queue_progress":
                    _, (iid, pct) = item
                    try: self.queue_tree.set(iid, "progress", pct)
                    except: pass
                elif kind == "queue_status":
                    _, (iid, st) = item
                    try: self.queue_tree.set(iid, "status", st)
                    except: pass
                elif kind == "parallel_slot_free":
                    self.after(50, self._launch_parallel_slots)
                    try:
                        total = len(self.queue_tree.get_children())
                        done = sum(1 for iid in self.queue_tree.get_children() if self.queue_tree.set(iid, "status") == "✅ اكتمل")
                        cancelled = sum(1 for iid in self.queue_tree.get_children() if self.queue_tree.set(iid, "status") == "⏹ ألغي")
                        self.status_var.set(f"متوازي: {done}/{total} اكتمل — نشط: {self._active_downloads}")
                        if self._active_downloads == 0 and len(self._pending_queue if hasattr(self, '_pending_queue') else []) == 0:
                            # كل المهام انتهت — أعد الأزرار
                            self.dl_btn.config(state="normal")
                            # لا تعطل الإيقاف إذا كان هناك لا يزال نشط
                            if self._active_downloads == 0:
                                self.stop_btn.config(state="disabled")
                                self.net_speed_var.set("--")
                    except: pass
                elif kind == "queue_size":
                    _, (iid, sz) = item
                    try: self._set_queue_size(iid, sz)
                    except: pass
                elif kind == "single_size":
                    _, sz = item
                    self.size_var.set(sz)
                elif kind == "net_speed":
                    _, spd = item
                    self.net_speed_var.set(spd)
                    self.speed_var.set(spd)
                elif kind == "queue_speed":
                    _, (iid, spd) = item
                    # حدّث السرعة العامة كآخر سرعة نشطة
                    self.net_speed_var.set(spd)
                elif kind == "done_ok":
                    _, full = item
                    self.downloading=False
                    self._aparat_retry = False
                    self._meyon_retry = False
                    self.dl_btn.config(state="normal"); self.stop_btn.config(state="disabled")
                    self.progress.config(value=100)
                    self.status_var.set("اكتمل التحميل ✅")
                    self.speed_var.set("")
                    self.log_msg("اكتمل التحميل بنجاح ✅", "ok")
                    # فتح المجلد تلقائيا؟ لا
                elif kind == "done_err":
                    _, full = item
                    self.downloading=False
                    self._stop_all = False
                    if full == "STOPPED_BY_USER":
                        self.dl_btn.config(state="normal"); self.stop_btn.config(state="disabled")
                        self.status_var.set("تم الإيقاف ⏹")
                        self.progress.config(value=0)
                        self.net_speed_var.set("--")
                        self.log_msg("⏹ تم الإيقاف بواسطة المستخدم", "warn")
                        continue
                    self.dl_btn.config(state="normal"); self.stop_btn.config(state="disabled")
                    self.status_var.set("فشل التحميل ❌")
                    self.progress.config(value=0)
                    diag = diagnose_error(full)
                    # محاولة بديلة لـ Aparat عبر API زر دانلود
                    if diag and "Aparat" in diag['title'] and not getattr(self, '_aparat_retry', False):
                        direct = get_aparat_direct_url(self.url_var.get())
                        if direct:
                            self.log_msg(f"🔄 محاولة بديلة عبر API زر دانلود: {direct[:100]}...", "info")
                            self.log_msg("✅ وجد رابط مباشر — جاري إعادة التحميل بدون المستخرج", "ok")
                            self._aparat_retry = True
                            self.after(600, lambda u=direct: (self.url_var.set(u), self.start_download()))
                            diag = None
                        else:
                            self._aparat_retry = False
                    elif "meyon" in self.url_var.get().lower() and not getattr(self, '_meyon_retry', False):
                        direct = get_meyon_direct_url(self.url_var.get())
                        if direct:
                            self.log_msg(f"🔄 Meyon fallback HLS: {direct[:100]}...", "info")
                            self.log_msg("✅ وجد رابط HLS — جاري التحميل عبر ffmpeg", "ok")
                            self._meyon_retry = True
                            self.after(600, lambda u=direct: (self.url_var.set(u), self.start_download()))
                            diag = None
                        else:
                            self._meyon_retry = False
                    else:
                        self._aparat_retry = False
                        self._meyon_retry = False
                    if diag:
                        self.log_msg(f"—— تشخيص: {diag['title']} ——", "err")
                        self.log_msg(diag["msg"], "warn")
                        self.log_msg("الحل المقترح:\n" + diag["fix"], "info")
                        # popup مفصل
                        self.show_error_dialog(diag, full)
                    elif not getattr(self, '_aparat_retry', False):
                        self.log_msg("خطأ غير مصنف — نص الخطأ كامل أعلاه", "err")
                        # حاول اقتراح عام
                        self.show_error_dialog(None, full)
        except queue.Empty:
            pass
        self.after(80, self.poll_queue)

    def show_error_dialog(self, diag, full_text):
        win = tk.Toplevel(self)
        win.title("تشخيص الخطأ — الحل المقترح")
        win.geometry("640x420")
        win.transient(self); win.grab_set()
        frm = ttk.Frame(win, padding=14); frm.pack(fill="both", expand=True)
        if diag:
            ttk.Label(frm, text="❌ " + diag["title"], font=("Segoe UI", 12, "bold"), foreground="#c00").pack(anchor="w")
            ttk.Label(frm, text=diag["msg"], wraplength=600, justify="left").pack(anchor="w", pady=6)
            ttk.Label(frm, text="الحل المقترح:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,4))
            txt = tk.Text(frm, height=8, wrap="word", font=("Segoe UI", 9), bg="#fff8e1")
            txt.pack(fill="x")
            txt.insert("1.0", diag["fix"])
            txt.config(state="disabled")
        else:
            ttk.Label(frm, text="❌ فشل التحميل", font=("Segoe UI", 12, "bold"), foreground="#c00").pack(anchor="w")
            ttk.Label(frm, text="لم يتم التعرف على نوع الخطأ تلقائياً. انسخ السجل وابحث عنه.", wraplength=600).pack(anchor="w", pady=6)

        ttk.Label(frm, text="نص الخطأ الخام:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10,4))
        raw = tk.Text(frm, height=7, wrap="word", font=("Consolas", 8), bg="#f8f9fa")
        raw.pack(fill="both", expand=True)
        raw.insert("1.0", full_text[-4000:])
        raw.config(state="disabled")
        btns = ttk.Frame(frm); btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="نسخ الخطأ", command=lambda: (self.clipboard_clear(), self.clipboard_append(full_text), self.status_var.set("تم نسخ الخطأ"))).pack(side="left")
        ttk.Button(btns, text="فتح GitHub yt-dlp", command=lambda: webbrowser.open("https://github.com/yt-dlp/yt-dlp/issues")).pack(side="left", padx=6)
        ttk.Button(btns, text="إغلاق", command=win.destroy).pack(side="right")

if __name__ == "__main__":
    # إنشاء مجلد التحميل الافتراضي
    Path(DEFAULT_OUTPUT).mkdir(parents=True, exist_ok=True)
    app = YtDlpGUI()
    app.mainloop()
