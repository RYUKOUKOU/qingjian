# 仅在隔离的 Windows CI runner 上安装、重装和卸载，核对列表与用户数据保留。
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$setup = @(Get-ChildItem (Join-Path $repo 'target\installer\*setup.exe'))
if ($setup.Count -ne 1) { throw 'Expected exactly one installer' }
$installDir = Join-Path $env:ProgramFiles 'Qingjian'
$uninstaller = Join-Path $installDir 'unins000.exe'
$marker = Join-Path $installDir 'offline-install.ini'
$userDir = Join-Path $env:APPDATA 'Qingjian'
New-Item -ItemType Directory -Path $userDir -Force | Out-Null
$sentinel = Join-Path $userDir 'installer-regression.txt'
Set-Content $sentinel 'preserve-user-data' -Encoding ascii
function Assert-NoUninstallEntry {
    $key = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A7E3C1F2-5B94-4D6A-9C0E-2F8B1D3A6E70}_is1'
    foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64, [Microsoft.Win32.RegistryView]::Registry32)) {
        foreach ($hive in @([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryHive]::CurrentUser)) {
            $root = [Microsoft.Win32.RegistryKey]::OpenBaseKey($hive, $view)
            try {
                $entry = $root.OpenSubKey($key)
                if ($entry) { $entry.Dispose(); throw 'Unexpected uninstall-list registration' }
            } finally { $root.Dispose() }
        }
    }
}
for ($attempt = 1; $attempt -le 2; $attempt++) {
    $log = Join-Path $env:RUNNER_TEMP "qingjian-install-$attempt.log"
    $process = Start-Process $setup[0].FullName -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', "/LOG=`"$log`"" -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Installation failed: $($process.ExitCode)" }
    if (!(Test-Path $uninstaller) -or !(Test-Path $marker)) { throw 'Missing uninstaller or version marker' }
    Assert-NoUninstallEntry
    if ($attempt -eq 1) {
        # 模拟旧安装器留下的同目录条目，重装必须清除。
        foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64, [Microsoft.Win32.RegistryView]::Registry32)) {
            $root = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine, $view)
            try {
                $entry = $root.CreateSubKey('Software\Microsoft\Windows\CurrentVersion\Uninstall\{A7E3C1F2-5B94-4D6A-9C0E-2F8B1D3A6E70}_is1')
                try { $entry.SetValue('InstallLocation', $installDir) } finally { $entry.Dispose() }
            } finally { $root.Dispose() }
        }
    }
    if ($attempt -eq 2 -and !(Select-String -Path $log -Pattern '安装目录发现旧版' -Encoding UTF8 -Quiet)) { throw 'Reinstall did not detect existing Server' }
}
$process = Start-Process $uninstaller -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Uninstallation failed: $($process.ExitCode)" }
Assert-NoUninstallEntry
if (Test-Path (Join-Path $installDir 'qingjian-server.exe')) { throw 'Server survived uninstallation' }
if ((Get-Content $sentinel -Raw).Trim() -ne 'preserve-user-data') { throw 'User data changed' }
Write-Host 'PASS: installation, directory-based reinstall, hidden app entry, uninstallation, user-data preservation'
