#!/bin/bash
#
# Setup script for Git hooks
# Installs pre-commit hooks for secret detection
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Git hooks...${NC}"

# Get the root directory of the git repository
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$GIT_ROOT" ]; then
    echo -e "${RED}Error: Not in a Git repository${NC}"
    exit 1
fi

cd "$GIT_ROOT"

# Configure Git to use the custom hooks directory
echo -e "${YELLOW}Configuring Git to use custom hooks directory...${NC}"
git config core.hooksPath .githooks

# Check if configuration was successful
HOOKS_PATH=$(git config core.hooksPath)
if [ "$HOOKS_PATH" = ".githooks" ]; then
    echo -e "${GREEN}✅ Git hooks directory configured successfully${NC}"
else
    echo -e "${RED}❌ Failed to configure Git hooks directory${NC}"
    exit 1
fi

# Make hooks executable
echo -e "${YELLOW}Making hooks executable...${NC}"
find .githooks -type f -exec chmod +x {} \;
chmod +x backend/scripts/detect_secrets.py 2>/dev/null || true

# Create .secrets-baseline file if it doesn't exist
BASELINE_FILE="$GIT_ROOT/.secrets-baseline"
if [ ! -f "$BASELINE_FILE" ]; then
    echo -e "${YELLOW}Creating secrets baseline file...${NC}"
    echo '{"secrets": []}' > "$BASELINE_FILE"
    echo -e "${GREEN}✅ Created .secrets-baseline${NC}"
fi

# Test Python availability
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: Python 3 not found${NC}"
    echo -e "   Secret detection requires Python 3. Please install it for full functionality."
else
    echo -e "${GREEN}✅ Python 3 detected${NC}"
fi

# Provide instructions
echo
echo -e "${GREEN}✅ Git hooks setup complete!${NC}"
echo
echo -e "${BLUE}The following hooks are now active:${NC}"
echo -e "  • ${YELLOW}pre-commit${NC}: Scans for secrets before allowing commits"
echo
echo -e "${BLUE}Usage:${NC}"
echo -e "  • Hooks will run automatically when you commit"
echo -e "  • To bypass hooks (not recommended): ${YELLOW}git commit --no-verify${NC}"
echo -e "  • To update the secrets baseline: ${YELLOW}python3 backend/scripts/detect_secrets.py --all --baseline .secrets-baseline --update-baseline${NC}"
echo
echo -e "${BLUE}To disable hooks:${NC}"
echo -e "  ${YELLOW}git config --unset core.hooksPath${NC}"
echo
echo -e "${GREEN}Happy coding! 🚀${NC}"