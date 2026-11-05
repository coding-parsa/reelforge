/* Reelforge desktop UI — vanilla JS, no build step. */

const S = {
  boot: null,
  settings: {},
  catalog: {},
  projects: [],
  project: null,
  view: 'studio',
  lang: 'en',
  preview: null,
  pollTimer: null,
  sceneFocus: null,
  settingsTab: 'ai',
  queueTab: 'import',
  busy: false,
};

/* ------------------------------------------------------------------ i18n */
const I18N = {
  en: {
    'nav.studio': 'Studio', 'nav.queue': 'Queue', 'nav.library': 'Library', 'nav.design': 'Design',
    'nav.extend': 'Extend', 'nav.settings': 'Settings',
    'common.save': 'Save', 'common.cancel': 'Cancel', 'common.close': 'Close', 'common.delete': 'Delete',
    'common.open': 'Open', 'common.copy': 'Copy', 'common.copied': 'Copied', 'common.loading': 'Loading…',
    'common.none': 'None', 'common.yes': 'Yes', 'common.no': 'No', 'common.retry': 'Retry',
    'common.apply': 'Rewrite',
    'studio.new': 'New video', 'studio.title': 'Video title', 'studio.source': 'Source',
    'studio.makecards': 'Make the cards', 'studio.makeai': 'Write with AI', 'studio.result': 'Your video',
    'f.label': 'Small label', 'f.big': 'Big text', 'f.body': 'Sentence under it', 'f.chip': 'Tag',
    'f.num': 'Number', 'f.unit': 'Unit', 'f.bullets': 'List items',
    'k.fact': 'Text card', 'k.stat': 'Number card', 'k.list': 'List card', 'k.cta': 'End card',
    'studio.url': 'Article URL', 'studio.paste': 'Paste text or a script instead',
    'studio.brief': 'Direction for the AI (optional)', 'studio.brief.ph': 'e.g. blunt tone, audience 18-24, mention the deadline',
    'studio.generate': 'Write the script', 'studio.blank': 'Start from scratch',
    'studio.scenes': 'Scenes', 'studio.preview': 'Preview', 'studio.render': 'Render video',
    'studio.render_draft': 'Draft', 'studio.addscene': 'Add card',
    'studio.kicker': 'Kicker (2-3 words)', 'studio.big': 'Headline (max 7 words, Enter for line 2)',
    'studio.body': 'Body (one sentence)', 'studio.chip': 'Chip (max 4 words)',
    'studio.bullets': 'Bullets (one per line)', 'studio.num': 'Number', 'studio.unit': 'Unit',
    'studio.rewrite': 'Ask the AI to rewrite this card', 'studio.kind': 'Card type',
    'studio.empty': 'Paste an article URL or some text on the left to begin.',
    'studio.needscript': 'Write a script to see the preview.',
    'studio.design': 'Design', 'studio.brand': 'Brand', 'studio.export': 'Metadata',
    'studio.meta': 'Write the publishing metadata', 'studio.hashtags': 'Hashtags',
    'studio.description': 'Description', 'studio.hook': 'Hook line',
    'queue.import': 'Add videos', 'queue.items': 'Queue', 'queue.urls': 'One URL per line',
    'queue.sitemap': 'Sitemap', 'queue.sitemap.ph': 'https://example.com/sitemap.xml',
    'queue.prefix': 'Only URLs containing', 'queue.limit': 'Max',
    'queue.add': 'Add to queue', 'queue.start': 'Start queue', 'queue.stop': 'Stop',
    'queue.auto': 'Hands-off', 'queue.auto.hint': 'Generate the script and render each item without asking.',
    'queue.review': 'Review before rendering', 'queue.review.hint': 'Every script waits for you to approve it.',
    'library.title': 'Rendered videos', 'library.empty': 'Nothing rendered yet.',
    'library.download': 'Download', 'library.folder': 'Folder', 'library.copy_meta': 'Copy caption',
    'design.title': 'Design system', 'design.hint': 'Every video picks its own theme, layout and motion unless you pin them. That is what keeps a feed from looking like one template.',
    'design.defaults': 'Save as defaults', 'design.theme': 'Theme', 'design.layout': 'Layout',
    'design.background': 'Background', 'design.transition': 'Transition', 'design.frame': 'Frame',
    'design.brand': 'Logo placement', 'design.format': 'Format',
    'extend.title': 'Extend', 'extend.hooks': 'Hooks', 'extend.hooks.hint': 'Drop a Python or JavaScript file in the hooks folder and it runs inside the pipeline. Return JSON to change the script, the design or to publish the result.',
    'extend.prompts': 'Prompt templates', 'extend.prompts.hint': 'These are the instructions the AI gets. Placeholders in double braces are filled by the app.',
    'extend.themes': 'Theme packs', 'extend.themes.hint': 'Add a .json file to the themes folder with deep/surface/ink/muted/accent/accent_deep/glow_a/glow_b colours, restart, and it appears in Design.',
    'settings.title': 'Settings', 'settings.ai': 'AI', 'settings.brand': 'Brand', 'settings.render': 'Render',
    'settings.automation': 'Automation', 'settings.paths': 'Paths', 'settings.ui': 'Interface',
    'settings.provider': 'Provider', 'settings.model': 'Model', 'settings.base': 'Base URL',
    'settings.key': 'API key', 'settings.key.hint': 'Stored with Windows DPAPI on this machine. Never leaves the app.',
    'settings.test': 'Test connection', 'settings.saved': 'Saved',
    'settings.quality': 'Quality', 'settings.fps': 'Frames per second',
    'settings.volume': 'Music volume', 'settings.sfx': 'Sound effects', 'settings.cover': 'Embed a cover frame',
    'settings.assets': 'Asset folder', 'settings.browser': 'Browser', 'settings.ffmpeg': 'ffmpeg',
    'settings.detect': 'Detect again', 'settings.autogen': 'Write scripts automatically',
    'settings.autometa': 'Write the caption automatically', 'settings.openfolder': 'Open folder',
    'status.draft': 'draft', 'status.script_ready': 'script ready', 'status.queued': 'queued',
    'status.rendering': 'rendering', 'status.done': 'done', 'status.failed': 'failed',
    'status.review': 'needs review', 'status.needs_script': 'needs a script',
  },
  fa: {
    'nav.studio': 'استودیو', 'nav.queue': 'صف', 'nav.library': 'کتابخانه', 'nav.design': 'ظاهر',
    'nav.extend': 'توسعه', 'nav.settings': 'تنظیمات',
    'common.save': 'ذخیره', 'common.cancel': 'انصراف', 'common.close': 'بستن', 'common.delete': 'حذف',
    'common.open': 'بازکردن', 'common.copy': 'کپی', 'common.copied': 'کپی شد', 'common.loading': 'در حال بارگذاری…',
    'common.none': 'هیچ', 'common.yes': 'بله', 'common.no': 'خیر', 'common.retry': 'تلاش دوباره',
    'common.apply': 'بازنویسی',
    'studio.new': 'ویدیوی تازه', 'studio.title': 'عنوان ویدیو', 'studio.source': 'منبع',
    'studio.makecards': 'ساخت کارت‌ها', 'studio.makeai': 'نوشتن با هوش مصنوعی', 'studio.result': 'ویدیوی تو',
    'f.label': 'برچسب کوچک', 'f.big': 'متن اصلی', 'f.body': 'جملهٔ زیر آن', 'f.chip': 'برچسب',
    'f.num': 'عدد', 'f.unit': 'واحد', 'f.bullets': 'موارد فهرست',
    'k.fact': 'کارت متنی', 'k.stat': 'کارت عددی', 'k.list': 'کارت فهرست', 'k.cta': 'کارت پایانی',
    'studio.url': 'نشانی مقاله', 'studio.paste': 'یا متن را اینجا بچسبان',
    'studio.brief': 'راهنمای هوش مصنوعی (اختیاری)', 'studio.brief.ph': 'مثال: لحن صریح، مخاطب ۱۸ تا ۲۴ سال، به مهلت اشاره کن',
    'studio.generate': 'نوشتن متن', 'studio.blank': 'از صفر شروع می‌کنم',
    'studio.scenes': 'صحنه‌ها', 'studio.preview': 'پیش‌نمایش', 'studio.render': 'ساخت ویدیو',
    'studio.render_draft': 'نسخهٔ سریع', 'studio.addscene': 'افزودن کارت',
    'studio.kicker': 'برچسب (۲ تا ۳ کلمه)', 'studio.big': 'تیتر (حداکثر ۷ کلمه، Enter برای خط دوم)',
    'studio.body': 'متن (یک جمله)', 'studio.chip': 'چیپ (حداکثر ۴ کلمه)',
    'studio.bullets': 'فهرست (هر مورد یک خط)', 'studio.num': 'عدد', 'studio.unit': 'واحد',
    'studio.rewrite': 'از هوش مصنوعی بخواه این کارت را بازنویسی کند', 'studio.kind': 'نوع کارت',
    'studio.empty': 'برای شروع، نشانی مقاله یا متن را در ستون کنار بگذار.',
    'studio.needscript': 'برای دیدن پیش‌نمایش، اول متن را بنویس.',
    'studio.design': 'ظاهر', 'studio.brand': 'برند', 'studio.export': 'متادیتا',
    'studio.meta': 'ساخت متن انتشار', 'studio.hashtags': 'هشتگ‌ها',
    'studio.description': 'توضیحات', 'studio.hook': 'جملهٔ قلاب',
    'queue.import': 'افزودن ویدیو', 'queue.items': 'صف', 'queue.urls': 'هر خط یک نشانی',
    'queue.sitemap': 'نقشهٔ سایت', 'queue.sitemap.ph': 'https://example.com/sitemap.xml',
    'queue.prefix': 'فقط نشانی‌های شامل', 'queue.limit': 'حداکثر',
    'queue.add': 'افزودن به صف', 'queue.start': 'شروع صف', 'queue.stop': 'توقف',
    'queue.auto': 'تمام‌خودکار', 'queue.auto.hint': 'متن را بنویس و بدون پرسیدن رندر کن.',
    'queue.review': 'بازبینی پیش از رندر', 'queue.review.hint': 'هر متن منتظر تأیید تو می‌ماند.',
    'library.title': 'ویدیوهای ساخته‌شده', 'library.empty': 'هنوز چیزی ساخته نشده.',
    'library.download': 'دانلود', 'library.folder': 'پوشه', 'library.copy_meta': 'کپی کپشن',
    'design.title': 'سیستم طراحی', 'design.hint': 'هر ویدیو تم، چیدمان و حرکت خودش را می‌گیرد مگر اینکه قفلش کنی؛ همین باعث می‌شود فید شبیه یک قالب تکراری نشود.',
    'design.defaults': 'ذخیره به‌عنوان پیش‌فرض', 'design.theme': 'تم', 'design.layout': 'چیدمان',
    'design.background': 'پس‌زمینه', 'design.transition': 'گذار', 'design.frame': 'قاب',
    'design.brand': 'جای لوگو', 'design.format': 'نسبت تصویر',
    'extend.title': 'توسعه', 'extend.hooks': 'هوک‌ها', 'extend.hooks.hint': 'یک فایل پایتون یا جاوااسکریپت در پوشهٔ hooks بگذار تا داخل خط تولید اجرا شود. با برگرداندن JSON متن، ظاهر یا انتشار را عوض کن.',
    'extend.prompts': 'قالب پرامپت‌ها', 'extend.prompts.hint': 'این‌ها دستورهایی است که هوش مصنوعی می‌گیرد. جای‌نگهدارهای داخل آکولاد دوتایی را برنامه پر می‌کند.',
    'extend.themes': 'بسته‌های تم', 'extend.themes.hint': 'یک فایل .json با رنگ‌های deep/surface/ink/muted/accent/accent_deep/glow_a/glow_b در پوشهٔ themes بگذار و برنامه را دوباره باز کن.',
    'settings.title': 'تنظیمات', 'settings.ai': 'هوش مصنوعی', 'settings.brand': 'برند', 'settings.render': 'رندر',
    'settings.automation': 'خودکارسازی', 'settings.paths': 'مسیرها', 'settings.ui': 'رابط',
    'settings.provider': 'سرویس‌دهنده', 'settings.model': 'مدل', 'settings.base': 'آدرس پایه',
    'settings.key': 'کلید API', 'settings.key.hint': 'با DPAPI ویندوز روی همین دستگاه ذخیره می‌شود و از برنامه بیرون نمی‌رود.',
    'settings.test': 'آزمایش اتصال', 'settings.saved': 'ذخیره شد',
    'settings.quality': 'کیفیت', 'settings.fps': 'فریم بر ثانیه',
    'settings.volume': 'صدای موسیقی', 'settings.sfx': 'افکت صوتی', 'settings.cover': 'جاسازی تصویر کاور',
    'settings.assets': 'پوشهٔ دارایی‌ها', 'settings.browser': 'مرورگر', 'settings.ffmpeg': 'ffmpeg',
    'settings.detect': 'تشخیص دوباره', 'settings.autogen': 'نوشتن خودکار متن',
    'settings.autometa': 'نوشتن خودکار کپشن', 'settings.openfolder': 'بازکردن پوشه',
    'status.draft': 'پیش‌نویس', 'status.script_ready': 'متن آماده', 'status.queued': 'در صف',
    'status.rendering': 'در حال رندر', 'status.done': 'تمام', 'status.failed': 'خطا',
    'status.review': 'منتظر بازبینی', 'status.needs_script': 'بدون متن',
  },
};

