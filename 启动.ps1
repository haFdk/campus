$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$nodeExe = 'D:\Node.js\node.exe'
if (-not (Test-Path -LiteralPath $nodeExe)) {
    $nodeExe = (Get-Command node -ErrorAction Stop).Source
}
& $nodeExe (Join-Path $projectRoot 'launcher.js') @args
exit $LASTEXITCODE
