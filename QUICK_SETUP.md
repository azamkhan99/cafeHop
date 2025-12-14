# Quick Setup Guide

## For Local Testing (Right Now)

You're getting the error because `config.js` needs to be accessible. Here's how to fix it:

### Option 1: Verify config.js exists and is in the right place

1. Make sure `config.js` is in the same directory as `add.html`
2. Open your browser's Developer Console (F12) and check:
   - Look for any errors loading `config.js`
   - Type `window.APP_CONFIG` in the console to see if it's loaded

### Option 2: If config.js is missing or not loading

Run this in your terminal (in the project root):
```bash
cp config.example.js config.js
```

Then edit `config.js` and make sure it has your API URL:
```javascript
window.APP_CONFIG = {
    API_GATEWAY_URL: 'https://1fanbo3g3k.execute-api.us-east-1.amazonaws.com'
};
```

### Option 3: If testing with file:// protocol

If you're opening the HTML file directly (not through a web server), scripts might not load due to browser security. Use a local server instead:

```bash
# Python 3
python3 -m http.server 8000

# Or Node.js
npx http-server
```

Then open: `http://localhost:8000/add.html`

---

## For GitHub Actions Deployment

### Step 1: Add GitHub Secret

1. Go to: `https://github.com/YOUR_USERNAME/cafeHop/settings/secrets/actions`
2. Click **"New repository secret"**
3. Name: `API_GATEWAY_URL`
4. Value: `https://1fanbo3g3k.execute-api.us-east-1.amazonaws.com`
5. Click **"Add secret"**

### Step 2: Update GitHub Actions Workflow

The workflow will automatically generate `config.js` during deployment. If you're using GitHub Pages, update the workflow:

```yaml
- name: Deploy to GitHub Pages
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./
```

### Step 3: Test the Workflow

1. Push your code to GitHub
2. Go to: `https://github.com/YOUR_USERNAME/cafeHop/actions`
3. The workflow should run and generate `config.js` automatically

---

## Troubleshooting

**Error: "API Gateway URL not configured"**

- ✅ Check browser console for `config.js` loading errors
- ✅ Verify `config.js` exists in the same directory as `add.html`
- ✅ Check that `window.APP_CONFIG.API_GATEWAY_URL` is set (type in console)
- ✅ If using GitHub Actions, verify the secret `API_GATEWAY_URL` is set

**For Local Development:**
- Make sure `config.js` exists (copy from `config.example.js`)
- Don't commit `config.js` (it's in `.gitignore`)

**For Production/Deployment:**
- GitHub Actions will generate `config.js` from secrets
- The file will be created during the deployment process
