# One-click setup for OmniChat-Gateway: installs Ollama, pulls the default model,
# provisions a Python venv, starts the FastAPI backend, and launches the chat UI.
# Idempotent -- safe to run again if a step was already completed.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

function Write-Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Wait-ForHttp($url, $timeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-RestMethod -Uri $url -TimeoutSec 2 | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

# Resolves the ollama.exe path directly instead of relying on `ollama` being on PATH.
# Silent/unattended installs (winget included) update the PATH registry key but don't
# always broadcast the change, so a freshly-installed ollama is often invisible to the
# current process's PATH even though it's on disk. Checking known install locations
# sidesteps that entirely.
function Resolve-OllamaExe {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),
        (Join-Path $env:ProgramFiles "Ollama\ollama.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

# 1. Ollama
Write-Step "Checking for Ollama"
$ollamaExe = Resolve-OllamaExe
if (-not $ollamaExe) {
    Write-Step "Installing Ollama"
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
    } else {
        $installerPath = Join-Path $env:TEMP "OllamaSetup.exe"
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installerPath
        Start-Process -FilePath $installerPath -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait
    }
    $ollamaExe = Resolve-OllamaExe
    if (-not $ollamaExe) {
        throw "Ollama installed but ollama.exe could not be located. Try re-running this script in a new terminal."
    }
} else {
    Write-Host "Ollama is already installed ($ollamaExe)."
}

# 2. Ensure the Ollama server is reachable
# Using 127.0.0.1 explicitly, not "localhost" -- on some machines "localhost" resolves
# to IPv6 (::1) first, and if Ollama is only bound to the IPv4 loopback, requests to
# "localhost" can fail or hang even though the server is genuinely up and reachable.
Write-Step "Checking Ollama server"
if (-not (Wait-ForHttp "http://127.0.0.1:11434/api/version" 3)) {
    Write-Host "Starting Ollama server..."
    Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    # A truly first launch right after install can be much slower than a warm start --
    # in practice this looks like Windows Defender/SmartScreen scanning the freshly
    # installed ollama.exe before it's allowed to run, on top of normal init. That scan
    # only happens once, so this window is generous and prints a heartbeat so it's
    # clear the script is still working rather than stuck.
    $deadline = (Get-Date).AddSeconds(300)
    $up = $false
    while ((Get-Date) -lt $deadline) {
        if (Wait-ForHttp "http://127.0.0.1:11434/api/version" 10) { $up = $true; break }
        Write-Host "  still waiting for Ollama to come up..."
    }
    if (-not $up) {
        throw "Ollama server did not become reachable within 5 minutes. Just run this script again -- Ollama's first-run scan/init only happens once, so it should come up quickly on the next try."
    }
}
Write-Host "Ollama server is up."

# 3. Pull the default model
Write-Step "Pulling default model: llama3 (first run only -- this can take a while)"
& $ollamaExe pull llama3

# 4. Ensure .env exists with the expected defaults
Write-Step "Writing .env"
$envPath = Join-Path $root ".env"
@"
MODEL_NAME=ollama/llama3
API_BASE=http://127.0.0.1:11434
DATABASE_URL=sqlite:///./chat_history.db
"@ | Set-Content -Path $envPath -Encoding UTF8

# 5. Python virtual environment + dependencies
Write-Step "Setting up the Python environment"
$venvDir = Join-Path $root ".venv"
if (-not (Test-Path $venvDir)) {
    # Prefer 3.12 over whatever "python" resolves to -- some dependencies (e.g. the
    # pinned litellm/tiktoken chain) don't yet ship prebuilt Windows wheels for the
    # newest CPython, which forces a source build that needs a Rust toolchain.
    $py = Get-Command "py" -ErrorAction SilentlyContinue
    if ($py) {
        $has312 = & py -0p 2>&1 | Select-String -SimpleMatch "3.12"
        if ($has312) {
            py -3.12 -m venv $venvDir
        } else {
            py -m venv $venvDir
        }
    } else {
        python -m venv $venvDir
    }
}
$venvPython = Join-Path $venvDir "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip -q
& $venvPython -m pip install -r (Join-Path $root "requirements.txt") -q

# 6. Start the FastAPI backend
Write-Step "Starting the OmniChat-Gateway backend"
$venvUvicorn = Join-Path $venvDir "Scripts\uvicorn.exe"
Start-Process -FilePath $venvUvicorn -ArgumentList "app.main:app", "--reload" -WorkingDirectory $root -WindowStyle Minimized

if (-not (Wait-ForHttp "http://127.0.0.1:8000/health" 30)) {
    throw "Backend did not become healthy within 30 seconds. Check that port 8000 is free."
}
Write-Host "Backend is up at http://127.0.0.1:8000"

# 7. Launch the chat UI (Streamlit opens the browser automatically)
Write-Step "Launching chat UI"
$venvStreamlit = Join-Path $venvDir "Scripts\streamlit.exe"
& $venvStreamlit run (Join-Path $root "chat_ui.py")
