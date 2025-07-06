#!/bin/bash

# =============================================================================
# Generate All Configuration Documentation
# =============================================================================
#
# This script generates comprehensive configuration documentation for both
# frontend and backend components, including validation rules, examples,
# and environment-specific guidelines.
#
# Usage:
#   ./scripts/generate-all-docs.sh [--output-dir docs] [--format all]
#
# Options:
#   --output-dir DIR    Output directory for documentation (default: docs/generated)
#   --format FORMAT     Output format: markdown, html, json, all (default: all)
#   --clean            Clean output directory before generation
#   --serve            Start a local server to view HTML docs
#   --help             Show this help message
#
# Generated Documentation:
#   - Backend configuration (Pydantic models)
#   - Frontend configuration (TypeScript interfaces)
#   - Combined configuration overview
#   - Environment setup guides
#   - Security best practices
#   - Troubleshooting guides
#
# =============================================================================

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
OUTPUT_DIR="$PROJECT_ROOT/docs/generated"
FORMAT="all"
CLEAN=false
SERVE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --serve)
            SERVE=true
            shift
            ;;
        --help)
            echo "Configuration Documentation Generator"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --output-dir DIR    Output directory (default: docs/generated)"
            echo "  --format FORMAT     Output format: markdown, html, json, all"
            echo "  --clean            Clean output directory before generation"
            echo "  --serve            Start local server to view HTML docs"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Generate all formats"
            echo "  $0 --format markdown                 # Generate only Markdown"
            echo "  $0 --output-dir ./my-docs --clean    # Custom output with cleanup"
            echo "  $0 --serve                           # Generate and serve docs"
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
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

