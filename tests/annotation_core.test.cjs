'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const core = require('../vision/evaluation/annotation-core.js');
const template = require('./fixtures/person-reference-v2.json');
const draft = () => core.clone(template);
const box = id => ({person_id: id, xyxy: [10, 20, 30, 80], visibility: 'visible', truncated: false, ignore: false, notes: ''});

test('drag normalizes direction, clamps bounds and rejects accidental clicks', () => {
  assert.deepEqual(core.boxFromPoints([150, 220], [-10, 20], 100, 200), [0, 20, 100, 200]);
  assert.throws(() => core.boxFromPoints([1, 1], [1.5, 2], 100, 200), /one pixel/);
});
test('empty frames need explicit confirmation; incomplete drafts cannot attest', () => {
  const d = draft();
  assert.throws(() => core.markReviewed(d, 0), /Confirm/);
  d.frames[0].empty_confirmed = true; core.markReviewed(d, 0);
  assert.equal(d.complete, false);
  assert.equal(core.validate(d, template), d);
  d.human_attested = true;
  assert.throws(() => core.validate(d, template), /attestation/);
});
test('manual identity continuity is copied without copying review or sharing geometry', () => {
  const d = draft(), id = core.newIdentity(d);
  d.frames[0].people.push(box(id)); core.touch(d, 'draw_fixture', 0); core.markReviewed(d, 0);
  core.copyPrevious(d, 1);
  assert.equal(d.frames[1].reviewed, false);
  assert.equal(d.frames[1].people[0].person_id, 'p001');
  d.frames[1].people[0].xyxy[0] = 11;
  assert.equal(d.frames[0].people[0].xyxy[0], 10);
  assert.throws(() => core.copyPrevious(d, 1), /without boxes/);
  assert.equal(core.validate(d, template), d);
});
test('duplicate identity, unresolved identity and undocumented ignore block review', () => {
  const d = draft(), id = core.newIdentity(d);
  d.frames[0].people = [box(id), box(id)];
  assert.throws(() => core.markReviewed(d, 0), /already has a box/);
  d.frames[0].people = [box(null)];
  assert.throws(() => core.markReviewed(d, 0), /assign an identity/);
  d.frames[0].people[0].ignore = true;
  assert.throws(() => core.markReviewed(d, 0), /explain why/);
  d.frames[0].people[0].notes = 'Synthetic fixture, unresolved identity';
  core.markReviewed(d, 0); core.validate(d, template);
});
test('selected interval completion and edits invalidate review and attestation', () => {
  const d = draft(); d.reviewer_kind = 'human'; d.review_end = 0;
  d.frames[0].empty_confirmed = true; core.markReviewed(d, 0); d.human_attested = true;
  core.validate(d, template); assert.equal(d.complete, true);
  d.frames[0].notes = 'changed'; core.touch(d, 'edit_notes', 0);
  assert.equal(d.frames[0].reviewed_by, null); assert.equal(d.complete, false);
  assert.equal(d.human_attested, false); core.validate(d, template);
});
test('nonhuman review can complete but cannot attest', () => {
  const d = draft(); d.frames.forEach((f, i) => { f.empty_confirmed = true; core.markReviewed(d, i); });
  assert.equal(d.complete, true); core.validate(d, template); d.human_attested = true;
  assert.throws(() => core.validate(d, template), /human review/);
});
test('saved draft round trips with source binding and rejects corrupt imports', () => {
  const d = draft(); d.frames[0].people = [box(core.newIdentity(d))]; core.touch(d, 'draw_fixture', 0);
  assert.deepEqual(core.validate(JSON.parse(JSON.stringify(d)), template), d);
  for (const field of ['manifest_sha256', 'video_sha256', 'split', 'width', 'frame_count']) {
    const wrong = core.clone(d); wrong[field] = 'wrong';
    assert.throws(() => core.validate(wrong, template), /different/);
  }
  const malformed = core.clone(d); malformed.history = [];
  assert.throws(() => core.validate(malformed, template), /history/);
  const extra = JSON.parse(JSON.stringify(d).replace('{', '{"__proto__":{},'));
  assert.throws(() => core.validate(extra, template), /Unexpected/);
  d.frames[0].people[0].xyxy[2] = 999;
  assert.throws(() => core.validate(d, template), /outside image/);
});
