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

function Install-MinGW64 {
    Write-Log "Configuring MinGW64..." -Level Info

    Write-Log "Fetching lastest MinGW64 download link at https://winlibs.com/..." -Level Info
    $WinlibsResponse = Invoke-WebRequest -Uri "https://winlibs.com/" -UseBasicParsing
    $MinGW64DownloadLink = ($WinlibsResponse.Links | Where-Object {
        $_.href -like "*winlibs-x86_64-posix-seh-gcc-*-mingw-w64ucrt-*.zip"
    } | Select-Object -First 1).href

    if (-not $MinGW64DownloadLink) {
        throw "Could not find a valid MinGW64 download link on WinLibs."
    }
    Write-Log "Done." -Level Success

    $MinGW64ZipFile = Join-Path $TmpDir "mingw64.zip"
    Write-Log "Downloading MinGW64 to $MinGW64ZipFile at $MinGW64DownloadLink..." -Level Info
    Invoke-WebRequest -Uri $MinGW64DownloadLink -UseBasicParsing -OutFile $MinGW64ZipFile
    Write-Log "Done." -Level Success

    Write-Log "Extracting MinGW64 to $RootDir\mingw64..." -Level Info
    & $SevenZipExe x $MinGW64ZipFile -o"$RootDir" -y
    Write-Log "Done." -Level Success

    Write-Log "Configuring environment variables..." -Level Info
    $MinGW64BinDir = Join-Path $RootDir "mingw64\bin"
    do {
        $Confirm = Read-Host "Add $MinGW64BinDir to User Path? (Y/N)"
        $Confirm = $Confirm.ToUpper()
    } while ($Confirm -notin @("Y", "N"))

    if ($Confirm -eq "Y") {
        Write-Log "Adding $MinGW64BinDir to User Path..." -Level Warning
        Add-UserPath -Path $MinGW64BinDir
        Write-Log "Done." -Level Success
    }
    else {
        Write-Log "Adding was canceled. You may need to manually configure User Path." -Level Warning
    }

    Write-Log "Successfully configure MinGW64." -Level Success
}

