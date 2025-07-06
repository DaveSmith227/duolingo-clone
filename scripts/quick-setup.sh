#!/bin/bash

# =============================================================================
# Duolingo Clone - Quick Development Setup (SQLite)
# =============================================================================
#
# This script provides a rapid setup using SQLite instead of PostgreSQL
# for developers who want to get started immediately without external services.
#
# Usage:
#   ./scripts/quick-setup.sh
#
# What this script does:
# - Sets up Python virtual environment
# - Installs dependencies
# - Creates SQLite database
# - Runs basic tests
# - Provides start commands
#
# Time: ~2 minutes
#
# =============================================================================

set -euo pipefail

# Colors
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "============================================================================="
echo -e "${BLUE}⚡ Duolingo Clone - Quick Setup${NC}"
echo "============================================================================="
echo ""

# Check prerequisites
log "Checking prerequisites..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command -v node >/dev/null 2>&1; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

success "Prerequisites check passed"

# Setup backend with SQLite
log "Setting up backend with SQLite..."
cd "$PROJECT_ROOT/backend"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1
pip install -r requirements.txt >/dev/null 2>&1

# Create .env with SQLite configuration
if [ ! -f ".env" ]; then
    cp .env.example .env
    
    # Configure for SQLite
    cat >> .env << 'EOF'

# Quick setup overrides (SQLite mode)
DATABASE_URL=sqlite:///./app.db
REDIS_HOST=localhost
REDIS_PORT=6379
ENVIRONMENT=development
DEBUG=true
EOF
    
    success "Created backend configuration for SQLite"
else
    warning "Backend .env already exists"
fi

# Run migrations
log "Setting up database..."
alembic upgrade head >/dev/null 2>&1
success "Database initialized"

# Setup frontend
log "Setting up frontend..."
cd "$PROJECT_ROOT/frontend"

if [ ! -f ".env.local" ]; then
    cp .env.example .env.local
    success "Created frontend configuration"
else
    warning "Frontend .env.local already exists"
fi

npm install --silent >/dev/null 2>&1
success "Frontend dependencies installed"

# Quick test
log "Running quick verification..."
cd "$PROJECT_ROOT/backend"
source venv/bin/activate

if python -c "from app.main import app; print('Backend imports OK')" >/dev/null 2>&1; then
    success "Backend verification passed"
else
    warning "Backend verification had issues"
fi

cd "$PROJECT_ROOT/frontend"
if npm run build >/dev/null 2>&1; then
    success "Frontend verification passed"
else
    warning "Frontend verification had issues"
fi

echo ""
echo "============================================================================="
echo -e "${GREEN}🎉 QUICK SETUP COMPLETE! 🎉${NC}"
echo "============================================================================="
echo ""
echo "📍 Start the application:"
echo ""
echo "1. Backend (terminal 1):"
echo "   cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo ""
echo "2. Frontend (terminal 2):"
echo "   cd frontend && npm run dev"
echo ""
echo "3. Open: http://localhost:3000"
echo ""
echo "📝 Notes:"
echo "• Using SQLite database (app.db in backend folder)"
echo "• Redis is optional for this setup"
echo "• For full setup with PostgreSQL, run: ./scripts/setup-dev.sh"
echo ""
echo "⏱️  Total time: ~2 minutes"
echo "============================================================================="