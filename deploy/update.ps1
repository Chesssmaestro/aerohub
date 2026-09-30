# Обновление сайта на сервере до текущего кода из этой папки.
#
#   powershell -ExecutionPolicy Bypass -File deploy\update.ps1
#
# Проверяет, что всё закоммичено и отправлено на GitHub, выкладывает код через upload.ps1
# (база, media и /etc/aerohub.env на сервере не трогаются) и проверяет, что сайт отдаёт новую версию.
param(
    [string]$Server = '45.147.176.233',
    [string]$Domain = 'aerohub24.ru',
    [string]$User = 'root',
    # Выложить даже с незакоммиченными правками
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

Write-Host '==> Проверка git'
Push-Location $root
try {
    git fetch -q origin
    $dirty = git status --porcelain
    $branch = git status -sb | Select-Object -First 1
    if (-not $Force) {
        if ($dirty) { throw "Есть незакоммиченные изменения:`n$($dirty -join "`n")`nЗакоммитьте их или запустите с -Force." }
        if ($branch -match 'ahead|behind') { throw "Ветка не совпадает с GitHub: $branch`nСделайте git push / git pull или запустите с -Force." }
    }
    Write-Host "Коммит: $(git log --oneline -1)"
} finally { Pop-Location }

& (Join-Path $PSScriptRoot 'upload.ps1') -Server $Server -Domain $Domain -User $User

Write-Host '==> Проверка сайта'
# Фразы, которых на сайте быть уже не должно
$removed = @(
    'в одной рабочей среде',
    'Единый кабинет сделки, поставки, обучения и эксплуатации'
)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$html = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 30 "https://$Domain/").Content
$left = $removed | Where-Object { $html.Contains($_) }
if ($left) {
    Write-Host "На сайте всё ещё есть: $($left -join '; ')" -ForegroundColor Red
    exit 1
}
Write-Host "Готово: https://$Domain отдаёт новую версию." -ForegroundColor Green
