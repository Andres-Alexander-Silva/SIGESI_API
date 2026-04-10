---
name: skill-creator
description: Helps the user or the agent create new Antigravity skills by generating the directory structure and SKILL.md template.
---

# Skill Creator Skill

Use this skill when you need to create a new Antigravity skill in this workspace.

## Step-by-Step Instructions

1.  **Define the Skill Purpose**: Briefly describe what the new skill will do.
2.  **Determine the Location**: 
    - The default location is `.agents/skills/<skill-name>/`.
3.  **Create Directory Structure**:
    - Create the directory: `.agents/skills/<skill-name>/`
    - Create optional directories if needed:
        - `scripts/`: For Python, Node.js, or Bash scripts.
        - `examples/`: For demonstration purposes.
        - `resources/`: For templates or extra documentation.
4.  **Create SKILL.md**:
    - Every skill MUST have a `SKILL.md` in its root folder.
    - It must start with YAML frontmatter:
        ```yaml
        ---
        name: <short-name>
        description: <A clear third-person description of the skill's capability>
        ---
        ```
    - The body should contain detailed Markdown instructions for the agent.
5.  **Add Scripts (Optional)**:
    - If scripts are needed, place them in `scripts/`.
    - Instructions in `SKILL.md` should tell the agent how to run them (e.g., "Run `python scripts/my_script.py --help` first").

## Template for SKILL.md

```markdown
---
name: [skill-name]
description: [Third person description of what the skill does]
---

# [Skill Title]

## Objectives
- [List major objectives]

## Guidelines
- [Step 1]
- [Step 2]
- [Step 3]

## Tools and Scripts
- [If any scripts are provided, list them here and how to use them]
```
