(() => {
  const button = document.getElementById('scan-camera');
  const video = document.getElementById('qr-camera');
  const status = document.getElementById('scan-status');
  const form = document.getElementById('scan-form');
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d', {willReadFrequently: true});
  let stream;
  let frame;
  function stop() {
    if (stream) stream.getTracks().forEach(track => track.stop());
    stream = null;
    clearTimeout(frame);
    video.srcObject = null;
    video.hidden = true;
    button.textContent = 'Kamera ile tara';
  }
  function scan() {
    if (!stream) return;
    if (video.readyState >= 2 && video.videoWidth) {
      canvas.width = Math.min(640, video.videoWidth);
      canvas.height = Math.round(canvas.width * video.videoHeight / video.videoWidth);
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
      const code = window.jsQR(pixels.data, pixels.width, pixels.height, {inversionAttempts: 'dontInvert'});
      if (code && /^KYS:[a-f0-9]{48}$/.test(code.data)) {
        document.getElementById('lookup').value = code.data;
        stop();
        form.requestSubmit();
        return;
      }
    }
    frame = setTimeout(scan, 150);
  }
  button.addEventListener('click', async () => {
    if (stream) { stop(); status.textContent = ''; return; }
    button.disabled = true;
    try {
      stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: 'environment'}, audio: false});
      video.srcObject = stream;
      video.hidden = false;
      await video.play();
      button.textContent = 'Taramayı durdur';
      status.textContent = 'Kartın QR kodunu kameraya gösterin.';
      scan();
    } catch {
      stop();
      status.textContent = 'Kamera açılamadı. Üye numarasını yazabilirsiniz.';
    } finally {
      button.disabled = false;
    }
  });
  window.addEventListener('pagehide', stop);
})();
