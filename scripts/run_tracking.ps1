param(
    [Parameter(Mandatory=$true)][ValidateSet('building','street')][string]$Video,
    [Parameter(Mandatory=$true)][ValidateSet('bytetrack','botsort')][string]$Tracker,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9_-]+$')][string]$RunName,
    [ValidatePattern('^[a-z0-9][a-z0-9_-]+$')][string]$BaselineRun,
    [ValidatePattern('^[a-z0-9][a-z0-9_-]+$')][string]$ConfigName
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$inputPath = (Resolve-Path (Join-Path $repoPath 'data/normalized')).Path
if (-not $BaselineRun) { $BaselineRun = "$Video-baseline" }
if (-not $ConfigName) { $ConfigName = $Tracker }
$baselinePath = (Resolve-Path (Join-Path $repoPath "data/runs/$BaselineRun")).Path
$outputPath = Join-Path $repoPath 'data/tracking'
New-Item -ItemType Directory -Force $outputPath | Out-Null
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges `
    --pids-limit 128 --memory 2g --cpus 2 --tmpfs /tmp:rw,noexec,nosuid,size=256m `
    -e PYTHONPATH=/src `
    --mount "type=bind,source=$repoPath/vision,target=/src/vision,readonly" `
    --mount "type=bind,source=$repoPath/experiments/configs,target=/configs,readonly" `
    --mount "type=bind,source=$inputPath,target=/videos,readonly" `
    --mount "type=bind,source=$baselinePath,target=/baseline,readonly" `
    --mount "type=bind,source=$outputPath,target=/output" `
    worksite-tracking:8.4.173 -m vision.tracking.run `
    --video "/videos/$Video.mp4" --detections /baseline/detections.jsonl `
    --baseline-summary /baseline/summary.json --config "/configs/$ConfigName.json" `
    --output "/output/$RunName"
if ($LASTEXITCODE -ne 0) { throw "Tracking failed (exit $LASTEXITCODE); inspect failure.json" }
