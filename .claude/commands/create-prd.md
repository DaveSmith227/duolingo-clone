# create-prd

You are given the following context:
$ARGUMENTS

## Instructions

Your task is to create a detailed Product Requirements Document (PRD) in Markdown format based on an initial user prompt. The PRD should be clear, actionable, and suitable for a junior developer to understand and implement.

### Process

1. **Receive Initial Prompt:** The user provides a brief description or request for a new feature or functionality.

2. **Ask Clarifying Questions:** Before writing the PRD, you *must* ask clarifying questions to gather sufficient detail. Focus on understanding the "what" and "why" of the feature, not the "how" (which the developer will determine).

3. **Generate PRD:** Based on the initial prompt and user's answers, create a comprehensive PRD using the structure below.

4. **Save PRD:** Save the document using the naming convention `prd-###-[feature-name].md` where ### is the next incremental number based on existing PRD files in the `/product-requirements/prds/` directory.

### Clarifying Questions

Adapt questions based on the prompt, but explore these areas:

- **Problem/Goal:** "What problem does this feature solve? What's the main goal?"
- **Target User:** "Who is the primary user of this feature?"
- **Core Functionality:** "What key actions should users be able to perform?"
- **User Stories:** "Can you provide user stories? (As a [user type], I want to [action] so that [benefit])"
- **Acceptance Criteria:** "How will we know this feature is successfully implemented?"
- **Scope/Boundaries:** "What should this feature NOT do (non-goals)?"
- **Data Requirements:** "What data does this feature need to display or manipulate?"
- **Design/UI:** "Are there design mockups or UI guidelines to follow?"
- **Edge Cases:** "What potential edge cases or error conditions should we consider?"

### PRD Structure

Generate a PRD with these sections:

1. **Introduction/Overview:** Brief feature description and problem it solves
2. **Goals:** Specific, measurable objectives
3. **User Stories:** Detailed user narratives with usage and benefits
4. **Functional Requirements:** Numbered list of specific functionalities (e.g., "The system must allow users to upload a profile picture")
5. **Non-Goals (Out of Scope):** What this feature will NOT include
6. **Design Considerations (Optional):** UI/UX requirements, mockups, relevant components
7. **Technical Considerations (Optional):** Known constraints, dependencies, integration points
8. **Success Metrics:** How success will be measured
9. **Open Questions:** Remaining questions or areas needing clarification

### Target Audience

Write for a **junior developer**. Requirements should be:
- Explicit and unambiguous
- Free of jargon where possible
- Detailed enough to understand purpose and core logic

### Output Requirements

- **Format:** Markdown (.md)
- **Location:** `/product-requirements/prds/`
- **Filename:** `prd-###-[feature-name].md` (where ### is the next incremental number)

### Execution Steps

1. **Check existing PRDs:** First, check the `/product-requirements/prds/` directory to find the highest numbered PRD file (e.g., if `prd-001-backend-architecture.md` exists, the next number would be `002`)
2. Ask clarifying questions based on the user's initial prompt
3. Wait for user responses
4. Generate comprehensive PRD using the structure above
5. Save to `/product-requirements/prds/prd-###-[feature-name].md` (where ### is the next incremental number with zero-padding)

**Important:** Do NOT start implementing the feature - only create the PRD document.