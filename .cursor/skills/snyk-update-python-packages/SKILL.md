---
name: snyk-update-python-packages
description: Sequential workflow: create Jira issue, create branch, run update_python_packages.py per Python version, commit/push, open PR. Steps must run in order. Use when updating Python packages for Snyk, creating a Snyk PR, or updating tk-framework-alias dependencies.
---

# Snyk Update Python Packages

Workflow to create a Jira issue, update Python packages in tk-framework-alias, create a branch, run the update script per Python version, and open a PR.

## Prerequisites

- Working directory: tk-framework-alias repo root
- The script `dev/update_python_packages.py` uses `sys.version_info` to target `dist/Python/Python{major}{minor}/` — invoke it with each Python interpreter

### Jira API setup

Create a Jira issue. Use environment variables for credentials (never hardcode):

- `JIRA_PROJECT` — **Required.** Jira project key. If not set and not provided by the user in the prompt, stop immediately before doing anything and ask: "Please provide the Jira project key (e.g. SHOT) or export JIRA_PROJECT."
- `JIRA_BASE_URL` — **Required.** Jira instance URL (no trailing slash). Use `$JIRA_BASE_URL` in all API calls. If not set, stop and ask: "Please export JIRA_BASE_URL (e.g. export JIRA_BASE_URL=https://jira.example.com)."
- `JIRA_TOKEN` — **Required.** Bearer token for API auth. Use `Authorization: Bearer $JIRA_TOKEN` (not Basic Auth). If not set, stop and ask the user to export it.
- `JIRA_USER` — **Required.** Jira username for API auth. If not set, stop and ask the user to export it.
- `JIRA_ASSIGNEE` — Optional. Username for assignee. For Jira Server/Data Center, the assignee uses `name`. To find by display name: `curl -s -H "Authorization: Bearer $JIRA_TOKEN" "$JIRA_BASE_URL/rest/api/2/user/search?username=..."`.

### GitHub CLI (gh) setup for SAML/SSO orgs

If the repo is in an organization with SAML/SSO `gh pr create` will fail until the token is authorized:

1. **Re-authenticate**: Run `gh auth login` and complete the flow. When prompted, authorize for the organization.
2. **Or use a Personal Access Token**: GitHub Settings → Developer settings → Personal access tokens → Create token (classic). Required scopes: `repo`, `read:org`. For fine-grained tokens, enable **Pull requests** with read/write. Then click **Configure SSO** next to the token and **Authorize** for the organization.
3. **One-time authorization**: If `gh pr create` fails with a URL like `https://github.com/enterprises/.../sso?authorization_request=...`, open that URL in a browser and authorize. After that, `gh` should work for that org.
4. **Token in shell profile**: Set `export GH_TOKEN="ghp_xxx"` in `~/.bashrc` or `~/.bash_profile`. gh will use it. Ensure the token is authorized for SAML/SSO orgs. Do not commit the profile if it contains the token.

## Python Version Selection

- **Default**: List `dist/Python/` and parse folder names `Python37`, `Python310`, etc. to get versions `(3,7)`, `(3,10)`, etc.
- **Override**: If the user specifies versions (e.g., "use python 3.10 and 3.11"), use only those.

**Which Python is used?** The script reads `sys.version_info` from the interpreter that runs it. So the version that gets updated is the version of the Python executable you invoke — e.g., running with Python 3.10 updates `dist/Python/Python310/`.

### Finding Python on Windows (when user specifies versions)

When the user specifies versions (e.g., "use python 3.10 and 3.11"), look for Python in `C:\Program Files`:

- `C:\Program Files\Python310\python.exe`
- `C:\Program Files\Python311\python.exe`

