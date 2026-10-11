param(
    [Parameter(Mandatory=$true)][ValidateSet('building','street')][string]$Video,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9_-]+$')][string]$RunName,
    [ValidateRange(0.001,1)][double]$Confidence = 0.25
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$modelPath = (Resolve-Path (Join-Path $repoPath 'data/quarantine/yolo26n_ppe.pt')).Path
$inputPath = (Resolve-Path (Join-Path $repoPath 'data/normalized')).Path
$outputPath = Join-Path $repoPath 'data/runs'
New-Item -ItemType Directory -Force $outputPath | Out-Null
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges `
    --pids-limit 128 --memory 2g --cpus 2 --tmpfs /tmp:rw,noexec,nosuid,size=256m `
    -e PYTHONPATH=/src `
    --mount "type=bind,source=$repoPath/vision,target=/src/vision,readonly" `
    --mount "type=bind,source=$modelPath,target=/input/model.pt,readonly" `
    --mount "type=bind,source=$inputPath,target=/videos,readonly" `
    --mount "type=bind,source=$outputPath,target=/output" `
    worksite-checkpoint-inspector:8.4.173 -m vision.detection.run `
    --model /input/model.pt --video "/videos/$Video.mp4" `
    --normalization "/videos/$Video.json" --output "/output/$RunName" `
    --conf $Confidence.ToString([System.Globalization.CultureInfo]::InvariantCulture)
if ($LASTEXITCODE -ne 0) { throw "Baseline failed (exit $LASTEXITCODE); inspect failure.json" }
