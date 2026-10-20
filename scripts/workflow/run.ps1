param(
 [string]$Image = "tyr-a14:20261018",
 [string]$SeedDb = "build/a07-ui/editor.sqlite3",
 [switch]$UiOnly,
 [switch]$PythonOnly,
 [switch]$BaselineOnly,
 [switch]$BrowserOnly,
 [Alias("WorkflowOnly")][switch]$BroadcastOnly
)
$ErrorActionPreference = "Stop"
$tyrRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "../..")).Path
$stamp = (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + [guid]::NewGuid().ToString("N").Substring(0,8)
$runDir = Join-Path $tyrRoot "build/workflow/$stamp"
New-Item -ItemType Directory -Path $runDir | Out-Null
$seed = Join-Path $runDir "seed.sqlite3"
$seedSource = (Resolve-Path -LiteralPath (Join-Path $tyrRoot $SeedDb)).Path
# Consistent local SQLite backup; original rows and revision remain untouched.
python -B -c "import sqlite3,sys; src=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True); dst=sqlite3.connect(sys.argv[2]); src.backup(dst); dst.close(); src.close()" $seedSource $seed
if ($LASTEXITCODE -ne 0) { throw "SQLite backup failed" }
$container = "tyr-workflow-$stamp"
$jar = (Resolve-Path -LiteralPath (Join-Path $tyrRoot "../bifrost/gates/target/bifrost-gates.jar")).Path
$schemas = (Resolve-Path -LiteralPath (Join-Path $tyrRoot "../bifrost/core/src/main/resources/mapping-contracts")).Path
$package = Join-Path $runDir "package.tar"
python -B -c "import pathlib,sys,tarfile; r=pathlib.Path(sys.argv[1]); t=tarfile.open(sys.argv[2],'w'); [t.add(r/n,arcname='tyr/'+n,filter=lambda i: None if '__pycache__' in i.name else i) for n in ['backend','frontend','scripts','contracts','evaluation-contracts','editor-contracts','fixtures','docs']]; t.add(r/'build/cross-graph-baseline/old-bifrost-gates.jar',arcname='old-bifrost-gates.jar'); t.add(sys.argv[3],arcname='bifrost/gates/target/bifrost-gates.jar'); t.add(sys.argv[4],arcname='bifrost/core/src/main/resources/mapping-contracts'); t.close()" $tyrRoot $package $jar $schemas
if ($LASTEXITCODE -ne 0) { throw "Input archive failed" }
$driver = Join-Path $runDir "accept.py"
python -B -c "import pathlib,sys,tarfile; t=tarfile.open(sys.argv[1]); pathlib.Path(sys.argv[2]).write_bytes(t.extractfile('tyr/scripts/workflow/accept.py').read()); t.close()" $package $driver
if ($LASTEXITCODE -ne 0) { throw "Driver snapshot failed" }
$createArgs = @("create","--pull=never","--name",$container,"--network","none","--dns","127.0.0.1","--cap-drop","ALL","--security-opt","no-new-privileges","--pids-limit","512","--memory","2g","--shm-size","256m",
 "--mount","type=bind,source=$package,target=/input/package.tar,readonly",
 "--mount","type=bind,source=$driver,target=/input/accept.py,readonly",
 "--mount","type=bind,source=$seed,target=/input/seed.sqlite3,readonly",
 "--mount","type=bind,source=$runDir,target=/evidence",$Image,"python","-B","/input/accept.py")
if ($BroadcastOnly) { $createArgs = @("create","--env","TYR_CROSS_PYTHON_ONLY=1","--env","TYR_BROADCAST_FOCUS_ONLY=1") + $createArgs[1..($createArgs.Length-1)] }
if ($BrowserOnly) { $createArgs = @("create","--env","TYR_BROADCAST_BROWSER_ONLY=1") + $createArgs[1..($createArgs.Length-1)] }
if ($UiOnly) { $createArgs = @("create","--env","TYR_EXPRESSION_UI_ONLY=1") + $createArgs[1..($createArgs.Length-1)] }
if ($PythonOnly) { $createArgs = @("create","--env","TYR_CROSS_PYTHON_ONLY=1") + $createArgs[1..($createArgs.Length-1)] }
if ($BaselineOnly) { $createArgs = @("create","--env","TYR_LIFECYCLE_BASELINE_ONLY=1") + $createArgs[1..($createArgs.Length-1)] }
 $createArgs | ConvertTo-Json | Out-File -LiteralPath (Join-Path $runDir "docker-arguments.json") -Encoding utf8

docker @createArgs | Out-File -LiteralPath (Join-Path $runDir "container-id.txt") -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "Container creation failed" }
try {
 docker inspect $container | Out-File -LiteralPath (Join-Path $runDir "docker-inspect-before.json") -Encoding utf8
 docker image inspect $Image | Out-File -LiteralPath (Join-Path $runDir "image-inspect.json") -Encoding utf8
 $ErrorActionPreference = "Continue"
 docker start --attach $container 2>&1 | Out-File -LiteralPath (Join-Path $runDir "container.log") -Encoding utf8
 $runExit = $LASTEXITCODE
 $ErrorActionPreference = "Stop"
 $runtimeArchive = Join-Path $runDir "runtime-evidence.tar"
 if (Test-Path -LiteralPath $runtimeArchive) {
  python -B -c "import tarfile,sys; t=tarfile.open(sys.argv[1]); t.extractall(sys.argv[2],filter='data'); t.close()" $runtimeArchive $runDir
  if ($LASTEXITCODE -ne 0) { throw "Runtime evidence extraction failed" }
 }

 docker inspect $container | Out-File -LiteralPath (Join-Path $runDir "docker-inspect-after.json") -Encoding utf8
 Write-Output "Broadcast evidence: $runDir"
 if ($runExit -ne 0) { throw "Broadcast failed (exit $runExit); see container.log and workflow-results.json" }
} finally {
 # Only this explicitly named, disposable container is removed. Evidence and image remain.
 docker rm $container | Out-Null
}
