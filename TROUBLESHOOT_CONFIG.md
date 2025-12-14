# Troubleshooting: config.js Not Loading After Deployment

## Problem
Workflow succeeds but you get "Failed to load resource" error for `config.js` on the live site.

## Quick Checks

### 1. Verify the file was deployed
After the workflow runs, check if `config.js` is actually on GitHub Pages:

1. Go to your GitHub Pages URL: `https://YOUR_USERNAME.github.io/cafeHop/config.js`
2. Or check the `gh-pages` branch: `https://github.com/YOUR_USERNAME/cafeHop/tree/gh-pages`
3. You should see `config.js` in the root directory

### 2. Check browser console
Open your live site and check the browser console (F12):
- Look for the exact error message
- Check the Network tab to see if `config.js` request is failing
- Note the exact URL it's trying to load

### 3. GitHub Pages Base Path Issue

If your site is at `https://YOUR_USERNAME.github.io/cafeHop/` (with a subdirectory), the script path might need to be absolute.

**Check your GitHub Pages URL:**
- If it's `https://YOUR_USERNAME.github.io/cafeHop/` → You need absolute paths
- If it's `https://YOUR_USERNAME.github.io/` → Relative paths work

## Solutions

### Solution 1: Use Absolute Path (If site is in subdirectory)

If your GitHub Pages URL includes the repository name (e.g., `/cafeHop/`), update `add.html`:

```html
<!-- Change from: -->
<script src="config.js"></script>

<!-- To: -->
<script src="/cafeHop/config.js"></script>
```

Or use a dynamic base path:
```html
<script>
  const basePath = window.location.pathname.split('/').slice(0, -1).join('/') || '';
  document.write('<script src="' + basePath + '/config.js"><\/script>');
</script>
```

### Solution 2: Verify File is Deployed

Check the workflow logs:
1. Go to: `https://github.com/YOUR_USERNAME/cafeHop/actions`
2. Click on the latest workflow run
3. Expand "List files to be deployed"
4. Verify `config.js` is in the list

### Solution 3: Clear Cache

Sometimes browsers cache the 404 error:
- Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Or open in incognito/private mode

### Solution 4: Check File Permissions

The file might be deployed but not accessible. Verify:
1. The file exists in the `gh-pages` branch
2. The file has content (not empty)
3. GitHub Pages is serving JavaScript files (should be by default)

## Debugging Steps

1. **Check workflow logs** - Look for "List files to be deployed" step
2. **Visit config.js directly** - `https://YOUR_USERNAME.github.io/cafeHop/config.js`
3. **Check browser Network tab** - See the exact request/response
4. **Verify secret is set** - Make sure `API_GATEWAY_URL` secret exists

## Most Common Issue

**If your GitHub Pages URL is `https://YOUR_USERNAME.github.io/cafeHop/`**, you need to use an absolute path:

```html
<script src="/cafeHop/config.js"></script>
```

Instead of:
```html
<script src="config.js"></script>
```
