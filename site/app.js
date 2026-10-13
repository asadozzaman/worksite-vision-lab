/* Read-only public viewer of source-verified, saved model predictions. */
(() => {
  'use strict';
  const canvas = document.getElementById('frame-canvas'), ctx = canvas.getContext('2d');
  const slider = document.getElementById('frame-slider'), status = document.getElementById('viewer-status');
  const modes = [...document.querySelectorAll('[data-mode]')];
  let data, image, current = 2, mode = 'detections', request = 0;
  const setStatus = (text, error = false) => { status.textContent = text; status.classList.toggle('error', error); };
  function activeBoxes() {
    if (mode === 'raw') return [];
    const frame = data.frames[current];
    return mode === 'detections' ? frame.detections : frame.tracks[mode];
  }
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!image) return;
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    activeBoxes().forEach(box => {
      const [x1, y1, x2, y2] = box.xyxy.map((v, i) => Math.max(0, Math.min(i % 2 ? canvas.height : canvas.width, v)));
      const color = mode === 'detections' ? '#c2e58c' : '#7ed4df';
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      const label = mode === 'detections' ? `Person ${box.confidence.toFixed(2)}` : `Track ${box.track_id}`;
      ctx.font = '12px monospace';
      const width = ctx.measureText(label).width + 10;
      const tx = Math.min(x1, Math.max(0, canvas.width - width)), ty = Math.max(19, Math.min(canvas.height - 4, y1 + 19));
      ctx.fillStyle = '#132520'; ctx.fillRect(tx, ty - 15, width, 20);
      ctx.fillStyle = color; ctx.fillText(label, tx + 5, ty);
    });
  }
  function updateRecords() {
    const frame = data.frames[current], boxes = activeBoxes();
    document.getElementById('frame-stamp').textContent = `FRAME ${String(frame.frame_index).padStart(3, '0')}`;
    document.getElementById('frame-time').textContent = `${frame.timestamp_seconds.toFixed(3)} s`;
    document.getElementById('sample-position').textContent = `${current + 1} / ${data.frames.length}`;
    document.getElementById('previous').disabled = current === 0;
    document.getElementById('next').disabled = current === data.frames.length - 1;
    document.getElementById('record-count').textContent = mode === 'raw' ? '—' : String(boxes.length);
    document.getElementById('record-label').textContent = mode === 'raw' ? 'Raw input / no overlays' : mode === 'detections' ? 'Person predictions' : 'Emitted tracks';
    const list = document.getElementById('record-list'); list.replaceChildren();
    boxes.forEach(box => {
      const row = document.createElement('div'); row.className = 'record-item';
      const title = document.createElement('strong'); title.textContent = mode === 'detections' ? 'Person' : `Track ${box.track_id}`;
      const confidence = document.createElement('span'); confidence.textContent = `conf ${box.confidence.toFixed(3)}`;
      row.append(title, confidence); list.appendChild(row);
    });
    if (mode !== 'raw' && !boxes.length) { const empty = document.createElement('p'); empty.className = 'record-note'; empty.textContent = 'No output boxes in this sampled frame.'; list.appendChild(empty); }
    canvas.setAttribute('aria-label', `Building frame ${frame.frame_index}, ${frame.timestamp_seconds.toFixed(3)} seconds; ${mode === 'raw' ? 'raw image' : `${boxes.length} saved ${mode} boxes`}. Not reference annotations.`);
    modes.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
    slider.value = String(current);
  }
  function show(index) {
    current = Math.max(0, Math.min(data.frames.length - 1, index));
    const frame = data.frames[current], ticket = ++request;
    image = null; draw(); updateRecords(); modes.forEach(button => { button.disabled = true; });
    setStatus('Loading source frame…');
    const nextImage = new Image();
    nextImage.onload = () => {
      if (ticket !== request) return;
      if (nextImage.naturalWidth !== data.clip.width || nextImage.naturalHeight !== data.clip.height) { setStatus('Source image dimensions differ from its record.', true); return; }
      image = nextImage; draw(); modes.forEach(button => { button.disabled = false; });
      setStatus(`25 fps · confidence ≥ 0.25 · saved baseline outputs · ${data.clip.author} / CC0`);
    };
    nextImage.onerror = () => { if (ticket === request) { modes.forEach(button => { button.disabled = false; }); setStatus('Source frame could not load. Retry using the frame controls.', true); } };
    nextImage.src = frame.image;
  }
  modes.forEach(button => { button.disabled = true; button.addEventListener('click', () => { if (!data || !image) return; mode = button.dataset.mode; updateRecords(); draw(); }); });
  slider.disabled = true;
  slider.addEventListener('input', () => { if (data) show(Number(slider.value)); });
  document.getElementById('previous').addEventListener('click', () => { if (data) show(current - 1); });
  document.getElementById('next').addEventListener('click', () => { if (data) show(current + 1); });
  document.getElementById('evidence').addEventListener('keydown', event => {
    if (!data || event.target.tagName === 'INPUT') return;
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); show(current + (event.key === 'ArrowLeft' ? -1 : 1)); }
  });
  fetch('results.json').then(response => { if (!response.ok) throw new Error('Frame records are unavailable.'); return response.json(); }).then(payload => {
    if (payload.schema_version !== 1 || payload.scope !== 'saved_person_predictions_only' || payload.accuracy !== null || !Array.isArray(payload.frames) || !payload.frames.length) throw new Error('Unexpected public frame-record format.');
    data = payload; canvas.width = data.clip.width; canvas.height = data.clip.height;
    slider.max = String(data.frames.length - 1); slider.disabled = false;
    document.querySelectorAll('[data-doc]').forEach(link => { link.href = `https://github.com/asadozzaman/worksite-vision-lab/blob/${data.source_commit}/${link.dataset.doc}`; });
    show(current);
  }).catch(error => { setStatus(error.message, true); document.getElementById('previous').disabled = document.getElementById('next').disabled = true; });
})();
