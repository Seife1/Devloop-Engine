# LearnLoop Testing Workflow
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Test LearnLoop with Your Real Projects" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Start Dashboard
Write-Host "Starting Dashboard..." -ForegroundColor Yellow
$dashboard = Start-Process python -ArgumentList "-m learnloop.dashboard" -PassThru -WindowStyle Hidden
Write-Host "Dashboard PID: $($dashboard.Id)" -ForegroundColor Green
Write-Host "Access: http://localhost:8765" -ForegroundColor Green

Write-Host "`nHow to test with your real projects:" -ForegroundColor Cyan
Write-Host "1. Navigate to your project folder" -ForegroundColor Gray
Write-Host "2. Run: learnloop init" -ForegroundColor Gray
Write-Host "3. Work with AI as usual (make commits!)" -ForegroundColor Gray
Write-Host "4. Get insights from dashboard" -ForegroundColor Gray

Write-Host "`nExample workflow:" -ForegroundColor Yellow
Write-Host "cd path/to/your/project" -ForegroundColor Gray
Write-Host "learnloop init" -ForegroundColor Gray
Write-Host "learnloop backfill  # Optional: backfill existing commits" -ForegroundColor Gray
Write-Host "`nThen work normally:" -ForegroundColor Gray
Write-Host "# AI writes code in main.py" -ForegroundColor Gray
Write-Host "git add main.py" -ForegroundColor Gray
Write-Host "git commit -m 'Add feature by AI'" -ForegroundColor Gray
Write-Host "`nTrack the work:" -ForegroundColor Gray
Write-Host "learnloop briefing  # Get session update" -ForegroundColor Gray
Write-Host "learnloop review    # Review knowledge" -ForegroundColor Gray

Write-Host "`nTest HTTP deployment:" -ForegroundColor Yellow
Write-Host "pip install -r requirements_http.txt" -ForegroundColor Gray
Write-Host "python learnloop_http.py" -ForegroundColor Gray
Write-Host "Access: http://localhost:8000" -ForegroundColor Gray

Write-Host "`nKey LearnLoop features to test:" -ForegroundColor Cyan
Write-Host "✅ Project initialization" -ForegroundColor Green
Write-Host "✅ Git commit tracking" -ForegroundColor Green
Write-Host "✅ Dashboard visualization" -ForegroundColor Green
Write-Host "✅ Session briefings" -ForegroundColor Green
Write-Host "✅ Knowledge item management" -ForegroundColor Green
Write-Host "✅ Spaced repetition reviews" -ForegroundColor Green
Write-Host "✅ HTTP/SSE deployment" -ForegroundColor Green

Write-Host "`nReady for production when:" -ForegroundColor Yellow
Write-Host "1. You've used it on 2-3 real projects" -ForegroundColor Gray
Write-Host "2. Dashboard provides useful insights" -ForegroundColor Gray
Write-Host "3. HTTP deployment works reliably" -ForegroundColor Gray
Write-Host "4. You understand the learning workflow" -ForegroundColor Gray

Write-Host "`nHappy testing! 🚀" -ForegroundColor Green
