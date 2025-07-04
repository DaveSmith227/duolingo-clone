# open-pull-request

You are given the following context:
$ARGUMENTS

## Instructions

Your task is to create a new pull request on GitHub based on the current branch and any uncommitted changes.

### Steps to follow:

1. First, check the current git status to understand what changes need to be committed
2. If there are uncommitted changes, stage and commit them with an appropriate message
3. Push the current branch to the remote repository
4. Create a pull request using the GitHub CLI (`gh pr create`)
5. Use the context provided in $ARGUMENTS to determine:
   - The PR title
   - The PR description/body
   - The target branch (default to main/master if not specified)

### Important considerations:

- If no arguments are provided, analyze the recent commits to generate an appropriate PR title and description
- Always include a clear summary of changes in the PR body
- Add a "Test plan" section if applicable
- Use the format specified in the GitHub PR creation guidelines from CLAUDE.md
- Return the PR URL after creation so the user can review it

### Example usage:
- `/open-pull-request "Add user authentication feature"`
- `/open-pull-request "Fix navigation bug in mobile view" --base develop`
- `/open-pull-request` (will auto-generate title and description from commits)