const t = (k) => (I18N[S.lang] && I18N[S.lang][k]) || I18N.en[k] || k;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

/* ------------------------------------------------------------------ api */
async function api(path, body, method) {
  const opts = { method: method || (body ? 'POST' : 'GET'), headers: { 'X-Reelforge': '1' } };
  if (body !== undefined && body !== null) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch (e) { data = null; }
  if (!res.ok) throw new Error((data && (data.detail || data.error)) || `HTTP ${res.status}`);
  return data;
}

function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; }, kind === 'err' ? 7000 : 3200);
  setTimeout(() => el.remove(), kind === 'err' ? 7600 : 3800);
}

function modal(html, onMount) {
  $('#modal').innerHTML = html;
  $('#overlay').hidden = false;
  if (onMount) onMount($('#modal'));
}
function closeModal() { $('#overlay').hidden = true; }
window.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

const hostOf = (url) => { try { return new URL(url).hostname.replace(/^www\./, ''); } catch (e) { return 'link'; } };
const statusBadge = (s) => `<span class="badge ${esc(s || 'draft')}"><span class="dot"></span>${esc(t('status.' + (s || 'draft')))}</span>`;
const fmtDur = (d) => d ? `${Math.round(d)}s` : '—';

/* ------------------------------------------------------------------ boot */
async function boot() {
  try {
    S.boot = await api('/api/bootstrap');
  } catch (e) {
    $('#boottext').textContent = 'Could not reach the local server. Is Reelforge still running?';
    return;
  }
  S.settings = S.boot.settings;
  S.catalog = S.boot.catalog;
  S.projects = S.boot.projects || [];
  S.lang = S.settings.ui_lang || 'en';
  applyLang();
  $('#version').textContent = 'v' + S.boot.version;
  $('#boot').classList.add('gone');
  if (!(S.boot.binaries || {}).ok) warnBinaries();
  if (!S.settings.onboarded) onboarding();
  const openId = new URLSearchParams(location.search).get('project');
  if (openId) openProject(openId);
  else setView('studio');
  setInterval(pollQueue, 3000);
}

function applyLang() {
  document.documentElement.lang = S.lang;
  document.documentElement.dir = S.lang === 'fa' ? 'rtl' : 'ltr';
  $('#langToggle').textContent = S.lang === 'fa' ? 'فا' : 'EN';
  $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  render();
}

function warnBinaries() {
  const b = S.boot.binaries || {};
  const missing = [b.ffmpeg ? null : 'ffmpeg', b.browser ? null : 'a Chromium browser'].filter(Boolean);
  toast('Missing ' + missing.join(' and ') + ' — rendering is disabled until that is fixed (Settings → Paths).', 'err');
}

/* ------------------------------------------------------------------ nav */
function setView(v, opts = {}) {
  S.view = v;
  $$('.navbtn').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  if (!opts.keepProject && v !== 'studio') { /* keep the project open in the background */ }
  render();
}

document.addEventListener('click', (e) => {
  const nav = e.target.closest('.navbtn');
  if (nav) { setView(nav.dataset.view); return; }
});

$('#langToggle').addEventListener('click', async () => {
  S.lang = S.lang === 'fa' ? 'en' : 'fa';
  S.settings.ui_lang = S.lang;
  applyLang();
  api('/api/settings', { ui_lang: S.lang }).catch(() => {});
});

/* ------------------------------------------------------------------ router */
function render() {
  $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  const view = $('#view');
  const crumbs = $('#crumbs');
  const actions = $('#topactions');
  actions.innerHTML = '';
  if (S.view === 'studio') renderStudio(view, crumbs, actions);
  else if (S.view === 'queue') renderQueue(view, crumbs, actions);
  else if (S.view === 'library') renderLibrary(view, crumbs, actions);
  else if (S.view === 'design') renderDesign(view, crumbs, actions);
  else if (S.view === 'extend') renderExtend(view, crumbs, actions);
  else renderSettings(view, crumbs, actions);
}

/* ================================================================== STUDIO */
function backToStart() {
  S.project = null;
  S.preview = null;
  S.view = 'studio';
  render();
  setTimeout(() => $('#startInput')?.focus(), 60);
}

async function openProject(pid) {
  try {
    S.project = await api('/api/project/' + pid);
  } catch (e) { toast(e.message, 'err'); return; }
  S.view = 'studio';
  $$('.navbtn').forEach(b => b.classList.toggle('active', b.dataset.view === 'studio'));
  S.preview = null;
  render();
  if ((S.project.script || {}).scenes) refreshPreview();
  if (['queued', 'rendering'].includes(S.project.status)) watchJob(S.project.id);
}

