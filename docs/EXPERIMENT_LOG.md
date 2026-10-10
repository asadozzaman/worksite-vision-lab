# Experiment log

No real-video baseline, training, tracking benchmark, or event comparison has run.
Synthetic software tests below are excluded from evaluation results.

## ENV-001 — foundation installation and checks

- Date: 2026-10-10, Asia/Dhaka.
- Hypothesis: a small Python-only foundation can validate provenance/settings and
  inspect checkpoint metadata without loading the CV stack.
- Environment: Windows, Python 3.10.10, isolated `.venv`, pinned foundation lock.
- First install failed because Hatchling editable installs with build isolation
  disabled require `editables`. Added and pinned `editables==0.5`; install passed.
- Initial archive-name regression failed on Windows because Python normalizes
  backslashes in ZIP names. Inspection now checks `ZipInfo.orig_filename`; this
  preserves the intended rejection on Windows and Linux.
- Local result: 31 tests passed in 0.39 s; Ruff lint/format passed; `pip check`
  reported no broken requirements. CLI asset and baseline configuration validation passed.
- These tests measure software behavior, not detection or safety accuracy.
- Follow-up: added a real FFmpeg/ffprobe integration test using a generated
  five-frame 64×48 software fixture, excluded from research data. All 32 local
  tests passed in 4.18 s; wheel build passed. Initial six-job GitHub CI matrix
  passed at commit `0ea80032e0560af04681f62a9e0a38ec8de97066` with 31 tests/job.

## MODEL-001 — static artifact inspection

- Input revision: SiteGuard `f4d1a097679439f3eaec4e5569d4e52d479cf592`.
- SHA-256: `b2e1cca6615d9826b061223ca646b3791efeb2cdca2917222d4899b705ccc0a3`.
- Question: is the download an inspectable PyTorch ZIP rather than a pointer or HTML?
- Result: 5,394,437 bytes; 718 members; `data.pkl` 185,046 bytes; 74,135
  opcodes; 28 explicit globals and 0 dynamic globals. No model load performed.
- Interpretation: compatible archive structure and recognizable symbols; not
  proof of architecture, safe execution, licensing or accuracy.
- Evidence: [checkpoint-static.json](evidence/checkpoint-static.json).

## Next gated experiments

1. Isolated restricted load, exact official-architecture state-dict comparison,
   and synthetic compatibility smoke test. Record actual loaded names and outcome.
2. Review and normalize acquired real footage, then run a fixed CPU detection baseline.
3. Annotate observed failures before proposing or tuning three controlled hypotheses.

No failure hypotheses or performance improvements are claimed before observation.
