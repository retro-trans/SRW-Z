param([int]$BootWait = 29)
Start-Sleep -Seconds $BootWait
$drive = "E:\Projects\SRW Z\_work\tools\drive.ps1"
& $drive -Keys "Return,1500,L,1500,Return,1500,L,2600" | Out-Null
& "E:\Projects\SRW Z\_work\tools\capture.ps1" -Out "E:\Projects\SRW Z\_work\analysis\hwexp_scr.png" | Out-Null
Write-Output "at char-select"
