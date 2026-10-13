const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const lines = name => fs.readFileSync(path.join(root, name), 'utf8').trim().split('\n').map(JSON.parse);
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

test('public sampled predictions equal the preserved detector and both tracker streams', () => {
  const payload = read('site/results.json');
  const detector = lines('experiments/results/building-baseline.jsonl');
  const tracker = Object.fromEntries(['bytetrack', 'botsort'].map(name => [name, lines(`experiments/results/tracking/building-${name}.jsonl`)]));
  const summary = read('experiments/results/building-baseline.json');
  const personClass = Number(Object.entries(summary.model.names).find(([, name]) => name.toLowerCase() === 'person')[0]);
  assert.equal(payload.clip.video_sha256, summary.video_sha256);
  assert.equal(payload.clip.frame_count, detector.length);
  assert.equal(payload.model.person_class_id, personClass);
  assert.equal(payload.model.confidence_floor, summary.parameters.conf);
  assert.equal(payload.model.sha256, summary.model.sha256);
  assert.equal(payload.scope, 'saved_person_predictions_only');
  assert.equal(payload.accuracy, null);
  assert.deepEqual(payload.frames.map(frame => frame.frame_index), [0, 25, 50, 75, 100, 130]);
  for (const frame of payload.frames) {
    const original = detector[frame.frame_index];
    assert.equal(frame.timestamp_seconds, original.timestamp_seconds);
    assert.deepEqual(frame.detections, original.detections.map((box, index) => ({source_index:index, ...box})).filter(box => box.class_id === personClass));
    for (const name of ['bytetrack', 'botsort']) assert.deepEqual(frame.tracks[name], tracker[name][frame.frame_index].tracks);
    assert.equal(digest(fs.readFileSync(path.join(root, 'site', frame.image))), frame.image_sha256);
  }
});

test('public payload contains only approved files and no user labels, model binaries or local paths', () => {
  const manifest = read('site/publish-manifest.json');
  const allowed = new Set(['.nojekyll','index.html','style.css','app.js','icon.svg','results.json','publish-manifest.json','assets/baseline-comparison.png',...[0,25,50,75,100,130].map(index => `assets/frames/${String(index).padStart(6,'0')}.jpg`)]);
  function walk(directory, prefix = '') {
    return fs.readdirSync(directory, {withFileTypes:true}).flatMap(entry => {
      assert.ok(!entry.isSymbolicLink());
      const name = prefix + entry.name;
      return entry.isDirectory() ? walk(path.join(directory,entry.name),name+'/') : [name];
    });
  }
  assert.deepEqual(new Set(walk(path.join(root,'site'))), allowed);
  assert.equal(manifest.files.length, allowed.size - 1);
  for (const file of manifest.files) {
    assert.ok(allowed.has(file.path));
    const bytes = fs.readFileSync(path.join(root,'site',file.path));
    assert.equal(digest(bytes), file.sha256);
    assert.equal(bytes.length, file.bytes);
  }
  const payload = fs.readFileSync(path.join(root,'site/results.json'),'utf8');
  assert.doesNotMatch(payload, /reviewed_by|human_attested|reviewer_kind|annotation_version|(?:[A-Z]:\\)|gh[pousr]_|github_pat_/);
  assert.equal(read('site/results.json').clip.license, 'CC0-1.0');
  assert.equal(manifest.accuracy_measured, false);
});
