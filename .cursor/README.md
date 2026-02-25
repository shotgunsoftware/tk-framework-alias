# Cursor Setup for tk-framework-alias

This folder contains Cursor skills and rules that help with development workflows in this project.

## Skills

Skills are reusable workflows you can invoke in Cursor chat. Reference them by name or describe what you want to do.

### snyk-update-python-packages

Updates Python packages for Snyk security: creates a Jira issue, creates a git branch with JIRA issue key, runs the update script per Python version, commits, and opens a PR.

**Usage examples:**

```bash
@snyk-update-python-packages Run workflow, Jira project <JIRA_PROJECT>, python 3.10 3.11
```

**Prerequisites:** `JIRA_PROJECT`, `JIRA_BASE_URL`, `JIRA_TOKEN`, `JIRA_USER` (and optionally `JIRA_ASSIGNEE`). See [skills/snyk-update-python-packages/SKILL.md](skills/snyk-update-python-packages/SKILL.md) for full details.

```bash
export JIRA_PROJECT=PROJ
export JIRA_BASE_URL=https://jira.example.com
export JIRA_TOKEN=your_bearer_token
export JIRA_USER=your_username
# export JIRA_ASSIGNEE=assignee_username  # optional
```

---

*More skills will be added here as they are created.*

## Rules

Rules provide persistent guidance for the AI (coding standards, security practices, project conventions). They apply automatically when working in this project.

- **Workspace rules** — Check `.cursor/rules/` for project-specific rules (`.mdc` files).
- **Global rules** — User-level rules in Cursor settings may also apply.

---

*More rules will be documented here as they are added.*
