# =============================================================================
# Duolingo Clone - Windows Development Environment Setup
# =============================================================================
#
# PowerShell script for setting up development environment on Windows.
# Requires PowerShell 5.1+ and admin privileges for some operations.
#
# Usage:
#   .\scripts\setup-dev.ps1 [-SkipDeps] [-SkipServices] [-SkipTests]
#
# Parameters:
#   -SkipDeps      Skip dependency installation
#   -SkipServices  Skip service setup 
#   -SkipTests     Skip test execution
#   -Help          Show this help message
#
# Requirements:
#   - Windows 10/11
#   - PowerShell 5.1+
#   - Git for Windows
#   - Node.js 18+ (https://nodejs.org)
#   - Python 3.11+ (https://python.org)
#   - Optional: Windows Subsystem for Linux (WSL)
#
# =============================================================================

param(
    [switch]$SkipDeps = $false,
    [switch]$SkipServices = $false, 
    [switch]$SkipTests = $false,
    [switch]$Help = $false
)

# Colors for output
$Red = [ConsoleColor]::Red
$Green = [ConsoleColor]::Green
$Yellow = [ConsoleColor]::Yellow
$Blue = [ConsoleColor]::Blue
$Cyan = [ConsoleColor]::Cyan

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogFile = Join-Path $ProjectRoot "setup-windows.log"
$StartTime = Get-Date

if ($Help) {
    Write-Host "Duolingo Clone Development Setup for Windows" -ForegroundColor $Cyan
    Write-Host ""
    Write-Host "Usage: .\scripts\setup-dev.ps1 [parameters]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -SkipDeps      Skip dependency installation"
    Write-Host "  -SkipServices  Skip service setup"
    Write-Host "  -SkipTests     Skip test execution"
    Write-Host "  -Help          Show this help message"
    exit 0
}

# Utility functions
function Write-Log {
    param([string]$Level, [string]$Message)
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    switch ($Level) {
        "INFO" { Write-Host "[INFO] $Message" -ForegroundColor $Blue }
        "SUCCESS" { Write-Host "[SUCCESS] $Message" -ForegroundColor $Green }
        "WARNING" { Write-Host "[WARNING] $Message" -ForegroundColor $Yellow }
        "ERROR" { Write-Host "[ERROR] $Message" -ForegroundColor $Red }
        "STEP" { Write-Host "[STEP] $Message" -ForegroundColor $Cyan }
    }
    
    Add-Content -Path $LogFile -Value $logEntry
}

function Test-Command {
    param([string]$Command)
    
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-Chocolatey {
    if (!(Test-Command "choco")) {
        Write-Log "INFO" "Installing Chocolatey package manager..."
        
        if (!(Test-Administrator)) {
            Write-Log "WARNING" "Chocolatey installation requires administrator privileges"
            Write-Log "INFO" "Please run PowerShell as Administrator or install manually"
            return $false
        }
        
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        
        refreshenv
        Write-Log "SUCCESS" "Chocolatey installed successfully"
        return $true
    }
    else {
        Write-Log "INFO" "Chocolatey already installed"
        return $true
    }
}

function Install-SystemDependencies {
    if ($SkipDeps) {
        Write-Log "INFO" "Skipping system dependency installation"
        return
    }
    
    Write-Log "STEP" "Installing system dependencies..."
    
    # Install Chocolatey if needed
    if (!(Install-Chocolatey)) {
        Write-Log "WARNING" "Could not install Chocolatey. Manual dependency installation required."
        return
    }
    
    $dependencies = @("postgresql", "redis-64", "python", "nodejs")
    
    foreach ($dep in $dependencies) {
        try {
            Write-Log "INFO" "Installing $dep..."
            choco install $dep -y --no-progress
            Write-Log "SUCCESS" "$dep installed"
        }
        catch {
            Write-Log "WARNING" "Failed to install $dep : $($_.Exception.Message)"
        }
    }
    
    # Refresh environment variables
    refreshenv
}

function Test-Prerequisites {
    Write-Log "STEP" "Checking prerequisites..."
    
    $missing = @()
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Write-Log "ERROR" "PowerShell 5.1+ is required. Current version: $($PSVersionTable.PSVersion)"
        $missing += "PowerShell 5.1+"
    }
    
    # Check Git
    if (!(Test-Command "git")) {
        $missing += "Git"
    }
    
    # Check Node.js
    if (!(Test-Command "node")) {
        $missing += "Node.js"
    }
    else {
        $nodeVersion = (node --version).Substring(1).Split('.')[0]
        if ([int]$nodeVersion -lt 18) {
            Write-Log "WARNING" "Node.js version $nodeVersion detected. Version 18+ recommended."
        }
    }
    
    # Check Python
    if (!(Test-Command "python")) {
        $missing += "Python 3.11+"
    }
    else {
        try {
            $pythonVersion = python --version 2>&1
            Write-Log "INFO" "Found $pythonVersion"
        }
        catch {
            Write-Log "WARNING" "Could not determine Python version"
        }
    }
    
    if ($missing.Count -gt 0) {
        Write-Log "ERROR" "Missing required dependencies: $($missing -join ', ')"
        Write-Log "INFO" "Install manually or run with administrator privileges"
        return $false
    }
    
    Write-Log "SUCCESS" "All prerequisites met"
    return $true
}

