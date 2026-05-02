# Move-BrowserProfiles.ps1
# Moves the browser_profiles folder from OneDrive to local storage
# to free up ~678 MB of OneDrive sync space.

$source = "C:\Users\suppo\OneDrive\Desktop\AI Agent 1\browser_profiles"
$destination = "C:\Users\suppo\LocalStorage\AI Agent 1\browser_profiles"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI Agent 1 - Browser Profiles Mover  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Verify source exists ---
if (-not (Test-Path $source)) {
    Write-Host "[ERROR] Source folder not found: $source" -ForegroundColor Red
    exit 1
}

$sourceSize = (Get-ChildItem $source -Recurse -File | Measure-Object -Property Length -Sum).Sum
$sourceSizeMB = [math]::Round($sourceSize / 1MB, 1)
$sourceFileCount = (Get-ChildItem $source -Recurse -File).Count

Write-Host "[INFO] Source: $source" -ForegroundColor Yellow
Write-Host "[INFO] Size:   $sourceSizeMB MB  ($sourceFileCount files)" -ForegroundColor Yellow
Write-Host ""

# --- Step 2: Create destination directory ---
if (-not (Test-Path $destination)) {
    Write-Host "[INFO] Creating destination directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Write-Host "[OK]   Created: $destination" -ForegroundColor Green
} else {
    Write-Host "[INFO] Destination already exists: $destination" -ForegroundColor Yellow
}
Write-Host ""

# --- Step 3: Move files (robocopy for reliability, then delete source) ---
Write-Host "[INFO] Moving files (this may take a moment for 678 MB)..." -ForegroundColor Yellow
Write-Host ""

$robocopyResult = robocopy $source $destination /E /MOVE /NFL /NDL /NJH /NJS /NC /NS

if ($LASTEXITCODE -le 7) {
    Write-Host "[OK]   Files moved successfully." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Robocopy encountered an error (exit code: $LASTEXITCODE). Check above for details." -ForegroundColor Red
    exit 1
}

# --- Step 4: Remove now-empty source folder ---
if (Test-Path $source) {
    $remaining = (Get-ChildItem $source -Recurse -File).Count
    if ($remaining -eq 0) {
        Remove-Item $source -Recurse -Force
        Write-Host "[OK]   Removed empty source folder from OneDrive." -ForegroundColor Green
    } else {
        Write-Host "[WARN] Source folder still has $remaining files — NOT deleted. Please check." -ForegroundColor Red
    }
}

Write-Host ""

# --- Step 5: Verify destination ---
Write-Host "[INFO] Verifying destination..." -ForegroundColor Yellow
$destFileCount = (Get-ChildItem $destination -Recurse -File).Count
$destSize = (Get-ChildItem $destination -Recurse -File | Measure-Object -Property Length -Sum).Sum
$destSizeMB = [math]::Round($destSize / 1MB, 1)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RESULTS                               " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Files at destination : $destFileCount" -ForegroundColor Green
Write-Host "  Size at destination  : $destSizeMB MB" -ForegroundColor Green
Write-Host "  OneDrive space freed : ~$sourceSizeMB MB" -ForegroundColor Green
Write-Host ""
Write-Host "  Destination path:" -ForegroundColor White
Write-Host "  $destination" -ForegroundColor White
Write-Host ""

if ($destFileCount -eq $sourceFileCount) {
    Write-Host "[SUCCESS] All $sourceFileCount files verified at destination." -ForegroundColor Green
} else {
    Write-Host "[WARN] File count mismatch — source had $sourceFileCount, destination has $destFileCount." -ForegroundColor Red
}

Write-Host ""
Write-Host "Done! browser_profiles is now stored locally and NOT syncing to OneDrive." -ForegroundColor Cyan
Write-Host ""
