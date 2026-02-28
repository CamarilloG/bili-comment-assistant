# 清理项目常用端口占用 (9527 Web后端, 5173 Vite前端, 8000 旧API)
# 用法: .\kill_port.ps1  或  .\kill_port.ps1 9527
$ports = if ($args[0]) { @($args[0]) } else { @(9527, 5173, 8000) }
foreach ($port in $ports) {
  $lines = netstat -ano | findstr "LISTENING" | findstr ":$port "
  if (-not $lines) { Write-Host "端口 $port 未被监听，跳过"; continue }
  $pids = $lines | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
  foreach ($pid in $pids) {
    if ($pid -match '^\d+$') {
      Write-Host "结束 PID $pid (端口 $port)..."
      taskkill /PID $pid /F 2>$null
    }
  }
}
Write-Host "完成."
