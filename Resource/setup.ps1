[CmdletBinding()]
param(
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $projectRoot ".venv"
$requirementsPath = Join-Path $projectRoot "requirements.txt"

& $PythonCommand --version
if ($LASTEXITCODE -ne 0) {
    throw "Khong tim thay Python. Hay cai Python 3.12 va dam bao lenh '$PythonCommand' chay duoc."
}

$pythonVersion = & $PythonCommand -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($pythonVersion -ne "3.12") {
    throw "CP1 can Python 3.12, nhung dang nhan Python $pythonVersion."
}

if (-not (Test-Path -LiteralPath $venvPath)) {
    & $PythonCommand -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { throw "Khong the tao .venv" }
}

$venvPython = Join-Path $venvPath "Scripts\\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r $requirementsPath

Write-Host "Da san sang moi truong CP1."
Write-Host "Dung: .\\.venv\\Scripts\\python cp1\\src\\main_RCAEval.py --help"
