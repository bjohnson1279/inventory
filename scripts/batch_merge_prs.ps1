# Batch PR Merger & Submodule Synchronizer (PowerShell)
param(
    [switch]$DryRun,
    [switch]$SkipSync
)

$ErrorActionPreference = "Continue"
$BaseDir = Split-Path -Parent $PSScriptRoot

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "🤖 Jules / Bolt / Sentinel PR Batch Automation Runner" -ForegroundColor Cyan
Write-Host "Base Directory: $BaseDir"
if ($DryRun) { Write-Host "Mode: DRY RUN (no state changes will be made)" -ForegroundColor Yellow }
Write-Host "======================================================================" -ForegroundColor Cyan

# STEP 1: Close Duplicate / Superseded PRs
Write-Host "`n======================================================================" -ForegroundColor Magenta
Write-Host "🚫 STEP 1: Closing Duplicate & Superseded PRs" -ForegroundColor Magenta
Write-Host "======================================================================" -ForegroundColor Magenta

$Superseded = @(
    @{ Repo = "inventory-python-sidecar"; PR = 67; Comment = "Closing as duplicate: RateLimitMiddleware memory leak fix is superseded by PR #69 which includes this fix plus missing HTTP security response headers." },
    @{ Repo = "react-ddd-inventory-client"; PR = 375; Comment = "Closing as duplicate: SupplierCollaborationPortal unit tests are superseded by more comprehensive test coverage in PR #376." },
    @{ Repo = "react-ddd-inventory-client"; PR = 372; Comment = "Closing as duplicate: PredictiveScheduling unit tests are superseded by broader test suite and mock isolation in PR #378." },
    @{ Repo = "react-ddd-inventory-client"; PR = 364; Comment = "Closing as duplicate: URL injection fix in ESG Emissions Panel is superseded by complete parameter encoding in PR #367." }
)

foreach ($item in $Superseded) {
    $repoDir = Join-Path $BaseDir $item.Repo
    Write-Host "Closing $($item.Repo) PR #$($item.PR)..." -ForegroundColor Yellow
    if ($DryRun) {
        Write-Host "  [DRY-RUN] gh pr close $($item.PR) --comment '$($item.Comment)' --delete-branch"
    } else {
        Push-Location $repoDir
        gh pr close $item.PR --comment $item.Comment --delete-branch
        Pop-Location
    }
}

# STEP 2: Squash-Merge Group A PRs
Write-Host "`n======================================================================" -ForegroundColor Green
Write-Host "🚀 STEP 2: Squash-Merging Group A PRs" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green

$MergeBatches = @(
    @{ Repo = "gql-ddd-inventory"; PRs = @(768, 767) },
    @{ Repo = "js-ddd-inventory"; PRs = @(874, 873, 872) },
    @{ Repo = "inventory-python-sidecar"; PRs = @(69, 68) },
    @{ Repo = "python-ddd-inventory"; PRs = @(158, 155, 153, 151, 146) },
    @{ Repo = "react-ddd-inventory-client"; PRs = @(
        389, 388, 387, 386, 385, 384, 383, 382,
        381, 380, 379, 378, 377, 376, 374, 373,
        371, 370, 369, 368, 367, 366
    ) }
)

$mergedCount = 0
foreach ($batch in $MergeBatches) {
    $repoDir = Join-Path $BaseDir $batch.Repo
    Write-Host "`n📦 Submodule: $($batch.Repo) ($($batch.PRs.Count) PRs to merge)" -ForegroundColor Cyan
    Push-Location $repoDir
    foreach ($pr in $batch.PRs) {
        Write-Host -NoNewline "  Merging PR #$pr... "
        if ($DryRun) {
            Write-Host "[DRY-RUN] gh pr merge $pr --squash --admin --delete-branch" -ForegroundColor Gray
            $mergedCount++
        } else {
            gh pr merge $pr --squash --admin --delete-branch
            if ($LASTEXITCODE -ne 0) {
                # Fallback to standard merge without --admin
                gh pr merge $pr --squash --delete-branch
            }
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Merged" -ForegroundColor Green
                $mergedCount++
            } else {
                Write-Host "❌ Failed (exit code $LASTEXITCODE)" -ForegroundColor Red
            }
            Start-Sleep -Milliseconds 400
        }
    }
    Pop-Location
}

# STEP 3: Submodule Sync & Gitlink Commit
if (-not $SkipSync) {
    Write-Host "`n======================================================================" -ForegroundColor Blue
    Write-Host "🔄 STEP 3: Synchronizing Submodules & Updating Parent Gitlinks" -ForegroundColor Blue
    Write-Host "======================================================================" -ForegroundColor Blue

    if ($DryRun) {
        Write-Host "  [DRY-RUN] Would run: python scripts/sync_submodules.py --commit"
    } else {
        python "$BaseDir/scripts/sync_submodules.py" --commit
    }
}

Write-Host "`n🎉 PR batch review automation finished!" -ForegroundColor Green
