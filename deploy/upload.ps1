# Выкладка АЭРОХАБ на VPS: упаковывает сайт, копирует на сервер и запускает install.sh.
#
#   powershell -ExecutionPolicy Bypass -File deploy\upload.ps1 -Server 203.0.113.10
#
# Один и тот же запуск и для первой установки, и для обновления.
# На сервер уходит только код: локальная база, .venv, media и tools не копируются.
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$Domain = 'aerohub63.ru',
    [string]$User = 'root'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$archive = Join-Path $env:TEMP 'aerohub.tar.gz'
$installer = Join-Path $env:TEMP 'aerohub-install.sh'

# install.sh должен уйти с переводами строк Unix, даже если git сделал CRLF
$text = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'install.sh')).Replace("`r`n", "`n")
[IO.File]::WriteAllText($installer, $text, (New-Object Text.UTF8Encoding $false))

Write-Host '==> Упаковка сайта'
Push-Location $root
try {
    tar -czf $archive --exclude=__pycache__ --exclude='*.pyc' app data requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'tar завершился с ошибкой' }
} finally { Pop-Location }
'{0:N1} МБ' -f ((Get-Item $archive).Length / 1MB) | Write-Host

Write-Host "==> Копирование на $Server (введите пароль root, если спросит)"
scp $archive $installer "${User}@${Server}:/tmp/"
if ($LASTEXITCODE -ne 0) { throw 'scp завершился с ошибкой' }

Write-Host '==> Установка на сервере'
ssh -t "${User}@${Server}" "bash /tmp/aerohub-install.sh /tmp/aerohub.tar.gz $Domain"
if ($LASTEXITCODE -ne 0) { throw 'Установка завершилась с ошибкой — смотрите вывод выше' }
