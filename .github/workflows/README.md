# GitHub Actions Workflows

This directory contains automated workflows for the design system validation and CI/CD pipeline.

## Workflows

### 1. Design System Validation (`design-system-validation.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`
- Manual dispatch with configuration options
- Only runs when design-related files are changed

**Features:**
- **Token Validation**: Syntax checking, type validation, and consistency checks
- **Visual Validation**: Screenshot-based validation using Puppeteer
- **Parallel Processing**: Efficient execution with job dependencies
- **Caching**: Intelligent caching of dependencies and validation artifacts
- **Reporting**: Detailed HTML and JSON reports with PR comments
- **Artifact Upload**: Validation reports and cache files for debugging

**Configuration:**
- Requires `frontend/validation.config.json` for visual validation
- Uses reference screenshots from `frontend/reference-screenshots/`
- Configurable timeout, concurrency, and report formats

**Manual Triggers:**
```yaml
# Validation modes:
- full: Complete validation with all checks
- quick: Fast validation with reduced concurrency
- tokens-only: Only token syntax and structure validation

# Report formats:
- html: Human-readable HTML reports
- json: Machine-readable JSON data
- both: Generate both formats
```

### 2. Design System Quick Check (`design-system-quick-check.yml`)

**Triggers:**
- Pull requests that modify design system or token files
- Focused on early feedback for development

**Features:**
- **Fast Execution**: Lightweight checks for rapid feedback
- **Code Quality**: Linting and TypeScript compilation
- **Unit Tests**: Quick validation of core functionality
- **Structure Validation**: Ensures proper file organization
- **CLI Testing**: Verifies command-line tools functionality

**Purpose:**
- Provide immediate feedback on basic issues
- Catch syntax errors and structural problems early
- Complement the full validation workflow

## Setup Requirements

### Environment Variables
- `NODE_VERSION`: Node.js version (default: '20')
- `VALIDATION_TIMEOUT`: Timeout for validation jobs (default: 300000ms)
- `CACHE_VERSION`: Cache key version for invalidation (default: 'v1')

### Dependencies
- Node.js and npm
- Chrome/Chromium for Puppeteer
- Design system CLI tools (extract, validate, cache)

### Required Files
- `frontend/package.json` with design system scripts
- `frontend/validation.config.json` (for visual validation)
- `frontend/reference-screenshots/` (for visual validation)
- Design system source code in `frontend/src/lib/design-system/`

## Usage

### Automatic Execution
Workflows run automatically based on their triggers. No manual intervention required for most cases.

### Manual Execution
1. Go to Actions tab in GitHub repository
2. Select "Design System Validation" workflow
3. Click "Run workflow"
4. Choose validation mode and report format
5. Click "Run workflow" button

### Viewing Results

**In Pull Requests:**
- Check status in the PR checks section
- View automated comments with validation summaries
- Download artifacts for detailed reports

**In Actions Tab:**
- Click on workflow run to see detailed logs
- Download artifacts from the run summary
- Review job-level results and timing

## Artifacts

### Validation Reports
- **Format**: HTML and JSON
- **Contents**: Screenshot comparisons, metrics, pass/fail status
- **Retention**: 30 days
- **Location**: `validation-reports-{run-number}` artifact

### Validation Cache
- **Contents**: Screenshot cache and Puppeteer data
- **Retention**: 7 days
- **Purpose**: Speed up subsequent runs

## Troubleshooting

### Common Issues

**"No validation configuration found"**
- Create `frontend/validation.config.json` using `npm run design:init`
- Ensure the file is committed to the repository

**"Chrome/Chromium not found"**
- The workflow installs Chrome automatically
- Local development may require manual Chrome installation

**"Validation timeout"**
- Increase `VALIDATION_TIMEOUT` environment variable
- Reduce concurrency in validation.config.json
- Use "quick" mode for faster execution

**"Token syntax errors"**
- Run TypeScript compilation locally: `npx tsc --noEmit`
- Check ESLint output: `npm run lint`
- Ensure proper import/export syntax

### Performance Optimization

**Reduce Validation Time:**
- Use path filters to limit workflow triggers
- Implement incremental validation for large changesets
- Optimize screenshot capture settings
- Use appropriate concurrency levels

**Cache Optimization:**
- Keep cache keys stable for better hit rates
- Clear cache when dependencies change significantly
- Monitor cache size and eviction policies

## Configuration Examples

### Basic validation.config.json
```json
{
  "screens": [
    {
      "id": "home",
      "name": "Home Page",
      "url": "http://localhost:3000",
      "referenceImage": "./reference-screenshots/home-desktop.png",
      "viewport": "desktop",
      "threshold": 5
    }
  ],
  "settings": {
    "defaultThreshold": 5,
    "timeout": 30000,
    "retries": 2,
    "concurrent": 2
  }
}
```

### Performance-optimized settings
```json
{
  "settings": {
    "defaultThreshold": 10,
    "timeout": 15000,
    "retries": 1,
    "concurrent": 3,
    "enableCache": true,
    "headless": true
  }
}
```

## Integration with Development Workflow

### Recommended Branch Strategy
1. **Feature branches**: Quick check runs on PR creation
2. **Develop branch**: Full validation on merge
3. **Main branch**: Complete validation with artifact retention

### Quality Gates
- Prevent merging PRs with failing validations
- Require manual review for validation bypasses
- Use draft PRs for work-in-progress changes

### Monitoring and Alerts
- Set up notifications for validation failures
- Monitor workflow execution times and success rates
- Track artifact storage usage and costs

## Security Considerations

- Workflows run in isolated environments
- No access to production secrets or data
- Screenshot data is temporary and auto-deleted
- Use read-only tokens for external integrations

## Maintenance

### Regular Tasks
- Update Node.js version quarterly
- Review and update timeout settings
- Clean up old artifacts and caches
- Monitor workflow execution trends

### Dependency Updates
- Keep Chrome version synchronized with Puppeteer
- Update design system CLI tools as needed
- Maintain compatibility with validation libraries