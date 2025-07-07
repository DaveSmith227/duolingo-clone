# Design System CLI Documentation

## Overview

The Design System CLI provides a comprehensive set of tools for extracting design tokens from screenshots, validating visual implementations, and maintaining design consistency across your application.

## Quick Start

### Installation

The CLI tools are included with the frontend project. Ensure you have all dependencies installed:

```bash
cd frontend
npm install
```

### Basic Usage

```bash
# Extract tokens from a screenshot
npm run design:extract path/to/screenshot.png

# Validate a URL against reference screenshots  
npm run design:validate http://localhost:3000

# Show cache statistics
npm run design:cache --stats

# Get help with all available commands
npm run design:help
```

## Available Commands

### Token Extraction

#### `design:extract` - Single Screenshot Extraction
Extract design tokens from a single screenshot image.

```bash
npm run design:extract <screenshot-path> [options]
```

**Arguments:**
- `screenshot-path`: Path to the screenshot image file

**Options:**
- `--output-dir <dir>`: Output directory for generated tokens (default: `./src/lib/design-system/tokens/generated`)
- `--format <format>`: Output format: `typescript`, `json`, `css`, `tailwind` (default: `typescript`)
- `--include-comments`: Include descriptive comments in generated files
- `--dry-run`: Show what would be generated without writing files
- `--verbose`: Enable detailed logging

**Example:**
```bash
npm run design:extract design-reference/landing-page/hero.png --format typescript --include-comments
```

#### `design:extract:batch` - Batch Screenshot Processing
Process multiple screenshots from a directory.

```bash
npm run design:extract:batch [options]
```

**Options:**
- `--input-dir <dir>`: Directory containing screenshots (default: `./design-reference`)
- `--output-dir <dir>`: Output directory for tokens
- `--config <file>`: Path to extraction configuration file
- `--parallel <num>`: Number of parallel extractions (default: 3)

### Visual Validation

#### `design:validate` - Single URL Validation
Validate a single URL against reference screenshots.

```bash
npm run design:validate <url> [options]
```

**Arguments:**
- `url`: URL to validate (e.g., `http://localhost:3000`)

**Options:**
- `--reference-dir <dir>`: Directory containing reference screenshots
- `--threshold <number>`: Difference threshold (0-1, default: 0.1)
- `--output-dir <dir>`: Directory for validation reports
- `--format <format>`: Report format: `html`, `json`, `markdown`
- `--viewport <preset>`: Viewport preset: `mobile`, `tablet`, `desktop`

#### `design:validate:batch` - Batch URL Validation
Validate multiple URLs using a configuration file.

```bash
npm run design:validate:batch <config-file>
```

**Configuration file example:**
```json
{
  "baseUrl": "http://localhost:3000",
  "pages": [
    { "path": "/", "name": "landing-page" },
    { "path": "/login", "name": "login-page" }
  ],
  "viewports": ["mobile", "desktop"],
  "threshold": 0.1,
  "outputDir": "./validation-reports"
}
```

#### `design:validate:compare` - Direct Image Comparison
Compare two images directly.

```bash
npm run design:validate:compare <reference-image> <actual-image> [options]
```

### Cache Management

#### `design:cache` - Cache Operations
Manage the screenshot and validation cache.

```bash
npm run design:cache [command] [options]
```

**Commands:**
- `--stats`: Show cache statistics
- `--clear`: Clear all cached data
- `--clear-screenshots`: Clear only screenshot cache
- `--clear-validations`: Clear only validation cache
- `--optimize`: Optimize cache storage

### Project Initialization

#### `design:init` - Initialize Design System
Set up design system configuration and directory structure.

```bash
npm run design:init
```

This command creates:
- Configuration files
- Directory structure
- Sample reference screenshots
- Git hooks for validation

### Incremental Updates

#### `design:update` - Incremental Token Updates
Update tokens from new screenshots without full regeneration.

```bash
npm run design:update [options]
```

