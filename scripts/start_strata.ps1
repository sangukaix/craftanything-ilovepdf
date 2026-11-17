$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$strataRoot=Join-Path $projectRoot 'tools\strata'
$terminal=Get-ChildItem -LiteralPath (Join-Path $strataRoot 'terminal') -Filter 'strata.cmd' -Recurse | Where-Object {$_.FullName -match '[\\/]bin[\\/]strata.cmd$'} | Select-Object -First 1
if(-not $terminal){throw 'Strata Terminal is missing. Run setup.cmd -AiEngine Strata.'}
$env:STRATA_NO_PATH='1'
$env:STRATA_DATA_DIR=$strataRoot
$env:STRATA_FEED='https://github.com/Niko1221/Strata/releases/download/v0.2.13'
& $terminal.FullName launch --family qwen --model iq2_xs --context 32k --vision off --yes --no-tui --data-dir (Join-Path $strataRoot 'data')
exit $LASTEXITCODE
