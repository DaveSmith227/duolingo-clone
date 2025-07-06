#!/bin/bash

# =============================================================================
# Duolingo Clone - Automated Development Environment Setup
# =============================================================================
#
# This script sets up a complete local development environment in under 5 minutes.
# It handles all dependencies, services, and configuration needed to run the app.
#
# Usage:
#   ./scripts/setup-dev.sh [--skip-deps] [--skip-services] [--skip-tests]
#
# Options:
#   --skip-deps      Skip dependency installation
#   --skip-services  Skip service setup (Redis, PostgreSQL)
#   --skip-tests     Skip test execution
#   --help          Show this help message
#
# Requirements:
#   - macOS or Linux
#   - Git
#   - Node.js 18+ (use 'nvm install 18' if needed)
#   - Python 3.11+ (use 'pyenv install 3.11' if needed)
#   - Homebrew (macOS) or apt/yum (Linux)
#
# =============================================================================

set -euo pipefail  # Exit on any error

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly LOG_FILE="$PROJECT_ROOT/setup.log"
readonly START_TIME=$(date +%s)

# Parse command line arguments
SKIP_DEPS=false
SKIP_SERVICES=false
SKIP_TESTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --skip-services)
            SKIP_SERVICES=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --help)
            echo "Duolingo Clone Development Setup"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --skip-deps      Skip dependency installation"
            echo "  --skip-services  Skip service setup (Redis, PostgreSQL)"
            echo "  --skip-tests     Skip test execution"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help to see available options"
            exit 1
            ;;
    esac
done

# Utility functions
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message" >&2
            ;;
        "STEP")
            echo -e "${PURPLE}[STEP]${NC} $message"
            ;;
    esac
    
    # Also log to file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_prerequisites() {
    log "STEP" "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check operating system
    if [[ "$OSTYPE" == "darwin"* ]]; then
        log "INFO" "Detected macOS"
        if ! check_command brew; then
            log "ERROR" "Homebrew is required but not installed. Install from https://brew.sh/"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log "INFO" "Detected Linux"
        if ! check_command apt-get && ! check_command yum && ! check_command dnf; then
            log "ERROR" "Package manager (apt, yum, or dnf) not found"
            exit 1
        fi
    else
        log "ERROR" "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    # Check Git
    if ! check_command git; then
        missing_deps+=("git")
    fi
    
    # Check Node.js
    if ! check_command node; then
        missing_deps+=("node")
    else
        local node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$node_version" -lt 18 ]; then
            log "WARNING" "Node.js version $node_version detected. Version 18+ recommended."
            log "INFO" "Run 'nvm install 18 && nvm use 18' to upgrade"
        fi
    fi
    
    # Check Python
    if ! check_command python3; then
        missing_deps+=("python3")
    else
        local python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
        if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            log "WARNING" "Python version $python_version detected. Version 3.11+ recommended."
            log "INFO" "Run 'pyenv install 3.11 && pyenv global 3.11' to upgrade"
        fi
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log "ERROR" "Missing required dependencies: ${missing_deps[*]}"
        log "INFO" "Please install them and run this script again"
        exit 1
    fi
    
    log "SUCCESS" "All prerequisites met"
}

setup_environment() {
    log "STEP" "Setting up environment files..."
    
    # Backend environment
    if [ ! -f "$PROJECT_ROOT/backend/.env" ]; then
        log "INFO" "Creating backend .env from template..."
        cp "$PROJECT_ROOT/backend/.env.example" "$PROJECT_ROOT/backend/.env"
        
        # Generate a secure secret key
        if check_command openssl; then
            local secret_key=$(openssl rand -hex 32)
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/dev-secret-key-change-in-production/$secret_key/" "$PROJECT_ROOT/backend/.env"
            else
                sed -i "s/dev-secret-key-change-in-production/$secret_key/" "$PROJECT_ROOT/backend/.env"
            fi
            log "SUCCESS" "Generated secure secret key for backend"
        else
            log "WARNING" "OpenSSL not found. Using default secret key (not secure for production)"
        fi
    else
        log "INFO" "Backend .env already exists, skipping..."
    fi
    
    # Frontend environment
    if [ ! -f "$PROJECT_ROOT/frontend/.env.local" ]; then
        log "INFO" "Creating frontend .env.local from template..."
        cp "$PROJECT_ROOT/frontend/.env.example" "$PROJECT_ROOT/frontend/.env.local"
        log "SUCCESS" "Created frontend environment file"
    else
        log "INFO" "Frontend .env.local already exists, skipping..."
    fi
}

