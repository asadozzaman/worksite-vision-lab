/* Local-only editor. No annotation data is sent over the network. */
(() => {
  'use strict';
  const core = window.AnnotationCore, $ = id => document.getElementById(id);
  const canvas = $('canvas'), ctx = canvas.getContext('2d');
  const storageKey = `worksite-reference-v2:${initialReference.manifest_sha256}`;
  let doc = core.clone(initialReference), current = 0, selected = -1, rawImage = null;
  let imageRequest = 0, gesture = null, undoStack = [], dirty = false;
  function message(text, error = false) { $('status').textContent = text; $('status').className = error ? 'error' : ''; }
  function snapshot() { undoStack.push(core.clone(doc)); if (undoStack.length > 30) undoStack.shift(); }
  function persist() {
    dirty = true;
    try { localStorage.setItem(storageKey, JSON.stringify(doc)); $('save-status').textContent = `Draft cached in this browser · revision ${doc.revision}. Download JSON for a durable copy.`; }
    catch (_) { $('save-status').textContent = 'Browser storage unavailable or full. Download JSON to keep your labels.'; }
  }
  function mutate(action, fn, index = current, invalidate = true) {
    const before = core.clone(doc);
    try {
      fn(); core.touch(doc, action, index, invalidate); core.validate(doc, initialReference);
      undoStack.push(before); if (undoStack.length > 30) undoStack.shift();
      persist(); render(); message('Change saved to the working draft.');
    } catch (error) { doc = before; render(); message(error.message, true); }
  }
  function point(event) {
    const rect = canvas.getBoundingClientRect();
    return [(event.clientX - rect.left) * canvas.width / rect.width, (event.clientY - rect.top) * canvas.height / rect.height];
  }
  function drawBox(box, text, color, dashed = false) {
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.setLineDash(dashed ? [5, 4] : []);
    ctx.strokeRect(box[0], box[1], box[2] - box[0], box[3] - box[1]); ctx.setLineDash([]);
    ctx.font = '12px sans-serif'; const y = Math.max(15, box[1] - 3), x = Math.max(1, box[0]);
    ctx.fillStyle = '#101a23'; ctx.fillRect(x, y - 12, ctx.measureText(text).width + 5, 15);
    ctx.fillStyle = color; ctx.fillText(text, x + 2, y);
  }
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!rawImage) return;
    ctx.drawImage(rawImage, 0, 0);
    const mode = $('overlay').value;
    if (mode === 'detections') bundle.frames[current].detections.forEach(d => drawBox(d.xyxy, `Model ${d.class_name} ${d.confidence.toFixed(2)}`, '#e4b55e', true));
    else if (mode !== 'none') bundle.trackers[mode][current].tracks.forEach(t => drawBox(t.xyxy, `Track ${t.track_id}`, '#e4b55e', true));
    doc.frames[current].people.forEach((box, i) => drawBox(box.xyxy, `${i + 1} · ${box.person_id || 'unassigned'}${box.ignore ? ' · ignore' : ''}`, i === selected ? '#ffffff' : '#58dfca'));
    if (gesture && $('mode').value === 'draw') {
      try { drawBox(core.boxFromPoints(gesture.start, gesture.end, canvas.width, canvas.height), 'New person', '#ffffff'); } catch (_) { /* tiny drag */ }
    }
  }
  function render() {
    const frame = doc.frames[current];
    if (selected >= frame.people.length) selected = -1;
    $('number').value = $('slider').value = current;
    $('time').textContent = `${(current / bundle.fps).toFixed(3)} s · ${bundle.width} × ${bundle.height}`;
    $('prev').disabled = current === 0; $('next').disabled = current === bundle.frames.length - 1;
    $('reviewer').value = doc.reviewer; $('reviewer-kind').value = doc.reviewer_kind;
    $('version').value = doc.annotation_version; $('start').value = doc.review_start; $('end').value = doc.review_end;
    $('frame-notes').value = frame.notes; $('empty').checked = frame.empty_confirmed;
    $('empty').disabled = frame.people.length > 0 || !rawImage;
    $('frame-state').textContent = frame.reviewed ? `Reviewed by ${frame.reviewed_by}` : 'Needs review';
    $('review').disabled = !rawImage || current < doc.review_start || current > doc.review_end;
    $('copy').disabled = !rawImage || current === 0 || frame.people.length > 0;
    $('undo').disabled = undoStack.length === 0;
    const reviewed = doc.frames.slice(doc.review_start, doc.review_end + 1).filter(f => f.reviewed).length;
    $('progress').textContent = `${reviewed} / ${doc.review_end - doc.review_start + 1} frames reviewed`;
    $('attest').disabled = !doc.complete || doc.reviewer_kind !== 'human'; $('attest').checked = doc.human_attested;
    $('boxes').replaceChildren();
    frame.people.forEach((box, index) => {
      const button = document.createElement('button'); button.type = 'button';
      button.textContent = `${index + 1}. ${box.person_id || 'Assign identity'} · ${box.visibility}${box.ignore ? ' · ignored' : ''}`;
      button.setAttribute('aria-label', `Select box ${index + 1}`); button.setAttribute('aria-pressed', String(index === selected));
      button.onclick = () => { selected = index; render(); }; $('boxes').appendChild(button);
    });
    $('box-empty').hidden = frame.people.length > 0;
    $('box-fields').disabled = selected < 0;
    const box = frame.people[selected];
    $('identity').replaceChildren(new Option('Unassigned', ''));
    doc.identities.forEach(i => $('identity').appendChild(new Option(i.person_id, i.person_id)));
    $('identity').value = box?.person_id || ''; $('visibility').value = box?.visibility || 'visible';
    $('ignore').checked = box?.ignore || false; $('truncated').checked = box?.truncated || false;
    $('box-notes').value = box?.notes || '';
    ['x1', 'y1', 'x2', 'y2'].forEach((name, i) => { $(name).value = box ? box.xyxy[i] : ''; });
    $('model-record').textContent = JSON.stringify($('overlay').value === 'none' ? {frame_index: current, predictions_hidden: true} : $('overlay').value === 'detections' ? bundle.frames[current] : bundle.trackers[$('overlay').value][current], null, 2);
    draw();
  }
  function show(index) {
    current = Math.max(0, Math.min(bundle.frames.length - 1, Math.trunc(Number(index) || 0)));
    selected = -1; gesture = null; rawImage = null; const request = ++imageRequest;
    message('Loading raw frame…'); render();
    const image = new Image();
    image.onload = () => { if (request !== imageRequest) return; rawImage = image; render(); message('Inspect all visible people before marking this frame reviewed.'); };
    image.onerror = () => { if (request !== imageRequest) return; message('Frame could not load. Keep the images folder beside this page.', true); };
    image.src = `images/${String(current).padStart(6, '0')}.jpg`;
  }
  canvas.addEventListener('pointerdown', event => {
    if (!rawImage || event.button !== 0) return;
    const start = point(event); canvas.setPointerCapture(event.pointerId);
    if ($('mode').value === 'select') {
      selected = doc.frames[current].people.findLastIndex(b => start[0] >= b.xyxy[0] && start[0] <= b.xyxy[2] && start[1] >= b.xyxy[1] && start[1] <= b.xyxy[3]);
      render(); return;
    }
    gesture = {start, end: start}; draw();
  });
  canvas.addEventListener('pointermove', event => { if (gesture) { gesture.end = point(event); draw(); } });
  canvas.addEventListener('pointerup', event => {
    if (!gesture) return;
    const start = gesture.start; gesture = null;
    try {
      const xyxy = core.boxFromPoints(start, point(event), canvas.width, canvas.height);
      mutate('draw_person_box', () => {
        doc.frames[current].people.push({person_id: null, xyxy, visibility: 'visible', truncated: false, ignore: false, notes: ''});
        doc.frames[current].empty_confirmed = false; selected = doc.frames[current].people.length - 1;
      });
    } catch (error) { message(error.message, true); draw(); }
  });
  canvas.addEventListener('pointercancel', () => { gesture = null; draw(); });
  $('prev').onclick = () => show(current - 1); $('next').onclick = () => show(current + 1);
  $('number').oninput = event => show(event.target.value); $('slider').oninput = event => show(event.target.value);
  $('next-unreviewed').onclick = () => {
    const indexes = Array.from({length: doc.review_end - doc.review_start + 1}, (_, i) => i + doc.review_start);
    const next = indexes.find(i => i > current && !doc.frames[i].reviewed) ?? indexes.find(i => !doc.frames[i].reviewed);
    if (next === undefined) message('Every frame in the selected interval is reviewed.'); else show(next);
  };
  $('overlay').onchange = render; $('mode').onchange = () => { gesture = null; draw(); };
  $('new-identity').onclick = () => mutate('assign_new_manual_identity', () => { doc.frames[current].people[selected].person_id = core.newIdentity(doc); });
  $('identity').onchange = event => mutate('assign_manual_identity', () => { doc.frames[current].people[selected].person_id = event.target.value || null; });
  $('visibility').onchange = event => mutate('set_visibility', () => { doc.frames[current].people[selected].visibility = event.target.value; });
  for (const name of ['ignore', 'truncated']) $(name).onchange = event => mutate(`set_${name}`, () => { doc.frames[current].people[selected][name] = event.target.checked; });
  $('box-notes').onchange = event => mutate('set_box_notes', () => { doc.frames[current].people[selected].notes = event.target.value; });
  $('apply-box').onclick = () => mutate('edit_box_coordinates', () => { doc.frames[current].people[selected].xyxy = ['x1', 'y1', 'x2', 'y2'].map(name => Number($(name).value)); });
  $('delete-box').onclick = () => mutate('delete_box', () => { doc.frames[current].people.splice(selected, 1); selected = -1; });
  $('frame-notes').onchange = event => mutate('set_frame_notes', () => { doc.frames[current].notes = event.target.value; });
  $('empty').onchange = event => mutate('confirm_no_visible_people', () => { doc.frames[current].empty_confirmed = event.target.checked; });
  $('reviewer').onchange = event => mutate('set_reviewer', () => {
    doc.reviewer = event.target.value.trim(); doc.frames.forEach(f => { f.reviewed = false; f.reviewed_by = null; });
  }, null);
  $('reviewer-kind').onchange = event => mutate('set_reviewer_kind', () => {
    doc.reviewer_kind = event.target.value; doc.frames.forEach(f => { f.reviewed = false; f.reviewed_by = null; });
  }, null);
  $('version').onchange = event => mutate('set_annotation_version', () => { doc.annotation_version = event.target.value.trim(); }, null);
  $('apply-range').onclick = () => mutate('set_review_interval', () => { doc.review_start = Number($('start').value); doc.review_end = Number($('end').value); }, null);
  $('review').onclick = () => {
    const before = core.clone(doc);
    try { core.markReviewed(doc, current); core.validate(doc, initialReference); undoStack.push(before); if (undoStack.length > 30) undoStack.shift(); persist(); render(); message('Frame reviewed. Continue to the next unreviewed frame.'); }
    catch (error) { doc = before; render(); message(error.message, true); }
  };
  $('copy').onclick = () => {
    const before = core.clone(doc);
    try { core.copyPrevious(doc, current); core.validate(doc, initialReference); undoStack.push(before); if (undoStack.length > 30) undoStack.shift(); selected = -1; persist(); render(); message('Copied manual boxes. Adjust them and review this frame separately.'); }
    catch (error) { doc = before; render(); message(error.message, true); }
  };
  $('undo').onclick = () => {
    if (!undoStack.length) return;
    const history = doc.history, revision = doc.revision; doc = undoStack.pop(); doc.history = history; doc.revision = revision;
    // Undo restores geometry but never silently restores a review attestation.
    doc.frames.forEach(f => { f.reviewed = false; f.reviewed_by = null; });
    core.touch(doc, 'undo_edit_clear_reviews', null); persist(); render(); message('Undo applied. Review confirmations were cleared.');
  };
  $('attest').onchange = event => {
    const value = event.target.checked;
    mutate('set_human_attestation', () => {}, null, false);
    if (doc.complete && doc.reviewer_kind === 'human') { doc.human_attested = value; persist(); render(); }
  };
  $('download').onclick = () => {
    try {
      core.validate(doc, initialReference);
      const url = URL.createObjectURL(new Blob([JSON.stringify(doc, null, 2) + '\n'], {type: 'application/json'}));
      const link = document.createElement('a'); link.href = url; link.download = `person-reference-${doc.video_sha256.slice(0, 8)}-r${doc.revision}.json`;
      link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); dirty = false;
      message('JSON download requested. Keep the downloaded file as your saved reference.');
    } catch (error) { message(error.message, true); }
  };
  $('import').onchange = async event => {
    const file = event.target.files[0]; if (!file) return;
    try {
      if (file.size > 50 * 1024 * 1024) throw new Error('Reference exceeds 50 MiB.');
      const next = core.validate(JSON.parse(await file.text()), initialReference);
      snapshot(); doc = next; persist(); show(doc.review_start); message('Saved reference loaded and validated for this clip.');
    } catch (error) { message(`Import rejected: ${error.message}`, true); }
    event.target.value = '';
  };
  document.addEventListener('keydown', event => {
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(event.target.tagName)) return;
    if (event.key === 'ArrowLeft') show(current - 1); if (event.key === 'ArrowRight') show(current + 1);
  });
  window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
  $('title').textContent = bundle.title; $('credit').textContent = bundle.attribution;
  $('source').textContent = `${bundle.split} · ${bundle.frame_count} frames · ${bundle.fps} fps`;
  canvas.width = bundle.width; canvas.height = bundle.height;
  $('number').max = $('slider').max = $('start').max = $('end').max = bundle.frame_count - 1;
  Object.keys(bundle.trackers).forEach(name => $('overlay').appendChild(new Option(name, name)));
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved) { doc = core.validate(JSON.parse(saved), initialReference); $('save-status').textContent = `Restored browser draft, revision ${doc.revision}. Download JSON for a durable copy.`; }
  } catch (_) { $('save-status').textContent = 'A browser draft could not be restored. Open your saved JSON or start a new draft.'; }
  show(doc.review_start);
})();
