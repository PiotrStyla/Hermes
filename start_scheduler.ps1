Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'src\.cli\s+scheduler\s+start' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Seconds 1
Start-Process `
    -FilePath "C:\Users\Hipek\CascadeProjects\windsurf-project-2\.venv\Scripts\pythonw.exe" `
    -ArgumentList "-m", "src.cli", "scheduler", "start", "--board-review-time", "10:00", "--board-review-timezone", "Europe/Warsaw" `
    -WorkingDirectory "C:\Users\Hipek\CascadeProjects\windsurf-project-2" `
    -WindowStyle Hidden
