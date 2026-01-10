try {
    Restart-Service -Name SunshineService
} catch {
    Write-Error $_
}
