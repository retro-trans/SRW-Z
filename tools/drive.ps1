# Send keystrokes to the PCSX2 window and optionally take a screenshot.
# Usage: drive.ps1 -Keys "Return,2000,X,1500" [-Shot]
#   Comma list alternates key names and post-press delays (ms).
param(
    [string]$Keys = "",
    [switch]$Shot,
    [int]$SettleMs = 400
)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern IntPtr FindWindow(string cls, string title);
    [DllImport("user32.dll", CharSet=CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder sb, int max);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr lp);
    public delegate bool EnumProc(IntPtr hWnd, IntPtr lp);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
    public const uint KEYUP = 0x2;
}
"@

# find the PCSX2 window via its process
$proc = Get-Process -Name "pcsx2-qt" -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $proc) { Write-Output "NO PCSX2 WINDOW"; exit 1 }
$script:hwnd = $proc.MainWindowHandle

$sb = New-Object System.Text.StringBuilder 256
[Win32]::GetWindowText($script:hwnd, $sb, 256) | Out-Null
Write-Output ("window: " + $sb.ToString())
[Win32]::SetForegroundWindow($script:hwnd) | Out-Null
Start-Sleep -Milliseconds $SettleMs

$VK = @{
    "Return"=0x0D; "Backspace"=0x08; "Up"=0x26; "Down"=0x28; "Left"=0x25; "Right"=0x27;
    "K"=0x4B; "L"=0x4C; "I"=0x49; "J"=0x4A; "Q"=0x51; "E"=0x45; "F8"=0x77; "1"=0x31; "2"=0x32;
    "F1"=0x70; "F2"=0x71; "F3"=0x72
}

if ($Keys) {
    $parts = $Keys.Split(",")
    for ($i = 0; $i -lt $parts.Length; $i += 2) {
        $k = $parts[$i].Trim()
        $delay = if ($i + 1 -lt $parts.Length) { [int]$parts[$i + 1] } else { 500 }
        if (-not $VK.ContainsKey($k)) { Write-Output "unknown key $k"; continue }
        $v = [byte]$VK[$k]
        # arrows are extended keys; without the flag they read as numpad
        $ext = if ($k -in @("Up","Down","Left","Right")) { [uint32]1 } else { [uint32]0 }
        [Win32]::keybd_event($v, 0, $ext, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 150
        [Win32]::keybd_event($v, 0, ($ext -bor [Win32]::KEYUP), [UIntPtr]::Zero)
        Write-Output ("pressed " + $k)
        Start-Sleep -Milliseconds $delay
    }
}

if ($Shot) {
    [Win32]::keybd_event(0x77, 0, 0, [UIntPtr]::Zero)   # F8
    Start-Sleep -Milliseconds 120
    [Win32]::keybd_event(0x77, 0, [Win32]::KEYUP, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 700
    $snap = Get-ChildItem "$env:USERPROFILE\Documents\PCSX2\snaps" -Filter *.png -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime | Select-Object -Last 1
    if ($snap) { Write-Output ("shot: " + $snap.FullName) } else { Write-Output "no screenshot found" }
}
