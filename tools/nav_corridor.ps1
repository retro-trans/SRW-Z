# Wait for boot, then drive from copyright screen to the Jerid corridor line.
param([int]$BootWait = 29)
Start-Sleep -Seconds $BootWait
$drive = "E:\Projects\SRW Z\_work\tools\drive.ps1"
# copyright -> title -> START -> char-select
& $drive -Keys "Return,1500,L,1500,Return,1500,L,2600" | Out-Null
# select female (Setsuko) -> profile
& $drive -Keys "Right,1200,L,2200" | Out-Null
# confirm profile -> start scenario (narration begins)
& $drive -Keys "Down,600,Down,600,Down,600,L,3000,Return,2600,L,2200" | Out-Null
# skip narration screens (each L advances one block)
& $drive -Keys "L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,2000" | Out-Null
& "E:\Projects\SRW Z\_work\tools\capture.ps1" -Out "E:\Projects\SRW Z\_work\analysis\hw_nav.png" | Out-Null
Write-Output "nav done"