function Install-UV {
    $UVDir = "$RootDir\uv"
    $UVBinDir = "$UVDir\bin"
    $UVCacheDir = "$UVDir\cache" # UV_CACHE_DIR
    $UVCredentialsDir = "$UVDir\credentials" # UV_CREDENTIALS_DIR
    $UVInstallDir = "$UVDir\install" # UV_INSTALL_DIR
    $UVPythonBinDir = "$UVDir\python-bin" # UV_PYTHON_BIN_DIR
    $UVPythonCacheDir = "$UVDir\python-cache" # UV_PYTHON_CACHE_DIR
    $UVPythonInstallDir = "$UVDir\python-install" # UV_PYTHON_INSTALL_DIR
    $UVToolBinDir = "$UVDir\tool-bin" # UV_TOOL_BIN_DIR
    $UVToolDir = "$UVDir\tool" # UV_TOOL_DIR

    Write-Log "Configuring UV..." -Level Info

    foreach ($Path in $UVDir, $UVBinDir, $UVCacheDir, $UVCredentialsDir, $UVInstallDir, $UVPythonBinDir, $UVPythonCacheDir, $UVPythonInstallDir, $UVToolBinDir, $UVToolDir) {
        Write-Log "Checking and creating directory: $Path." -Level Info
        New-Directory -Path $Path
        Write-Log "Done." -Level Success
    }

    $UVZipFile = Join-Path $TmpDir "uv.zip"
    $UVDownloadLink = "https://github.com/astral-sh/uv/releases/latest/download/uv-i686-pc-windows-msvc.zip"
    Write-Log "Downloading UV to $UVZipFile at $UVDownloadLink..." -Level Info
    Invoke-WebRequest -Uri $UVDownloadLink -UseBasicParsing -OutFile $UVZipFile
    Write-Log "Done." -Level Success

    Write-Log "Extracting UV to $UVBinDir..." -Level Info
    & $SevenZipExe x $UVZipFile -o"$UVBinDir" -y
    Write-Log "Done." -Level Success

    Write-Log "Configuring environment variables..." -Level Info
    $ModifiedEnvVars = @"
Following variables will add to User environment:
UV_CACHE_DIR=$UVCacheDir
UV_CREDENTIALS_DIR=$UVCredentialsDir
UV_INSTALL_DIR=$UVInstallDir
UV_PYTHON_BIN_DIR=$UVPythonBinDir
UV_PYTHON_CACHE_DIR=$UVPythonCacheDir
UV_PYTHON_INSTALL_DIR=$UVPythonInstallDir
UV_TOOL_BIN_DIR=$UVToolBinDir
UV_TOOL_DIR=$UVToolDir
Path+=Path;$UVBinDir;$UVPythonBinDir
"@
    Write-Log $ModifiedEnvVars -Level Warning
    do {
        $Confirm = Read-Host "Confirm? (Y/N)"
        $Confirm = $Confirm.ToUpper()
    } while ($Confirm -notin @("Y", "N"))

    if ($Confirm -eq "Y") {
        foreach ($var in $UVBinDir, $UVPythonBinDir) {
            Write-Log "Adding $var to User Path..." -Level Warning
            Add-UserPath -Path $var
            Write-Log "Done." -Level Success
        }

        $UVEnvVarsDict = [ordered]@{
            "UV_CACHE_DIR" = $UVCacheDir
            "UV_CREDENTIALS_DIR" = $UVCredentialsDir
            "UV_INSTALL_DIR" = $UVInstallDir
            "UV_PYTHON_BIN_DIR" = $UVPythonBinDir
            "UV_PYTHON_CACHE_DIR" = $UVPythonCacheDir
            "UV_PYTHON_INSTALL_DIR" = $UVPythonInstallDir
            "UV_TOOL_BIN_DIR" = $UVToolBinDir
            "UV_TOOL_DIR" = $UVToolDir
        }
        foreach ($item in $UVEnvVarsDict.Keys) {
            $K = $item
            $V = $UVEnvVarsDict[$item]
            Write-Log "Adding $K=$V to User environments..." -Level Warning
            [System.Environment]::SetEnvironmentVariable($K, $V, "User")
            Write-Log "Done." -Level Success
        }
    } else {
        Write-Log "Adding was canceled. You may need to manually configure User Path." -Level Warning
    }

    Write-Log "Successfully configure UV." -Level Success
}

function Install-Git {
    Write-Log "Configuring Git..." -Level Info

    Write-Log "Fetching lastest PortableGit download link at https://git-scm.com/install/windows..." -Level Info
    $GitScmResponse = Invoke-WebRequest -Uri "https://git-scm.com/install/windows" -UseBasicParsing
    $PortableGitDownloadLink = ($GitScmResponse.Links | Where-Object {
        $_.href -like "*PortableGit-*-64-bit.7z.exe"
    } | Select-Object -First 1).href

    if (-not $PortableGitDownloadLink) {
        throw "Could not find a valid PortableGit download link."
    }
    Write-Log "Done." -Level Success

    $PortableGitExeFile = Join-Path $TmpDir "portable-git.exe"
    Write-Log "Downloading PortableGit to $PortableGitExeFile at $PortableGitDownloadLink..." -Level Info
    Invoke-WebRequest -Uri $PortableGitDownloadLink -UseBasicParsing -OutFile $PortableGitExeFile
    Write-Log "Done." -Level Success

    $GitDir = Join-Path $RootDir "git"
    Write-Log "Extracting Git to $GitDir..." -Level Info
    & $PortableGitExeFile -o $GitDir -y
    Write-Log "Done." -Level Success
    Write-Log "YOU NEED TO WAIT A FEW SECONDS AFTER EXTRACTION" -Level Warning

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
    Install-MinGW64
    Install-UV
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