Or `C:\Program Files\Python 3.10\`, `C:\Program Files\Python 3.11\` (with space). Invoke directly if found, e.g.:

```powershell
& "C:\Program Files\Python310\python.exe" dev/update_python_packages.py
```

If not in Program Files, try `py -3.10` / `py -3.11` (py launcher) or `C:\Users\<user>\AppData\Local\Programs\Python\Python310\python.exe`.

## Workflow

**CRITICAL: Execute steps strictly in order. Do not parallelize or reorder. Each step depends on the previous one. Complete Step N fully before starting Step N+1. The pre-step must run first — if JIRA_PROJECT, JIRA_BASE_URL, JIRA_TOKEN, or JIRA_USER is not set or provided, stop and ask before doing anything.**

Copy this checklist and mark items as you complete them:

```
Task Progress:
- [ ] Pre-step: Verify JIRA_PROJECT, JIRA_BASE_URL, JIRA_TOKEN, and JIRA_USER are set (env or user prompt)
- [ ] Step 0: Create Jira issue, assign, transition to In Progress
- [ ] Step 1: Create branch $ISSUE_KEY/snyk-update-packages
- [ ] Step 2: Run update_python_packages.py per Python version
- [ ] Step 3: Commit and push
- [ ] Step 4: Create PR
```

### Pre-step: Verify JIRA_PROJECT, JIRA_BASE_URL, JIRA_TOKEN, and JIRA_USER

**Before doing anything else**, check that all required variables are available:

1. **JIRA_PROJECT**: Check if set in the environment. If not, check if the user provided the project key in their prompt (e.g. "use SHOT", "project PROJ", "Jira project: SHOT"). If neither, **stop immediately** and ask: "Please provide the Jira project key (e.g. SHOT) or export JIRA_PROJECT." If the user provided it in the prompt, set it for the session: `export JIRA_PROJECT=<key>`.
2. **JIRA_BASE_URL**: Check if set in the environment. If not, **stop immediately** and ask: "Please export JIRA_BASE_URL (e.g. export JIRA_BASE_URL=https://jira.example.com)." Do not use hardcoded fallback URLs.
3. **JIRA_TOKEN**: Check if set in the environment. If not, **stop immediately** and ask the user to export it.
4. **JIRA_USER**: Check if set in the environment. If not, **stop immediately** and ask the user to export it.

Do not create issues, branches, or run any commands until all four are confirmed. Only after all are set, proceed to Step 0.

### Step 0: Create Jira issue

Create a Jira issue in project `$JIRA_PROJECT` with the following details, then assign (if `JIRA_ASSIGNEE` is set) and set status to In Progress.

**Issue fields:**
- Project: `$JIRA_PROJECT`
- Title: Snyk: Update Python Package
- Component: tk-framework-alias
- Description: Snyk security requires python packages update. TODO: add details
- Assignee: (from `JIRA_ASSIGNEE` if set)
- Status: In Progress

**1. Create the issue** (use Bearer auth: `Authorization: Bearer $JIRA_TOKEN`). For API v2, use `/rest/api/2/issue` with plain-text description and `"issuetype": {"name": "Task"}`. Use `$JIRA_PROJECT` for the project key:

```bash
if [ -z "$JIRA_PROJECT" ]; then
  echo "Error: JIRA_PROJECT is not set. Please export JIRA_PROJECT or provide the Jira project key."
  exit 1
fi
if [ -z "$JIRA_BASE_URL" ]; then
  echo "Error: JIRA_BASE_URL is not set. Please export JIRA_BASE_URL."
  exit 1
fi
if [ -z "$JIRA_TOKEN" ]; then
  echo "Error: JIRA_TOKEN is not set. Please export JIRA_TOKEN."
  exit 1
fi
if [ -z "$JIRA_USER" ]; then
  echo "Error: JIRA_USER is not set. Please export JIRA_USER."
  exit 1
fi
JIRA_URL="$JIRA_BASE_URL"
RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $JIRA_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "fields": {
      "project": {"key": "'"$JIRA_PROJECT"'"},
      "issuetype": {"name": "Task"},
      "summary": "Snyk: Update Python Package",
      "description": "Snyk security requires python packages update. TODO: add details",
      "components": [{"name": "tk-framework-alias"}]
    }
  }' \
  "$JIRA_URL/rest/api/2/issue")
ISSUE_KEY=$(echo "$RESPONSE" | jq -r '.key // empty')
# Stop if creation failed: if [ -z "$ISSUE_KEY" ]; then echo "Jira issue creation failed: $RESPONSE"; exit 1; fi
```

**2. Assign** (uses `JIRA_ASSIGNEE`; for Jira Server/Data Center (API v2), use `name`). Only run if `JIRA_ASSIGNEE` is set; verify the username exists in Jira:

```bash
if [ -n "$JIRA_ASSIGNEE" ]; then
  curl -s -X PUT \
    -H "Authorization: Bearer $JIRA_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "'"$JIRA_ASSIGNEE"'"}' \
    "$JIRA_URL/rest/api/2/issue/$ISSUE_KEY/assignee"
