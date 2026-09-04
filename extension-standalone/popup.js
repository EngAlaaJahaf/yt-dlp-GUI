const $ = id => document.getElementById(id);
function setStatus(m,c="ok"){const s=$("status");s.textContent=m;s.className="status "+c;s.style.display="block";}

$("scan").onclick = async () => {
  const [tab] = await chrome.tabs.query({active:true, currentWindow:true});
  if(!tab?.id) return;
  setStatus("جاري الفحص...", "ok");
  try {
    const res = await chrome.scripting.executeScript({
      target:{tabId: tab.id},
      func: () => {
        const out=[];
        document.querySelectorAll("video").forEach(v=>{
          if(v.currentSrc) out.push({src:v.currentSrc, type:"video tag", w:v.videoWidth, h:v.videoHeight});
          if(v.src && v.src!==v.currentSrc) out.push({src:v.src, type:"video.src"});
          const s=v.querySelector("source");
          if(s && s.src) out.push({src:s.src, type:"source"});
        });
        document.querySelectorAll("source[src]").forEach(s=>{ if(!out.find(o=>o.src===s.src)) out.push({src:s.src, type:"source tag"})});
        // also find direct mp4 links in page
        document.querySelectorAll('a[href$=".mp4"],a[href$=".webm"],a[href*="googlevideo"],a[href*=".m3u8"]').forEach(a=>out.push({src:a.href, type:"link"}));
        // performance entries for media
        try{
          performance.getEntriesByType("resource").forEach(r=>{
            if(/\.(mp4|webm|m3u8|mpd)(\?|$)/.test(r.name) && !out.find(o=>o.src===r.name)) out.push({src:r.name, type:"resource"});
          });
        }catch(e){}
        return [...new Map(out.map(o=>[o.src,o])).values()].slice(0,20);
      }
    });
    let items = res[0]?.result || [];
    // Aparat fallback عبر API زر دانلود
    try {
      const [tab2] = await chrome.tabs.query({active:true, currentWindow:true});
      if (/aparat\.com\/v\//.test(tab2.url)) {
        const m = tab2.url.match(/\/v\/([a-zA-Z0-9]+)/);
        if (m) {
          const api = `https://www.aparat.com/api/fa/v1/video/video/show/videohash/${m[1]}`;
          const r = await fetch(api);
          const j = await r.json();
          const fl = j?.data?.attributes?.file_link_all;
          if (fl && Array.isArray(fl)) {
            fl.forEach(f => { if(f.urls && f.urls[0]) items.push({src: f.urls[0], type: `Aparat ${f.profile}`}); });
          } else if (j?.data?.attributes?.file_link) {
            items.push({src: j.data.attributes.file_link, type: "Aparat file_link"});
          }
        }
      }
    } catch(e) { console.warn("Aparat API", e); }
    const list=$("list"); list.innerHTML="";
    if(!items.length){ setStatus("لم يُعثر على فيديو مباشر في هذه الصفحة", "err"); $("dlAll").style.display="none"; return; }
    setStatus(`عُثر على ${items.length} رابط`, "ok");
    items.forEach((it,i)=>{
      const isDirect = /\.(mp4|webm)(\?|$)/i.test(it.src);
      const isHls = /\.(m3u8|mpd)(\?|$)/i.test(it.src);
      const div=document.createElement("div");
      div.className="item";
      div.innerHTML=`<b>${isDirect?"🟢 مباشر":isHls?"🟡 HLS/m3u8":"🔵"} ${it.type}</b> ${it.w?`(${it.w}x${it.h})`:""}<br><a href="${it.src}" target="_blank">${it.src.slice(0,80)}...</a><div class="dl" data-i="${i}">${isDirect?"⬇️ تحميل":"⬇️ تحميل (قد لا يعمل بدون دمج)"}</div>`;
      list.appendChild(div);
    });
    $("dlAll").style.display="block";
    $("dlAll").onclick = ()=> {
      items.forEach(it=>{ if(/\.(mp4|webm)(\?|$)/i.test(it.src)) chrome.downloads.download({url: it.src}); });
      setStatus("بدأ تحميل الروابط المباشرة", "ok");
    };
    list.querySelectorAll(".dl").forEach(el=> el.onclick = ()=>{
      const it = items[el.dataset.i];
      chrome.downloads.download({url: it.src}, id=> {
        if(chrome.runtime.lastError) setStatus(chrome.runtime.lastError.message, "err");
        else setStatus("بدأ التحميل", "ok");
      });
    });
  } catch(e){ setStatus(e.message, "err"); }
};
