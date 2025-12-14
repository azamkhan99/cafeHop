# Configuration Setup Guide

## Issue Fixed
The hardcoded AWS API Gateway URL has been removed from `add.html` and replaced with a configuration file approach.

## How to Use GitHub Secrets

### Step 1: Add Secret to GitHub Repository

1. Go to your GitHub repository
2. Click on **Settings** (in the repository navigation bar)
3. In the left sidebar, click on **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Name: `API_GATEWAY_URL`
6. Value: Your full API Gateway URL (e.g., `https://1fanbo3g3k.execute-api.us-east-1.amazonaws.com`)
7. Click **Add secret**

### Step 2: Local Development Setup

For local development, you need to create a `config.js` file:

1. Copy the example file:
   ```bash
   cp config.example.js config.js
   ```

2. Edit `config.js` and replace `YOUR_API_ID` with your actual API Gateway URL:
   ```javascript
   window.APP_CONFIG = {
       API_GATEWAY_URL: 'https://your-api-id.execute-api.us-east-1.amazonaws.com'
   };
   ```

**Note:** `config.js` is already in `.gitignore`, so it won't be committed to the repository.

### Step 3: Automated Deployment

The GitHub Actions workflow (`.github/workflows/deploy.yml`) will automatically:
- Read the `API_GATEWAY_URL` secret
- Generate `config.js` during deployment
- Deploy your site with the correct configuration

### Manual Deployment Alternative

If you're not using GitHub Actions, you can manually create `config.js` on your server:

```bash
cat > config.js << EOF
window.APP_CONFIG = {
    API_GATEWAY_URL: 'https://your-api-id.execute-api.us-east-1.amazonaws.com'
};
EOF
```

## Files Changed

- ✅ `add.html` - Now uses `window.APP_CONFIG.API_GATEWAY_URL` instead of hardcoded URL
- ✅ `config.example.js` - Template file for configuration
- ✅ `config.js` - Actual config file (excluded from git)
- ✅ `.gitignore` - Updated to exclude `config.js`
- ✅ `.github/workflows/deploy.yml` - GitHub Actions workflow to inject secrets

## Security Benefits

- ✅ No sensitive infrastructure details in version control
- ✅ Different configurations for different environments
- ✅ Easy rotation of API endpoints without code changes
- ✅ Secrets managed securely through GitHub Secrets