fi
```

**3. Transition to In Progress** — fetch available transitions, find the "In Progress" id, then POST:

```bash
# Get transitions and extract the id for "In Progress"
TRANSITIONS=$(curl -s -H "Authorization: Bearer $JIRA_TOKEN" \
  -H "Accept: application/json" \
  "$JIRA_URL/rest/api/2/issue/$ISSUE_KEY/transitions")
TRANSITION_ID=$(echo "$TRANSITIONS" | jq -r '.transitions[] | select(.name | startswith("In Progress")) | .id' | head -1)
if [ -n "$TRANSITION_ID" ]; then
  curl -s -X POST \
    -H "Authorization: Bearer $JIRA_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"transition": {"id": "'"$TRANSITION_ID"'"}}' \
    "$JIRA_URL/rest/api/2/issue/$ISSUE_KEY/transitions"
fi
```

**Required:** Keep `$ISSUE_KEY` (e.g. PROJ-1234) — it is used for the branch name in Step 1 and can be referenced in the PR body. **Do not proceed until the Jira issue exists and $ISSUE_KEY is set.**

### Step 1: Create branch

First ensure you are on main with the latest changes. Create a branch prefixed with the Jira ticket key from Step 0 (e.g. `PROJ-1234/snyk-update-packages`):

```bash
git checkout main
git pull origin main
git checkout -b "$ISSUE_KEY/snyk-update-packages"
```

On Windows (PowerShell):

```powershell
git checkout main
git pull origin main
git checkout -b "$ISSUE_KEY/snyk-update-packages"
```

If the default branch is not `main`, use the branch that `origin/HEAD` points to (e.g., `develop`).

**Only after the branch is created**, proceed to Step 2.

### Step 2: Run script per Python version

For each version (e.g., 3.7, 3.10, 3.11), run from tk-framework-alias root:

**Windows** — Try in order:
1. `C:\Program Files\Python3X\python.exe` or `C:\Program Files\Python 3.X\python.exe` (when user specifies versions)
2. `py -3.X` (py launcher)

```bash
py -3.7 dev/update_python_packages.py
py -3.10 dev/update_python_packages.py
py -3.11 dev/update_python_packages.py
```

**Linux/Mac**:

```bash
python3.7 dev/update_python_packages.py
python3.10 dev/update_python_packages.py
python3.11 dev/update_python_packages.py
```

Skip versions where the interpreter is not installed. If a run fails, report the error and stop. **Only after all Python versions have been updated**, proceed to Step 3.

### Step 3: Commit and push

Dist files are in `.gitignore`; use `-f` to force-add them. Use `--force` on push so `pkgs.zip` and other large dist files are pushed.

```bash
git add -f dist/Python/Python*/packages/frozen_requirements.txt dist/Python/Python*/packages/pkgs.zip
git commit -m "Snyk: update python packages"
git push -u origin "$ISSUE_KEY/snyk-update-packages" --force
```

**Only after the branch is pushed**, proceed to Step 4.

### Step 4: Create PR

1. Check if GitHub CLI is available: `gh --version` or `gh pr create --help`
2. **If gh is installed**:
   ```bash
   gh pr create --title "$ISSUE_KEY: Snyk update python packages" --body "Updates Python packages. Jira: $ISSUE_KEY"
   ```
   (Non-interactive use requires `--body`. Do not add "Made with Cursor" or similar footers to the PR body.)
3. **If gh is not available**: After pushing, provide the compare URL. Get remote URL with `git remote get-url origin`, then construct:
   ```
   https://github.com/<owner>/<repo>/compare/<base-branch>...$ISSUE_KEY/snyk-update-packages?expand=1
   ```
   Tell the user to open this URL to create the PR in the browser.

## Checklist

- [ ] Verify JIRA_PROJECT, JIRA_BASE_URL, JIRA_TOKEN, and JIRA_USER; create Jira issue (title, component tk-framework-alias, assign if JIRA_ASSIGNEE set, status In Progress)
- [ ] Checkout main, pull latest, create branch `$ISSUE_KEY/snyk-update-packages`
- [ ] Run update script for each Python version (default: from dist/Python folders; override if user specified)
- [ ] Commit and push
- [ ] Create PR via `gh pr create` or provide compare URL (optionally reference Jira issue key in PR body)