**Options (passed as JSON string):**
```bash
npm run design:update '{"watchDirectory":"./new-screenshots","dryRun":true}'
```

#### `design:watch` - Watch for Changes
Continuously monitor for new screenshots and update tokens automatically.

```bash
npm run design:watch [options]
```

#### `design:add` - Add New Screenshots
Add new screenshots to the design system.

```bash
npm run design:add <comma-separated-paths> [options]
```

**Example:**
```bash
npm run design:add "screenshot1.png,screenshot2.png" '{"verbose":true}'
```

## Configuration

### Global Configuration

Create a `.design-system.config.json` file in your project root:

```json
{
  "extraction": {
    "apiEndpoint": "http://localhost:8000/api/design-system",
    "outputFormats": ["typescript", "tailwind", "css"],
    "includeComments": true,
    "ignoreMobbinWatermark": true
  },
  "validation": {
    "threshold": 0.1,
    "viewports": {
      "mobile": { "width": 375, "height": 667 },
      "tablet": { "width": 768, "height": 1024 },
      "desktop": { "width": 1440, "height": 900 }
    },
    "caching": {
      "enabled": true,
      "maxAge": 86400000,
      "maxSize": 500
    }
  },
  "directories": {
    "reference": "./design-reference",
    "output": "./src/lib/design-system/tokens/generated",
    "reports": "./design-validation-reports"
  }
}
```

### Package.json Integration

The following scripts are automatically added to your `package.json`:

```json
{
  "scripts": {
    "design:extract": "tsx src/lib/design-system/cli/extract.ts extract",
    "design:extract:batch": "tsx src/lib/design-system/cli/extract.ts batch",
    "design:validate": "tsx src/lib/design-system/cli/validate.ts validate",
    "design:validate:batch": "tsx src/lib/design-system/cli/validate.ts batch",
    "design:validate:compare": "tsx src/lib/design-system/cli/validate.ts compare",
    "design:cache": "tsx src/lib/design-system/cli/validate.ts cache",
    "design:init": "tsx src/lib/design-system/cli/validate.ts init",
    "design:update": "tsx -e 'import { runIncrementalUpdate } from \"./src/lib/design-system/cli/incremental-update\"; runIncrementalUpdate(JSON.parse(process.argv[2] || \"{}\")).then(r => console.log(JSON.stringify(r, null, 2)))'",
    "design:watch": "tsx -e 'import { watchForChanges } from \"./src/lib/design-system/cli/incremental-update\"; watchForChanges(JSON.parse(process.argv[2] || \"{}\"))'",
    "design:add": "tsx -e 'import { addNewScreenshots } from \"./src/lib/design-system/cli/incremental-update\"; addNewScreenshots(process.argv[2].split(\",\"), JSON.parse(process.argv[3] || \"{}\")).then(r => console.log(JSON.stringify(r, null, 2)))'",
    "design:help": "echo 'Design System CLI Commands:\\n  npm run design:extract <screenshot> -- Extract tokens from screenshot\\n  npm run design:validate <url> -- Validate URL against reference\\n  npm run design:validate:batch <config> -- Batch validation\\n  npm run design:validate:compare <ref> <actual> -- Compare images\\n  npm run design:cache --stats -- Show cache stats\\n  npm run design:init -- Initialize validation config\\n  npm run design:update -- Incremental update from screenshots\\n  npm run design:watch -- Watch for screenshot changes\\n  npm run design:add <paths> -- Add new screenshots'"
  }
}
```

## Workflows

### Development Workflow

1. **Initial Setup**
   ```bash
   npm run design:init
   ```

2. **Extract Tokens from Design References**
   ```bash
   npm run design:extract:batch --input-dir ./design-reference
   ```

3. **Implement Components**
   - Use generated tokens in your components
   - Follow the token naming conventions

4. **Validate Implementation**
   ```bash
   npm run design:validate http://localhost:3000
   ```

5. **Add New Screenshots**
   ```bash
   npm run design:add "new-design.png"
   ```

### CI/CD Integration

The design system includes GitHub Actions workflows that automatically:

- Validate design consistency on pull requests
- Update tokens when new screenshots are added
- Generate visual regression reports
- Cache validation results for faster builds

### Git Hooks

Pre-commit hooks automatically:
- Run visual validation on changed pages
- Ensure token consistency
- Prevent commits that break design system compliance

## Token Migration

### Migrating Between Versions

When the design system token format changes, use the migration tools:

```bash
# Check compatibility between versions
npm run design:migrate:check 1.0.0 2.0.0

# Perform migration
npm run design:migrate --from 1.0.0 --to 2.0.0

# Rollback if needed
npm run design:migrate:rollback /path/to/backup
```

### Migration Options

```json
{
  "sourceVersion": "1.0.0",
  "targetVersion": "2.0.0",
  "dryRun": true,
  "verbose": true,
  "force": false,
  "skipValidation": false
}
```

## Output Formats

### TypeScript Tokens
```typescript
export const tokens = {
  colors: {
    primary: {
      50: '#eff6ff',
      500: '#3b82f6',
      900: '#1e3a8a'
    }
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem'
  }
};
```

### Tailwind Config
```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          900: '#1e3a8a'
        }
      }
    }
  }
};
```

### CSS Variables
```css
:root {
  --color-primary-50: #eff6ff;
  --color-primary-500: #3b82f6;
  --color-primary-900: #1e3a8a;
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
}
```

## Performance Optimization

### Caching Strategy

The CLI includes intelligent caching:
- Screenshot analysis results are cached
- Token extraction is cached based on image content
- Validation results are cached by URL and viewport
- Cache automatically invalidates when source images change

### Parallel Processing

Batch operations support parallel processing:
```bash
npm run design:extract:batch --parallel 5
```

### Memory Management

For large screenshot sets, use memory optimization:
```bash
npm run test:memory  # Monitor memory usage
npm run design:cache --optimize  # Optimize cache storage
```

## Troubleshooting

### Common Issues

**1. Memory Errors During Batch Processing**
```bash
# Reduce parallel processing
npm run design:extract:batch --parallel 1

# Clear cache
npm run design:cache --clear
```

**2. Validation Threshold Too Strict**
```bash
# Increase threshold for more tolerance
npm run design:validate http://localhost:3000 --threshold 0.2
```

**3. Missing Dependencies**
```bash
# Ensure all dependencies are installed
npm install

# Check for Puppeteer issues
npx puppeteer browsers install chrome
```

### Debug Mode

Enable verbose logging for debugging:
```bash
npm run design:extract screenshot.png --verbose
npm run design:validate http://localhost:3000 --verbose
```

### Performance Monitoring

Monitor CLI performance:
```bash
# Check cache statistics
npm run design:cache --stats

# Run performance tests
npm run test:performance

# Monitor memory usage
npm run test:memory
```

## API Reference

### TokenExtractor Class

```typescript
import { TokenExtractor } from './lib/design-system/extractor/tokenizer';

const extractor = new TokenExtractor(analyzer, apiEndpoint);
const results = await extractor.extractAllTokens(imagePath, options);
```

### VisualValidator Class

```typescript
import { VisualValidator } from './lib/design-system/validator/visual-validator';

const validator = new VisualValidator(options);
const report = await validator.validateUrl(url, referenceDir);
```

### Migration System

```typescript
import { migrateTokens } from './lib/design-system/cli/migration-tools';

const result = await migrateTokens({
  sourceVersion: '1.0.0',
  targetVersion: '2.0.0',
  dryRun: false
});
```

## Contributing

### Adding New Commands

1. Create command file in `src/lib/design-system/cli/`
2. Add corresponding test file
3. Update package.json scripts
4. Update this documentation

### Testing

```bash
# Run all design system tests
npm run test:design

# Run specific test suite
npm run test -- migration-tools.test.ts

# Run with coverage
npm run test:coverage
```

## Support

For issues and questions:
- Check the troubleshooting section
- Review test files for usage examples
- Open an issue in the project repository