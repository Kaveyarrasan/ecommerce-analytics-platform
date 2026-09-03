# GitHub Actions Troubleshooting Guide

## Issue: Node.js Version Conflicts (Resolved: 2026-09-03)

### Problem Description
GitHub Actions workflows were showing deprecation warnings due to Node.js version conflicts:
- **Runner Image**: `ubuntu-24.04` comes with Node.js 20.x LTS
- **Actions**: `actions/checkout@v4` and `actions/setup-python@v5` require Node.js 20
- **Previous Config**: Used `ubuntu-latest` which recently updated to `ubuntu-24.04`

### Symptoms
1. Deprecation warnings in workflow logs about Node.js versions
2. Workflow runs showing yellow warning badges
3. Potential future failures as GitHub deprecates older Node.js versions

### Root Cause
GitHub is transitioning from Node.js 16 → Node.js 20 for all actions. The `ubuntu-latest` runner image was updated from `ubuntu-22.04` to `ubuntu-24.04`, which includes Node.js 20.x by default.

---

## Solutions Applied

### 1. **Explicitly Specify Runner Version**
```yaml
jobs:
  validate-and-deploy:
    runs-on: ubuntu-24.04  # ✅ Explicitly use ubuntu-24.04 (latest LTS)
```
**Why**: Prevents unexpected changes when GitHub updates `ubuntu-latest`.

### 2. **Update Action Versions**
```yaml
- uses: actions/checkout@v4      # ✅ Uses Node.js 20
- uses: actions/setup-python@v5  # ✅ Uses Node.js 20
```
**Why**: Latest versions are compatible with Node.js 20.

### 3. **Add Workflow Metadata**
```yaml
permissions:
  contents: read
  pull-requests: write

concurrency:
  group: ${{{{ github.workflow }}}}-${{{{ github.ref }}}}
  cancel-in-progress: true
```
**Why**: 
- `permissions`: Follows least-privilege principle
- `concurrency`: Prevents multiple workflow runs from interfering

### 4. **Add Timeout Protection**
```yaml
jobs:
  validate-and-deploy:
    timeout-minutes: 30  # ✅ Prevent workflows from hanging
```
**Why**: Prevents runaway workflows from consuming GitHub Actions minutes.

### 5. **Improve Dependency Management**
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'  # ✅ Cache pip dependencies

- name: Install dependencies
  run: |
    python -m pip install --upgrade pip  # ✅ Always upgrade pip first
    pip install databricks-cli
```
**Why**: Faster builds and consistent dependency versions.

---

## Issue: Git Push Failures (Resolved: 2026-09-03)

### Problem Description
Git push was rejected with error:
```
! [rejected]        main -> main (fetch first)
error: failed to push some refs
```

### Root Cause
The remote repository had commits that weren't present locally (diverged history).

### Solution: Pull with Rebase
```bash
# Step 1: Fetch to see what changed
git fetch origin

# Step 2: Check differences
git log origin/main..main --oneline  # Local commits not pushed
git log main..origin/main --oneline  # Remote commits not pulled

# Step 3: Pull with rebase (keeps clean history)
git pull --rebase origin main

# Step 4: Push your changes
git push origin main
```

**Why Rebase Instead of Merge?**
- **Rebase**: Creates linear history (cleaner)
- **Merge**: Creates merge commits (clutters history)

---

## Future Troubleshooting Steps

### When You See Node.js Deprecation Warnings

1. **Check Your Runner Version**
   ```yaml
   runs-on: ubuntu-24.04  # Use explicit version
   ```

2. **Update Action Versions**
   - Visit GitHub Actions Marketplace
   - Check for latest versions of actions you're using
   - Update to versions that support Node.js 20+

3. **Test Workflow Changes**
   - Make changes in a feature branch first
   - Test via pull request before merging to main

### When Git Push Fails

1. **Always fetch first** to see remote changes:
   ```bash
   git fetch origin
   ```

2. **Check for diverged history**:
   ```bash
   git status
   git log origin/main..main --oneline
   git log main..origin/main --oneline
   ```

3. **Pull with rebase** (preferred for clean history):
   ```bash
   git pull --rebase origin main
   ```

4. **If conflicts occur**, resolve them:
   ```bash
   # Edit conflicted files
   git add <resolved-files>
   git rebase --continue
   ```

5. **Push your changes**:
   ```bash
   git push origin main
   ```

### When Workflow Hangs or Times Out

1. **Check job timeout**:
   ```yaml
   jobs:
     my-job:
       timeout-minutes: 30  # Add this
   ```

2. **Check step timeouts**:
   ```yaml
   - name: Long-running step
     timeout-minutes: 10  # Add this
     run: |
       # your commands
   ```

3. **Review logs** in GitHub Actions UI:
   - Click on the workflow run
   - Expand each step to see where it's hanging
   - Look for unresponsive commands or network issues

---

## Best Practices Going Forward

### 1. **Pin Runner Versions**
```yaml
runs-on: ubuntu-24.04  # ✅ Good: Explicit version
# runs-on: ubuntu-latest  # ⚠️ Avoid: Can change unexpectedly
```

### 2. **Keep Actions Updated**
- Review and update action versions quarterly
- Subscribe to GitHub's changelog

### 3. **Use Dependency Caching**
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'  # ✅ Caches dependencies
```

### 4. **Add Concurrency Control**
```yaml
concurrency:
  group: ${{{{ github.workflow }}}}-${{{{ github.ref }}}}
  cancel-in-progress: true
```

### 5. **Always Pull Before Push**
```bash
# ✅ Good: Pull first, then push
git pull --rebase origin main
git push origin main

# ❌ Bad: Push without pulling
git push origin main  # May fail if remote has changed
```

### 6. **Use Rebase for Clean History**
```bash
# For feature branches
git pull --rebase origin main

# For main branch
git pull --rebase origin main
```

### 7. **Monitor Workflow Runs**
- Set up email notifications for failures
- Review workflow runs regularly
- Check for deprecation warnings

---

## Quick Reference Commands

### Git Commands
```bash
# Check status
git status
git remote -v

# Fetch and compare
git fetch origin
git log origin/main..main --oneline  # Local only
git log main..origin/main --oneline  # Remote only

# Pull and push
git pull --rebase origin main
git push origin main

# Undo local commits (if needed)
git reset --soft HEAD~1  # Keep changes
git reset --hard HEAD~1  # Discard changes
```

---

## Resources

- **GitHub Actions Documentation**: https://docs.github.com/en/actions
- **Node.js Versions on Runners**: https://github.com/actions/runner-images
- **Action Versions**: https://github.com/marketplace?type=actions
- **Databricks CLI**: https://docs.databricks.com/dev-tools/cli/
- **Git Rebase Guide**: https://git-scm.com/book/en/v2/Git-Branching-Rebasing

---

**Last Updated**: 2026-09-03  
**Status**: ✅ All issues resolved