function Setup-Environment {
    Write-Log "STEP" "Setting up environment files..."
    
    # Backend environment
    $backendEnv = Join-Path $ProjectRoot "backend\.env"
    $backendEnvExample = Join-Path $ProjectRoot "backend\.env.example"
    
    if (!(Test-Path $backendEnv)) {
        Write-Log "INFO" "Creating backend .env from template..."
        Copy-Item $backendEnvExample $backendEnv
        
        # Generate secure secret key if possible
        try {
            $bytes = New-Object byte[] 32
            [System.Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes)
            $secretKey = [System.Convert]::ToBase64String($bytes)
            
            $content = Get-Content $backendEnv
            $content = $content -replace 'dev-secret-key-change-in-production', $secretKey
            Set-Content $backendEnv $content
            
            Write-Log "SUCCESS" "Generated secure secret key for backend"
        }
        catch {
            Write-Log "WARNING" "Could not generate secure secret key, using default"
        }
    }
    else {
        Write-Log "INFO" "Backend .env already exists, skipping..."
    }
    
    # Frontend environment
    $frontendEnv = Join-Path $ProjectRoot "frontend\.env.local"
    $frontendEnvExample = Join-Path $ProjectRoot "frontend\.env.example"
    
    if (!(Test-Path $frontendEnv)) {
        Write-Log "INFO" "Creating frontend .env.local from template..."
        Copy-Item $frontendEnvExample $frontendEnv
        Write-Log "SUCCESS" "Created frontend environment file"
    }
    else {
        Write-Log "INFO" "Frontend .env.local already exists, skipping..."
    }
}

function Setup-Services {
    if ($SkipServices) {
        Write-Log "INFO" "Skipping service setup"
        return
    }
    
    Write-Log "STEP" "Setting up services..."
    
    # Check if services are installed
    if (Test-Command "psql") {
        Write-Log "INFO" "PostgreSQL found, attempting to start service..."
        try {
            Start-Service postgresql* -ErrorAction SilentlyContinue
            Write-Log "SUCCESS" "PostgreSQL service started"
        }
        catch {
            Write-Log "WARNING" "Could not start PostgreSQL service automatically"
        }
    }
    
    if (Test-Command "redis-server") {
        Write-Log "INFO" "Redis found, attempting to start service..."
        try {
            Start-Service redis* -ErrorAction SilentlyContinue
            Write-Log "SUCCESS" "Redis service started"
        }
        catch {
            Write-Log "WARNING" "Could not start Redis service automatically"
        }
    }
    
    # Note: On Windows, services often need manual configuration
    Write-Log "INFO" "Services may require manual configuration on Windows"
}

function Setup-Backend {
    Write-Log "STEP" "Setting up backend..."
    
    Push-Location (Join-Path $ProjectRoot "backend")
    
    try {
        # Create virtual environment
        if (!(Test-Path "venv")) {
            Write-Log "INFO" "Creating Python virtual environment..."
            python -m venv venv
        }
        
        # Activate virtual environment
        $activateScript = "venv\Scripts\Activate.ps1"
        if (Test-Path $activateScript) {
            & $activateScript
        }
        else {
            Write-Log "ERROR" "Could not activate virtual environment"
            return
        }
        
        # Upgrade pip
        Write-Log "INFO" "Upgrading pip..."
        python -m pip install --upgrade pip | Out-Null
        
        # Install dependencies
        if (!$SkipDeps) {
            Write-Log "INFO" "Installing Python dependencies..."
            pip install -r requirements.txt | Out-Null
        }
        
        # Run database migrations
        Write-Log "INFO" "Running database migrations..."
        alembic upgrade head
        
        Write-Log "SUCCESS" "Backend setup complete"
    }
    catch {
        Write-Log "ERROR" "Backend setup failed: $($_.Exception.Message)"
    }
    finally {
        Pop-Location
    }
}

function Setup-Frontend {
    Write-Log "STEP" "Setting up frontend..."
    
    Push-Location (Join-Path $ProjectRoot "frontend")
    
    try {
        # Install dependencies
        if (!$SkipDeps) {
            Write-Log "INFO" "Installing Node.js dependencies..."
            
            if (Test-Path "package-lock.json") {
                npm ci --silent
            }
            else {
                npm install --silent
            }
        }
        
        # Build project to check for errors
        Write-Log "INFO" "Building frontend..."
        npm run build | Out-Null
        
        Write-Log "SUCCESS" "Frontend setup complete"
    }
    catch {
        Write-Log "ERROR" "Frontend setup failed: $($_.Exception.Message)"
    }
    finally {
        Pop-Location
    }
}