check_prerequisites() {
    step "Checking prerequisites..."
    
    local missing=()
    
    # Check Python (for backend docs)
    if ! command -v python3 >/dev/null 2>&1; then
        missing+=("python3")
    fi
    
    # Check Node.js (for frontend docs)
    if ! command -v node >/dev/null 2>&1; then
        missing+=("node")
    fi
    
    # Check if virtual environment exists for backend
    if [ ! -d "$PROJECT_ROOT/backend/venv" ]; then
        warning "Backend virtual environment not found. Run setup-dev.sh first."
    fi
    
    # Check if node_modules exists for frontend
    if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
        warning "Frontend dependencies not found. Run 'npm install' in frontend directory."
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        error "Missing required dependencies: ${missing[*]}"
        error "Please install them and run this script again"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

clean_output_dir() {
    if [ "$CLEAN" = true ]; then
        step "Cleaning output directory..."
        if [ -d "$OUTPUT_DIR" ]; then
            rm -rf "$OUTPUT_DIR"
            log "Removed existing output directory"
        fi
    fi
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    log "Created output directory: $OUTPUT_DIR"
}

generate_backend_docs() {
    step "Generating backend configuration documentation..."
    
    cd "$PROJECT_ROOT/backend"
    
    # Check if virtual environment is activated or activate it
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            log "Activated Python virtual environment"
        else
            error "Virtual environment not found. Run setup-dev.sh first."
            return 1
        fi
    fi
    
    # Run backend documentation generator
    if python scripts/generate_config_docs.py --output-dir "$OUTPUT_DIR" --format "$FORMAT"; then
        success "Backend documentation generated successfully"
    else
        error "Failed to generate backend documentation"
        return 1
    fi
}

generate_frontend_docs() {
    step "Generating frontend configuration documentation..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # Check if we have tsx/ts-node available
    if ! command -v npx >/dev/null 2>&1; then
        error "npx not found. Node.js installation may be incomplete."
        return 1
    fi
    
    # Run frontend documentation generator
    if npx tsx scripts/generate-config-docs.ts --output-dir "$OUTPUT_DIR" --format "$FORMAT"; then
        success "Frontend documentation generated successfully"
    else
        warning "Frontend documentation generator failed. Continuing with backend docs only."
    fi
}

generate_overview_docs() {
    step "Generating configuration overview documentation..."
    
    # Create a comprehensive overview document
    cat > "$OUTPUT_DIR/configuration-overview.md" << 'EOF'
# Configuration Overview

This document provides a comprehensive overview of the configuration system for the Duolingo Clone application.

## Architecture

The configuration system is split between frontend and backend components:

- **Backend Configuration**: Python-based using Pydantic for validation and type safety
- **Frontend Configuration**: TypeScript-based using Zod for runtime validation
- **Environment Variables**: Shared configuration through environment variables
- **Security**: Multi-layered approach with field-level permissions and audit logging

## Quick Start

### 1. Environment Setup

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your configuration

# Frontend  
cp frontend/.env.example frontend/.env.local
# Edit frontend/.env.local with your configuration
```

### 2. Required Configuration

**Backend (minimum required):**
- `SECRET_KEY`: Cryptographic secret for sessions/JWT
- `DATABASE_URL`: Database connection string (optional for SQLite)
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anonymous key

**Frontend (minimum required):**
- `NEXT_PUBLIC_API_URL`: Backend API URL
- `NEXT_PUBLIC_SUPABASE_URL`: Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase anonymous key

### 3. Environment-Specific Settings

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| DEBUG | ✅ true | ❌ false | ❌ false |
| Database | SQLite | PostgreSQL | PostgreSQL |
| HTTPS | ❌ Optional | ✅ Required | ✅ Required |
| Secrets | Default OK | Staging secrets | Production secrets |

## Configuration Files

| File | Purpose | Committed to Git |
|------|---------|------------------|
| `.env.example` | Template and documentation | ✅ Yes |
| `.env` / `.env.local` | Actual configuration | ❌ No |
| `.env.development` | Development defaults | ✅ Yes (no secrets) |
| `.env.production` | Production defaults | ✅ Yes (no secrets) |

## Security Model

### 1. Field-Level Security

- **Public**: Safe to expose (app name, version)
- **Internal**: Application configuration (timeouts, features)
- **Sensitive**: Secrets and keys (never logged or exposed)

### 2. Access Control

- **Role-Based Permissions**: Different roles have different access levels
- **Environment Restrictions**: Production has stricter controls
- **Audit Logging**: All configuration access is logged

### 3. Validation Framework

- **Type Safety**: Pydantic (backend) and Zod (frontend) validation
- **Business Rules**: Custom validators for complex requirements
- **Environment-Specific**: Different rules per environment

## Common Configuration Patterns

### Database Configuration

```bash
# Development (SQLite)
# DATABASE_URL not needed - uses SQLite by default

# Production (PostgreSQL)
DATABASE_URL="postgresql://user:password@host:port/dbname"
```

### API URLs

```bash
# Development
NEXT_PUBLIC_API_URL="http://localhost:8000"

# Production  
NEXT_PUBLIC_API_URL="https://api.yourdomain.com"
```

### Feature Flags

```bash
# Enable/disable features
NEXT_PUBLIC_ENABLE_ANALYTICS="true"
NEXT_PUBLIC_ENABLE_DEBUG="false"
NEXT_PUBLIC_ENABLE_EXPERIMENTAL="false"
```

## Troubleshooting

### Common Issues

1. **"Configuration validation failed"**
   - Check for missing required variables
   - Verify value formats (URLs, numbers, booleans)
   - Check environment-specific requirements

2. **"SECRET_KEY too short"**
   - Generate secure key: `openssl rand -hex 32`
   - Must be at least 32 characters

3. **"Database connection failed"**
   - Verify DATABASE_URL format
   - Check database server is running
   - Confirm credentials and permissions

4. **"CORS errors in browser"**
   - Check CORS_ORIGINS includes frontend URL
   - Verify protocol (http vs https)
   - Check port numbers

### Validation Commands

```bash
# Backend validation
cd backend && python -c "from app.core.config import Settings; Settings()"

# Frontend validation  
cd frontend && npm run build
```

## Documentation

- [Backend Configuration](./configuration.md) - Complete backend configuration reference
- [Frontend Configuration](./frontend-configuration.md) - Complete frontend configuration reference
- [Setup Scripts](../scripts/README.md) - Automated setup documentation

## Support

If you encounter issues:

1. Check the validation error messages
2. Review the environment-specific guidelines
3. Run the verification script: `./scripts/verify-setup.sh --verbose`
4. Check the setup logs for detailed error information

For additional help, consult the individual configuration documentation files or create an issue with your configuration (remove any secrets first).
EOF

    success "Configuration overview generated"
}

generate_index_html() {
    if [ "$FORMAT" = "html" ] || [ "$FORMAT" = "all" ]; then
        step "Generating documentation index..."
        
        cat > "$OUTPUT_DIR/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configuration Documentation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            background-color: #f8f9fa;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2563eb;
            border-bottom: 3px solid #e5e7eb;
            padding-bottom: 15px;
        }
        .doc-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .doc-card {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #2563eb;
        }
        .doc-card h3 {
            margin-top: 0;
            color: #1f2937;
        }
        .doc-card a {
            color: #2563eb;
            text-decoration: none;
            font-weight: 500;
        }
        .doc-card a:hover {
            text-decoration: underline;
        }
        .quick-links {
            background-color: #e0f2fe;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 Configuration Documentation</h1>
        
        <p>Welcome to the comprehensive configuration documentation for the Duolingo Clone application. This documentation covers all aspects of configuring both the frontend and backend components.</p>
        
        <div class="quick-links">
            <h3>🚀 Quick Start</h3>
            <p>New to the project? Start here:</p>
            <ol>
                <li>Run the setup script: <code>./scripts/setup-dev.sh</code></li>
                <li>Read the <a href="#overview">Configuration Overview</a></li>
                <li>Configure your <a href="#backend">Backend Settings</a></li>
                <li>Configure your <a href="#frontend">Frontend Settings</a></li>
            </ol>
        </div>
        
        <div class="doc-grid">
            <div class="doc-card" id="overview">
                <h3>📋 Configuration Overview</h3>
                <p>High-level overview of the configuration system, architecture, and common patterns.</p>
                <a href="configuration-overview.md">View Overview →</a>
            </div>
            
            <div class="doc-card" id="backend">
                <h3>⚙️ Backend Configuration</h3>
                <p>Complete backend configuration reference with Pydantic models, validation rules, and examples.</p>
                <a href="configuration.html">View Backend Docs →</a>
            </div>
            
            <div class="doc-card" id="frontend">
                <h3>🎨 Frontend Configuration</h3>
                <p>Frontend configuration guide covering Next.js environment variables, TypeScript interfaces, and client-side settings.</p>
                <a href="frontend-configuration.html">View Frontend Docs →</a>
            </div>
            
            <div class="doc-card">
                <h3>🔒 Security Guidelines</h3>
                <p>Security best practices, secret management, and environment-specific security requirements.</p>
                <a href="configuration.html#security-best-practices">View Security Guide →</a>
            </div>
            
            <div class="doc-card">
                <h3>🛠️ Setup Scripts</h3>
                <p>Automated setup scripts for different environments and platforms.</p>
                <a href="../scripts/README.md">View Setup Guide →</a>
            </div>
            
            <div class="doc-card">
                <h3>🔍 Troubleshooting</h3>
                <p>Common issues, validation errors, and their solutions.</p>
                <a href="configuration-overview.md#troubleshooting">View Troubleshooting →</a>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated on: <script>document.write(new Date().toLocaleString())</script></p>
            <p>For the latest documentation, regenerate using: <code>./scripts/generate-all-docs.sh</code></p>
        </div>
    </div>
</body>
</html>
EOF
        
        success "Documentation index generated"
    fi
}

serve_docs() {
    if [ "$SERVE" = true ]; then
        step "Starting documentation server..."
        
        if command -v python3 >/dev/null 2>&1; then
            log "Starting Python HTTP server on http://localhost:8080"
            log "Press Ctrl+C to stop the server"
            cd "$OUTPUT_DIR"
            python3 -m http.server 8080
        elif command -v node >/dev/null 2>&1; then
            log "Starting Node.js HTTP server on http://localhost:8080"
            log "Press Ctrl+C to stop the server"
            cd "$OUTPUT_DIR"
            npx http-server -p 8080
        else
            warning "No HTTP server available. Install Python or Node.js to serve docs."
            log "You can manually open: $OUTPUT_DIR/index.html"
        fi
    fi
}

print_summary() {
    echo ""
    echo "============================================================================="
    echo -e "${CYAN}📚 DOCUMENTATION GENERATION COMPLETE! 📚${NC}"
    echo "============================================================================="
    echo ""
    echo -e "${GREEN}✅ Successfully generated configuration documentation${NC}"
    echo ""
    echo "📂 Output directory: $OUTPUT_DIR"
    echo "📝 Format: $FORMAT"
    echo ""
    echo "📖 Generated files:"
    if [ -f "$OUTPUT_DIR/configuration.md" ]; then
        echo "   • configuration.md (Backend configuration)"
    fi
    if [ -f "$OUTPUT_DIR/frontend-configuration.md" ]; then
        echo "   • frontend-configuration.md (Frontend configuration)"
    fi
    if [ -f "$OUTPUT_DIR/configuration-overview.md" ]; then
        echo "   • configuration-overview.md (Complete overview)"
    fi
    if [ -f "$OUTPUT_DIR/index.html" ]; then
        echo "   • index.html (Documentation portal)"
    fi
    echo ""
    echo "🌐 View documentation:"
    if [ -f "$OUTPUT_DIR/index.html" ]; then
        echo "   • Open: file://$OUTPUT_DIR/index.html"
        echo "   • Or run: $0 --serve"
    fi
    echo ""
    echo "🔄 Regenerate docs: $0"
    echo "============================================================================="
}

main() {
    echo "============================================================================="
    echo -e "${CYAN}📚 Configuration Documentation Generator${NC}"
    echo "============================================================================="
    echo ""
    
    check_prerequisites
    clean_output_dir
    
    # Generate backend documentation
    if generate_backend_docs; then
        success "Backend documentation completed"
    else
        error "Backend documentation failed"
        exit 1
    fi
    
    # Generate frontend documentation
    generate_frontend_docs
    
    # Generate overview and index
    generate_overview_docs
    generate_index_html
    
    print_summary
    
    # Serve docs if requested
    serve_docs
}

# Run main function
main "$@"