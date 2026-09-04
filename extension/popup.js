const $ = id => document.getElementById(id);
const API = "http://127.0.0.1:8765";

function setStatus(msg, cls="ok") {
  const s = $("status");
  s.textContent = msg;
  s.className = "status " + cls;
}

async function getTabUrl() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab?.url || "";
}

function isUdemy(u){ return /udemy\.com/.test(u); }
function updateUdemyBox(){
  const u = $("url").value.trim();
  $("udemyBox").style.display = isUdemy(u) ? "block" : "none";
}
$("url").addEventListener("input", updateUdemyBox);

$("dl").onclick = async () => {
  const url = $("url").value.trim();
  if (!/^https?:\/\//.test(url)) { setStatus("الصق رابط صحيح يبدأ بـ https://", "err"); return; }
  $("dl").disabled = true;
  setStatus("جاري الإرسال للتطبيق...", "warn");
  const res = await chrome.runtime.sendMessage({ action: "download", url });
  $("dl").disabled = false;
  if (res?.ok) {
    if(res.via==="udemy-window") setStatus("📋 فتحت نافذة قائمة Udemy — اختر الفيديوهات", "ok");
    else setStatus("✅ تم الإرسال للتطبيق — تابع التقدم في الواجهة", "ok");
  } else setStatus("❌ " + (res?.error || "فشل"), "err");
};
$("udemyDirect").onclick = async () => {
  const url = $("url").value.trim();
  setStatus("⬇️ تنزيل Udemy مباشر...", "warn");
  const r = await chrome.runtime.sendMessage({ action: "downloadUdemyDirect", url });
  if(r?.ok) setStatus("✅ بدأ التحميل المباشر", "ok"); else setStatus("❌ "+(r?.error||"فشل"), "err");
};
$("udemyList").onclick = async () => {
  const r = await chrome.runtime.sendMessage({ action: "openUdemyWindow" });
  if(r?.ok) setStatus("📋 فتحت نافذة القائمة الكاملة", "ok"); else setStatus("❌ "+(r?.error||"فشل"), "err");
};

$("copy").onclick = async () => {
  const v = $("url").value.trim();
  await navigator.clipboard.writeText(v);
  setStatus("تم النسخ 📋", "ok");
};

$("ping").onclick = async () => {
  setStatus("جاري فحص الاتصال...", "warn");
  const r = await chrome.runtime.sendMessage({ action: "ping" });
  if (r?.ok) setStatus("✅ التطبيق متصل على 127.0.0.1:8765", "ok");
  else setStatus("❌ التطبيق غير مشغّل — افتح yt-dlp-GUI.exe أولاً", "err");
};

$("open").onclick = async () => {
  // just ping to show folder? extension cannot open folder directly, notify app
  setStatus("افتح التطبيق → 'فتح مجلد التحميل'", "warn");
};

(async () => {
  const url = await getTabUrl();
  if (url) { $("url").value = url; updateUdemyBox(); }
  // auto ping
  const r = await chrome.runtime.sendMessage({ action: "ping" }).catch(()=>null);
  if (!r?.ok) setStatus("⚠️ افتح yt-dlp GUI أولاً ليستقبل التحميل", "warn");
})();
