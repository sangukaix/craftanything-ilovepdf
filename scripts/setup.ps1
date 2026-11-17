param(
  [Alias('Profile')][ValidateSet('Full','Core')][string]$InstallProfile='Full',
  [ValidateSet('Auto','Existing','Ollama','Strata','None')][string]$AiEngine='Auto',
  [switch]$SkipVerification
)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$projectRoot=Split-Path -Parent $PSScriptRoot
if(-not [Environment]::Is64BitOperatingSystem){throw 'Windows x64 is required.'}
if($projectRoot.StartsWith('\\')){throw 'Extract the project to a local Windows drive first.'}
if($projectRoot.Length -gt 150){throw 'Use a shorter checkout path, for example C:\Projects\pdf-tools.'}
[Net.ServicePointManager]::SecurityProtocol=[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$manifest=Get-Content -LiteralPath (Join-Path $projectRoot 'dependencies.lock.json') -Raw | ConvertFrom-Json
$cache=Join-Path $projectRoot '.local-data\downloads'
New-Item -ItemType Directory -Path $cache -Force | Out-Null
function Fetch-Verified($asset){
 $target=Join-Path $cache $asset.filename
 if(Test-Path -LiteralPath $target){
  if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -eq $asset.sha256){return $target}
  throw "Cached file hash mismatch: $($asset.filename). Move it out of .local-data/downloads and retry."
 }
 Write-Host "Downloading $($asset.filename) ..."
 $partial=$target+'.partial'
 Invoke-WebRequest -UseBasicParsing -Uri $asset.url -OutFile $partial
 if((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant() -ne $asset.sha256){throw "Download hash mismatch: $($asset.filename)"}
 Move-Item -LiteralPath $partial -Destination $target
 return $target
}
try{
 Write-Host '1/7 Preparing isolated Python and Node runtimes (no global PATH changes)...'
 $uvDir=Join-Path $projectRoot 'tools\uv'
 $uv=Join-Path $uvDir 'uv.exe'
 if(-not(Test-Path -LiteralPath $uv)){
  $uvZip=Fetch-Verified $manifest.assets.uv
  Expand-Archive -LiteralPath $uvZip -DestinationPath $uvDir -Force
 }
 $nodeDir=Join-Path $projectRoot ('tools\node\node-'+$manifest.assets.node.version+'-win-x64')
 if(-not(Test-Path -LiteralPath (Join-Path $nodeDir 'node.exe'))){
  $nodeZip=Fetch-Verified $manifest.assets.node
  Expand-Archive -LiteralPath $nodeZip -DestinationPath (Join-Path $projectRoot 'tools\node') -Force
 }
 $env:UV_PYTHON_INSTALL_DIR=Join-Path $projectRoot 'tools\python'
 $env:UV_CACHE_DIR=Join-Path $projectRoot '.local-data\uv-cache'
 $env:UV_PYTHON_BIN_DIR=Join-Path $projectRoot 'tools\python-bin'
 $env:UV_NO_MODIFY_PATH='1'
 $env:UV_NO_CONFIG='1'
 $env:UV_MANAGED_PYTHON='1'
 $env:PYTHONUTF8='1'
 $env:PATH=$nodeDir+';'+$env:PATH
 & $uv python install $manifest.python --no-bin --no-registry
 if($LASTEXITCODE -ne 0){throw 'Managed Python download failed.'}
 $venv=Join-Path $projectRoot '.pdf-service-venv'
 if(-not(Test-Path -LiteralPath (Join-Path $venv 'Scripts\python.exe'))){
  & $uv venv --python $manifest.python $venv
  if($LASTEXITCODE -ne 0){throw 'Virtual environment creation failed.'}
 }
 $python=Join-Path $venv 'Scripts\python.exe'
 Write-Host '2/7 Installing pinned Python packages...'
 & $uv pip sync --python $python --require-hashes (Join-Path $projectRoot 'scripts\python-requirements.lock')
 if($LASTEXITCODE -ne 0){throw 'Python package installation failed.'}
 Write-Host '3/7 Installing locked JavaScript packages...'
 Push-Location (Join-Path $projectRoot 'app')
 try{& (Join-Path $nodeDir 'npm.cmd') ci --no-audit --no-fund;if($LASTEXITCODE -ne 0){throw 'npm ci failed.'}}finally{Pop-Location}
 Write-Host '4/7 Preparing document engines...'
 & $python (Join-Path $PSScriptRoot 'install_runtime.py') --profile $InstallProfile --ai-engine $AiEngine
 if($LASTEXITCODE -ne 0){throw 'Document/AI runtime preparation failed.'}
 Write-Host '5/7 Building the website...'
 $env:NEXT_TELEMETRY_DISABLED='1'
 Push-Location (Join-Path $projectRoot 'app')
 try{& (Join-Path $nodeDir 'npm.cmd') run build;if($LASTEXITCODE -ne 0){throw 'Web build failed.'}}finally{Pop-Location}
 Write-Host '6/7 Checking installed features...'
 & $python (Join-Path $PSScriptRoot 'doctor.py') --profile $InstallProfile
 if($LASTEXITCODE -ne 0){throw 'Installation check failed. See .local-data/doctor.json.'}
 if(-not $SkipVerification){
  Write-Host '7/7 Running synthetic-file installation tests...'
  & $python (Join-Path $PSScriptRoot 'verify_install.py') --profile $InstallProfile
  if($LASTEXITCODE -ne 0){throw 'File verification failed. See .local-data/verification.'}
 }
 Write-Host 'Ready. Double-click start-local-pdf.cmd. Results: .local-data\doctor.json'
}catch{
 Write-Error $_
 exit 1
}
