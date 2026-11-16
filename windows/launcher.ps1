# Se ejecuta al iniciar sesion en Windows. Espera a que el disco con Universia Control este conectado
# (sin importar que letra tenga) y lanza iniciar.ps1 si no esta corriendo.
while ($true) {
  $script = $null
  foreach ($d in (Get-PSDrive -PSProvider FileSystem)) {
    $p = Join-Path $d.Root "universia-control\windows\iniciar.ps1"
    if (Test-Path $p) { $script = $p; break }
  }
  if ($script) {
    $running = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
      Where-Object { $_.CommandLine -like "*universia-control*iniciar.ps1*" }
    if (-not $running) {
      Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$script`""
    }
  }
  Start-Sleep 30
}
