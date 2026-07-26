$ErrorActionPreference = "Stop"

Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class NativeProcess
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct STARTUPINFO
    {
        public uint cb;
        public string lpReserved;
        public string lpDesktop;
        public string lpTitle;
        public uint dwX;
        public uint dwY;
        public uint dwXSize;
        public uint dwYSize;
        public uint dwXCountChars;
        public uint dwYCountChars;
        public uint dwFillAttribute;
        public uint dwFlags;
        public ushort wShowWindow;
        public ushort cbReserved2;
        public IntPtr lpReserved2;
        public IntPtr hStdInput;
        public IntPtr hStdOutput;
        public IntPtr hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION
    {
        public IntPtr hProcess;
        public IntPtr hThread;
        public uint dwProcessId;
        public uint dwThreadId;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool CreateProcessW(
        string lpApplicationName,
        string lpCommandLine,
        IntPtr lpProcessAttributes,
        IntPtr lpThreadAttributes,
        bool bInheritHandles,
        uint dwCreationFlags,
        IntPtr lpEnvironment,
        string lpCurrentDirectory,
        ref STARTUPINFO lpStartupInfo,
        out PROCESS_INFORMATION lpProcessInformation);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool CloseHandle(IntPtr hObject);
}
"@

$startupInfo = New-Object NativeProcess+STARTUPINFO
$startupInfo.cb = [System.Runtime.InteropServices.Marshal]::SizeOf($startupInfo)
$startupInfo.dwFlags = 1
$startupInfo.wShowWindow = 0

$processInfo = New-Object NativeProcess+PROCESS_INFORMATION
$cmdExe = "C:\Windows\System32\cmd.exe"
$startScript = Join-Path $PSScriptRoot "start-frontend-local.cmd"
$commandLine = '"{0}" /c call "{1}"' -f $cmdExe, $startScript
$workingDirectory = $PSScriptRoot

$DETACHED_PROCESS = 0x00000008
$CREATE_NEW_PROCESS_GROUP = 0x00000200
$CREATE_BREAKAWAY_FROM_JOB = 0x01000000
$CREATE_NO_WINDOW = 0x08000000
$flags = $DETACHED_PROCESS -bor $CREATE_NEW_PROCESS_GROUP -bor $CREATE_BREAKAWAY_FROM_JOB -bor $CREATE_NO_WINDOW

$ok = [NativeProcess]::CreateProcessW(
    $cmdExe,
    $commandLine,
    [IntPtr]::Zero,
    [IntPtr]::Zero,
    $false,
    $flags,
    [IntPtr]::Zero,
    $workingDirectory,
    [ref]$startupInfo,
    [ref]$processInfo)

if (-not $ok) {
    $errorCode = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    throw "CreateProcessW failed with Win32 error $errorCode"
}

[NativeProcess]::CloseHandle($processInfo.hThread) | Out-Null
[NativeProcess]::CloseHandle($processInfo.hProcess) | Out-Null
Write-Output $processInfo.dwProcessId