function renderStudio(view, crumbs, actions) {
  const p = S.project;
  crumbs.innerHTML = p
    ? `<h1 title="${esc(p.title || '')}">${esc(p.title || 'Untitled')}</h1>${statusBadge(p.status)}
       ${p.source_url ? `<a class="tag" href="${esc(p.source_url)}" target="_blank" rel="noreferrer"
            title="${esc(p.source_url)}">↗ ${esc(hostOf(p.source_url))}</a>` : '<span class="tag">pasted text</span>'}`
    : `<h1>${t('nav.studio')}</h1>`;

  const canRender = !!(p && p.script);
  actions.innerHTML = `
    <button class="btn ghost small" data-act="new">+ ${t('studio.new')}</button>
    ${p && p.script ? `<button class="btn small" data-act="preview">${t('studio.preview')}</button>` : ''}
    ${p ? `<button class="btn small" data-act="draft" ${canRender ? '' : 'disabled'}>${t('studio.render_draft')}</button>` : ''}
    ${p ? `<button class="btn primary small" data-act="render" ${canRender ? '' : 'disabled'}>▸ ${t('studio.render')}</button>` : ''}`;

  if (!p) {
    renderStart(view);
    return;
  }

  const script = p.script || null;
  const design = p.design || {};
  view.innerHTML = `
    <div class="studio">
      <div class="studio-main">
        ${p.video ? `<div class="card resultcard">
          <div class="row" style="margin-bottom:10px"><h3 style="margin:0">${t('studio.result')}</h3>
            <span class="spacer"></span>
            <span class="tiny muted">${fmtDur(p.duration)} · ${p.size_mb || 0} MB</span></div>
          <video src="/out/${p.id}/video.mp4" controls preload="metadata" poster="/out/${p.id}/cover.jpg"></video>
          <div class="row" style="margin-top:10px">
            <a class="btn primary small" href="/out/${p.id}/video.mp4" download>${t('library.download')}</a>
            <button class="btn ghost small" data-act="openout" data-path="${esc(p.video)}">${t('settings.openfolder')}</button>
            <button class="btn ghost small" data-act="openlib">${t('nav.library')}</button>
          </div>
        </div>` : ''}
        <div class="jobbar" id="jobbar" hidden>
          <div class="jprog"><i id="jprog"></i></div>
          <span class="jmsg" id="jmsg"></span>
          <button class="btn ghost small" data-act="canceljob">Cancel</button>
        </div>
        ${p.status === 'review' ? `<div class="card" style="border-color:rgba(111,214,196,.45);background:rgba(111,214,196,.06)">
          <div class="row"><b>Script ready — waiting for your approval</b><span class="spacer"></span>
            <button class="btn small" data-act="preview">${t('studio.preview')}</button>
            <button class="btn primary small" data-act="render">▸ ${t('studio.render')}</button></div>
          <p class="tiny muted" style="margin:8px 0 0">Review the cards below, fix anything, then render. This gate is on because “review before rendering” is enabled in Queue.</p>
        </div>` : ''}
        ${p.error ? `<div class="card" style="border-color:#5a2a30;background:#2a1418">
          <div class="row"><b style="color:var(--danger)">Last error</b><span class="spacer"></span>
            <button class="btn ghost small" data-copy="${esc(p.error)}">${t('common.copy')}</button></div>
          <p class="tiny" style="margin:8px 0 0;color:#ffc9c9;white-space:pre-wrap">${esc(p.error)}</p>
        </div>` : ''}
        <div class="card" id="sourceCard">
          <div class="row" style="margin-bottom:10px">
            <h3 style="margin:0">${t('studio.source')}</h3>
            <span class="spacer"></span>
            <span class="tiny muted">${(p.article || {}).word_count || 0} words${(p.article || {}).image ? ' · image' : ''}</span>
          </div>
          <p class="srcname">${esc((p.article || {}).title || '')}</p>
          <div class="srcbox">
            <input type="url" id="srcUrl" placeholder="https://example.com/article" value="${esc(p.source_url || '')}">
            <button class="btn small" data-act="fetch" title="Load this URL">↻</button>
          </div>
          <label class="field" style="margin-top:12px">
            <span>${t('studio.brief')}</span>
            <input type="text" id="brief" placeholder="${esc(t('studio.brief.ph'))}" value="${esc((p.meta || {}).brief || '')}">
          </label>
          <div class="row">
            <button class="btn primary small" data-act="generate">${p.script ? '↻ Regenerate cards' : '✍ ' + t('studio.makecards')}</button>
            ${S.boot.ai_configured ? `<button class="btn small" data-act="generate-ai">✦ ${t('studio.makeai')}</button>` : ''}
            <button class="btn ghost small" data-act="blank">${t('studio.blank')}</button>
          </div>
          <p class="tiny muted" style="margin:8px 0 0">${S.boot.ai_configured
            ? '“Regenerate” rebuilds the cards from the article text — no AI, instant, free.'
            : 'No AI key set: the cards are built from the article text itself. Add a key in Settings to write them with a model.'}</p>
        </div>

        <div class="card">
          <div class="row" style="margin-bottom:12px">
            <h3 style="margin:0">${t('studio.scenes')}</h3>
            <span class="spacer"></span>
            ${script ? `<button class="btn ghost small" data-act="addscene">+ ${t('studio.addscene')}</button>` : ''}
          </div>
          <div id="scenes">${script ? script.scenes.map((sc, i) => sceneCard(sc, i)).join('') : `
            <div class="scenes-empty">
              <p>This video has no cards yet.</p>
              <div class="row">
                <button class="btn primary small" data-act="generate">✍ ${t('studio.makecards')}</button>
                ${S.boot.ai_configured ? `<button class="btn small" data-act="generate-ai">✦ ${t('studio.makeai')}</button>` : ''}
                <button class="btn ghost small" data-act="blank">${t('studio.blank')}</button>
              </div>
              <p class="tiny muted">Without a key, Reelforge turns the article text into cards itself.</p>
            </div>`}</div>
        </div>

        <div class="card" id="metaCard">
          <div class="row"><h3 style="margin:0">${esc(t('studio.export'))}</h3><span class="spacer"></span>
            <button class="btn ghost small" data-act="meta">✦ ${t('studio.meta')}</button></div>
          ${renderMeta(p.meta)}
        </div>
      </div>

      <div class="studio-side">
        <div class="phonewrap">
          <div class="phone ${design.format === '1:1' ? 'square' : design.format === '16:9' ? 'wide' : design.format === '4:5' ? 'tall' : ''}" id="phone">
            ${S.preview ? `<iframe id="pframe" src="${esc(S.preview.page)}" allow="autoplay"></iframe>` : `<div class="empty">${t('studio.needscript')}</div>`}
          </div>
          <div class="phone-ctl">
            <button class="btn small" data-act="play">▶</button>
            <div class="track"><i id="ptrack"></i></div>
            <span class="tiny muted mono" id="ptime">0.0s</span>
            <button class="btn ghost small" data-act="popout" title="Open the preview in a window">⤢</button>
          </div>
          <div class="scenelist" id="scenelist">
            ${(S.preview && S.preview.scenes ? S.preview.scenes : []).map((sc, i) =>
              `<button data-jump="${sc.start}" title="${esc(sc.kind)}">${i + 1} · ${sc.kind}</button>`).join('')}
          </div>
        </div>

        <div class="card">
          <h3 style="margin:0 0 4px">${t('studio.design')}</h3>
          <div class="tiny muted" style="margin-bottom:10px">${esc((S.preview && S.preview.design.theme) || design.theme || 'auto')} · ${esc(design.format || '9:16')}</div>
          <div class="swatches" id="swatches">
            <div class="swatch ${design.theme === 'auto' || !design.theme ? 'sel' : ''}" data-theme="auto" title="auto"><i style="background:linear-gradient(135deg,#0b1d2b,#f2d391)"></i></div>
            ${(S.catalog.themes || []).map(th => `<div class="swatch ${design.theme === th.name ? 'sel' : ''}" data-theme="${esc(th.name)}" title="${esc(th.name)}"><i style="background:linear-gradient(135deg,${esc(th.deep)},${esc(th.accent)})"></i></div>`).join('')}
          </div>
          <div class="two" style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px">
            ${designSelect('layout', S.catalog.layouts, design.layout)}
            ${designSelect('background', S.catalog.backgrounds, design.background)}
            ${designSelect('transition', S.catalog.transitions, design.transition)}
            ${designSelect('brand', S.catalog.brands, design.brand)}
            ${designSelect('frame', S.catalog.frames, design.frame)}
            ${designSelect('format', S.catalog.formats, design.format || '9:16', 'label')}
          </div>
        </div>

        <div class="card">
          <h3>${t('studio.brand')}</h3>
          <p class="hint">${esc(S.settings.brand_name || '')} · ${esc(S.settings.brand_site || '')} · ${esc(S.settings.brand_cta_chip || '')}</p>
          <button class="btn ghost small" data-act="brandsettings">${t('nav.settings')} →</button>
        </div>
      </div>
    </div>`;

  bindStudio();
  if (S.preview) startPreviewClock();
}

/* ---- first screen: paste something, get cards, no key required ---- */
function renderStart(view) {
  view.innerHTML = `
    <div class="startwrap">
      <h1>Make a video from an article</h1>
      <p class="lead">Paste a link, or the text itself. <b>No AI key needed</b> — Reelforge can build the
        cards from the article on its own, and you edit anything you don't like.</p>
      <div class="startcard">
        <textarea id="startInput" rows="6" placeholder="https://example.com/article&#10;&#10;…or paste the article text here"></textarea>
        <div class="row" style="margin-top:12px">
          <button class="btn primary" data-act="start">Make the cards →</button>
          <button class="btn" data-act="demo">▶ See a demo video</button>
          <span class="spacer"></span>
          <span class="tiny muted">Everything stays on this computer.</span>
        </div>
      </div>
      <div class="startsteps">
        <div><b>1</b><span>Paste a link or text</span></div>
        <div><b>2</b><span>Fix anything you want</span></div>
        <div><b>3</b><span>Press Render — get an mp4</span></div>
      </div>
    </div>`;
}

async function startFromInput(btn) {
  const raw = ($('#startInput')?.value || '').trim();
  if (!raw) { $('#startInput')?.focus(); toast('Paste a link or some text first'); return; }
  const isUrl = /^https?:\/\//i.test(raw);
  const label = btn.textContent;
  btn.disabled = true;
  btn.textContent = isUrl ? 'Reading the article…' : 'Making the cards…';
  try {
    const res = await api('/api/project', isUrl ? { url: raw } : { text: raw });
    if (!res.ok) throw new Error(res.error);
    S.project = res.project;
    const s = await api(`/api/project/${S.project.id}/script`, { mode: 'auto' });
    if (s.ok) {
      S.project.script = s.script;
      S.project.meta = (s.project || {}).meta || S.project.meta;
      S.project.status = 'script_ready';
      S.preview = null;
      render();
      refreshPreview();
      toast('Cards ready — change anything you like, then press Render', 'ok');
    } else {
      render();
      toast(s.error || 'Could not build the cards', 'err');
    }
  } catch (e) {
    toast(e.message, 'err');
  } finally {
    btn.disabled = false;
    btn.textContent = label;
  }
}

async function loadDemo(btn) {
  const label = btn.textContent;
  btn.disabled = true; btn.textContent = 'Building the demo…';
  try {
    const res = await api('/api/demo');
    S.project = res.project;
    S.preview = null;
    render();
    refreshPreview();
    toast('Demo ready — rendering a draft so you can watch it', 'ok');
    startRender('draft');
  } catch (e) { toast(e.message, 'err'); }
  finally { btn.disabled = false; btn.textContent = label; }
}

function designSelect(key, items, value, valueKey = 'name') {
  const v = value || 'auto';
  return `<label class="field" style="margin:0"><span>${t('design.' + key) || key}</span>
    <select data-design="${key}">
      ${(items || []).map(it => {
        const val = it.name;
        const label = it.label || it.name;
        return `<option value="${esc(val)}" ${String(v) === String(val) ? 'selected' : ''}>${esc(label)}</option>`;
      }).join('')}
    </select></label>`;
}

function renderMeta(meta) {
  if (!meta || (!meta.title && !meta.hashtags)) return `<p class="tiny muted">—</p>`;
  const tags = (meta.hashtags || []).join(' ');
  return `
    <div class="kv" style="margin-top:8px">
      <div>${t('studio.title')}</div><div>${esc(meta.title || '')}</div>
      <div>${t('studio.hook')}</div><div>${esc(meta.hook_line || '')}</div>
      <div>${t('studio.description')}</div><div>${esc(meta.description || '')}</div>
      <div>${t('studio.hashtags')}</div><div class="mono tiny">${esc(tags)}</div>
    </div>
    <div class="row" style="margin-top:10px">
      <button class="btn ghost small" data-copy="${esc([meta.title, meta.description, tags].filter(Boolean).join('\n\n'))}">${t('common.copy')}</button>
    </div>`;
}

function sceneCard(sc, i) {
  const kind = sc.kind || 'fact';
  const big = sc.big || '';
  return `
  <div class="scene ${S.sceneFocus === i ? 'focus' : ''}" data-scene="${i}">
    <header>
      <span class="n">${i + 1}</span>
      <select data-f="kind" class="kindsel" style="width:auto;padding:2px 22px 2px 8px;height:22px;font-size:11px">
        ${['fact', 'stat', 'list', 'cta'].map(k => `<option value="${k}" ${kind === k ? 'selected' : ''}>${t('k.' + k)}</option>`).join('')}
      </select>
      <span class="time">${S.preview && S.preview.scenes && S.preview.scenes[i] ? S.preview.scenes[i].duration + 's' : ''}</span>
      <button class="ghost small" data-act="delscene" title="delete">✕</button>
    </header>
    <div class="body">
      ${kind === 'stat' ? `
      <div class="three">
        <label class="field" style="margin:0"><span>${t('f.label')}</span>
          <input type="text" data-f="kicker" value="${esc(sc.kicker || '')}"></label>
        <label class="field" style="margin:0"><span>${t('f.num')}</span>
          <input type="text" data-f="num" value="${esc(sc.num ?? '')}" placeholder="900"></label>
        <label class="field" style="margin:0"><span>${t('f.unit')}</span>
          <input type="text" data-f="unit" value="${esc(sc.unit || '')}" placeholder="euros a month"></label>
      </div>` : `
      <div class="two">
        <label class="field" style="margin:0"><span>${t('f.label')}</span>
          <input type="text" data-f="kicker" value="${esc(sc.kicker || '')}" placeholder="The trap"></label>
        <label class="field" style="margin:0"><span>${t('f.chip')}</span>
          <input type="text" data-f="chip" value="${esc(sc.chip || '')}" placeholder="one term extra"></label>
      </div>`}
      <label class="field" style="margin:0"><span>${t('f.big')}<i class="fldhint">2 short lines</i></span>
        <textarea data-f="big" class="bigtext" rows="2" placeholder="A cheap course&#10;costs an extra term">${esc(big)}</textarea></label>
      ${kind === 'list'
        ? `<label class="field" style="margin:0"><span>${t('f.bullets')}</span>
             <textarea data-f="bullets" rows="4" placeholder="One item per line">${esc((sc.bullets || []).join('\n'))}</textarea></label>`
        : `<label class="field" style="margin:0"><span>${t('f.body')}</span>
             <textarea data-f="body" rows="2" placeholder="One sentence that explains the big text.">${esc(sc.body || '')}</textarea></label>`}
      <div class="aimini">
        <input type="text" placeholder="${S.boot.ai_configured ? 'Tell the AI what to change on this card' : 'Add an AI key to rewrite this card automatically'}" data-ai="${i}" ${S.boot.ai_configured ? '' : 'disabled'}>
        <button class="btn small" data-act="aiscene" ${S.boot.ai_configured ? '' : 'disabled'}>✦ ${t('common.apply')}</button>
      </div>
    </div>
  </div>`;
}

