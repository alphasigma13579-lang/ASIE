param(
  [string]$Volume = "asie-master-build-package-v100-r11-agent-engineer_asie-data",
  [string]$Destination = ".\backups"
)

$ErrorActionPreference = "Stop"
$resolved = [IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Force -Path $resolved | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archive = Join-Path $resolved "asie-data-$stamp.tar.gz"

docker run --rm -v "${Volume}:/source:ro" -v "${resolved}:/backup" alpine:3.20 sh -c "tar -czf /backup/asie-data-$stamp.tar.gz -C /source ."
if ($LASTEXITCODE -ne 0) { throw "SQLite volume backup failed" }
Write-Output $archive
