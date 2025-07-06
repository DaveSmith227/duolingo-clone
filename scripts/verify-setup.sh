#!/bin/bash

# =============================================================================
# Duolingo Clone - Development Environment Verification
# =============================================================================
#
# This script verifies that the development environment is properly configured
# and all services are running correctly.
#
# Usage:
#   ./scripts/verify-setup.sh [--fix] [--verbose]
#
# Options:
#   --fix       Attempt to fix common issues automatically
#   --verbose   Show detailed output for debugging
#   --help      Show this help message
#
# =============================================================================

set -euo pipefail

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly NC='\033[0m'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Options
FIX_MODE=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Development Environment Verification"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --fix       Attempt to fix common issues automatically"
            echo "  --verbose   Show detailed output for debugging"
            echo "  --help      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help to see available options"
            exit 1
            ;;
    esac
done

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Utility functions
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${PURPLE}[DEBUG]${NC} $1"
    fi
}

check_command() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if command -v "$1" >/dev/null 2>&1; then
        success "$1 is installed"
        if [ "$VERBOSE" = true ]; then
            local version=$($1 --version 2>/dev/null | head -n1 || echo "Version unknown")
            verbose "$version"
        fi
        return 0
    else
        fail "$1 is not installed"
        return 1
    fi
}

check_file() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -f "$1" ]; then
        success "File exists: $1"
        return 0
    else
        fail "File missing: $1"
        if [ "$FIX_MODE" = true ] && [ -f "$1.example" ]; then
            log "Attempting to fix: copying from $1.example"
            cp "$1.example" "$1"
            success "Fixed: Created $1 from template"
        fi
        return 1
    fi
}

check_directory() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -d "$1" ]; then
        success "Directory exists: $1"
        return 0
    else
        fail "Directory missing: $1"
        return 1
    fi
}

check_service() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    local service_name=$1
    local check_command=$2
    
    if eval "$check_command" >/dev/null 2>&1; then
        success "$service_name is running"
        return 0
    else
        fail "$service_name is not running"
        if [ "$FIX_MODE" = true ]; then
            case $service_name in
                "PostgreSQL")
                    if [[ "$OSTYPE" == "darwin"* ]]; then
                        log "Attempting to start PostgreSQL with Homebrew..."
                        brew services start postgresql@14 && success "Started PostgreSQL"
                    fi
                    ;;
                "Redis")
                    if [[ "$OSTYPE" == "darwin"* ]]; then
                        log "Attempting to start Redis with Homebrew..."
                        brew services start redis && success "Started Redis"
                    fi
                    ;;
            esac
        fi
        return 1
    fi
}

check_python_packages() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    cd "$PROJECT_ROOT/backend"
    
    if [ ! -d "venv" ]; then
        fail "Python virtual environment not found"
        if [ "$FIX_MODE" = true ]; then
            log "Creating Python virtual environment..."
            python3 -m venv venv
            success "Created virtual environment"
        fi
        return 1
    fi
    
    source venv/bin/activate
    
    # Check if requirements are installed
    if pip list | grep -q fastapi; then
        success "Python packages appear to be installed"
        if [ "$VERBOSE" = true ]; then
            verbose "FastAPI version: $(pip show fastapi | grep Version | cut -d' ' -f2)"
        fi
        return 0
    else
        fail "Python packages not installed"
        if [ "$FIX_MODE" = true ]; then
            log "Installing Python packages..."
            pip install -r requirements.txt
            success "Installed Python packages"
        fi
        return 1
    fi
}

check_node_packages() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    cd "$PROJECT_ROOT/frontend"
    
    if [ -d "node_modules" ] && [ -f "node_modules/.package-lock.json" ]; then
        success "Node.js packages appear to be installed"
        if [ "$VERBOSE" = true ]; then
            local next_version=$(npm list next --depth=0 2>/dev/null | grep next@ | cut -d'@' -f2 || echo "unknown")
            verbose "Next.js version: $next_version"
        fi
        return 0
    else
        fail "Node.js packages not installed"
        if [ "$FIX_MODE" = true ]; then
            log "Installing Node.js packages..."
            npm install
            success "Installed Node.js packages"
        fi
        return 1
    fi
}

check_database() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    cd "$PROJECT_ROOT/backend"
    
    # Check if we have .env file first
    if [ ! -f ".env" ]; then
        fail "Backend .env file missing (cannot check database)"
        return 1
    fi
    
    source .env
    
    # Check if using SQLite or PostgreSQL
    if [[ "${DATABASE_URL:-}" == *"sqlite"* ]] || [ -z "${DATABASE_URL:-}" ]; then
        # SQLite mode
        if [ -f "app.db" ]; then
            success "SQLite database file exists"
            return 0
        else
            fail "SQLite database file missing"
            if [ "$FIX_MODE" = true ]; then
                log "Running database migrations to create SQLite database..."
                source venv/bin/activate
                alembic upgrade head
                success "Created SQLite database"
            fi
            return 1
        fi
    else
        # PostgreSQL mode
        if psql "${DATABASE_URL}" -c "SELECT 1;" >/dev/null 2>&1; then
            success "PostgreSQL database is accessible"
            return 0
        else
            fail "PostgreSQL database is not accessible"
            return 1
        fi
    fi
}

