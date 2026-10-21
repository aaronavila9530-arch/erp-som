$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Users\aaron\Documents\RECONIS\tools\run_aai_outlook_fiscal_sync.ps1"'
Set-ScheduledTask -TaskName 'RECONIS Outlook Fiscal AAI' -Action $action