function bindStudio() {
  const v = $('#view');

  v.querySelectorAll('[data-design]').forEach(sel => {
    sel.addEventListener('change', async () => {
      const key = sel.dataset.design;
      const design = { ...(S.project.design || {}), [key]: sel.value };
      S.project.design = design;
      await api('/api/project/' + S.project.id, { design }, 'PATCH');
      refreshPreview();
    });
  });

  v.querySelectorAll('.swatch[data-theme]').forEach(sw => {
    sw.addEventListener('click', async () => {
      const design = { ...(S.project.design || {}), theme: sw.dataset.theme };
      S.project.design = design;
      v.querySelectorAll('.swatch').forEach(x => x.classList.toggle('sel', x === sw));
      await api('/api/project/' + S.project.id, { design }, 'PATCH');
      refreshPreview();
    });
  });

  // scene edits (debounced save)
  v.querySelectorAll('.scene').forEach(card => {
    const idx = +card.dataset.scene;
    card.querySelectorAll('[data-f]').forEach(input => {
      input.addEventListener('input', () => {
        const f = input.dataset.f;
        const sc = S.project.script.scenes[idx];
        if (f === 'bullets') sc.bullets = input.value.split('\n').map(x => x.trim()).filter(Boolean);
        else if (f === 'num') sc.num = input.value;
        else sc[f] = input.value;
        queueSave();
      });
      input.addEventListener('focus', () => {
        S.sceneFocus = idx;
        v.querySelectorAll('.scene').forEach(c => c.classList.toggle('focus', +c.dataset.scene === idx));
        v.querySelectorAll('#scenelist button').forEach((b, k) => b.classList.toggle('sel', k === idx));
        const pr = S.preview && S.preview.scenes && S.preview.scenes[idx];
        const frame = document.querySelector('#pframe');
        if (pr && frame && frame.contentWindow && frame.contentWindow.rf) {
          frame.contentWindow.rf.seek(pr.start + Math.min(1.2, pr.duration / 2));
        }
      });
    });
    card.querySelector('[data-act="delscene"]')?.addEventListener('click', () => {
      S.project.script.scenes.splice(idx, 1);
      S.sceneFocus = null;
      saveScript(true);
    });
    card.querySelector('[data-act="aiscene"]')?.addEventListener('click', async (e) => {
      const input = card.querySelector('[data-ai]');
      const instruction = input.value.trim();
      if (!instruction) { input.focus(); return; }
      e.target.disabled = true;
      e.target.textContent = '…';
      try {
        const res = await api(`/api/project/${S.project.id}/scene`, { index: idx, instruction });
        if (!res.ok) throw new Error(res.error);
        S.project.script = res.script;
        render();
        toast('Card rewritten');
      } catch (err) { toast(err.message, 'err'); }
      finally { e.target.disabled = false; e.target.textContent = '✦'; }
    });
  });

  v.querySelectorAll('[data-jump]').forEach(b => {
    b.addEventListener('click', () => {
      const fr = $('#pframe');
      if (fr && fr.contentWindow && fr.contentWindow.rf) fr.contentWindow.rf.seek(parseFloat(b.dataset.jump) + 0.6);
    });
  });
}

let saveTimer = null;
function queueSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => saveScript(false), 700);
}

async function saveScript(rerender) {
  if (!S.project || !S.project.script) return;
  try {
    await api('/api/project/' + S.project.id, { script: S.project.script }, 'PATCH');
    if (rerender) render();
    if (S.view === 'studio' && (S.project.script.scenes || []).length) refreshPreview(true);
  } catch (e) { toast(e.message, 'err'); }
}

async function refreshPreview(quiet) {
  if (!S.project || !S.project.script) return;
  try {
    const res = await api(`/api/project/${S.project.id}/preview`, {});
    if (!res.ok) { if (!quiet) toast(res.error || 'preview failed', 'err'); return; }
    S.preview = res;
    const phone = $('#phone');
    if (!phone) { render(); return; }
    phone.innerHTML = `<iframe id="pframe" src="${esc(res.page)}" allow="autoplay"></iframe>`;
    const sl = $('#scenelist');
    if (sl) sl.innerHTML = (res.scenes || []).map((sc, i) => `<button data-jump="${sc.start}">${i + 1} · ${sc.kind}</button>`).join('');
    startPreviewClock();
  } catch (e) { if (!quiet) toast(e.message, 'err'); }
}

function startPreviewClock() {
  const tick = () => {
    const fr = $('#pframe');
    if (!fr || !fr.contentWindow || !fr.contentWindow.rf) return;
    try {
      const time = fr.contentWindow.rf.time();
      const total = fr.contentWindow.rf.duration || 1;
      const bar = $('#ptrack'), label = $('#ptime');
      if (bar) bar.style.width = Math.min(100, time / total * 100) + '%';
      if (label) label.textContent = time.toFixed(1) + 's / ' + Math.round(total) + 's';
    } catch (e) { /* iframe not ready */ }
  };
  clearInterval(window.__previewClock);
  window.__previewClock = setInterval(tick, 200);
}

/* ------------------------------------------------------------------ actions */
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-act]');
  if (btn) {
    const act = btn.dataset.act;
    if (act === 'new') return backToStart();
    if (act === 'start') return startFromInput(btn);
    if (act === 'demo') return loadDemo(btn);
    if (act === 'fetch') return fetchIntoProject();
    if (act === 'generate') return generateScript('auto', btn);
    if (act === 'generate-ai') return generateScript('ai', btn);
    if (act === 'canceljob') { await api(`/api/project/${S.project.id}/cancel`, {}); toast('Stopping after this frame…'); return; }
    if (act === 'openout') { await api('/api/open', { path: btn.dataset.path }); return; }
    if (act === 'openlib') { setView('library'); return; }
    if (act === 'blank') return blankScript();
    if (act === 'preview') return refreshPreview();
    if (act === 'play') return playPreview();
    if (act === 'popout') {
      const url = S.preview ? S.preview.page : `/render/${S.project.id}/index.html?preview=1`;
      window.open(url, 'rfpreview', 'width=560,height=1000');
      return;
    }
    if (act === 'render') return startRender('high');
    if (act === 'draft') return startRender('draft');
    if (act === 'addscene') return addScene();
    if (act === 'meta') return makeMeta(btn);
    if (act === 'brandsettings') { S.settingsTab = 'brand'; setView('settings'); return; }
  }
  const copyBtn = e.target.closest('[data-copy]');
  if (copyBtn) {
    try { await navigator.clipboard.writeText(copyBtn.dataset.copy); toast(t('common.copied'), 'ok'); }
    catch (err) { toast('clipboard blocked', 'err'); }
  }
});

function playPreview() {
  const fr = $('#pframe');
  if (!fr) { refreshPreview(); return; }
  try { fr.contentWindow.rf.play(0); fr.contentWindow.postMessage('play', '*'); } catch (e) { fr.src = fr.src; }
}

function newProjectDialog() {
  modal(`
    <h2>${t('studio.new')}</h2>
    <p>${t('studio.paste')}</p>
    <label class="field"><span>${t('studio.url')}</span>
      <input type="url" id="mUrl" placeholder="https://example.com/blog/article"></label>
    <label class="field"><span>${t('studio.paste')}</span>
      <textarea id="mText" rows="7" placeholder="…"></textarea></label>
    <label class="field"><span>${t('studio.title')}</span>
      <input type="text" id="mTitle" placeholder="optional"></label>
    <div class="foot">
      <button class="btn ghost" data-close>${t('common.cancel')}</button>
      <button class="btn primary" id="mCreate">${t('studio.new')}</button>
    </div>`, (root) => {
    root.querySelector('[data-close]').onclick = closeModal;
    root.querySelector('#mCreate').onclick = async () => {
      const url = root.querySelector('#mUrl').value.trim();
      const text = root.querySelector('#mText').value.trim();
      const title = root.querySelector('#mTitle').value.trim();
      if (!url && !text) { toast('Add a URL or some text', 'err'); return; }
      const b = root.querySelector('#mCreate');
      b.disabled = true; b.textContent = t('common.loading');
      try {
        const res = await api('/api/project', { url, text, title });
        if (!res.ok) throw new Error(res.error);
        closeModal();
        S.project = res.project;
        S.preview = null;
        render();
        if (url) generateScript($('[data-act="generate"]'));
      } catch (err) { toast(err.message, 'err'); b.disabled = false; b.textContent = t('studio.new'); }
    };
  });
}

async function fetchIntoProject() {
  const url = $('#srcUrl')?.value.trim();
  if (!url || !S.project) return;
  try {
    const res = await api('/api/project', { url, title: S.project.title });
    if (!res.ok) throw new Error(res.error);
    S.project = res.project;
    S.preview = null;
    render();
    toast('Article loaded');
  } catch (e) { toast(e.message, 'err'); }
}

async function generateScript(mode, btn) {
  if (!S.project) return;
  const brief = ($('#brief')?.value || '').trim();
  const label = btn ? btn.textContent : '';
  if (btn) { btn.disabled = true; btn.textContent = mode === 'ai' ? 'Writing… this can take a minute' : 'Reading the article…'; }
  try {
    const res = await api(`/api/project/${S.project.id}/script`, { mode, extra: brief });
    if (!res.ok) throw new Error(res.error);
    S.project.script = res.script;
    S.project.meta = (res.project || {}).meta || S.project.meta;
    S.project.status = 'script_ready';
    render();
    refreshPreview();
    if ((res.warnings || []).length) toast(res.warnings.join(' · '), '');
    toast(mode === 'ai' ? 'Script written by the model' : 'Cards built from the article', 'ok');
  } catch (e) { toast(e.message, 'err'); }
  finally { if (btn) { btn.disabled = false; btn.textContent = label; } }
}

