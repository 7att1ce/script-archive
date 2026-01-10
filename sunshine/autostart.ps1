try {
    $SunshineService = Get-CimInstance -ClassName Win32_Service | Where-Object {
        $_.Name -eq "SunshineService"
    }

    if ($SunshineService.StartMode -eq "Auto") {
        Set-Service -Name SunshineService -StartupType Manual
    } elseif ($SunshineService.StartMode -eq "Manual") {
        Set-Service -Name SunshineService -StartupType Automatic
    }
} catch {
    Write-Error $_
}
