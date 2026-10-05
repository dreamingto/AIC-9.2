param([ValidateSet('fixture', 'real', 'neural')][string]$Profile = 'fixture')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    if (!(Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
    docker info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) { throw '请先启动 Docker Desktop。' }
    $composeArgs = @('-f', 'docker-compose.yml')
    if ($Profile -ne 'fixture') {
        if (!(Test-Path -LiteralPath 'backend/data/assets/ai_real_v1')) {
            throw '请先按 release/README.md 恢复国内数据包。'
        }
        $composeArgs += @('-f', 'docker-compose.ai-real.yml')
    }
    if ($Profile -eq 'neural') {
        & '.\backend\model_runtime\start.ps1'
        $composeArgs += @('-f', 'docker-compose.neural.yml')
    }
    docker compose @composeArgs up --build -d --wait
    if ($LASTEXITCODE -ne 0) { throw '服务未全部健康，请检查 docker compose logs。' }
    Write-Output '前端：http://localhost；API：http://localhost:8000/docs'
} finally { Pop-Location }