async function blankScript() {
  if (!S.project) return;
  const res = await api(`/api/project/${S.project.id}/script`, { mode: 'blank' });
  S.project.script = res.script;
  render();
  refreshPreview();
}

function addScene() {
  if (!S.project.script) return;
  S.project.script.scenes.push({ kind: 'fact', kicker: '', big: 'New line\nsecond line', body: '', chip: '' });
  saveScript(true);
}

async function makeMeta(btn) {
  if (btn) { btn.disabled = true; btn.textContent = t('common.loading'); }
  try {
    const res = await api(`/api/project/${S.project.id}/meta`, {});
    if (!res.ok) throw new Error(res.error);
    S.project.meta = res.meta;
    render();
    toast('Metadata written', 'ok');
  } catch (e) { toast(e.message, 'err'); }
  finally { if (btn) { btn.disabled = false; btn.textContent = '✦ ' + t('studio.meta'); } }
}

async function startRender(quality) {
  if (!S.project) return;
  try {
    await api(`/api/project/${S.project.id}/render`, { review: false, quality });
    toast(quality === 'draft' ? 'Draft render started' : 'Render started — a 40s video takes 2-3 minutes', 'ok');
    watchJob(S.project.id);
  } catch (e) { toast(e.message, 'err'); }
}

function paintJob(job) {
  const bar = $('#jobbar');
  if (!bar) return;
  if (!job || job.status !== 'running') { bar.hidden = true; return; }
  bar.hidden = false;
  const pct = Math.round((job.progress || 0) * 100);
  const fill = $('#jprog');
  if (fill) fill.style.width = pct + '%';
  const msg = $('#jmsg');
  if (msg) msg.textContent = `${job.message || 'working'} · ${pct}%`;
}

function watchJob(pid) {
  clearInterval(S.jobTimer);
  S.jobTimer = setInterval(async () => {
    try {
      const res = await api(`/api/project/${pid}/job`);
      const job = res.job;
      paintJob(job);
      const badge = $('#crumbs .badge');
      if (badge) badge.outerHTML = statusBadge(res.project.status);
      if (job && job.status === 'running') {
        const pct = Math.round((job.progress || 0) * 100);
        const b = $('[data-act="render"]');
        if (b) b.textContent = `▸ ${pct}%`;
      }
      if (!job || job.status !== 'running') {
        paintJob(job);
        clearInterval(S.jobTimer);
        const b = $('[data-act="render"]');
        if (b) b.textContent = '▸ ' + t('studio.render');
        const fresh = await api('/api/project/' + pid);
        S.project = fresh;
        render();
        if (fresh.status === 'done') toast('Video rendered', 'ok');
        else if (fresh.status === 'failed') toast(fresh.error || 'render failed', 'err');
      }
    } catch (e) { /* keep polling */ }
  }, 1200);
}

