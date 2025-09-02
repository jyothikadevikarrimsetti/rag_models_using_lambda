# PowerShell script for starting Vector Search API on Windows
# Usage: .\start_api.ps1 [local|docker|test]

param(
    [Parameter(Position=0)]
    [ValidateSet("local", "docker", "test", "install", "check", "help")]
    [string]$Command = "local"
)

# Color functions
function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️ $Message" -ForegroundColor Blue
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️ $Message" -ForegroundColor Yellow
}

function Test-RedisConnection {
    Write-Info "Checking Redis connection..."
    
    try {
        # Try to connect to Redis
        $redisHost = $env:REDIS_HOST ?? "localhost"
        $redisPort = $env:REDIS_PORT ?? 6379
        
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.Connect($redisHost, $redisPort)
        $tcpClient.Close()
        
        Write-Success "Redis is running at ${redisHost}:${redisPort}"
        return $true
    }
    catch {
        Write-Error "Redis connection failed: $($_.Exception.Message)"
        Write-Info "To start Redis:"
        Write-Host "  - Docker: docker run -d -p 6379:6379 redis:7-alpine"
        Write-Host "  - Windows: Download and install Redis for Windows"
        return $false
    }
}

function Test-PythonDependencies {
    Write-Info "Checking Python dependencies..."
    
    $requiredPackages = @("fastapi", "uvicorn", "redis", "pymongo", "openai")
    $missingPackages = @()
    
    foreach ($package in $requiredPackages) {
        try {
            python -c "import $package" 2>$null
            if ($LASTEXITCODE -ne 0) {
                $missingPackages += $package
            }
        }
        catch {
            $missingPackages += $package
        }
    }
    
    if ($missingPackages.Count -eq 0) {
        Write-Success "All required packages are installed"
        return $true
    }
    else {
        Write-Error "Missing packages: $($missingPackages -join ', ')"
        Write-Info "Install them with: pip install -r requirements.api.txt"
        return $false
    }
}

function Start-LocalAPI {
    Write-Info "Starting Vector Search API locally..."
    
    # Check dependencies
    if (-not (Test-PythonDependencies)) {
        return
    }
    
    # Setup environment
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Write-Info "Creating .env file from .env.example"
            Copy-Item ".env.example" ".env"
        }
        else {
            Write-Warning "No .env file found. Please create one based on .env.example"
        }
    }
    
    # Check Redis
    Test-RedisConnection | Out-Null
    
    # Start the API
    Write-Info "Starting API server..."
    Write-Host "📡 API will be available at: http://localhost:8000"
    Write-Host "📚 API docs will be available at: http://localhost:8000/docs"
    Write-Host "🔍 Health check: http://localhost:8000/"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop the server"
    Write-Host ""
    
    try {
        python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
    }
    catch {
        Write-Error "Failed to start API: $($_.Exception.Message)"
    }
}

function Start-Docker {
    Write-Info "Starting with Docker Compose..."
    
    if (-not (Test-Path "docker-compose.yml")) {
        Write-Error "docker-compose.yml not found"
        return
    }
    
    try {
        Write-Info "Building and starting services..."
        docker-compose up --build -d
        
        Write-Info "Waiting for services to start..."
        Start-Sleep -Seconds 10
        
        Write-Info "Service Status:"
        docker-compose ps
        
        Write-Success "Services started successfully!"
        Write-Host "📡 API should be available at: http://localhost:8000"
        Write-Host "📚 API docs: http://localhost:8000/docs"
        Write-Host ""
        Write-Host "To stop services: docker-compose down"
    }
    catch {
        Write-Error "Docker Compose failed: $($_.Exception.Message)"
    }
}

function Run-Tests {
    Write-Info "Running API tests..."
    
    # Check if API is running
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "API is running, starting tests..."
        }
        else {
            Write-Warning "API returned non-200 status, proceeding with tests..."
        }
    }
    catch {
        Write-Warning "API may not be running, tests might fail..."
    }
    
    # Run simple demo (works without extra dependencies)
    Write-Info "Running simple demo..."
    try {
        python demo_simple.py
    }
    catch {
        Write-Error "Demo failed: $($_.Exception.Message)"
    }
}

function Install-Dependencies {
    Write-Info "Installing dependencies..."
    
    try {
        python -m pip install -r requirements.api.txt
        Write-Success "Dependencies installed successfully"
    }
    catch {
        Write-Error "Failed to install dependencies: $($_.Exception.Message)"
    }
}

function Show-SystemCheck {
    Write-Info "Checking system dependencies..."
    
    $pythonOk = $false
    $depsOk = $false
    $redisOk = $false
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Success "Python: $pythonVersion"
        $pythonOk = $true
    }
    catch {
        Write-Error "Python not found or not in PATH"
    }
    
    # Check dependencies
    if ($pythonOk) {
        $depsOk = Test-PythonDependencies
    }
    
    # Check Redis
    $redisOk = Test-RedisConnection
    
    # Summary
    Write-Host ""
    if ($pythonOk -and $depsOk -and $redisOk) {
        Write-Success "System is ready to run the API"
    }
    else {
        Write-Error "System needs setup before running the API"
        Write-Host ""
        Write-Info "Setup steps:"
        if (-not $pythonOk) { Write-Host "  1. Install Python 3.8+" }
        if (-not $depsOk) { Write-Host "  2. Run: .\start_api.ps1 install" }
        if (-not $redisOk) { Write-Host "  3. Start Redis server" }
    }
}

function Show-Help {
    Write-Host @"
🔍 Vector Search API with Chat History - Windows PowerShell Script

Usage: .\start_api.ps1 [command]

Commands:
  local     Start API locally with Python (default)
  docker    Start with Docker Compose (full stack)
  test      Run API tests and demos
  install   Install Python dependencies
  check     Check system requirements
  help      Show this help message

Examples:
  .\start_api.ps1              # Start locally
  .\start_api.ps1 local        # Start locally (explicit)
  .\start_api.ps1 docker       # Start with Docker
  .\start_api.ps1 test         # Run tests
  .\start_api.ps1 install      # Install dependencies
  .\start_api.ps1 check        # Check system

Prerequisites:
  - Python 3.8+
  - Redis server (local or Docker)
  - Environment variables configured (.env file)

For more information, see README_API.md
"@
}

# Main script execution
Write-Host "🔍 Vector Search API with Chat History" -ForegroundColor Cyan
Write-Host "=" * 40

switch ($Command.ToLower()) {
    "local" { Start-LocalAPI }
    "docker" { Start-Docker }
    "test" { Run-Tests }
    "install" { Install-Dependencies }
    "check" { Show-SystemCheck }
    "help" { Show-Help }
    default { 
        Write-Error "Unknown command: $Command"
        Show-Help
    }
}
