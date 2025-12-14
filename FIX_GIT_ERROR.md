# Fix: Git Exit Code 128 Error

## Problem
GitHub Actions deployment fails with: "The process '/usr/bin/git' failed with exit code 128"

This is a **permissions issue** - GitHub Actions doesn't have permission to write to your repository.

## Solution (Two Steps Required)

### Step 1: Update Repository Settings (CRITICAL)

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Go to **Actions** → **General** (left sidebar)
4. Scroll down to **"Workflow permissions"**
5. Select: **"Read and write permissions"** ✅
6. Check: **"Allow GitHub Actions to create and approve pull requests"** (optional but recommended)
7. Click **Save**

**This is the most important step!** Without this, the workflow cannot push to GitHub Pages.

### Step 2: Verify Workflow File

The workflow file should already have the correct permissions (I've updated it):

```yaml
permissions:
  contents: write  # ✅ This allows writing to the repo
  pages: write
  id-token: write
```

And it uses the latest action version:
```yaml
uses: peaceiris/actions-gh-pages@v4
```

### Step 3: Re-run the Workflow

After updating the repository settings:

1. Go to: `https://github.com/YOUR_USERNAME/cafeHop/actions`
2. Find the failed workflow run
3. Click **"Re-run all jobs"** (or push a new commit)
4. The workflow should now succeed

## Why This Happens

By default, GitHub Actions has **read-only** permissions for security. To deploy to GitHub Pages, the workflow needs **write** permissions to:
- Push to the `gh-pages` branch (or your Pages branch)
- Create/update deployment artifacts

## Verification

After fixing, you should see:
- ✅ Workflow completes successfully
- ✅ `config.js` is deployed to your live site
- ✅ No more "exit code 128" errors

## Still Having Issues?

If it still fails after Step 1:

1. **Check the Actions log** for the exact error message
2. **Verify the secret exists**: Settings → Secrets → Actions → `API_GATEWAY_URL`
3. **Check GitHub Pages source**: Settings → Pages → Source should be "GitHub Actions"
4. **Try manual trigger**: Actions → "Deploy with Config" → "Run workflow"