test_backend_startup() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate
    
    log "Testing backend startup (this may take a moment)..."
    
    # Start backend in background
    if timeout 15s uvicorn app.main:app --host 127.0.0.1 --port 8001 >/dev/null 2>&1 &
    then
        local backend_pid=$!
        sleep 5
        
        # Test health endpoint
        if curl -s http://127.0.0.1:8001/health >/dev/null 2>&1; then
            success "Backend starts and responds correctly"
            kill $backend_pid 2>/dev/null || true
            return 0
        else
            fail "Backend starts but doesn't respond to health check"
            kill $backend_pid 2>/dev/null || true
            return 1
        fi
    else
        fail "Backend failed to start"
        return 1
    fi
}

test_frontend_build() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    cd "$PROJECT_ROOT/frontend"
    
    log "Testing frontend build (this may take a moment)..."
    
    if npm run build >/dev/null 2>&1; then
        success "Frontend builds successfully"
        return 0
    else
        fail "Frontend build failed"
        if [ "$VERBOSE" = true ]; then
            verbose "Try running 'npm run build' manually to see detailed errors"
        fi
        return 1
    fi
}

check_git_setup() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    cd "$PROJECT_ROOT"
    
    if [ -f ".git/hooks/pre-commit" ]; then
        success "Git pre-commit hooks are installed"
        return 0
    else
        warning "Git pre-commit hooks not installed"
        if [ "$FIX_MODE" = true ] && [ -f "scripts/setup-git-hooks.sh" ]; then
            log "Installing git hooks..."
            chmod +x scripts/setup-git-hooks.sh
            ./scripts/setup-git-hooks.sh
            success "Installed git hooks"
        fi
        return 1
    fi
}

check_env_variables() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    cd "$PROJECT_ROOT/backend"
    
    if [ -f ".env" ]; then
        source .env
        
        # Check for default/insecure values
        local issues=()
        
        if [[ "${SECRET_KEY:-}" == "dev-secret-key-change-in-production" ]]; then
            issues+=("SECRET_KEY is still using default value")
        fi
        
        if [[ "${DB_PASSWORD:-}" == "password" ]]; then
            issues+=("DB_PASSWORD is using default value")
        fi
        
        if [ ${#issues[@]} -eq 0 ]; then
            success "Environment variables look good"
            return 0
        else
            warning "Environment configuration issues found:"
            for issue in "${issues[@]}"; do
                echo "    - $issue"
            done
            return 1
        fi
    else
        fail "Backend .env file not found"
        return 1
    fi
}

print_summary() {
    echo ""
    echo "============================================================================="
    echo -e "${BLUE}📋 VERIFICATION SUMMARY${NC}"
    echo "============================================================================="
    echo ""
    echo -e "Total checks: ${TOTAL_CHECKS}"
    echo -e "${GREEN}Passed: ${PASSED_CHECKS}${NC}"
    echo -e "${RED}Failed: ${FAILED_CHECKS}${NC}"
    echo -e "${YELLOW}Warnings: ${WARNINGS}${NC}"
    echo ""
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "${GREEN}🎉 All checks passed! Your development environment is ready.${NC}"
        echo ""
        echo "🚀 Start the application:"
        echo "   Backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
        echo "   Frontend: cd frontend && npm run dev"
        echo ""
        return 0
    else
        echo -e "${RED}❌ Some checks failed. Your environment needs attention.${NC}"
        echo ""
        if [ "$FIX_MODE" = false ]; then
            echo "💡 Try running with --fix to automatically resolve common issues:"
            echo "   ./scripts/verify-setup.sh --fix"
        fi
        echo ""
        echo "🔧 Manual setup options:"
        echo "   Full setup:  ./scripts/setup-dev.sh"
        echo "   Quick setup: ./scripts/quick-setup.sh"
        echo ""
        return 1
    fi
}

main() {
    echo "============================================================================="
    echo -e "${BLUE}🔍 Development Environment Verification${NC}"
    echo "============================================================================="
    echo ""
    
    if [ "$FIX_MODE" = true ]; then
        log "Fix mode enabled - will attempt to resolve issues automatically"
        echo ""
    fi
    
    log "Checking system prerequisites..."
    check_command python3
    check_command node
    check_command git
    
    echo ""
    log "Checking project structure..."
    check_directory "$PROJECT_ROOT/backend"
    check_directory "$PROJECT_ROOT/frontend"
    check_file "$PROJECT_ROOT/backend/.env"
    check_file "$PROJECT_ROOT/frontend/.env.local"
    
    echo ""
    log "Checking dependencies..."
    check_python_packages
    check_node_packages
    
    echo ""
    log "Checking database..."
    check_database
    
    echo ""
    log "Checking services..."
    check_service "Redis" "redis-cli ping | grep -q PONG"
    # Only check PostgreSQL if not using SQLite
    if [ -f "$PROJECT_ROOT/backend/.env" ]; then
        source "$PROJECT_ROOT/backend/.env"
        if [[ "${DATABASE_URL:-}" != *"sqlite"* ]] && [ -n "${DATABASE_URL:-}" ]; then
            check_service "PostgreSQL" "psql -c 'SELECT 1;' '${DATABASE_URL}'"
        fi
    fi
    
    echo ""
    log "Checking configuration..."
    check_env_variables
    check_git_setup
    
    echo ""
    log "Testing application startup..."
    test_backend_startup
    test_frontend_build
    
    print_summary
}

# Handle cleanup
cleanup() {
    # Kill any background processes we started
    jobs -p | xargs -r kill 2>/dev/null || true
}

trap cleanup EXIT

# Run main function
main "$@"