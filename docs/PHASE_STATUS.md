# Phase status

As of 2026-10-10 (Asia/Dhaka). Status describes execution, not code volume.

| Phase | Status | Evidence / gate |
|---|---|---|
| 0 — foundation | Partially implemented and verified | Local package and 32 tests pass; initial six-job CI matrix passed; repository and push access verified; model static inspection done. Isolated model check pending; real-video acquisition and weight rights unresolved. |
| 1 — real detection baseline | Blocked before execution | No acquired/visually reviewed real footage; no cleared PPE baseline. |
| 2 — tracking comparison | Not started | Depends on actual baseline input and outputs. |
| 3 — failure analysis | Not started | Requires observed failures and reference annotations. |
| 4 — event reliability | Not started | Requires class/association evidence and frozen evaluation set. |
| 5 — API/dashboard | Not started | Deliberately gated by research verification. |
| 6 — release validation | Not started | Requires an end-to-end real CPU demonstration. |

## Phase 0 objective and delivered work

Establish a repeatable research foundation before inference or training. Added:

- Python package/CLI, validated experiment settings and asset provenance schema.
- Streaming hashes, bounded static checkpoint inspection and FFmpeg metadata probing.
- Isolated Docker checkpoint procedure and explicit, reviewed load allowlist.
- Windows/Linux Python 3.10–3.12 CI matrix; pinned foundation environment.
- AGPL license, third-party notices, asset acquisition and phased acceptance plans.
- Unit tests covering malformed archives, no pickle execution, configuration,
  provenance claims, class resolution, CLI behavior and video probing.

Changed files: `vision/`, `tests/`, `scripts/`, `docker/`, `requirements/`,
`experiments/configs/`, `docs/`, `.github/workflows/ci.yml`, packaging, README,
license, notices, ignore rules and environment template. No application code from
SiteGuard or private/employer assets was imported.

## Provenance and measured results

- SiteGuard artifact pinned to commit `f4d1a097679439f3eaec4e5569d4e52d479cf592`;
  5,394,437 bytes and SHA-256 recorded in [assets.json](assets.json).
- Static inspection: 718 archive members, 28 explicit globals; no unpickle/load.
- Foundation: 32 tests passed (4.18 s), lint and formatting pass, `pip check` passes;
  editable installation and wheel build pass. The added FFmpeg integration test
  uses a synthetic five-frame fixture solely to verify metadata tooling.
- Pexels clip descriptions/licenses reviewed; publisher metadata recorded, files
  not acquired or independently measured. No claims of observed violations.
- No detection precision/recall/mAP, tracking scores, false-alert rates, GPU
  utilization or CPU video throughput measured.

## Repository and external access

The expected GitHub repository initially returned not found. After the owner made
it available, authenticated API inspection confirmed
`asadozzaman/worksite-vision-lab`, an empty public repository with default branch
`main` and push permission. Remote history was empty. An empty base commit
`a5f8ce3` initializes `main`; implementation is on `feat/phase-0-foundation`.
No feature work is merged into `main`.

Initial implementation commit: `0ea80032e0560af04681f62a9e0a38ec8de97066`.
[Draft PR #1](https://github.com/asadozzaman/worksite-vision-lab/pull/1) is open.
[Initial Actions run](https://github.com/asadozzaman/worksite-vision-lab/actions/runs/38035960790)
passed all six OS/Python jobs at that commit. The initial matrix ran 31 foundation
tests per job. Subsequent verification changes require their own CI result.

No GitHub connector is installed, but Git Credential Manager authentication works
for Git and GitHub REST. No exposed Kaggle connector/execution action was found;
plugin search for Kaggle returned no match. No cloud GPU work was submitted.

## Decisions, failures and limitations

Start with Ultralytics 8.4.173, inspected locally, rather than silently using latest.
Use restricted loading inside an offline, non-root, resource-limited container.
Keep checkpoints/videos outside Git. Treat `none` as unresolved, and lack of a PPE
detection as unknown. Do not progress to a decorative dashboard before a baseline.

Editable installation initially lacked `editables`; fixed and retested. A Windows
ZIP-name normalization issue was exposed by a security regression test and fixed
using original archive names. See [experiment log](EXPERIMENT_LOG.md).

Pexels terms restrict unauthorized automated collection; manual acquisition steps
are documented. SiteGuard's repository MIT statement does not independently clear
weight/data redistribution. Ground-truth annotations do not yet exist.

## Next actions

Finish isolated checkpoint verification and update the published foundation PR.
Acquire the two clips through their normal download controls and review the actual
footage. Resolve weight rights or select a documented alternative. Only then begin
Phase 1 and record a real CPU detection baseline.
