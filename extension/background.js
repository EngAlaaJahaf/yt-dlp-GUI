// background.js - yt-dlp GUI + Udemy direct (merged from Udemy Downloader)
const API = "http://127.0.0.1:8765";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "dl-page", title: "⬇️ تنزيل هذه الصفحة بهذا التطبيق", contexts: ["page"] });
  chrome.contextMenus.create({ id: "dl-link", title: "⬇️ تنزيل هذا الرابط", contexts: ["link"] });
  chrome.contextMenus.create({ id: "dl-video", title: "⬇️ تنزيل هذا الفيديو", contexts: ["video", "audio"] });
  chrome.contextMenus.create({ id: "dl-selection", title: "⬇️ تنزيل الرابط المحدد", contexts: ["selection"] });
  // Udemy: خياران معاً
  chrome.contextMenus.create({ id: "udemy-direct", title: "⬇️ Udemy: تنزيل هذا الفيديو مباشرة", contexts: ["page", "link", "video"], documentUrlPatterns: ["*://*.udemy.com/*"] });
  chrome.contextMenus.create({ id: "udemy-list", title: "📋 Udemy: فتح قائمة الكورس كاملة", contexts: ["page", "link"], documentUrlPatterns: ["*://*.udemy.com/*"] });
});

// ---------- Udemy direct logic (from Sanches extension) ----------
function getUdemyCookies() {
  return new Promise(resolve => {
    chrome.cookies.getAll({ domain: "www.udemy.com" }, cookies => {
      const map = {};
      cookies.forEach(c => map[c.name] = c.value);
      resolve(map);
    });
  });
}
function udemyHeaders(cookies) {
  return {
    "Content-Type": "application/json, text/plain, */*",
    "x-udemy-authorization": "Bearer " + (cookies["access_token"] || ""),
    "x-udemy-cache-brand": cookies["ud_cache_brand"] || "",
    "x-udemy-cache-campaign-code": cookies["ud_cache_campaign_code"] || "",
    "x-udemy-cache-device": cookies["ud_cache_device"] || "",
    "x-udemy-cache-language": cookies["ud_cache_language"] || "",
    "x-udemy-cache-logged-in": cookies["ud_cache_logged_in"] || "",
    "x-udemy-cache-marketplace-country": cookies["ud_cache_marketplace_country"] || "",
    "x-udemy-cache-modern-browser": cookies["ud_cache_modern_browser"] || "",
    "x-udemy-cache-price-country": cookies["ud_cache_price_country"] || "",
    "x-udemy-cache-release": cookies["ud_cache_release"] || "",
    "x-udemy-cache-user": cookies["ud_cache_user"] || "",
    "x-udemy-cache-version": cookies["ud_cache_version"] || ""
  };
}
async function udemyApi(url, params, cookies) {
  const u = new URL(url);
  Object.entries(params || {}).forEach(([k,v]) => u.searchParams.set(k, v));
  const r = await fetch(u.toString(), { headers: udemyHeaders(cookies) });
  if (!r.ok) throw new Error(`Udemy API ${r.status}`);
  return r.json();
}
async function downloadUdemyLecture(pageUrl) {
  const cookies = await getUdemyCookies();
  if (!cookies["ud_cache_user"] || cookies["ud_cache_user"].length < 3) {
    throw new Error("سجّل دخولك في udemy.com أولاً");
  }
  // extract slug and lectureId
  const m = pageUrl.match(/\/course\/([^\/]+)\/learn\/lecture\/(\d+)/);
  if (!m) throw new Error("رابط Udemy غير مدعوم — استخدم رابط المحاضرة /learn/lecture/");
  const slug = m[1];
  const lectureId = m[2];
  // get courseId from slug
  const courseInfo = await udemyApi(`https://www.udemy.com/api-2.0/courses/${slug}`, { "fields[course]": "id,title" }, cookies);
  const courseId = courseInfo.id;
  if (!courseId) throw new Error("لم يُعثر على courseId");
  // get lecture asset
  const lecture = await udemyApi(`https://www.udemy.com/api-2.0/users/me/subscribed-courses/${courseId}/lectures/${lectureId}`, {
    "fields[lecture]": "asset,description,download_url",
    "fields[asset]": "asset_type,length,stream_urls,captions,download_urls"
  }, cookies);
  const asset = lecture.asset;
  if (!asset) throw new Error("لا يوجد asset للفيديو");
  // prefer download_urls then stream_urls.Video
  let fileUrl = null;
  if (asset.download_urls && asset.download_urls.Video) {
    // highest quality
    const vids = asset.download_urls.Video;
    fileUrl = vids.reduce((a,b)=> (b.height||0)>(a.height||0)?b:a, vids[0]).file;
  } else if (asset.stream_urls && asset.stream_urls.Video) {
    fileUrl = asset.stream_urls.Video[0].file;
  }
  if (!fileUrl) throw new Error("لم يُعثر على رابط الفيديو");
  const title = (lecture.title || `lecture-${lectureId}`).replace(/[\\/:*?"<>|]/g, "");
  await new Promise((resolve, reject) => {
    chrome.downloads.download({
      url: fileUrl,
      filename: `Udemy/${slug}/${lectureId} - ${title}.mp4`,
      saveAs: false
    }, id => {
      if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
      else resolve(id);
    });
  });
  return { ok: true, file: title };
}

function openUdemyWindow() {
  return chrome.windows.create({
    url: chrome.runtime.getURL("udemy.html"),
    type: "popup",
    width: 1092,
    height: 700,
    focused: true
  });
}
async function sendToApp(url) {
  if (!url || !/^https?:\/\//.test(url)) return { ok: false, error: "رابط غير صالح" };
  // Udemy: حاول تنزيل مباشر أولاً (السلوك السابق) — يحافظ على 403 fix
  if (/udemy\.com\/course.*\/learn\/lecture\//.test(url)) {
    try {
      await downloadUdemyLecture(url);
      return { ok: true, via: "udemy-direct" };
    } catch (e) {
      console.warn("Udemy direct failed, opening window as fallback:", e.message);
      try {
        await openUdemyWindow();
        return { ok: true, via: "udemy-window" };
      } catch {}
    }
  }
  if (/udemy\.com/.test(url)) {
    // رابط كورس عام — افتح النافذة مباشرة
    try {
      await openUdemyWindow();
      return { ok: true, via: "udemy-window" };
    } catch (e) {
      console.warn("Udemy window failed:", e.message);
    }
  }
  try {
    const r = await fetch(`${API}/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const j = await r.json().catch(() => ({}));
    if (r.ok) return { ok: true, data: j };
    return { ok: false, error: j.error || `HTTP ${r.status}` };
  } catch (e) {
    return { ok: false, error: "التطبيق غير مشغّل. افتح yt-dlp GUI أولاً (127.0.0.1:8765)" };
  }
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "udemy-direct") {
    let url = info.linkUrl || info.srcUrl || info.pageUrl;
    try { await downloadUdemyLecture(url); chrome.notifications?.create({ type: "basic", iconUrl: "icon128.png", title: "تم التنزيل المباشر ✅", message: url.slice(0,120) }); } catch(e){ console.warn(e); }
    return;
  }
  if (info.menuItemId === "udemy-list") {
    await openUdemyWindow();
    return;
  }
  let url = info.linkUrl || info.srcUrl || info.pageUrl;
  if (info.selectionText && /^https?:\/\//.test(info.selectionText.trim())) url = info.selectionText.trim();
  const res = await sendToApp(url);
  if (res.ok) {
    chrome.notifications?.create({ type: "basic", iconUrl: "icon128.png", title: "تم الإرسال ✅", message: url.slice(0,120) });
  } else {
    console.warn(res.error);
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "download") {
    sendToApp(msg.url).then(sendResponse);
    return true;
  }
  if (msg.action === "downloadUdemyDirect") {
    downloadUdemyLecture(msg.url).then(r=>sendResponse({ok:true,r})).catch(e=>sendResponse({ok:false,error:e.message}));
    return true;
  }
  if (msg.action === "openUdemyWindow") {
    openUdemyWindow().then(()=>sendResponse({ok:true})).catch(e=>sendResponse({ok:false,error:e.message}));
    return true;
  }
  if (msg.action === "ping") {
    fetch(`${API}/ping`).then(r=>r.json()).then(j=>sendResponse({ok:true,j})).catch(()=>sendResponse({ok:false}));
    return true;
  }
});
