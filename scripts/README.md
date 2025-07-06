# Development Setup Scripts

This directory contains automated setup scripts for the Duolingo Clone development environment.

## Quick Start

### 🚀 Full Setup (Recommended)
```bash
# macOS/Linux
./scripts/setup-dev.sh

# Windows (PowerShell as Administrator)
.\scripts\setup-dev.ps1
```

### ⚡ Quick Setup (SQLite, 2 minutes)
```bash
./scripts/quick-setup.sh
```

### 🔍 Verify Setup
```bash
./scripts/verify-setup.sh
```

## Scripts Overview

| Script | Platform | Purpose | Time |
|--------|----------|---------|------|
| `setup-dev.sh` | macOS/Linux | Full development environment with PostgreSQL/Redis | ~5 min |
| `setup-dev.ps1` | Windows | Full development environment (PowerShell) | ~5 min |
| `quick-setup.sh` | macOS/Linux | Minimal setup with SQLite | ~2 min |
| `verify-setup.sh` | macOS/Linux | Verify and fix environment issues | ~1 min |

## What Gets Set Up

### Full Setup (`setup-dev.sh`)
- ✅ System dependencies (PostgreSQL, Redis, Python, Node.js)
- ✅ Python virtual environment + dependencies
- ✅ Node.js dependencies
- ✅ Environment configuration (.env files)
- ✅ Database creation and migrations
- ✅ Git hooks for security
- ✅ Service startup
- ✅ Verification tests

### Quick Setup (`quick-setup.sh`)
- ✅ Python virtual environment + dependencies
- ✅ Node.js dependencies
- ✅ SQLite database setup
- ✅ Basic environment configuration
- ✅ Quick verification

## Prerequisites

### macOS
- macOS 10.15+
- Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- Git, Node.js 18+, Python 3.11+

### Linux (Ubuntu/Debian)
- Ubuntu 20.04+ / Debian 11+
- Git, Node.js 18+, Python 3.11+
- `sudo` access for package installation

### Windows
- Windows 10/11
- PowerShell 5.1+
- Git for Windows
- Node.js 18+, Python 3.11+
- Administrator privileges (for service installation)

## Script Options

### setup-dev.sh / setup-dev.ps1
```bash
./scripts/setup-dev.sh [options]

Options:
  --skip-deps      Skip dependency installation
  --skip-services  Skip service setup (PostgreSQL, Redis)
  --skip-tests     Skip test execution
  --help          Show help message
```

### verify-setup.sh
```bash
./scripts/verify-setup.sh [options]

Options:
  --fix       Attempt to fix issues automatically
  --verbose   Show detailed debug output
  --help      Show help message
```

## Troubleshooting

### Common Issues

#### "Permission denied" on macOS/Linux
```bash
chmod +x scripts/*.sh
```

#### Node.js version too old
```bash
# Install/update Node.js with nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```

#### Python version too old
```bash
# Install/update Python with pyenv
curl https://pyenv.run | bash
pyenv install 3.11
pyenv global 3.11
```

#### PostgreSQL connection issues
```bash
# macOS
brew services restart postgresql@14

# Linux
sudo systemctl restart postgresql
```

#### Redis connection issues
```bash
# macOS
brew services restart redis

# Linux
sudo systemctl restart redis
```

#### Windows PowerShell execution policy
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Manual Setup

If automated setup fails, follow these manual steps:

1. **Backend Setup**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
alembic upgrade head
```

2. **Frontend Setup**
```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your configuration
npm run build
```

3. **Start Services**
```bash
# Backend
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev
```

## Environment Files

After setup, you'll have these configuration files:

- `backend/.env` - Backend configuration (database, secrets, etc.)
- `frontend/.env.local` - Frontend configuration (API URLs, features, etc.)

⚠️ **Never commit these files to git!** They contain secrets and local configuration.

## What's Next?

After successful setup:

1. **Start the application:**
   - Backend: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload`
   - Frontend: `cd frontend && npm run dev`

2. **Visit the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

3. **Development workflow:**
   - Make changes to code
   - Tests run automatically
   - Hot reload keeps everything in sync

## Getting Help

- 📖 Check the main [README.md](../README.md)
- 🐛 Run verification: `./scripts/verify-setup.sh --verbose`
- 🔧 Auto-fix issues: `./scripts/verify-setup.sh --fix`
- 📝 Check logs: Look for `setup.log` in project root
- 💬 Ask for help: Create an issue with your setup log

## Contributing

To improve these setup scripts:

1. Test on your platform
2. Add error handling for edge cases
3. Update documentation
4. Submit a pull request

The scripts are designed to be:
- ✅ Idempotent (safe to run multiple times)
- ✅ Cross-platform compatible
- ✅ Self-documenting with verbose output
- ✅ Recoverable from failures