/* ================================================================== QUEUE */
function renderQueue(view, crumbs, actions) {
  crumbs.innerHTML = `<h1>${t('nav.queue')}</h1>`;
  const q = S.queueState || { projects: [], queue: {} };
  actions.innerHTML = `
    <button class="btn small" data-q="start">${t('queue.start')}</button>
    <button class="btn ghost small" data-q="stop">${t('queue.stop')}</button>`;
  view.innerHTML = `
    <div class="split" style="grid-template-columns: 380px minmax(0,1fr)">
      <div>
        <div class="card">
          <h3>${t('queue.import')}</h3>
          <p class="hint">${t('queue.urls')} — ${t('studio.paste')}</p>
          <textarea id="qUrls" rows="8" placeholder="https://site.com/blog/post-1&#10;https://site.com/blog/post-2"></textarea>
          <label class="field" style="margin-top:10px"><span>${t('queue.sitemap')}</span>
            <input type="text" id="qSitemap" placeholder="${esc(t('queue.sitemap.ph'))}"></label>
          <div class="two" style="display:grid;grid-template-columns:1fr 90px;gap:10px">
            <label class="field" style="margin:0"><span>${t('queue.prefix')}</span>
              <input type="text" id="qPrefix" placeholder="/blog/"></label>
            <label class="field" style="margin:0"><span>${t('queue.limit')}</span>
              <input type="number" id="qLimit" value="20" min="1" max="500"></label>
          </div>
          <div class="row" style="margin-top:12px">
            <button class="btn primary small" data-q="add">+ ${t('queue.add')}</button>
            <span class="spacer"></span>
            <label class="switch"><input type="checkbox" id="qAuto" ${S.settings.auto_render ? 'checked' : ''}><i></i>
              <span class="tiny">Render new items automatically</span></label>
          </div>
          <p class="tiny muted" style="margin:10px 0 0">${t('queue.auto.hint')}</p>
          <hr class="sep">
          <label class="switch"><input type="checkbox" id="qReview" ${S.settings.review_gate ? 'checked' : ''}><i></i>
            <span class="tiny">Pause for review before rendering</span></label>
          <p class="tiny muted" style="margin:6px 0 0">${t('queue.review.hint')}</p>
        </div>
        <div class="card">
          <h3>${t('queue.items')}</h3>
          <p class="hint">${(q.queue || {}).alive ? 'worker running' : 'worker idle'}${(q.queue || {}).current ? ' · ' + (q.queue || {}).current : ''}</p>
          <pre class="snippet" style="max-height:190px;overflow:auto">${esc(((q.queue || {}).log || []).slice(-12).join('\n'))}</pre>
        </div>
      </div>
      <div class="card">
        <h3 style="margin:0 0 10px">${t('queue.items')}</h3>
        <table class="grid">
          <thead><tr><th>Video</th><th>Status</th><th></th></tr></thead>
          <tbody>
          ${(q.projects || []).length ? (q.projects || []).map(p => `
            <tr>
              <td><div class="celltitle"><b>${esc(p.title)}</b>
                <span class="tiny muted">${esc((p.source_url || '').replace(/^https?:\/\//, '').slice(0, 60))}</span></div></td>
              <td>${statusBadge(p.status)}
                ${p.job && p.job.status === 'running' ? `<div class="progress" style="margin-top:6px"><i style="width:${Math.round((p.job.progress || 0) * 100)}%"></i></div>
                  <span class="tiny muted">${esc(p.job.message || '')}</span>` : ''}
                ${p.error ? `<div class="tiny" style="color:var(--danger);max-width:38ch">${esc(p.error)}</div>` : ''}</td>
              <td style="text-align:end;white-space:nowrap">
                <button class="btn ghost small" data-open="${p.id}">${t('common.open')}</button>
                ${['failed', 'review', 'draft', 'needs_script'].includes(p.status)
                  ? `<button class="btn ghost small" data-retry="${p.id}">${t('common.retry')}</button>` : ''}
              </td>
            </tr>`).join('') : `<tr><td colspan="3"><p class="muted tiny" style="padding:20px 0;text-align:center">${t('library.empty')}</p></td></tr>`}
          </tbody>
        </table>
        ${(q.projects || []).length ? '' : `<p class="muted tiny" style="padding:26px 0;text-align:center">Nothing here yet — paste article URLs or a sitemap on the left and they appear in this list.</p>`}
      </div>
    </div>`;

  view.querySelectorAll('[data-open]').forEach(b => b.onclick = () => openProject(b.dataset.open));
  view.querySelectorAll('[data-retry]').forEach(b => b.onclick = async () => {
    await api('/api/queue/retry', { ids: [b.dataset.retry] });
    pollQueue();
    toast('Queued again');
  });
  view.querySelectorAll('[data-q]').forEach(b => b.onclick = async () => {
    const act = b.dataset.q;
    if (act === 'add') {
      b.disabled = true; b.textContent = t('common.loading');
      const urls = $('#qUrls').value.trim();
      const sitemap = $('#qSitemap').value.trim();
      const body = sitemap
        ? { mode: 'sitemap', sitemap, prefix: $('#qPrefix').value.trim(), limit: +$('#qLimit').value || 20 }
        : { mode: 'urls', urls };
      try {
        const res = await api('/api/queue/import', body);
        if (!res.ok) throw new Error(res.error);
        toast(`${res.count} added${res.skipped ? `, ${res.skipped} already in the library` : ''}`, 'ok');
        if ((res.errors || []).length) toast(res.errors.slice(0, 3).join(' · '), 'err');
        $('#qUrls').value = '';
        pollQueue();
      } catch (e) { toast(e.message, 'err'); }
      finally { b.disabled = false; b.textContent = '+ ' + t('queue.add'); }
    }
    if (act === 'start') { await api('/api/queue/start', {}); pollQueue(); }
    if (act === 'stop') { await api('/api/queue/stop', { hard: true }); pollQueue(); }
  });
  $('#qAuto')?.addEventListener('change', e => api('/api/settings', { auto_render: e.target.checked }));
  $('#qReview')?.addEventListener('change', e => api('/api/settings', { review_gate: e.target.checked }));

  if (!S.queueState) pollQueue();
}

async function pollQueue() {
  try {
    const res = await api('/api/queue');
    S.queueState = res;
    if (S.view !== 'queue') { S.queueSig = null; return; }
    const sig = (res.projects || []).map(p => p.id + ':' + p.status + ':' + Math.round(((p.job || {}).progress || 0) * 100)).join('|');
    if (sig === S.queueSig) return;
    S.queueSig = sig;
    const active = document.activeElement;
    if (active && active.closest && active.closest('#view') && ['INPUT', 'TEXTAREA'].includes(active.tagName)) return;
    const scroll = $('#view').scrollTop;
    render();
    $('#view').scrollTop = scroll;
  } catch (e) { /* ignore */ }
}

/* ================================================================== LIBRARY */
function renderLibrary(view, crumbs, actions) {
  crumbs.innerHTML = `<h1>${t('library.title')}</h1>`;
  const done = S.projects.filter(p => p.has_video);
  view.innerHTML = done.length ? `<div class="libgrid">${done.map(p => `
    <div class="libcard">
      <div class="thumb" style="${p.has_video ? `background-image:url('/out/${p.id}/cover.jpg')` : ''}">
        <video src="/out/${p.id}/video.mp4#t=0.1" preload="metadata" onmouseover="this.play()" onmouseout="this.pause()" muted loop></video>
      </div>
      <div class="meta">
        <b>${esc(p.title)}</b>
        <span class="tiny muted">${fmtDur(p.duration)} · ${p.size_mb || 0} MB</span>
        <div class="acts">
          <a class="btn small" href="/out/${p.id}/video.mp4" download>${t('library.download')}</a>
          <button class="btn ghost small" data-openlib="${p.id}">${t('common.open')}</button>
          <button class="btn ghost small" data-caption="${p.id}" title="Copy caption">${t('library.copy_meta')}</button>
          <button class="btn ghost small" data-dellib="${p.id}" title="${t('common.delete')}">✕</button>
        </div>
      </div>
    </div>`).join('')}</div>` : `<div class="empty-state"><h2>${t('library.empty')}</h2></div>`;

  view.querySelectorAll('[data-openlib]').forEach(b => b.onclick = () => openProject(b.dataset.openlib));
  view.querySelectorAll('[data-dellib]').forEach(b => b.onclick = async () => {
    if (!confirm('Delete this video and its files? This cannot be undone.')) return;
    await api('/api/project/' + b.dataset.dellib, null, 'DELETE');
    S.projects = S.projects.filter(x => x.id !== b.dataset.dellib);
    toast('Deleted');
    render();
  });
  view.querySelectorAll('[data-caption]').forEach(b => b.onclick = async () => {
    const full = await api('/api/project/' + b.dataset.caption);
    const m = full.meta || {};
    const text = [m.title, m.description, (m.hashtags || []).join(' ')].filter(Boolean).join('\n\n');
    try { await navigator.clipboard.writeText(text || full.title); toast(t('common.copied'), 'ok'); }
    catch (e) { toast('clipboard blocked', 'err'); }
  });
}

/* ================================================================== DESIGN */
function renderDesign(view, crumbs, actions) {
  crumbs.innerHTML = `<h1>${t('design.title')}</h1>`;
  const d = (S.project && S.project.design) || {};
  actions.innerHTML = S.project ? `<button class="btn primary small" data-apply>${t('common.save')}</button>` : '';
  view.innerHTML = `
    <p class="help" style="max-width:70ch;margin-bottom:18px">${t('design.hint')}</p>
    <div class="card">
      <h3>${t('design.theme')}</h3>
      <p class="hint">${(S.catalog.custom_themes || []).length ? (S.catalog.custom_themes || []).join(' · ') : ''}</p>
      <div class="swatches" style="gap:10px">
        ${(S.catalog.themes || []).map(th => `
          <div class="swatch ${d.theme === th.name ? 'sel' : ''}" data-dtheme="${esc(th.name)}" title="${esc(th.name)}"
               style="width:64px;height:44px;border-radius:10px">
            <i style="background:linear-gradient(135deg,${esc(th.deep)} 0%,${esc(th.deep)} 55%,${esc(th.accent)} 100%)"></i>
          </div>`).join('')}
      </div>
    </div>
    <div class="split" style="grid-template-columns:1fr 1fr">
      <div class="card">
        <h3>${t('design.layout')} · ${t('design.background')}</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">
          ${designSelect('layout', S.catalog.layouts, d.layout)}
          ${designSelect('background', S.catalog.backgrounds, d.background)}
        </div>
      </div>
      <div class="card">
        <h3>${t('design.transition')} · ${t('design.frame')}</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">
          ${designSelect('transition', S.catalog.transitions, d.transition)}
          ${designSelect('frame', S.catalog.frames, d.frame)}
          ${designSelect('brand', S.catalog.brands, d.brand)}
          ${designSelect('format', S.catalog.formats, d.format || '9:16', 'label')}
        </div>
      </div>
    </div>
    <div class="card">
      <h3>${t('extend.themes')}</h3>
      <p class="hint">${t('extend.themes.hint')}</p>
      <button class="btn ghost small" data-openfolder="themes">${t('settings.openfolder')}</button>
    </div>`;

  view.querySelectorAll('[data-dtheme]').forEach(sw => sw.onclick = () => {
    view.querySelectorAll('[data-dtheme]').forEach(x => x.classList.toggle('sel', x === sw));
    S._designDraft = { ...(S._designDraft || {}), theme: sw.dataset.dtheme };
  });
  view.querySelectorAll('[data-design]').forEach(sel => sel.onchange = () => {
    S._designDraft = { ...(S._designDraft || {}), [sel.dataset.design]: sel.value };
  });
  view.querySelectorAll('[data-openfolder]').forEach(b => b.onclick = () => api('/api/open', { which: b.dataset.openfolder }));
  $('[data-apply]')?.addEventListener('click', async () => {
    const design = S._designDraft || {};
    if (!Object.keys(design).length) { toast('Nothing changed'); return; }
    await api('/api/project/' + S.project.id, { design: { ...(S.project.design || {}), ...design } }, 'PATCH');
    await api('/api/settings', design);
    S.project.design = { ...(S.project.design || {}), ...design };
    S._designDraft = null;
    toast(t('settings.saved'), 'ok');
    render();
  });
}

/* ================================================================== EXTEND */
function renderExtend(view, crumbs, actions) {
  crumbs.innerHTML = `<h1>${t('extend.title')}</h1>`;
  const hooksState = S.boot.hooks || [];
  view.innerHTML = `
    <div class="split" style="grid-template-columns:1fr 1fr">
      <div class="card">
        <h3>${t('extend.hooks')}</h3>
        <p class="hint">${t('extend.hooks.hint')}</p>
        ${hooksState.map(h => `
          <div class="row" style="border:1px solid var(--line);border-radius:10px;padding:9px 11px;margin-bottom:8px">
            <span class="badge ${h.active ? 'done' : ''}">${h.stage}</span>
            <span class="tiny muted mono">${h.active ? esc(h.file.split(/[\\/]/).pop()) : '—'}</span>
            <span class="spacer"></span>
            <button class="btn ghost small" data-hook="${h.stage}">${h.active ? '↻' : '+ py'}</button>
            <button class="btn ghost small" data-hookjs="${h.stage}">+ js</button>
          </div>`).join('')}
        <button class="btn ghost small" data-openfolder="hooks" style="margin-top:6px">${t('settings.openfolder')}</button>
      </div>
      <div class="card">
        <h3>${t('extend.prompts')}</h3>
        <p class="hint">${t('extend.prompts.hint')}</p>
        <label class="field"><span>script</span>
          <textarea id="promptScript" rows="12" class="mono" style="font-size:11.5px">${esc(S.settings.prompt_script || S.boot.prompts.script)}</textarea></label>
        <label class="field"><span>metadata</span>
          <textarea id="promptMeta" rows="6" class="mono" style="font-size:11.5px">${esc(S.settings.prompt_meta || S.boot.prompts.meta)}</textarea></label>
        <div class="row">
          <button class="btn primary small" data-saveprompt>${t('common.save')}</button>
          <button class="btn ghost small" data-resetprompt>reset</button>
        </div>
      </div>
    </div>
    <div class="card">
      <h3>API contract</h3>
      <p class="hint">Hooks receive JSON on stdin and print JSON on stdout. Python hooks get a <code>payload</code> global and may define <code>run(payload)</code>.</p>
      <pre class="snippet">before_script  {"project","article","config"}      -> {"script": {...}}            # skip the AI
before_render  {"project","script","design","brand"} -> {"script","design","brand"}    # override anything
after_render   {"project","video","cover","meta"}    -> {"url": "https://…"}          # publish / log</pre>
      <p class="help" style="margin-top:10px">A full working example lives in <code>hooks/examples/</code> next to the app data folder.</p>
    </div>`;

  view.querySelectorAll('[data-hook]').forEach(b => b.onclick = () => createHook(b.dataset.hook, 'py'));
  view.querySelectorAll('[data-hookjs]').forEach(b => b.onclick = () => createHook(b.dataset.hookjs, 'js'));
  view.querySelectorAll('[data-openfolder]').forEach(b => b.onclick = () => api('/api/open', { which: b.dataset.openfolder }));
  $('[data-saveprompt]').onclick = async () => {
    const prompt_script = $('#promptScript').value;
    const prompt_meta = $('#promptMeta').value;
    // prompts are free-form settings, not in DEFAULTS, so they go through the raw store
    await api('/api/settings', { prompt_script, prompt_meta });
    S.settings.prompt_script = prompt_script;
    S.settings.prompt_meta = prompt_meta;
    toast(t('settings.saved'), 'ok');
  };
  $('[data-resetprompt]').onclick = async () => {
    $('#promptScript').value = S.boot.prompts.script;
    $('#promptMeta').value = S.boot.prompts.meta;
    await api('/api/settings', { prompt_script: '', prompt_meta: '' });
    toast('reset');
  };
}

async function createHook(stage, kind) {
  const res = await api('/api/hooks/example', { stage, kind, overwrite: true });
  if (res.ok) { S.boot.hooks = res.hooks; toast(`${stage}.${kind} created`, 'ok'); render(); }
  else toast(res.error || 'failed', 'err');
}

/* ================================================================== SETTINGS */
function renderSettings(view, crumbs, actions) {
  crumbs.innerHTML = `<h1>${t('settings.title')}</h1>`;
  const s = S.settings;
  const tabs = ['ai', 'brand', 'render', 'automation', 'paths', 'ui'];
  actions.innerHTML = `<button class="btn primary small" data-savesettings>${t('common.save')}</button>`;
  view.innerHTML = `
    <div class="tabs">${tabs.map(tb => `<button data-tab="${tb}" class="${S.settingsTab === tb ? 'active' : ''}">${t('settings.' + tb)}</button>`).join('')}</div>
    <div id="settingsBody"></div>`;

  view.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => { S.settingsTab = b.dataset.tab; render(); });

  const body = $('#settingsBody');
  const field = (key, label, type = 'text', extra = '') => `
    <label class="field"><span>${label}</span>
      <input type="${type}" data-set="${key}" value="${esc(s[key] ?? '')}" ${extra}></label>`;

  if (S.settingsTab === 'ai') {
    const presets = S.boot.presets || [];
    body.innerHTML = `
      <div class="card">
        <h3>Paste a key — that's the whole setup</h3>
        <p class="hint">Reelforge reads the key and picks the provider for you. Works with OpenAI, OpenRouter,
          Groq, DeepSeek, xAI, Mistral, Together, Fireworks, Perplexity, Claude, Gemini, or any endpoint that
          speaks the OpenAI chat format.</p>
        <div class="srcbox">
          <input id="aiKeyPaste" type="password" placeholder="sk-…  ·  sk-ant-…  ·  gsk_…  ·  AIza…">
          <button class="btn primary small" id="aiDetectBtn">Use this key</button>
        </div>
        <p class="tiny" id="aiDetectOut" style="min-height:18px;margin:8px 0 0"></p>
        <hr class="sep">
        <div class="row">
          <button class="btn ghost small" id="aiLocalBtn">Find a model on this computer</button>
          <span class="tiny muted">Ollama, LM Studio, llama.cpp — free, no key needed.</span>
        </div>
        <div id="aiLocalOut" style="margin-top:10px"></div>
      </div>

      <div class="card">
        <h3>Or set it by hand</h3>
        <div class="split" style="grid-template-columns:1fr 1fr">
          <label class="field"><span>Provider</span>
            <select data-set="ai_provider" id="aiProvider">
              ${presets.map(p => `<option value="${p.id}" ${s.ai_provider === p.id ? 'selected' : ''}>${esc(p.label)}</option>`).join('')}
              <option value="none" ${s.ai_provider === 'none' ? 'selected' : ''}>No AI — build cards from the article</option>
            </select></label>
          <label class="field"><span>Model</span>
            <div class="srcbox">
              <input type="text" data-set="ai_model" id="aiModel" list="aiModels" value="${esc(s.ai_model || '')}">
              <button class="btn small" id="aiModelsBtn" title="Ask the endpoint which models it has">List</button>
            </div>
            <datalist id="aiModels"></datalist></label>
        </div>
        <label class="field"><span>Base URL</span>
          <input type="text" data-set="ai_base_url" id="aiBase" value="${esc(s.ai_base_url || '')}"
                 placeholder="https://api.openai.com/v1"></label>
        <label class="field"><span>API key</span>
          <input type="password" data-set="ai_key" id="aiKey" value="${esc(s.ai_key_set ? s.ai_key : '')}" placeholder="sk-…">
          <span class="tiny muted">${t('settings.key.hint')}</span></label>
        <div class="split" style="grid-template-columns:1fr 1fr">
          <label class="field"><span>Script language</span>
            <select data-set="ai_language">
              ${['auto', 'fa', 'en', 'de', 'tr', 'ar', 'ru'].map(l => `<option value="${l}" ${s.ai_language === l ? 'selected' : ''}>${l}</option>`).join('')}
            </select></label>
          <label class="field"><span>Temperature</span>
            <input type="number" step="0.1" min="0" max="1.5" data-set="ai_temperature" value="${esc(s.ai_temperature)}"></label>
        </div>
        <div class="row">
          <button class="btn small" id="aiTestBtn">Test connection</button>
          <span class="tiny muted" id="aiTestOut"></span>
        </div>
        <details style="margin-top:14px">
          <summary class="tiny muted" style="cursor:pointer">Advanced — extra headers or body fields (Azure, gateways)</summary>
          <label class="field" style="margin-top:10px"><span>Extra request headers (JSON)</span>
            <input type="text" data-set="ai_headers" value="${esc(s.ai_headers || '')}"
                   placeholder='{"api-key": "..."}'></label>
          <label class="field"><span>Extra body fields (JSON)</span>
            <input type="text" data-set="ai_extra" value="${esc(s.ai_extra || '')}"
                   placeholder='{"response_format": {"type": "json_object"}}'></label>
          <p class="tiny muted">Azure OpenAI: set the base URL to
            <code class="mono">https://RESOURCE.openai.azure.com/openai/deployments/DEPLOYMENT</code>,
            the model to the deployment name, and add <code class="mono">{"api-key": "…"}</code> above.</p>
        </details>
      </div>`;

    const setProvider = (preset) => {
      if (!preset) return;
      const sel = $('#aiProvider'), model = $('#aiModel'), base = $('#aiBase');
      if (sel && preset.id) sel.value = preset.id;
      if (model && preset.model) model.value = preset.model;
      if (base && preset.base) base.value = preset.base;
    };

    $('[data-set=ai_provider]').addEventListener('change', (e) => {
      const preset = presets.find(p => p.id === e.target.value);
      if (preset && preset.base) { $('#aiBase').value = preset.base; $('#aiModel').value = preset.model; }
      if (e.target.value === 'none') { $('#aiBase').value = ''; $('#aiModel').value = ''; }
    });

    $('#aiDetectBtn').onclick = async () => {
      const key = $('#aiKeyPaste').value.trim();
      const out = $('#aiDetectOut');
      if (!key) { $('#aiKeyPaste').focus(); out.textContent = 'Paste the key first.'; return; }
      out.textContent = 'Checking…'; out.style.color = 'var(--muted)';
      const res = await api('/api/ai/detect', { key, apply: true });
      if (res.provider) {
        const preset = presets.find(p => p.id === res.provider) || { id: res.provider, base: res.base_url, model: res.model };
        setProvider({ id: res.provider, base: res.base_url || preset.base, model: res.model || preset.model });
        $('#aiKey').value = key;
        out.textContent = `Looks like ${res.label || res.provider}.` + (res.note ? ' ' + res.note : '');
        out.style.color = 'var(--ok)';
        await saveSettings(true);
        const test = await api('/api/ai/test', {});
        out.textContent += test.ok ? ' Connected.' : ' Test failed: ' + (test.error || '');
        out.style.color = test.ok ? 'var(--ok)' : 'var(--danger)';
        if (test.ok) { S.boot.ai_configured = true; toast('AI connected', 'ok'); }
      } else {
        out.textContent = res.note || 'Could not identify that key — set the provider by hand below.';
        out.style.color = 'var(--warn)';
      }
    };

    $('#aiModelsBtn').onclick = async () => {
      const btn = $('#aiModelsBtn');
      btn.disabled = true; btn.textContent = '…';
      const res = await api('/api/ai/models', { base_url: $('#aiBase').value, provider: $('#aiProvider').value });
      btn.disabled = false; btn.textContent = 'List';
      const list = $('#aiModels');
      list.innerHTML = (res.models || []).map(m => `<option value="${esc(m)}"></option>`).join('');
      if ((res.models || []).length) {
        toast(`${res.models.length} models found — start typing to pick one`, 'ok');
        if (!$('#aiModel').value) $('#aiModel').value = res.models[0];
      } else toast(res.error || 'No model list from that endpoint', 'err');
    };

    $('#aiLocalBtn').onclick = async () => {
      const out = $('#aiLocalOut');
      out.innerHTML = '<span class="tiny muted">Looking…</span>';
      const res = await api('/api/ai/local');
      if (!res.ok) { out.innerHTML = `<span class="tiny muted">${esc(res.hint || '')}</span>`; return; }
      out.innerHTML = res.servers.map((sv, i) => `
        <div class="row" style="border:1px solid var(--line);border-radius:10px;padding:8px 10px;margin-bottom:6px">
          <b class="tiny">${esc(sv.label)}</b>
          <span class="tiny muted mono">${esc(sv.base_url)}</span>
          <span class="spacer"></span>
          <select class="tiny" data-local-models="${i}" style="width:auto;max-width:220px;padding:4px 8px">
            ${sv.models.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('')}
          </select>
          <button class="btn small" data-local-use="${i}">Use</button>
        </div>`).join('');
      out.querySelectorAll('[data-local-use]').forEach(b => b.onclick = async () => {
        const sv = res.servers[+b.dataset.localUse];
        const sel = out.querySelector(`[data-local-models="${b.dataset.localUse}"]`);
        setProvider({ id: sv.provider, base: sv.base_url, model: sel.value });
        await saveSettings(true);
        S.boot.ai_configured = true;
        toast(`${sv.label} connected`, 'ok');
        render();
      });
    };

    $('#aiTestBtn').onclick = async () => {
      const out = $('#aiTestOut');
      out.textContent = t('common.loading'); out.style.color = 'var(--muted)';
      await saveSettings(true);
      const res = await api('/api/ai/test', {});
      out.textContent = res.ok ? '✓ connected — ' + (res.reply || '') : '✗ ' + (res.error || 'failed');
      out.style.color = res.ok ? 'var(--ok)' : 'var(--danger)';
      if (res.ok) S.boot.ai_configured = true;
    };
  } else if (S.settingsTab === 'brand') {
    body.innerHTML = `
      <div class="card">
        <h3>${t('settings.brand')}</h3>
        <p class="hint">Rendered on every card. The CTA card uses these words exactly.</p>
        <div class="split" style="grid-template-columns:1fr 1fr">
          ${field('brand_name', 'Name')}
          ${field('brand_latin', 'Latin name / handle')}
          ${field('brand_site', 'Site shown on each card')}
          ${field('brand_logo', 'Logo (path or /assets/logo.png)')}
        </div>
        ${field('brand_cta_title', 'CTA headline')}
        ${field('brand_cta_body', 'CTA body')}
        <div class="split" style="grid-template-columns:1fr 1fr">
          ${field('brand_cta_chip', 'CTA chip')}
          ${field('brand_footer_cta', 'Footer line on the CTA card')}
        </div>
      </div>`;
  } else if (S.settingsTab === 'render') {
    body.innerHTML = `
      <div class="card">
        <h3>${t('settings.render')}</h3>
        <div class="split" style="grid-template-columns:1fr 1fr">
          <label class="field"><span>${t('settings.quality')}</span>
            <select data-set="render_quality">
              <option value="high" ${s.render_quality === 'high' ? 'selected' : ''}>high</option>
              <option value="draft" ${s.render_quality === 'draft' ? 'selected' : ''}>draft (2-3× faster)</option>
            </select></label>
          <label class="field"><span>${t('settings.fps')}</span>
            <select data-set="fps">${[24, 25, 30, 60].map(f => `<option value="${f}" ${+s.fps === f ? 'selected' : ''}>${f}</option>`).join('')}</select></label>
        </div>
        <label class="field"><span>${t('settings.volume')} (0–1)</span>
          <input type="number" step="0.05" min="0" max="1" data-set="music_volume" value="${esc(s.music_volume)}"></label>
        <label class="switch"><input type="checkbox" data-set="sfx_enabled" ${s.sfx_enabled ? 'checked' : ''}><i></i><span>${t('settings.sfx')}</span></label>
        <br><br>
        <label class="switch"><input type="checkbox" data-set="cover" ${s.cover ? 'checked' : ''}><i></i><span>${t('settings.cover')}</span></label>
      </div>`;
  } else if (S.settingsTab === 'automation') {
    body.innerHTML = `
      <div class="card">
        <h3>${t('settings.automation')}</h3>
        ${[['auto_generate', t('settings.autogen')], ['auto_meta', t('settings.autometa')],
           ['auto_render', 'Render queue items automatically'], ['review_gate', t('queue.review')]]
          .map(([k, label]) => `<label class="switch" style="display:flex;margin-bottom:14px">
            <input type="checkbox" data-set="${k}" ${s[k] ? 'checked' : ''}><i></i><span>${label}</span></label>`).join('')}
        <hr class="sep">
        <label class="field"><span>How cards get written</span>
          <select data-set="script_mode">
            <option value="auto" ${s.script_mode === 'auto' ? 'selected' : ''}>Use the AI if a key is set, otherwise build them from the article</option>
            <option value="ai" ${s.script_mode === 'ai' ? 'selected' : ''}>Always use the AI</option>
            <option value="manual" ${s.script_mode === 'manual' ? 'selected' : ''}>Never write automatically — I write them</option>
          </select></label>
        <label class="field"><span>${t('design.title')} default</span>
          <select data-set="default_design_mode">
            <option value="auto" ${s.default_design_mode === 'auto' ? 'selected' : ''}>auto — vary every video</option>
            <option value="fixed" ${s.default_design_mode === 'fixed' ? 'selected' : ''}>fixed</option>
          </select></label>
      </div>`;
  } else if (S.settingsTab === 'paths') {
    const b = S.boot.binaries || {};
    body.innerHTML = `
      <div class="card">
        <h3>${t('settings.paths')}</h3>
        <div class="kv" style="margin-bottom:14px">
          <div>${t('settings.ffmpeg')}</div><div class="mono tiny">${esc(b.ffmpeg || 'not found')}</div>
          <div>${t('settings.browser')}</div><div class="mono tiny">${esc(b.browser || 'not found')}</div>
          <div>home</div><div class="mono tiny">${esc((s.paths || {}).home || '')}</div>
        </div>
        <div class="row" style="margin-bottom:14px">
          <button class="btn small" data-detect>${t('settings.detect')}</button>
          <button class="btn ghost small" data-openfolder="home">${t('settings.openfolder')}</button>
        </div>
        ${field('assets_dir', t('settings.assets'), 'text', 'placeholder="' + esc((s.paths || {}).assets || '') + '"')}
        ${field('ffmpeg_path', t('settings.ffmpeg') + ' (exe or folder)')}
        ${field('browser_path', t('settings.browser') + ' (exe)')}
      </div>
      <div class="card">
        <h3>${t('settings.assets')}</h3>
        <p class="hint">broll ${(S.boot.assets || {}).broll || 0} · music ${(S.boot.assets || {}).music || 0} · sfx ${(S.boot.assets || {}).sfx || 0} · photos ${(S.boot.assets || {}).photos || 0}</p>
        <div class="row">
          <button class="btn ghost small" data-openfolder="assets">broll / music / sfx</button>
          <button class="btn ghost small" data-openfolder="out">${t('library.title')}</button>
          <button class="btn ghost small" data-openfolder="logs">logs</button>
        </div>
        <p class="help" style="margin-top:12px">Drop <code>.mp4</code> clips in <code>assets/broll</code> (name them by topic: china-01.mp4, money-02.mp4…),
        music beds in <code>assets/music</code>, and <code>whoosh/tick/thump</code> sounds in <code>assets/sfx</code>. Without them Reelforge still renders —
        it falls back to gradient backgrounds and silence.</p>
      </div>`;
    $('[data-detect]').onclick = async () => { S.boot.binaries = await api('/api/binaries'); render(); };
    body.querySelectorAll('[data-openfolder]').forEach(b2 => b2.onclick = () => api('/api/open', { which: b2.dataset.openfolder }));
  } else {
    body.innerHTML = `
      <div class="card">
        <h3>${t('settings.ui')}</h3>
        <label class="field"><span>Language</span>
          <select data-set="ui_lang">
            <option value="en" ${s.ui_lang === 'en' ? 'selected' : ''}>English</option>
            <option value="fa" ${s.ui_lang === 'fa' ? 'selected' : ''}>فارسی</option>
          </select></label>
        <p class="hint">Reelforge ${esc(S.boot.version)} · ${esc((S.boot.platform || {}).os || '')}</p>
        <button class="btn ghost small" data-onboard>Show the welcome tour</button>
      </div>`;
    $('[data-onboard]').onclick = () => onboarding(true);
  }

  $('[data-savesettings]')?.addEventListener('click', saveSettings);
}

async function saveSettings(quiet) {
  const payload = {};
  $$('[data-set]').forEach(el => {
    if (el.type === 'checkbox') payload[el.dataset.set] = el.checked;
    else payload[el.dataset.set] = el.value;
  });
  if (payload.ai_key && payload.ai_key.includes('…')) delete payload.ai_key;
  try {
    const res = await api('/api/settings', payload);
    S.settings = res.settings;
    const prov = res.settings.ai_provider || 'none';
    S.boot.ai_configured = ['none', ''].includes(prov) ? false
      : (['ollama', 'lmstudio', 'llamacpp'].includes(prov) || !!res.settings.ai_key_set);
    if (payload.ui_lang && payload.ui_lang !== S.lang) { S.lang = payload.ui_lang; applyLang(); }
    if (!quiet) toast(t('settings.saved'), 'ok');
    return res;
  } catch (e) { toast(e.message, 'err'); }
}

/* ------------------------------------------------------------------ onboarding */
function onboarding(force) {
  const finishOnboarding = async (extra = {}) => {
    await api('/api/settings', { onboarded: true, ...extra });
    S.settings.onboarded = true;
    closeModal();
    S.boot = await api('/api/bootstrap');
    S.settings = S.boot.settings;
    render();
  };

  const stepBrand = () => {
    modal(`
      <h2>Welcome to Reelforge</h2>
      <p>Turn an article, a link or a paragraph into a finished vertical short video.
         Everything runs on this computer — nothing is uploaded.</p>
      <label class="field"><span>Brand name <i class="fldhint">printed on the cards</i></span>
        <input id="obName" value="${esc(['', 'Reelforge'].includes(S.settings.brand_name) ? '' : S.settings.brand_name)}" placeholder="Acme Studio"></label>
      <label class="field"><span>Site or handle</span>
        <input id="obSite" value="${esc(['', 'example.com'].includes(S.settings.brand_site) ? '' : S.settings.brand_site)}" placeholder="acme.studio">
        <span class="tiny muted">Optional. You can change both later in Settings → Brand.</span></label>
      <div class="foot">
        <button class="btn ghost" data-skip>Skip</button>
        <button class="btn primary" data-next>Continue</button>
      </div>`, root => {
      root.querySelector('[data-skip]').onclick = () => finishOnboarding();
      root.querySelector('[data-next]').onclick = async () => {
        const brand_name = root.querySelector('#obName').value.trim();
        const brand_site = root.querySelector('#obSite').value.trim();
        const payload = {};
        if (brand_name) { payload.brand_name = brand_name; payload.brand_latin = brand_name.toUpperCase().slice(0, 22); }
        if (brand_site) payload.brand_site = brand_site.replace(/^https?:\/\//, '').replace(/\/$/, '');
        if (Object.keys(payload).length) {
          const res = await api('/api/settings', payload);
          S.settings = res.settings;
        }
        stepScript();
      };
    });
  };

  const stepScript = () => {
    modal(`
      <h2>How should the cards be written?</h2>
      <p>You can change this at any time — nothing here is permanent.</p>
      <div class="choices">
        <button class="choice" data-choice="auto">
          <b>From the article itself</b>
          <span>No key, no cost, instant. Reelforge pulls the sentences and the numbers out of the page and
            builds the cards. You edit anything you don't like.</span>
          <i>Recommended</i>
        </button>
        <button class="choice" data-choice="ai">
          <b>With an AI model</b>
          <span>Paste one key — OpenAI, OpenRouter, Groq, DeepSeek, Claude, Gemini, or a free local model.
            Better headlines, better order.</span>
        </button>
        <button class="choice" data-choice="manual">
          <b>I'll write them myself</b>
          <span>Start with empty cards and type your own words.</span>
        </button>
      </div>
      <div class="foot"><button class="btn ghost" data-back>Back</button></div>`, root => {
      root.querySelector('[data-back]').onclick = stepBrand;
      root.querySelectorAll('[data-choice]').forEach(b => b.onclick = async () => {
        if (b.dataset.choice === 'auto') return finishOnboarding({ ai_provider: 'none', script_mode: 'auto' });
        if (b.dataset.choice === 'manual') return finishOnboarding({ ai_provider: 'none', script_mode: 'manual' });
        stepAi();
      });
    });
  };

  const stepAi = () => {
    modal(`
      <h2>Paste your API key</h2>
      <p>Reelforge works out which service it belongs to and sets everything up. The key is encrypted on this
         machine with Windows DPAPI and only sent to the provider you chose.</p>
      <div class="srcbox">
        <input id="obKey" type="password" placeholder="sk-…  ·  sk-ant-…  ·  gsk_…  ·  AIza…">
        <button class="btn primary" id="obUse">Use this key</button>
      </div>
      <p class="tiny" id="obOut" style="min-height:20px;margin:10px 0 0"></p>
      <hr class="sep">
      <div class="row">
        <button class="btn ghost small" id="obLocal">Find a free model on this computer</button>
        <span class="spacer"></span>
        <button class="btn ghost small" data-skip>Skip — use the article instead</button>
      </div>
      <div id="obLocalOut"></div>
      <div class="foot"><button class="btn ghost" data-back>Back</button></div>`, root => {
      const out = root.querySelector('#obOut');
      root.querySelector('[data-back]').onclick = stepScript;
      root.querySelector('[data-skip]').onclick = () => finishOnboarding({ ai_provider: 'none', script_mode: 'auto' });
      root.querySelector('#obUse').onclick = async () => {
        const key = root.querySelector('#obKey').value.trim();
        if (!key) { root.querySelector('#obKey').focus(); return; }
        out.textContent = 'Checking the key…'; out.style.color = 'var(--muted)';
        const res = await api('/api/ai/detect', { key, apply: true });
        if (!res.provider) {
          out.textContent = res.note || 'Could not identify that key.';
          out.style.color = 'var(--warn)';
          return;
        }
        const test = await api('/api/ai/test', {});
        out.textContent = test.ok
          ? `Connected to ${res.label || res.provider}. You're ready.`
          : `Saved as ${res.label || res.provider}, but the test failed: ${test.error || ''}. You can fix it in Settings → AI.`;
        out.style.color = test.ok ? 'var(--ok)' : 'var(--danger)';
        if (test.ok) setTimeout(() => finishOnboarding({ ai_provider: res.provider, script_mode: 'ai' }), 900);
      };
      root.querySelector('#obLocal').onclick = async () => {
        const box = root.querySelector('#obLocalOut');
        box.innerHTML = '<p class="tiny muted">Looking…</p>';
        const res = await api('/api/ai/local');
        if (!res.ok) { box.innerHTML = `<p class="tiny muted">${esc(res.hint || '')}</p>`; return; }
        box.innerHTML = res.servers.map((sv, i) => `
          <div class="row" style="border:1px solid var(--line);border-radius:10px;padding:8px 10px;margin-top:8px">
            <b class="tiny">${esc(sv.label)}</b>
            <span class="spacer"></span>
            <select data-m="${i}" style="width:auto;max-width:220px;padding:5px 8px;font-size:12px">
              ${sv.models.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('')}
            </select>
            <button class="btn small" data-use="${i}">Use</button>
          </div>`).join('');
        box.querySelectorAll('[data-use]').forEach(btn => btn.onclick = async () => {
          const sv = res.servers[+btn.dataset.use];
          const model = box.querySelector(`[data-m="${btn.dataset.use}"]`).value;
          await api('/api/settings', { ai_provider: sv.provider, ai_base_url: sv.base_url, ai_model: model });
          const test = await api('/api/ai/test', {});
          out.textContent = test.ok ? `${sv.label} connected (${model}).` : `Saved, but the test failed: ${test.error || ''}`;
          out.style.color = test.ok ? 'var(--ok)' : 'var(--danger)';
          if (test.ok) setTimeout(() => finishOnboarding({ ai_provider: sv.provider, script_mode: 'ai' }), 900);
        });
      };
    });
  };

  stepBrand();
}
/* ------------------------------------------------------------------ start */
boot();
