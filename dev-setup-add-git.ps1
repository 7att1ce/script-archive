# Stop execution on any error
$ErrorActionPreference = "Stop"
# Disable the Invoke-WebRequest progress bar
$ProgressPreference = 'SilentlyContinue'
# Configure proxy settings (optional).
$PSDefaultParameterValues = @{ "Invoke-WebRequest:Proxy" = "http://127.0.0.1:10000" }
# Modify $RootDir as work directory
$RootDir = "D:\cli-programs"
$TmpDir = Join-Path $RootDir "tmp"
$SevenZipExe = "C:\Program Files\7-Zip\7z.exe"

function Write-Log {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [Parameter(Mandatory = $true)]
        [ValidateSet("Info", "Success", "Warning", "Error")]
        [string]$Level
    )

    switch ($Level) {
        "Info" { Write-Host "[-] $Message" -ForegroundColor Cyan }
        "Success" { Write-Host "[+] $Message" -ForegroundColor Green }
        "Warning" { Write-Host "[!] $Message" -ForegroundColor Yellow }
        "Error" { Write-Host "[X] $Message" -ForegroundColor Red }
    }
}

function New-Directory {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

# Reference: https://stackoverflow.com/questions/76871462/set-itemproperty-is-failing-to-add-item-to-path/76876384#76876384
function Add-UserPath {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $RegPath = "registry::HKEY_CURRENT_USER\Environment"
    $CurrentDirs = (Get-Item -LiteralPath $RegPath).GetValue("Path", "", "DoNotExpandEnvironmentNames") -split ";" -ne ""

    if ($Path -in $CurrentDirs) {
        Write-Log "$Path already on User Path, skip." -Level Info
        return
    }

    $NewUserPath = ($CurrentDirs + $Path) -join ";"
    Set-ItemProperty -Type ExpandString -LiteralPath $RegPath Path $NewUserPath

    # Broadcast WM_SETTINGCHANGE
    $DummyName = New-Guid
    [System.Environment]::SetEnvironmentVariable($DummyName, 'dummy', 'User')
    [System.Environment]::SetEnvironmentVariable($DummyName, $null, 'User')
}

function Initialize-Installation {
    Write-Log "Verifying 7-Zip installation..." -Level Info
    if (-not (Test-Path -Path $SevenZipExe)) {
        throw "7-Zip not found at $SevenZipExe. Please install it at https://www.7-zip.org/ first."
    }
    Write-Log "Done." -Level Success

    foreach ($Path in $RootDir, $TmpDir) {
        Write-Log "Checking and creating directory: $Path." -Level Info
        New-Directory -Path $Path
        Write-Log "Done." -Level Success
    }
}

# New adding git function
# Will merge, but not test
function Install-Git {
    Write-Log "Configuring Git..." -Level Info

    Write-Log "Fetching lastest PortableGit download link at https://git-scm.com/install/windows..." -Level Info
    $GitScmResponse = Invoke-WebRequest -Uri "https://git-scm.com/install/windows" -UseBasicParsing
    $PortableGitDownloadLink = ($GitScmResponse.Links | Where-Object {
        $_.href -like "*PortableGit-*-64-bit.7z.exe"
    }).href

    if (-not $MinGW64DownloadLink) {
        throw "Could not find a valid PortableGit download link."
    }
    Write-Log "Done." -Level Success

    $PortableGitExeFile = Join-Path $TmpDir "portable-git.exe"
    Write-Log "Downloading PortableGit to $PortableGitExeFile at $PortableGitDownloadLink..." -Level Info
    Invoke-WebRequest -Uri $PortableGitDownloadLink -UseBasicParsing -OutFile $PortableGitExeFile
    Write-Log "Done." -Level Success

    $GitDir = Join-Path $RootDir "git"
    Write-Log "Extracting Git to $GitDir..." -Level Info
    & $PortableGitExeFile -y -gm2 -InstallPath=$GitDir
    Write-Log "Done." -Level Success

    Write-Log "Configuring environment variables..." -Level Info
    $GitBinDir = Join-Path $GitDir "cmd"
    do {
        $Confirm = Read-Host "Add $GitBinDir to User Path? (Y/N)"
        $Confirm = $Confirm.ToUpper()
    } while ($Confirm -notin @("Y", "N"))

    if ($Confirm -eq "Y") {
        Write-Log "Adding $GitBinDir to User Path..." -Level Warning
        Add-UserPath -Path $GitBinDir
        Write-Log "Done." -Level Success
    }
    else {
        Write-Log "Adding was canceled. You may need to manually configure User Path." -Level Warning
    }

    Write-Log "Successfully configure Git." -Level Success
}

function Install-All {
    Initialize-Installation
    Install-Git

    Write-Log "Deleting $TmpDir..." -Level Info
    Remove-Item $TmpDir -Recurse -Force
    Write-Log "Done." -Level Success

    Write-Log "If it doesn't work, please log out or reboot." -Level Info
}

try {
    Install-All
} catch {
    Write-Log $_ -Level Error
}