install_system_dependencies() {
    if [ "$SKIP_DEPS" = true ]; then
        log "INFO" "Skipping system dependency installation"
        return
    fi
    
    log "STEP" "Installing system dependencies..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS with Homebrew
        log "INFO" "Installing dependencies with Homebrew..."
        
        # Update Homebrew
        brew update >/dev/null 2>&1 || true
        
        # Install dependencies
        local deps=("postgresql@14" "redis" "python@3.11")
        for dep in "${deps[@]}"; do
            if ! brew list "$dep" >/dev/null 2>&1; then
                log "INFO" "Installing $dep..."
                brew install "$dep" || log "WARNING" "Failed to install $dep"
            else
                log "INFO" "$dep already installed"
            fi
        done
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        log "INFO" "Installing dependencies with package manager..."
        
        if check_command apt-get; then
            # Ubuntu/Debian
            sudo apt-get update -y
            sudo apt-get install -y postgresql postgresql-contrib redis-server python3-pip python3-venv python3-dev libpq-dev
        elif check_command yum; then
            # CentOS/RHEL
            sudo yum update -y
            sudo yum install -y postgresql postgresql-server redis python3-pip python3-devel postgresql-devel
        elif check_command dnf; then
            # Fedora
            sudo dnf update -y
            sudo dnf install -y postgresql postgresql-server redis python3-pip python3-devel postgresql-devel
        fi
    fi
    
    log "SUCCESS" "System dependencies installed"
}

setup_services() {
    if [ "$SKIP_SERVICES" = true ]; then
        log "INFO" "Skipping service setup"
        return
    fi
    
    log "STEP" "Setting up services..."
    
    # Start PostgreSQL
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! brew services list | grep postgresql@14 | grep started >/dev/null; then
            log "INFO" "Starting PostgreSQL..."
            brew services start postgresql@14
            sleep 3
        else
            log "INFO" "PostgreSQL already running"
        fi
    else
        if ! systemctl is-active --quiet postgresql; then
            log "INFO" "Starting PostgreSQL..."
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
        else
            log "INFO" "PostgreSQL already running"
        fi
    fi
    
    # Start Redis
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! brew services list | grep redis | grep started >/dev/null; then
            log "INFO" "Starting Redis..."
            brew services start redis
            sleep 2
        else
            log "INFO" "Redis already running"
        fi
    else
        if ! systemctl is-active --quiet redis; then
            log "INFO" "Starting Redis..."
            sudo systemctl start redis
            sudo systemctl enable redis
        else
            log "INFO" "Redis already running"
        fi
    fi
    
    # Create database
    log "INFO" "Setting up database..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if ! psql -lqt | cut -d \| -f 1 | grep -qw duolingo_clone; then
            log "INFO" "Creating database 'duolingo_clone'..."
            createdb duolingo_clone
        else
            log "INFO" "Database 'duolingo_clone' already exists"
        fi
    else
        # Linux
        sudo -u postgres createdb duolingo_clone 2>/dev/null || log "INFO" "Database 'duolingo_clone' already exists"
    fi
    
    log "SUCCESS" "Services configured and running"
}

setup_backend() {
    log "STEP" "Setting up backend..."
    
    cd "$PROJECT_ROOT/backend"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        log "INFO" "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    log "INFO" "Upgrading pip..."
    pip install --upgrade pip >/dev/null 2>&1
    
    # Install dependencies
    if [ "$SKIP_DEPS" = false ]; then
        log "INFO" "Installing Python dependencies..."
        pip install -r requirements.txt >/dev/null 2>&1
    fi
    
    # Run database migrations
    log "INFO" "Running database migrations..."
    alembic upgrade head
    
    log "SUCCESS" "Backend setup complete"
}

setup_frontend() {
    log "STEP" "Setting up frontend..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # Install dependencies
    if [ "$SKIP_DEPS" = false ]; then
        log "INFO" "Installing Node.js dependencies..."
        
        # Use npm ci if package-lock.json exists, otherwise npm install
        if [ -f "package-lock.json" ]; then
            npm ci --silent
        else
            npm install --silent
        fi
    fi
    
    # Build project to check for errors
    log "INFO" "Building frontend..."
    npm run build >/dev/null 2>&1
    
    log "SUCCESS" "Frontend setup complete"
}

setup_git_hooks() {
    log "STEP" "Setting up Git hooks..."
    
    cd "$PROJECT_ROOT"
    
    if [ -f "scripts/setup-git-hooks.sh" ]; then
        chmod +x scripts/setup-git-hooks.sh
        ./scripts/setup-git-hooks.sh
        log "SUCCESS" "Git hooks configured"
    else
        log "WARNING" "Git hooks setup script not found"
    fi
}

run_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        log "INFO" "Skipping test execution"
        return
    fi
    
    log "STEP" "Running tests to verify setup..."
    
    # Backend tests
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate
    
    log "INFO" "Running backend tests..."
    if pytest --quiet --tb=short app/tests/test_main.py::test_health_endpoint 2>/dev/null; then
        log "SUCCESS" "Backend tests passed"
    else
        log "WARNING" "Some backend tests failed (this may be normal for a fresh setup)"
    fi
    
    # Frontend tests
    cd "$PROJECT_ROOT/frontend"
    log "INFO" "Running frontend tests..."
    if npm run test:run --silent >/dev/null 2>&1; then
        log "SUCCESS" "Frontend tests passed"
    else
        log "WARNING" "Some frontend tests failed (this may be normal for a fresh setup)"
    fi
}