function Test-Setup {
    if ($SkipTests) {
        Write-Log "INFO" "Skipping test execution"
        return
    }
    
    Write-Log "STEP" "Running verification tests..."
    
    # Test backend
    Push-Location (Join-Path $ProjectRoot "backend")
    try {
        & "venv\Scripts\Activate.ps1"
        Write-Log "INFO" "Testing backend imports..."
        python -c "from app.main import app; print('Backend imports OK')" | Out-Null
        Write-Log "SUCCESS" "Backend verification passed"
    }
    catch {
        Write-Log "WARNING" "Backend verification failed: $($_.Exception.Message)"
    }
    finally {
        Pop-Location
    }
    
    # Test frontend
    Push-Location (Join-Path $ProjectRoot "frontend")
    try {
        Write-Log "INFO" "Testing frontend build..."
        npm run build | Out-Null
        Write-Log "SUCCESS" "Frontend verification passed"
    }
    catch {
        Write-Log "WARNING" "Frontend verification failed: $($_.Exception.Message)"
    }
    finally {
        Pop-Location
    }
}

function Show-Summary {
    $endTime = Get-Date
    $duration = $endTime - $StartTime
    
    Write-Host ""
    Write-Host "=============================================================================" -ForegroundColor $Cyan
    Write-Host "🎉 WINDOWS SETUP COMPLETE! 🎉" -ForegroundColor $Green
    Write-Host "=============================================================================" -ForegroundColor $Cyan
    Write-Host ""
    Write-Host "Setup completed in $($duration.Minutes)m $($duration.Seconds)s" -ForegroundColor $Cyan
    Write-Host ""
    Write-Host "📍 Next steps:" -ForegroundColor $Yellow
    Write-Host ""
    Write-Host "1. Start the backend server:" -ForegroundColor $White
    Write-Host "   cd backend" -ForegroundColor $Gray
    Write-Host "   venv\Scripts\Activate.ps1" -ForegroundColor $Gray
    Write-Host "   uvicorn app.main:app --reload" -ForegroundColor $Gray
    Write-Host ""
    Write-Host "2. Start the frontend development server:" -ForegroundColor $White
    Write-Host "   cd frontend" -ForegroundColor $Gray
    Write-Host "   npm run dev" -ForegroundColor $Gray
    Write-Host ""
    Write-Host "3. Open your browser to:" -ForegroundColor $White
    Write-Host "   🌐 Frontend: http://localhost:3000" -ForegroundColor $Blue
    Write-Host "   🔧 Backend API: http://localhost:8000" -ForegroundColor $Blue
    Write-Host "   📚 API Docs: http://localhost:8000/docs" -ForegroundColor $Blue
    Write-Host ""
    Write-Host "📝 Configuration files created:" -ForegroundColor $Yellow
    Write-Host "   • backend\.env (database, API keys, etc.)" -ForegroundColor $Gray
    Write-Host "   • frontend\.env.local (client configuration)" -ForegroundColor $Gray
    Write-Host ""
    Write-Host "🔧 Windows Notes:" -ForegroundColor $Yellow
    Write-Host "   • Services may need manual start: Services.msc" -ForegroundColor $Gray
    Write-Host "   • PostgreSQL: Check pgAdmin or command line" -ForegroundColor $Gray
    Write-Host "   • Redis: May need manual service configuration" -ForegroundColor $Gray
    Write-Host ""
    Write-Host "📋 Setup log saved to: $LogFile" -ForegroundColor $White
    Write-Host ""
    Write-Host "Need help? Check the documentation or run with -Help" -ForegroundColor $White
    Write-Host "=============================================================================" -ForegroundColor $Cyan
}

# Main execution
function Main {
    # Initialize log file
    "Setup started at $(Get-Date)" | Out-File -FilePath $LogFile -Encoding UTF8
    
    Write-Host "=============================================================================" -ForegroundColor $Cyan
    Write-Host "🚀 Duolingo Clone - Windows Development Setup" -ForegroundColor $Cyan
    Write-Host "=============================================================================" -ForegroundColor $Cyan
    Write-Host ""
    
    if (!(Test-Prerequisites)) {
        Write-Log "ERROR" "Prerequisites check failed"
        exit 1
    }
    
    Setup-Environment
    Install-SystemDependencies
    Setup-Services
    Setup-Backend
    Setup-Frontend
    Test-Setup
    
    Show-Summary
}

# Error handling
trap {
    Write-Log "ERROR" "Setup failed with error: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "❌ Setup failed. Check the log file: $LogFile" -ForegroundColor $Red
    Write-Host ""
    Write-Host "Common Windows issues:" -ForegroundColor $Yellow
    Write-Host "• Run PowerShell as Administrator for service installation" -ForegroundColor $Gray
    Write-Host "• Check Windows Defender / Antivirus isn't blocking installations" -ForegroundColor $Gray
    Write-Host "• Ensure execution policy allows script running: Set-ExecutionPolicy RemoteSigned" -ForegroundColor $Gray
    Write-Host "• Try manual installation of Node.js and Python from official websites" -ForegroundColor $Gray
    exit 1
}

# Run main function
Main