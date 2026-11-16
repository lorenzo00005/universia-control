# Universia Control - arranque en Windows (se ejecuta desde el disco externo).
# Levanta Docker, restaura la base si hace falta, arranca todo, publica el link y hace respaldos.
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Log = Join-Path $Root "iniciar.log"
$Compose = @("compose", "-f", "docker-compose.yml", "-f", "docker-compose.usb.yml")

function Log($msg) {
  $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
  Add-Content -Path $Log -Value $line
  Write-Host $line
}
function Dc { & docker @Compose @args }

function EnvValue($name, $default) {
  $f = Join-Path $Root ".env"
  if (Test-Path $f) {
    $m = Select-String -Path $f -Pattern ("^{0}=(.*)$" -f $name) | Select-Object -First 1
    if ($m) { return $m.Matches[0].Groups[1].Value.Trim() }
  }
  return $default
}
$PgUser = EnvValue "POSTGRES_USER" "rcm"
$PgDb = EnvValue "POSTGRES_DB" "rcm"

function Wait-Docker {
  $null = docker info 2>&1
  if ($LASTEXITCODE -eq 0) { return $true }
  $dd = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
  if (Test-Path $dd) { Log "Abriendo Docker Desktop..."; Start-Process $dd }
  for ($i = 0; $i -lt 120; $i++) {
    Start-Sleep 5
    $null = docker info 2>&1
    if ($LASTEXITCODE -eq 0) { return $true }
  }
  return $false
}

function Backup-Db {
  $dir = Join-Path $Root "backups"
  New-Item -ItemType Directory -Force $dir | Out-Null
  $file = "backups\rcm-{0}.dump" -f (Get-Date -Format "yyyyMMdd-HHmm")
  Dc exec -T postgres pg_dump -U $PgUser -d $PgDb -Fc -f /tmp/rcm.dump
  if ($LASTEXITCODE -ne 0) { Log "Respaldo: fallo pg_dump"; return }
  Dc cp postgres:/tmp/rcm.dump $file
  if ($LASTEXITCODE -eq 0) {
    Log "Respaldo guardado: $file"
    Get-ChildItem $dir -Filter "rcm-*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 14 | Remove-Item -Force
  }
}

function Restore-IfEmpty {
  # Cuenta usuarios; si la tabla no existe (base nueva) da 0. Evita saltear la restauracion si el backend ya creo tablas vacias.
  $q = "select case when to_regclass('public.users') is null then 0 else (xpath('/row/c/text()', query_to_xml('select count(*) as c from public.users', false, true, '')))[1]::text::int end"
  $n = (Dc exec -T postgres psql -U $PgUser -d $PgDb -tAc $q | Out-String).Trim()
  if ($n -ne "0") { return }
  $last = Get-ChildItem (Join-Path $Root "backups") -Filter "rcm-*.dump" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $last) { Log "Base vacia y sin respaldos: arranca desde cero."; return }
  Log "Base vacia: restauro $($last.Name)"
  Dc cp ("backups\" + $last.Name) postgres:/tmp/restore.dump
  Dc exec -T postgres pg_restore -U $PgUser -d $PgDb --no-owner --clean --if-exists /tmp/restore.dump
}

Log "Iniciando Universia Control desde $Root"
if (-not (Wait-Docker)) { Log "Docker no arranco. Abri Docker Desktop y volve a intentar."; exit 1 }

Dc up -d postgres
for ($i = 0; $i -lt 60; $i++) {
  Dc exec -T postgres pg_isready -U $PgUser -d $PgDb *> $null
  if ($LASTEXITCODE -eq 0) { break }
  Start-Sleep 2
}
Restore-IfEmpty
Dc up -d --build
Log "Servicios levantados."

$lastUrl = ""
$lastBackup = Get-Date
while ($true) {
  if (-not (Test-Path (Join-Path $Root "docker-compose.yml"))) {
    Log "El disco se desconecto: detengo los servicios."
    docker ps -q --filter "label=com.docker.compose.project=rcm" | ForEach-Object { docker stop $_ | Out-Null }
    break
  }
  $logs = (Dc logs --no-color cloudflared 2>$null | Out-String)
  $m = [regex]::Matches($logs, 'https://[a-z0-9-]+\.trycloudflare\.com')
  if ($m.Count -gt 0) {
    $url = $m[$m.Count - 1].Value
    if ($url -ne $lastUrl) {
      $lastUrl = $url
      Set-Content -Path (Join-Path $Root "URL-ACTUAL.txt") -Value $url
      Log "Link publico: $url"
    }
  }
  if (((Get-Date) - $lastBackup).TotalHours -ge 6) { Backup-Db; $lastBackup = Get-Date }
  Start-Sleep 20
}
