# GeoNER - AWS Lambda Deployment Package

## ✅ Ready for Deployment!

Your model is now configured for **AWS Lambda** with the cheapest possible setup.

## What's Been Created

### 1. `lambda_handler.py`
- AWS Lambda entry point function
- Handles model loading and caching
- Processes NER inference requests
- Returns JSON responses with CORS headers

### 2. Updated `Dockerfile`
- Uses AWS Lambda Python 3.11 base image
- Optimized for container size
- Places adapter at `/opt/adapter/best`
- Sets correct handler command

### 3. `app/static/index_vercel.html`
- Frontend configured for Vercel deployment
- API_BASE placeholder for Lambda Function URL
- Same beautiful UI as original

### 4. Documentation
- `LAMBDA_DEPLOYMENT.md` - Complete Lambda setup guide
- `VERCEL_DEPLOYMENT.md` - Frontend deployment instructions

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│   Vercel        │         │   AWS Lambda     │
│   (Frontend)    │ ──────▶ │   (Backend)      │
│   FREE          │  HTTP   │   $1-5/month     │
│                 │         │                  │
│ index_vercel.html│         │ lambda_handler.py│
│                 │         │ GLiNER2 Model    │
└─────────────────┘         └──────────────────┘
```

## Cost Breakdown 💰

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| **AWS Lambda** | 3008 MB, 30s timeout | $1-5 |
| **Vercel** | Hobby Plan | FREE |
| **Total** | | **$1-5/month** |

### Memory Options

| Memory | Cold Start | Cost/Month | Recommendation |
|--------|------------|------------|----------------|
| 3008 MB | 15-25s | ~$1-2 | ✅ Cheapest (use this) |
| 4096 MB | 10-18s | ~$2-3 | Better UX |
| 6144 MB | 8-12s | ~$3-5 | Fastest |

## Quick Deploy Steps

### Backend (AWS Lambda)

```bash
# 1. Build Docker image
docker build -t geoner-lambda .

# 2. Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
docker tag geoner-lambda:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/geoner-lambda:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/geoner-lambda:latest

# 3. Create Lambda (see LAMBDA_DEPLOYMENT.md for full commands)
aws lambda create-function \
  --function-name GeoNER-API \
  --package-type Image \
  --code ImageUri=<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/geoner-lambda:latest \
  --role arn:aws:iam::<ACCOUNT_ID>:role/lambda-geoner-role \
  --memory-size 3008 \
  --timeout 30

# 4. Enable Function URL
aws lambda create-function-url-config \
  --function-name GeoNER-API \
  --auth-type NONE \
  --cors '{"AllowOrigins": ["*"], "AllowMethods": ["GET", "POST", "OPTIONS"]}'
```

### Frontend (Vercel)

```bash
# 1. Update API_BASE in app/static/index_vercel.html
# Replace YOUR_LAMBDA_FUNCTION_URL with actual URL

# 2. Deploy to Vercel
cd app/static
vercel --prod
```

## API Endpoints

Once deployed, your Lambda Function URL will support:

- `GET /health` - Health check
- `POST /api/ner` - Named entity recognition
- `GET /api/info` - Model information

## Testing

```bash
# Test health endpoint
curl https://YOUR_URL.lambda-url.us-east-1.on.aws/health

# Test NER
curl -X POST https://YOUR_URL.lambda-url.us-east-1.on.aws/api/ner \
  -H "Content-Type: application/json" \
  -d '{"text": "John Doe visited Paris last week.", "labels": ["PERSON", "GPE", "DATE"]}'
```

## Important Notes

⚠️ **Cold Starts**: First request after inactivity takes 15-25 seconds. This is normal for ML models on Lambda.

✅ **Model Caching**: The model stays loaded in memory between invocations, so subsequent requests are fast (~100-500ms).

💡 **Tip**: For demos, consider pinging the endpoint every 5-10 minutes to keep it warm.

## Files Modified/Created

```
/workspace/
├── lambda_handler.py          # NEW - Lambda entry point
├── Dockerfile                 # UPDATED - Lambda container config
├── LAMBDA_DEPLOYMENT.md       # NEW - Backend deployment guide
├── VERCEL_DEPLOYMENT.md       # NEW - Frontend deployment guide
├── DEPLOYMENT_SUMMARY.md      # NEW - This file
└── app/
    ├── static/
    │   ├── index.html         # Original (FastAPI)
    │   └── index_vercel.html  # NEW (Vercel)
    └── adapter/best/          # Your finetuned adapter
```

## Next Steps

1. ✅ Review `LAMBDA_DEPLOYMENT.md` for detailed AWS setup
2. ✅ Update `index_vercel.html` with your Lambda URL
3. ✅ Deploy frontend to Vercel
4. ✅ Test the complete flow
5. 🎉 Share your demo!

---

Built by Saurabh Hadole (AVI) — ML/AI Engineer  
Portfolio: https://saurabhhadole.vercel.app/  
GitHub: https://github.com/Import-Saurabh
