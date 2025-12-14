# Fix: config.js Not Loading on Live Site

## Problem
After deploying to GitHub, the live site shows: "Failed to load config.js"

## Solution Applied
The GitHub Actions workflow now properly deploys `config.js` to GitHub Pages.

## Required Setup Steps

### 1. Add GitHub Secret (REQUIRED)

1. Go to: `https://github.com/YOUR_USERNAME/cafeHop/settings/secrets/actions`
2. Click **"New repository secret"**
3. Name: `API_GATEWAY_URL`
4. Value: `https://1fanbo3g3k.execute-api.us-east-1.amazonaws.com`
5. Click **"Add secret"**

**⚠️ Without this secret, the workflow will fail!**

### 2. Enable GitHub Pages (If Not Already Enabled)

1. Go to: `https://github.com/YOUR_USERNAME/cafeHop/settings/pages`
2. Under "Source", select: **"GitHub Actions"** (not "Deploy from a branch")
3. Save

### 3. Push and Deploy

1. Commit and push the updated workflow:
   ```bash
   git add .github/workflows/deploy.yml
   git commit -m "Fix: Deploy config.js to GitHub Pages"
   git push
   ```

2. The workflow will automatically:
   - Generate `config.js` from your secret
   - Deploy it to GitHub Pages
   - Make it available on your live site

### 4. Verify Deployment

1. Go to: `https://github.com/YOUR_USERNAME/cafeHop/actions`
2. Check that the workflow runs successfully
3. Visit your GitHub Pages site
4. Open browser console and type: `window.APP_CONFIG`
5. You should see your API URL configured

## What Changed

✅ The workflow now actually deploys to GitHub Pages (was commented out before)
✅ Added proper permissions for GitHub Pages deployment
✅ Added error checking if secret is missing
✅ `config.js` will now be included in the deployment

## Troubleshooting

**Workflow fails with "API_GATEWAY_URL secret is not set"**
- Go to Settings > Secrets and add the secret (Step 1 above)

**Workflow succeeds but config.js still not loading**
- Check GitHub Pages settings (Step 2 above)
- Make sure you selected "GitHub Actions" as the source
- Clear browser cache and hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

**config.js loads but API_GATEWAY_URL is undefined**
- Check the secret value in GitHub Settings
- Make sure there are no extra spaces or quotes in the secret value
