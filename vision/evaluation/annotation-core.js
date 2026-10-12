/* Pure annotation state operations; used by the browser and Node tests. */
(function (root) {
  'use strict';
  const clone = value => JSON.parse(JSON.stringify(value));
  const integer = value => Number.isInteger(value) && value >= 0;
  const idPattern = /^p[0-9]{3,6}$/;
  function frameIssues(doc, frame) {
    const errors = [];
    if (!doc.reviewer.trim()) errors.push('Enter your reviewer name first.');
    if (!frame.people.length && !frame.empty_confirmed) errors.push('Confirm that no people are visible, or add their boxes.');
    const used = new Set();
    frame.people.forEach((box, i) => {
      if (box.person_id && used.has(box.person_id)) errors.push(`Box ${i + 1}: this identity already has a box in this frame.`);
      if (box.person_id) used.add(box.person_id);
      if (!box.person_id && !box.ignore) errors.push(`Box ${i + 1}: assign an identity or ignore with a reason.`);
      if (box.visibility === 'uncertain' && !box.ignore) errors.push(`Box ${i + 1}: uncertain visibility must be ignored.`);
      if (box.ignore && !box.notes.trim()) errors.push(`Box ${i + 1}: explain why this box is ignored.`);
    });
    return errors;
  }
  function complete(doc) {
    return doc.frames.slice(doc.review_start, doc.review_end + 1).every(frame => frame.reviewed);
  }
  function touch(doc, action, index = null, invalidate = true) {
    doc.human_attested = false;
    if (index !== null && invalidate) {
      doc.frames[index].reviewed = false;
      doc.frames[index].reviewed_by = null;
    }
    doc.complete = complete(doc);
    doc.revision += 1;
    doc.history.push({revision: doc.revision, at: new Date().toISOString(), action, frame_index: index});
  }
  function boxFromPoints(a, b, width, height) {
    const bound = (v, max) => Math.max(0, Math.min(max, v));
    const xyxy = [bound(Math.min(a[0], b[0]), width), bound(Math.min(a[1], b[1]), height),
      bound(Math.max(a[0], b[0]), width), bound(Math.max(a[1], b[1]), height)].map(v => Math.round(v * 100) / 100);
    if (xyxy[2] - xyxy[0] < 1 || xyxy[3] - xyxy[1] < 1) throw new Error('Draw a box at least one pixel wide and high.');
    return xyxy;
  }
  function newIdentity(doc, notes = '') {
    const used = new Set(doc.identities.map(item => item.person_id));
    let index = 1;
    while (used.has(`p${String(index).padStart(3, '0')}`)) index += 1;
    const id = `p${String(index).padStart(3, '0')}`;
    if (!idPattern.test(id)) throw new Error('Identity limit reached.');
    doc.identities.push({person_id: id, notes});
    return id;
  }
  function markReviewed(doc, index) {
    const errors = frameIssues(doc, doc.frames[index]);
    if (errors.length) throw new Error(errors.join(' '));
    doc.frames[index].reviewed = true;
    doc.frames[index].reviewed_by = doc.reviewer;
    touch(doc, 'review_frame', index, false);
  }
  function copyPrevious(doc, index) {
    if (!index) throw new Error('There is no previous frame.');
    if (doc.frames[index].people.length) throw new Error('Copy is available only on frames without boxes.');
    doc.frames[index].people = clone(doc.frames[index - 1].people);
    doc.frames[index].empty_confirmed = false;
    touch(doc, 'copy_previous_manual_boxes', index);
  }
  function validate(doc, template) {
    const fail = message => { throw new Error(message); };
    if (!doc || typeof doc !== 'object' || Array.isArray(doc)) fail('Expected an annotation object.');
    if (doc.schema_version !== 2) fail('Use a version 2 person reference. Older empty templates need a new export.');
    if (Object.keys(doc).some(key => !Object.hasOwn(template, key)) || Object.keys(template).some(key => !Object.hasOwn(doc, key))) fail('Unexpected or missing annotation fields.');
    for (const key of ['scope', 'manifest_sha256', 'video_sha256', 'split', 'width', 'height', 'fps', 'frame_count']) {
      if (doc[key] !== template[key]) fail(`This annotation has a different ${key}.`);
    }
    if (!integer(doc.review_start) || !integer(doc.review_end) || doc.review_start > doc.review_end || doc.review_end >= doc.frame_count) fail('Review interval is outside this clip.');
    if (typeof doc.reviewer !== 'string' || doc.reviewer.length > 200) fail('Invalid reviewer name.');
    if (!['human', 'assistant', 'software_fixture'].includes(doc.reviewer_kind)) fail('Invalid reviewer kind.');
    if (typeof doc.annotation_version !== 'string' || !doc.annotation_version.trim() || doc.annotation_version.length > 100) fail('Invalid annotation version.');
    if (typeof doc.human_attested !== 'boolean' || typeof doc.complete !== 'boolean') fail('Invalid review status.');
    if (!Array.isArray(doc.identities) || doc.identities.length > 10000) fail('Invalid identities.');
    const ids = new Set();
    for (const identity of doc.identities) {
      if (!identity || !idPattern.test(identity.person_id) || ids.has(identity.person_id) || typeof identity.notes !== 'string' || identity.notes.length > 2000 || Object.keys(identity).some(k => !['person_id', 'notes'].includes(k))) fail('Invalid or duplicate manual identity.');
      ids.add(identity.person_id);
    }
    if (!Array.isArray(doc.frames) || doc.frames.length !== doc.frame_count) fail('Frame count differs from the clip.');
    doc.frames.forEach((frame, i) => {
      if (!frame || frame.frame_index !== i || typeof frame.reviewed !== 'boolean' || typeof frame.empty_confirmed !== 'boolean' || !Array.isArray(frame.people) || frame.people.length > 1000 || typeof frame.notes !== 'string' || frame.notes.length > 4000) fail(`Invalid frame ${i}.`);
      if (Object.keys(frame).some(k => !['frame_index', 'reviewed', 'reviewed_by', 'empty_confirmed', 'people', 'notes'].includes(k))) fail(`Unknown fields at frame ${i}.`);
      if (frame.people.length && frame.empty_confirmed) fail(`Frame ${i} contains people and a no-people confirmation.`);
      const used = new Set();
      for (const box of frame.people) {
        if (!box || !Array.isArray(box.xyxy) || box.xyxy.length !== 4 || !box.xyxy.every(Number.isFinite)) fail(`Invalid box at frame ${i}.`);
        const [x1, y1, x2, y2] = box.xyxy;
        if (!(0 <= x1 && x1 < x2 && x2 <= doc.width && 0 <= y1 && y1 < y2 && y2 <= doc.height)) fail(`Box outside image at frame ${i}.`);
        if (!(box.person_id === null || ids.has(box.person_id)) || (box.person_id && used.has(box.person_id))) fail(`Unknown or repeated identity at frame ${i}.`);
        if (box.person_id) used.add(box.person_id);
        if (!['visible', 'partial', 'uncertain'].includes(box.visibility) || typeof box.truncated !== 'boolean' || typeof box.ignore !== 'boolean' || typeof box.notes !== 'string' || box.notes.length > 2000 || Object.keys(box).some(k => !['person_id', 'xyxy', 'visibility', 'truncated', 'ignore', 'notes'].includes(k))) fail(`Invalid box attributes at frame ${i}.`);
      }
      if (frame.reviewed && (frame.reviewed_by !== doc.reviewer || frameIssues(doc, frame).length)) fail(`Frame ${i} was marked reviewed with unresolved labels.`);
      if (!frame.reviewed && frame.reviewed_by !== null) fail(`Frame ${i} has an inconsistent reviewer.`);
    });
    if (doc.complete !== complete(doc)) fail('Completion flag disagrees with reviewed frames.');
    if (doc.human_attested && (doc.reviewer_kind !== 'human' || !doc.complete)) fail('Human attestation requires completed human review.');
    if (!integer(doc.revision) || !Array.isArray(doc.history) || doc.history.length !== doc.revision || doc.history.length > 200000) fail('Invalid revision history.');
    doc.history.forEach((h, i) => {
      if (!h || h.revision !== i + 1 || typeof h.at !== 'string' || !h.at || h.at.length > 50 || typeof h.action !== 'string' || !h.action || h.action.length > 100 || (h.frame_index !== null && (!integer(h.frame_index) || h.frame_index >= doc.frame_count)) || Object.keys(h).some(k => !['revision', 'at', 'action', 'frame_index'].includes(k))) fail('Revision history is incomplete or malformed.');
    });
    return doc;
  }
  const api = {clone, frameIssues, complete, touch, boxFromPoints, newIdentity, markReviewed, copyPrevious, validate};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AnnotationCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
