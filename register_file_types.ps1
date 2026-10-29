# Register .umbra as an UmbraForge project file (current user only).
#
# No installer and no administrator rights needed. Double-clicking a project
# then launches UmbraForge.pyw with the file, and the project opens with every
# layer still editable. PNG and other image formats are untouched.
#
#   powershell -ExecutionPolicy Bypass -File .\register_file_types.ps1
#   powershell -ExecutionPolicy Bypass -File .\register_file_types.ps1 -Remove

param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$progId = "UmbraForge.Project"
$extensionKey = "HKCU:\Software\Classes\.umbra"
$progIdKey = "HKCU:\Software\Classes\$progId"

if ($Remove) {
    Remove-Item -Path $extensionKey -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $progIdKey -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Removed the .umbra file association." -ForegroundColor Yellow
    exit 0
}

$launcher = Join-Path $root "UmbraForge.pyw"
$exe = Join-Path $root "UmbraForge.exe"
$icon = Join-Path $root "assets\umbraforge.ico"
if (Test-Path $exe) {
    $openCommand = "`"$exe`" `"%1`""
    $launcherLabel = $exe
} else {
    if (-not (Test-Path $launcher)) {
        throw "Could not find UmbraForge.exe or $launcher. Run this from the UmbraForge folder."
    }

    $pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
    if (-not (Test-Path $pythonw)) {
        $pythonw = Join-Path $root ".venv\Scripts\python.exe"
    }
    if (-not (Test-Path $pythonw)) {
        $command = Get-Command pythonw.exe -ErrorAction SilentlyContinue
        if ($command) {
            $pythonw = $command.Source
        } else {
            $command = Get-Command python.exe -ErrorAction SilentlyContinue
            if ($command) {
                $pythonw = $command.Source
            }
        }
    }
    if (-not (Test-Path $pythonw)) {
        throw "Could not find Python. Create the .venv or install Python first."
    }
    $openCommand = "`"$pythonw`" `"$launcher`" `"%1`""
    $launcherLabel = $pythonw
}

New-Item -Path $extensionKey -Force | Out-Null
Set-Item -Path $extensionKey -Value $progId
New-ItemProperty -Path $extensionKey -Name "Content Type" `
    -Value "application/x-umbraforge-project" -PropertyType String -Force | Out-Null

New-Item -Path $progIdKey -Force | Out-Null
Set-Item -Path $progIdKey -Value "UmbraForge project"
New-ItemProperty -Path $progIdKey -Name "FriendlyTypeName" `
    -Value "UmbraForge project" -PropertyType String -Force | Out-Null

$iconKey = Join-Path $progIdKey "DefaultIcon"
New-Item -Path $iconKey -Force | Out-Null
if (Test-Path $icon) {
    Set-Item -Path $iconKey -Value "`"$icon`",0"
}

$commandKey = Join-Path $progIdKey "shell\open\command"
New-Item -Path $commandKey -Force | Out-Null
Set-Item -Path $commandKey -Value $openCommand

# Tell Explorer that the association changed, so icons update without a reboot.
try {
    Add-Type -Namespace Win32 -Name Shell -MemberDefinition @"
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(int eventId, int flags, System.IntPtr item1, System.IntPtr item2);
"@
    [Win32.Shell]::SHChangeNotify(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)
} catch {
    # The association still works; Explorer just refreshes on its own later.
}

Write-Host "Registered .umbra as an UmbraForge project." -ForegroundColor Green
Write-Host "Double-click a project, or drag one onto UmbraForge, to keep editing."
Write-Host "Launcher: $launcherLabel"
Write-Host "Open command: $openCommand"
