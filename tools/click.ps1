# Click at a point in the PCSX2 window (client-relative), or type text / a menu.
# Usage: click.ps1 -X 178 -Y 42        # click client (178,42)
#        click.ps1 -Text "0x1FF0000"   # type a string
param([int]$X = -1, [int]$Y = -1, [string]$Text = "", [switch]$Enter)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class M {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
    public struct R { public int L, T, Rt, B; }
    public const uint LDOWN=0x2, LUP=0x4;
}
"@
Add-Type -AssemblyName System.Windows.Forms

$proc = Get-Process -Name "pcsx2-qt" -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $proc) { "NO WINDOW"; exit 1 }
$h = $proc.MainWindowHandle
[M]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 300

# window-rect-relative coords (same system as capture.ps1)
$r = New-Object M+R
[M]::GetWindowRect($h, [ref]$r) | Out-Null

if ($X -ge 0 -and $Y -ge 0) {
    $sx = $r.L + $X; $sy = $r.T + $Y
    [M]::SetCursorPos($sx, $sy) | Out-Null
    Start-Sleep -Milliseconds 150
    [M]::mouse_event([M]::LDOWN,0,0,0,[UIntPtr]::Zero)
    Start-Sleep -Milliseconds 60
    [M]::mouse_event([M]::LUP,0,0,0,[UIntPtr]::Zero)
    "clicked window ($X,$Y) -> screen ($sx,$sy)  [win L=$($r.L) T=$($r.T)]"
    Start-Sleep -Milliseconds 300
}
if ($Text) {
    [System.Windows.Forms.SendKeys]::SendWait($Text)
    "typed: $Text"
}
if ($Enter) { [System.Windows.Forms.SendKeys]::SendWait("{ENTER}") }
