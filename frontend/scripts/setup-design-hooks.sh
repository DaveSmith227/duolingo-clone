#!/bin/bash
#
# Setup script for Design System Git hooks
# Configures pre-commit validation for design tokens and visual validation
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Design System Git hooks...${NC}"

# Get the root directory of the git repository
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$GIT_ROOT" ]; then
    echo -e "${RED}Error: Not in a Git repository${NC}"
    exit 1
fi

cd "$GIT_ROOT"

# Check if the main setup script has been run
if [ ! -f ".githooks/pre-commit" ]; then
    echo -e "${YELLOW}Main Git hooks not set up. Running main setup script...${NC}"
    
    if [ -f "scripts/setup-git-hooks.sh" ]; then
        bash scripts/setup-git-hooks.sh
    else
        echo -e "${RED}Error: Main Git hooks setup script not found${NC}"
        echo -e "Please run the main Git hooks setup first"
        exit 1
    fi
fi

# Ensure the pre-commit hook is executable
chmod +x .githooks/pre-commit

# Check if design system dependencies are installed
cd "$GIT_ROOT/frontend"

echo -e "${YELLOW}Checking Node.js dependencies...${NC}"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm not found${NC}"
    echo -e "Please install Node.js and npm to enable design system validation"
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
    npm install
fi

# Check for specific design system dependencies
MISSING_DEPS=()

if ! npm list tsx &> /dev/null; then
    MISSING_DEPS+=("tsx")
fi

if ! npm list commander &> /dev/null; then
    MISSING_DEPS+=("commander")
fi

if ! npm list chalk &> /dev/null; then
    MISSING_DEPS+=("chalk")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Installing missing dependencies: ${MISSING_DEPS[*]}${NC}"
    npm install "${MISSING_DEPS[@]}"
fi

# Create validation configuration if it doesn't exist
VALIDATION_CONFIG="$GIT_ROOT/frontend/validation.config.json"
if [ ! -f "$VALIDATION_CONFIG" ]; then
    echo -e "${YELLOW}Creating validation configuration...${NC}"
    npm run design:init -- --output "$VALIDATION_CONFIG"
    
    if [ -f "$VALIDATION_CONFIG" ]; then
        echo -e "${GREEN}✅ Created validation configuration${NC}"
    else
        echo -e "${YELLOW}⚠️  Failed to create validation configuration${NC}"
        echo -e "   You can create it manually by running: npm run design:init"
    fi
fi

# Create reference screenshots directory
REF_DIR="$GIT_ROOT/frontend/reference-screenshots"
if [ ! -d "$REF_DIR" ]; then
    echo -e "${YELLOW}Creating reference screenshots directory...${NC}"
    mkdir -p "$REF_DIR"
    
    # Create a sample reference file
    cat > "$REF_DIR/README.md" << EOF
# Reference Screenshots

This directory contains reference screenshots for visual validation.

## Structure

- Place reference screenshots here with descriptive names
- Use the naming pattern: \`[screen-name]-[viewport].png\`
- Examples:
  - \`home-desktop.png\`
  - \`about-mobile.png\`
  - \`login-tablet.png\`

## Usage

1. Add your reference screenshots to this directory
2. Update \`validation.config.json\` to reference the screenshots
3. Run validation: \`npm run design:validate:batch validation.config.json\`

## Git Integration

The pre-commit hook will automatically run design validation when:
- Design-related files are modified (.tsx, .css, .png, etc.)
- Token files are changed
- Visual validation configuration is updated
EOF
    
    echo -e "${GREEN}✅ Created reference screenshots directory${NC}"
fi

# Test the design system CLI commands
echo -e "${YELLOW}Testing design system CLI commands...${NC}"

# Test extract command
if npm run design:extract -- --help &> /dev/null; then
    echo -e "${GREEN}✅ Extract command working${NC}"
else
    echo -e "${YELLOW}⚠️  Extract command may have issues${NC}"
fi

# Test validate command
if npm run design:validate -- --help &> /dev/null; then
    echo -e "${GREEN}✅ Validate command working${NC}"
else
    echo -e "${YELLOW}⚠️  Validate command may have issues${NC}"
fi

# Test cache command
if npm run design:cache -- --help &> /dev/null; then
    echo -e "${GREEN}✅ Cache command working${NC}"
else
    echo -e "${YELLOW}⚠️  Cache command may have issues${NC}"
fi

# Create a git hook test
echo -e "${YELLOW}Testing Git hook integration...${NC}"

# Create a temporary test file
TEST_FILE="$GIT_ROOT/frontend/test-design-hook.css"
echo "/* Test file for design system git hook */" > "$TEST_FILE"

# Stage the test file
git add "$TEST_FILE" 2>/dev/null

# Test the pre-commit hook (dry run)
if bash "$GIT_ROOT/.githooks/pre-commit" &> /dev/null; then
    echo -e "${GREEN}✅ Git hook test passed${NC}"
else
    echo -e "${YELLOW}⚠️  Git hook test had issues (this may be expected)${NC}"
fi

# Clean up test file
git reset "$TEST_FILE" 2>/dev/null
rm -f "$TEST_FILE"

# Go back to git root
cd "$GIT_ROOT"

# Provide usage instructions
echo
echo -e "${GREEN}✅ Design System Git hooks setup complete!${NC}"
echo
echo -e "${BLUE}The following validation will now run on commit:${NC}"
echo -e "  • ${YELLOW}Design token syntax validation${NC}"
echo -e "  • ${YELLOW}Visual validation (if config exists)${NC}"
echo -e "  • ${YELLOW}Secret detection${NC}"
echo
echo -e "${BLUE}Available design system commands:${NC}"
echo -e "  • ${YELLOW}npm run design:extract <screenshot>${NC} - Extract tokens from screenshot"
echo -e "  • ${YELLOW}npm run design:validate <url>${NC} - Validate URL against reference"
echo -e "  • ${YELLOW}npm run design:validate:batch <config>${NC} - Batch validation"
echo -e "  • ${YELLOW}npm run design:init${NC} - Initialize validation config"
echo -e "  • ${YELLOW}npm run design:cache --stats${NC} - Show cache statistics"
echo -e "  • ${YELLOW}npm run design:help${NC} - Show all available commands"
echo
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Add reference screenshots to ${YELLOW}frontend/reference-screenshots/${NC}"
echo -e "  2. Update ${YELLOW}frontend/validation.config.json${NC} with your screens"
echo -e "  3. Run validation: ${YELLOW}npm run design:validate:batch validation.config.json${NC}"
echo -e "  4. Commit changes to test the hooks: ${YELLOW}git commit -m \"Test design hooks\"${NC}"
echo
echo -e "${BLUE}To disable design validation hooks:${NC}"
echo -e "  Remove the design validation section from ${YELLOW}.githooks/pre-commit${NC}"
echo
echo -e "${GREEN}Happy designing! 🎨${NC}"