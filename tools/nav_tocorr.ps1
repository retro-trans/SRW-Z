# From char-select, drive to the corridor Jerid line (game already booted).
$drive = "E:\Projects\SRW Z\_work\tools\drive.ps1"
& $drive -Keys "Right,1200,L,2200" | Out-Null
& $drive -Keys "Down,600,Down,600,Down,600,L,3000,Return,2600,L,2200" | Out-Null
& $drive -Keys "L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,1400,L,2000" | Out-Null
& "E:\Projects\SRW Z\_work\tools\capture.ps1" -Out "E:\Projects\SRW Z\_work\analysis\hwexp_corr.png" | Out-Null
Write-Output "at corridor"
