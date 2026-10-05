param(
    [string]$Runtime = 'D:\codex-runtime\jitu-retrieval',
    [string]$ModelRoot = 'D:\codex-models\jitu-retrieval',
    [ValidateSet('auto', 'cpu', 'cuda')][string]$Device = 'auto'
)
$ErrorActionPreference = 'Stop'
$python = Join-Path $Runtime 'Scripts\python.exe'
$backendDirectory = Split-Path $PSScriptRoot -Parent
if (!(Test-Path -LiteralPath $python)) { throw '请先按 model_runtime/README.md 安装隔离推理环境。' }
if (!(Test-Path -LiteralPath (Join-Path $ModelRoot 'models.lock.json'))) { throw '请先下载并锁定模型。' }
try {
    $existing = Invoke-RestMethod 'http://127.0.0.1:8767/health' -TimeoutSec 2
    if ($existing.status -eq 'ready') { Write-Output "检索模型服务已就绪，设备: $($existing.device)"; return }
} catch { }
$logDirectory = Join-Path $Runtime 'logs'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$env:TUJI_MODEL_ROOT = $ModelRoot
$env:PYTHONIOENCODING = 'utf-8'
if ($Device -ne 'auto') { $env:TUJI_MODEL_DEVICE = $Device }
$process = Start-Process -FilePath $python -ArgumentList @('-m', 'model_runtime.service') `
    -WorkingDirectory $backendDirectory -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $logDirectory 'stdout.log') `
    -RedirectStandardError (Join-Path $logDirectory 'stderr.log')
for ($attempt = 0; $attempt -lt 25; $attempt++) {
    Start-Sleep -Seconds 2
    if ($process.HasExited) { throw "模型服务启动失败；查看 $logDirectory\stderr.log" }
    try {
        $status = Invoke-RestMethod 'http://127.0.0.1:8767/health' -TimeoutSec 1
        if ($status.status -eq 'ready') { Write-Output "检索模型服务已就绪，PID: $($process.Id)，设备: $($status.device)"; return }
    } catch { }
}
throw "模型仍在启动；查看 $logDirectory\stderr.log，PID: $($process.Id)"