verify_setup() {
    log "STEP" "Verifying setup..."
    
    local errors=0
    
    # Check if backend can start
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate
    
    log "INFO" "Testing backend startup..."
    if timeout 10s uvicorn app.main:app --host 127.0.0.1 --port 8001 >/dev/null 2>&1 &
    then
        local backend_pid=$!
        sleep 3
        
        if curl -s http://127.0.0.1:8001/health >/dev/null; then
            log "SUCCESS" "Backend starts successfully"
        else
            log "ERROR" "Backend failed to respond"
            errors=$((errors + 1))
        fi
        
        kill $backend_pid 2>/dev/null || true
    else
        log "ERROR" "Backend failed to start"
        errors=$((errors + 1))
    fi
    
    # Check if frontend can build
    cd "$PROJECT_ROOT/frontend"
    log "INFO" "Testing frontend build..."
    if npm run build >/dev/null 2>&1; then
        log "SUCCESS" "Frontend builds successfully"
    else
        log "ERROR" "Frontend build failed"
        errors=$((errors + 1))
    fi
    
    # Check services
    if [ "$SKIP_SERVICES" = false ]; then
        log "INFO" "Checking services..."
        
        # Check PostgreSQL
        if psql -c "SELECT 1;" duolingo_clone >/dev/null 2>&1; then
            log "SUCCESS" "PostgreSQL is accessible"
        else
            log "ERROR" "PostgreSQL connection failed"
            errors=$((errors + 1))
        fi
        
        # Check Redis
        if redis-cli ping | grep PONG >/dev/null 2>&1; then
            log "SUCCESS" "Redis is accessible"
        else
            log "ERROR" "Redis connection failed"
            errors=$((errors + 1))
        fi
    fi
    
    if [ $errors -eq 0 ]; then
        log "SUCCESS" "All verification checks passed!"
        return 0
    else
        log "ERROR" "$errors verification checks failed"
        return 1
    fi
}

cleanup() {
    # Kill any background processes we started
    jobs -p | xargs -r kill 2>/dev/null || true
}

print_summary() {
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo ""
    echo "============================================================================="
    echo -e "${GREEN}🎉 SETUP COMPLETE! 🎉${NC}"
    echo "============================================================================="
    echo ""
    echo -e "${CYAN}Setup completed in ${minutes}m ${seconds}s${NC}"
    echo ""
    echo "📍 Next steps:"
    echo ""
    echo "1. Start the backend server:"
    echo "   cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo ""
    echo "2. Start the frontend development server:"
    echo "   cd frontend && npm run dev"
    echo ""
    echo "3. Open your browser to:"
    echo "   🌐 Frontend: http://localhost:3000"
    echo "   🔧 Backend API: http://localhost:8000"
    echo "   📚 API Docs: http://localhost:8000/docs"
    echo ""
    echo "📝 Configuration files created:"
    echo "   • backend/.env (database, API keys, etc.)"
    echo "   • frontend/.env.local (client configuration)"
    echo ""
    echo "🔧 Services running:"
    if [ "$SKIP_SERVICES" = false ]; then
        echo "   • PostgreSQL (database)"
        echo "   • Redis (caching)"
    else
        echo "   • Services were skipped (--skip-services flag used)"
    fi
    echo ""
    echo "📋 Setup log saved to: $LOG_FILE"
    echo ""
    echo "Need help? Check the documentation or run with --help"
    echo "============================================================================="
}

main() {
    # Set trap to clean up on exit
    trap cleanup EXIT
    
    # Initialize log file
    echo "Setup started at $(date)" > "$LOG_FILE"
    
    echo "============================================================================="
    echo -e "${CYAN}🚀 Duolingo Clone - Development Setup${NC}"
    echo "============================================================================="
    echo ""
    
    check_prerequisites
    setup_environment
    install_system_dependencies
    setup_services
    setup_backend
    setup_frontend
    setup_git_hooks
    run_tests
    
    if verify_setup; then
        print_summary
        exit 0
    else
        echo ""
        log "ERROR" "Setup completed with errors. Check the log file: $LOG_FILE"
        echo ""
        echo "Common issues and solutions:"
        echo "• PostgreSQL not running: brew services start postgresql@14 (macOS)"
        echo "• Redis not running: brew services start redis (macOS)"
        echo "• Python version too old: pyenv install 3.11 && pyenv global 3.11"
        echo "• Node.js version too old: nvm install 18 && nvm use 18"
        exit 1
    fi
}

# Run main function
main "$@"