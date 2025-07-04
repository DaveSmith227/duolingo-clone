# Create Command

You are given the following context:
$ARGUMENTS

## Instructions

Your task is to create a new custom command that we can use with Claude Code.

### Command Structure

When creating a new command, follow this structure:

1. **File Path**: Create the command file in `.claude/commands/` directory
2. **File Name**: Use kebab-case naming (e.g., `my-command.md`)
3. **Content Format**: Use Markdown with clear sections

### File Format
```
# <command-name>

You are given the following context:
$ARGUMENTS

<command-here>
```