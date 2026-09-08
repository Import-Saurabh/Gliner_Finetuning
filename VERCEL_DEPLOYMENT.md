# Vercel Frontend Deployment Guide

## Quick Setup

Your frontend is ready for Vercel! The file `app/static/index_vercel.html` has been configured to work with your Lambda backend.

## Step 1: Update API URL

Open `app/static/index_vercel.html` and find this line (around line 210):

```javascript
const API_BASE = "https://YOUR_LAMBDA_FUNCTION_URL.lambda-url.us-east-1.on.aws";
```

Replace `YOUR_LAMBDA_FUNCTION_URL` with your actual Lambda Function URL from AWS.

## Step 2: Deploy to Vercel

### Option A: Using Vercel CLI (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to static folder
cd app/static

# Deploy
vercel --prod
```

### Option B: Using Vercel Dashboard

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New Project"
3. Import your GitHub repository
4. Configure build settings:
   - **Framework Preset**: Other
   - **Build Command**: `cp app/static/index_vercel.html index.html`
   - **Output Directory**: `.`
5. Click "Deploy"

### Option C: Simple Static Hosting

1. Copy `index_vercel.html` to a new folder
2. Rename it to `index.html`
3. Drag and drop that folder to Vercel's deploy page

## Step 3: Update API URL in Vercel (Optional)

For better configuration management, you can use Vercel Environment Variables:

1. In Vercel Dashboard, go to your project Settings → Environment Variables
2. Add `NEXT_PUBLIC_API_BASE` with your Lambda URL
3. Update the code to read from environment variable

## File Structure for Vercel

```
your-project/
├── app/
│   └── static/
│       ├── index.html          # Original (for FastAPI)
│       └── index_vercel.html   # Modified for Vercel deployment
├── lambda_handler.py           # Lambda backend
├── Dockerfile                  # Lambda container
└── LAMBDA_DEPLOYMENT.md        # Lambda setup guide
```

## Testing Locally

Before deploying, test locally:

```bash
# Serve the static file
cd app/static
python -m http.server 8080

# Open browser to http://localhost:8080/index_vercel.html
# Test the NER functionality
```

## CORS Configuration

Your Lambda already has CORS enabled with `Access-Control-Allow-Origin: *`, which allows requests from any domain including your Vercel frontend.

If you want to restrict to your Vercel domain only, update `lambda_handler.py`:

```python
headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "https://your-app.vercel.app",
    ...
}
```

## Cost Breakdown

- **Vercel Hobby Plan**: FREE (perfect for demos)
  - Unlimited deployments
  - 100GB bandwidth/month
  - More than enough for a demo app

- **AWS Lambda**: $1-5/month (as calculated earlier)

**Total Monthly Cost: $1-5** 🎉

## Troubleshooting

### "Failed to load samples" error
- Check that `API_BASE` URL is correct
- Ensure Lambda Function URL is accessible
- Verify CORS is enabled on Lambda

### Cold start delays
- First request takes 15-25 seconds (normal for ML models on Lambda)
- Subsequent requests are fast (~100-500ms)
- Consider adding a warm-up ping every 5-10 minutes

### Network errors
- Check browser console for detailed error messages
- Verify Lambda has Function URL enabled
- Ensure IAM permissions allow public access (auth-type NONE)

---

Built by Saurabh Hadole (AVI) — ML/AI Engineer  
Portfolio: https://saurabhhadole.vercel.app/  
GitHub: https://github.com/Import-Saurabh
