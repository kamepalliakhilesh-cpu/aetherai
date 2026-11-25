# Demo Backup Video Script
# Records the screen during the hackathon demo as a backup in case live demo fails.
# Run from project root: powershell -ExecutionPolicy Bypass -File scripts/record_demo.ps1
#
# Usage:
#   .\record_demo.ps1                # Records for 3 minutes
#   .\record_demo.ps1 -Duration 120  # Records for 2 minutes
#   .\record_demo.ps1 -Output "my_demo.mp4"  # Custom output path

param(
    [int]$Duration = 180,  # Default 3 minutes
    [string]$Output = "data/demo_backup.mp4"
)

# Create data directory
$dataDir = Split-Path -Parent $Output
if (!(Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}

Write-Host "=" -ForegroundColor Cyan
Write-Host "  AETHER.AI-PC DEMO BACKUP RECORDER" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Duration: $Duration seconds" -ForegroundColor White
Write-Host "  Output:   $Output" -ForegroundColor White
Write-Host ""
Write-Host "  Press Ctrl+C to stop early" -ForegroundColor Yellow
Write-Host ""

# Check for ffmpeg
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (!$ffmpeg) {
    Write-Host "  [WARN] ffmpeg not found. Trying Windows built-in screen recorder..." -ForegroundColor Yellow

    # Use PowerShell screen capture
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)

    $endTime = (Get-Date).AddSeconds($Duration)
    $frameCount = 0

    Write-Host "  Recording... ($Duration seconds)" -ForegroundColor Green

    while ((Get-Date) -lt $endTime) {
        $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $bitmap.Save("$Output.frame$frameCount.png")
        $frameCount++
        Start-Sleep -Milliseconds 500
    }

    $graphics.Dispose()
    $bitmap.Dispose()

    Write-Host ""
    Write-Host "  Captured $frameCount frames to $Output.frame*.png" -ForegroundColor Green
    Write-Host "  Use ffmpeg to convert: ffmpeg -framerate 2 -i '$Output.frame%d.png' $Output" -ForegroundColor Yellow
}
else {
    Write-Host "  [OK] ffmpeg found - starting recording" -ForegroundColor Green

    $ffmpegArgs = @(
        "-f", "gdigrab",
        "-framerate", "30",
        "-i", "desktop",
        "-t", "$Duration",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-y",
        $Output
    )

    Write-Host "  Running: ffmpeg $($ffmpegArgs -join ' ')" -ForegroundColor DarkGray
    & ffmpeg @ffmpegArgs

    Write-Host ""
    Write-Host "  [OK] Recording saved to: $Output" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" -ForegroundColor Cyan
Write-Host "  DONE" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan