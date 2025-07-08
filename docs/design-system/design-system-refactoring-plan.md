# Design System Refactoring Plan

## Overview
This document outlines the systematic refactoring of the design system extraction codebase to address violations of adapted Sandi Metz principles and improve maintainability.

## Refactoring Phases

### Phase 1: High Priority Issues (Days 1-3)

#### 1.1 Split ReportGenerator (Day 1)
**File**: `src/lib/design-system/validator/reports.ts` (1278 lines → ~200 lines each)

**New Structure**:
```
validator/
├── reports/
│   ├── index.ts                    # Main exports
│   ├── types.ts                    # Shared types
│   ├── report-orchestrator.ts      # Main coordinator (~200 lines)
│   ├── data-processor.ts           # Data processing (~150 lines)
│   ├── builders/
│   │   ├── html-builder.ts         # HTML generation (~200 lines)
│   │   ├── markdown-builder.ts     # Markdown generation (~150 lines)
│   │   └── json-builder.ts         # JSON generation (~100 lines)
│   ├── asset-manager.ts            # Image/asset handling (~150 lines)
│   └── style-generator.ts          # CSS/JS generation (~200 lines)
```

**Tasks**:
- [ ] Create new directory structure
- [ ] Extract interfaces and types
- [ ] Move HTML generation logic to HTMLReportBuilder
- [ ] Move Markdown generation to MarkdownReportBuilder
- [ ] Extract asset management to ReportAssetManager
- [ ] Create ReportOrchestrator to coordinate
- [ ] Update imports across codebase
- [ ] Run tests to ensure no regression

#### 1.2 Refactor Large CLI Methods (Day 2)
**Files**: 
- `src/lib/design-system/cli/validate.ts` (773 lines)
- `src/lib/design-system/cli/extract.ts` (400+ lines)

**Refactoring setupCommands() (82 lines → 6 methods of ~15 lines)**:
- setupValidateCommand()
- setupBatchCommand()
- setupCompareCommand()
- setupCacheCommand()
- setupReportCommand()
- setupInitCommand()

**Tasks**:
- [ ] Break down setupCommands() into focused methods
- [ ] Extract command builders to separate files
- [ ] Create command factory pattern
- [ ] Simplify action handlers
- [ ] Add unit tests for each command setup

#### 1.3 Fix API Inconsistencies (Day 3)
**Files**: 
- `src/lib/design-system/validator/puppeteer-capture.ts`
- `src/lib/design-system/extractor/tokenizer.ts`

**Issues to Fix**:
- captureMultipleViewports returns error object instead of throwing
- Inconsistent error handling between sync/async methods
- Mixed return types for similar operations

**Tasks**:
- [ ] Standardize error handling (throw vs return)
- [ ] Fix return type inconsistencies
- [ ] Create custom error classes
- [ ] Update tests for new error handling
- [ ] Document API contracts

### Phase 2: Medium Priority Issues (Days 4-5)

#### 2.1 Extract Business Logic from CLI (Day 4)
**Create Service Layer**:
```
services/
├── validation-service.ts      # Validation business logic
├── extraction-service.ts      # Token extraction logic
├── migration-service.ts       # Migration business logic
└── cache-service.ts          # Cache management logic
```

**Tasks**:
- [ ] Create service classes for each domain
- [ ] Move business logic from CLI actions to services
- [ ] Keep CLI focused on parsing and display
- [ ] Add dependency injection for testability
- [ ] Create integration tests for services

#### 2.2 Reduce File Sizes (Day 4-5)
**Target Files**:
- `overlay-visualizer.ts` (1055 → ~300 lines per file)
- `documentation-generator.ts` (1004 → ~300 lines per file)
- `migration-tools.ts` (749 → ~250 lines per file)
- `versioning.ts` (709 → ~250 lines per file)

**Tasks**:
- [ ] Split overlay-visualizer by visualization mode
- [ ] Extract documentation templates to separate files
- [ ] Split migration tools by migration type
- [ ] Separate version comparison from storage
- [ ] Update imports and tests

#### 2.3 Improve Error Handling (Day 5)
**Create Error Hierarchy**:
```typescript
// errors/index.ts
export class DesignSystemError extends Error {}
export class ExtractionError extends DesignSystemError {}
export class ValidationError extends DesignSystemError {}
export class GenerationError extends DesignSystemError {}
```

**Tasks**:
- [ ] Create custom error classes
- [ ] Standardize error messages
- [ ] Add error recovery strategies
- [ ] Implement consistent logging
- [ ] Add error documentation

### Phase 3: Low Priority Issues (Day 6)

#### 3.1 Improve Naming
**Rename Methods**:
- `processResult()` → `processValidationResult()`
- `generate()` → `generateHTMLReport()` / `generateMarkdownReport()`
- `handle()` → `handleValidationRequest()` / `handleExtractionRequest()`

#### 3.2 Implement Patterns
**Builder Pattern for Reports**:
```typescript
const report = new ReportBuilder()
  .withTitle("Validation Report")
  .withFormat("html")
  .withMetrics(true)
  .withVisualizations(true)
  .build();
```

#### 3.3 Add Error Scenario Tests
- Network failure tests
- Invalid input tests
- Timeout handling tests
- Memory limit tests

## Implementation Schedule

| Day | Tasks | Files Affected |
|-----|-------|----------------|
| 1 | Split ReportGenerator | reports.ts → reports/* |
| 2 | Refactor CLI methods | validate.ts, extract.ts |
| 3 | Fix API inconsistencies | puppeteer-capture.ts, tokenizer.ts |
| 4 | Extract business logic | cli/* → services/* |
| 5 | Reduce file sizes | 4 large files → 12 focused files |
| 6 | Low priority improvements | Various |

## Success Metrics

- No file >300 lines (except test files)
- No method >15 lines (except where complexity justified)
- All tests passing
- Performance unchanged or improved
- 100% backward compatibility

## Testing Strategy

1. **Before Each Refactor**:
   - Run full test suite
   - Record performance metrics
   - Create snapshot of current behavior

2. **After Each Refactor**:
   - Run tests to ensure no regression
   - Compare performance metrics
   - Update documentation

3. **Integration Testing**:
   - End-to-end tests remain unchanged
   - Add new unit tests for extracted components
   - Verify API compatibility

## Rollback Plan

- Each refactoring in separate PR
- Feature flags for major changes
- Maintain old code paths temporarily
- Gradual migration for consumers