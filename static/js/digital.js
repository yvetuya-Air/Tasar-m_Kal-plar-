(() => {
  const reader = document.getElementById('digital-reader');
  const status = document.getElementById('reader-status');
  const meter = document.getElementById('reading-progress');
  const requestBody = values => new URLSearchParams({csrf_token: reader.dataset.csrf, ...values});
  async function post(url, values) {
    try {
      const response = await fetch(url, {method: 'POST', body: requestBody(values), keepalive: true});
      if (!response.ok) throw new Error();
      status.textContent = '';
      return true;
    } catch {
      status.textContent = 'İlerleme veya ayraç kaydedilemedi.';
      return false;
    }
  }
  function showProgress(position, total) {
    meter.value = total > 0 ? Math.min(100, Math.round(position / total * 100)) : 0;
    meter.textContent = '%' + meter.value;
  }
  const image = document.getElementById('pdf-page');
  const readable = document.getElementById('pdf-text');
  if (readable) {
    const position = Number(reader.dataset.position);
    showProgress(position, Number(readable.dataset.pages));
    post(reader.dataset.progress, {position});
  } else if (image) {
    const field = document.getElementById('page-number');
    const zoom = document.getElementById('zoom');
    const bookmark = document.getElementById('bookmark');
    const bookmarks = document.getElementById('bookmarks');
    const previous = document.getElementById('previous');
    const next = document.getElementById('next');
    const total = Number(field.max);
    let page = Number(field.value);
    let pending = Promise.resolve();
    const savedPages = new Set([...bookmarks.options].map(option => Number(option.value)).filter(Boolean));
    function updateControls() {
      previous.disabled = page === 1;
      next.disabled = page === total;
      bookmark.setAttribute('aria-pressed', String(savedPages.has(page)));
      bookmark.textContent = savedPages.has(page) ? 'Ayracı kaldır' : 'Sayfayı işaretle';
    }
    function go(number) {
      page = Math.max(1, Math.min(total, Number.isInteger(number) ? number : page));
      field.value = page;
      image.alt = 'Kitap sayfası ' + page;
      image.src = image.dataset.first.replace(/\/1$/, '/' + page) + '?zoom=' + zoom.value;
      image.style.width = (Number(zoom.value) / 1.4 * 100) + '%';
      showProgress(page, total);
      updateControls();
    }
    image.addEventListener('load', () => {
      if (!image.complete || !image.naturalWidth) return;
      const position = page;
      pending = pending.then(() => post(reader.dataset.progress, {position}));
    });
    image.addEventListener('error', () => { status.textContent = 'Sayfa görüntülenemedi.'; });
    previous.addEventListener('click', () => go(page - 1));
    next.addEventListener('click', () => go(page + 1));
    field.addEventListener('change', () => go(Number(field.value)));
    zoom.addEventListener('change', () => go(page));
    bookmarks.addEventListener('change', () => { if (bookmarks.value) go(Number(bookmarks.value)); });
    bookmark.addEventListener('click', async () => {
      const number = page;
      const marked = !savedPages.has(number);
      bookmark.disabled = true;
      if (await post(bookmarks.dataset.url, {page: number, marked: marked ? 'yes' : 'no'})) {
        if (marked) savedPages.add(number);
        else savedPages.delete(number);
        bookmarks.length = 1;
        for (const item of [...savedPages].sort((a, b) => a - b)) bookmarks.add(new Option(item, item));
      }
      bookmark.disabled = false;
      updateControls();
    });
    const fullscreen = document.getElementById('fullscreen');
    fullscreen.hidden = !document.fullscreenEnabled;
    fullscreen.addEventListener('click', () => {
      const operation = document.fullscreenElement ? document.exitFullscreen() : reader.requestFullscreen();
      operation.catch(() => { status.textContent = 'Tam ekran açılamadı.'; });
    });
    document.addEventListener('fullscreenchange', () => {
      fullscreen.textContent = document.fullscreenElement ? 'Tam ekrandan çık' : 'Tam ekran';
    });
    go(page);
  } else {
    const audio = document.getElementById('audio-reader');
    let lastSaved = 0;
    audio.addEventListener('loadedmetadata', () => {
      audio.currentTime = Math.min(audio.duration, Number(reader.dataset.position));
      showProgress(audio.currentTime, audio.duration);
    });
    document.getElementById('speed').addEventListener('change', event => {
      audio.playbackRate = Number(event.target.value);
    });
    const volume = document.getElementById('volume');
    volume.addEventListener('input', () => {
      audio.muted = false;
      audio.volume = Number(volume.value);
    });
    audio.addEventListener('volumechange', () => { volume.value = audio.muted ? 0 : audio.volume; });
    const save = () => post(reader.dataset.progress, {position: audio.currentTime});
    audio.addEventListener('pause', save);
    audio.addEventListener('seeked', save);
    audio.addEventListener('timeupdate', () => {
      showProgress(audio.currentTime, audio.duration);
      if (!audio.paused && performance.now() - lastSaved >= 5000) {
        lastSaved = performance.now();
        save();
      }
    });
    window.addEventListener('pagehide', () => {
      if (audio.readyState) navigator.sendBeacon(reader.dataset.progress, requestBody({position: audio.currentTime}));
    });
  }
})();
