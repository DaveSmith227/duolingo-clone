# Complete Tasks Command

Execute systematic task completion with user confirmation checkpoints.

## Usage
```
/complete-tasks [task-file-path]
```

## Process

### Pre-Execution Setup
1. **Load task file** - Read the specified markdown task file
2. **Identify next parent task** - Find the first incomplete parent task `[ ]`
3. **Initialize TodoWrite** - Create todo items for all subtasks under the current parent task

### Task Execution Loop

#### Sub-task Completion
1. **Mark subtask in-progress** - Update TodoWrite status to `in_progress`
2. **Implement the subtask** - Write/modify code as required
3. **Apply adapted Sandi Metz principles** - Ensure code follows:
   - **Most important**: Single Responsibility Principle (each class/method has one reason to change)
   - Extract methods if >10 lines (relaxed for complex game logic and UI components)
   - Limit parameters to <6 (relaxed for complex functions like game state management)
   - Refactor for readability and maintainability over strict line limits
   - Allow complexity for interactive features, animations, and media handling
4. **Mark subtask complete** - Update both TodoWrite and markdown file `[x]`
5. **Update "Relevant Files" section** - Add/update file entries with descriptions

#### Parent Task Completion Protocol
When all subtasks under a parent task are complete:

1. **Run unit tests** - Execute test suite, use Puppeteer for UI screenshots if needed
   - Verify tests follow "Arrange, Act, Assert" pattern
   - Ensure test methods are small and focused on single behavior
2. **Code quality review** - Apply adapted Sandi Metz principles:
   - Classes <200 lines (relaxed for complex UI components and game logic)
   - Methods <10 lines (relaxed for animation, audio, and game mechanics)
   - **Prioritize**: Single Responsibility Principle and testability
   - Prefer composition over inheritance
   - Design for dependency injection and testability
   - Allow complexity where needed for game features and interactive elements
3. **Mark parent task complete** - Change `[ ]` to `[x]` in markdown file
3. **Append detailed review** - Add comprehensive review section to the task file covering:
   - Changes implemented
   - Technical decisions and reasoning
   - Files modified/created
   - Testing results
4. **User checkpoint** - Display: "I have completed [parent task #] - [description]. Ready for next parent task? Respond with 'Go' to proceed."
5. **Wait for confirmation** - Pause execution until user responds with "Go", "Yes", or "y"
6. **Create commit and PR** - Use `/open-pull-request` command to commit changes and create pull request
7. **Move to next parent task** - Repeat process for next incomplete parent task

### Continuous Maintenance
- Update task file after each significant change
- Mark tasks and subtasks as completed ([x]) per the protocol
- Add newly discovered tasks as they emerge
- Keep "Relevant Files" section current and accurate
- Use TodoWrite tool to track current progress and provide user visibility

### Exit Conditions
- All parent tasks marked complete `[x]`
- User provides stop instruction
- Error requiring user intervention

## Implementation Notes
- Uses TodoWrite/TodoRead for progress tracking
- Integrates with git for commit management
- Supports Puppeteer for UI testing and screenshots
- Maintains markdown task file as source of truth
- Enforces user confirmation at parent task boundaries