# 🚀 GeoNER Deployment Checklist

## ✅ Repository Status: READY FOR DEPLOYMENT

All files have been updated and verified for AWS Lambda + Vercel deployment.

---

## 1. Backend (AWS Lambda) - ✅ READY

### Files Updated:
- ✅ `lambda_handler.py` - Rate limiting, abuse prevention, model caching
- ✅ `Dockerfile` - Optimized for Lambda with security env vars
- ✅ `requirements.txt` - All dependencies listed
- ✅ `app/adapter/best/` - Fine-tuned model adapter included

### Security Features Implemented:
- ✅ Rate limiting (10 req/min per IP, configurable)
- ✅ Text length limits (max 4000 chars)
- ✅ Input validation (required fields, type checking)
- ✅ CORS configuration for Vercel
- ✅ Proper HTTP error codes (429, 413, 422, 500)

### Deployment Steps:
```bash
# 1. Build Docker image
docker build -t geoner-lambda .

# 2. Push to AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag geoner-lambda:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/geoner-lambda:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/geoner-lambda:latest

# 3. Create Lambda function
aws lambda create-function \
  --function-name GeoNER-API \
  --package-type Image \
  --code ImageUri=<account-id>.dkr.ecr.us-east-1.amazonaws.com/geoner-lambda:latest \
  --role arn:aws:iam::<account-id>:role/lambda-geoner-role \
  --memory-size 3008 \
  --timeout 30 \
  --environment Variables="{ENABLE_RATE_LIMIT=true,RATE_LIMIT_REQUESTS=10,RATE_LIMIT_WINDOW=60,GLINER_BASE_MODEL=fastino/gliner2-base-v1,NER_LABELS=PERSON,GPE,ORG,EVENT,DATE,NER_THRESHOLD=0.3,MAX_TEXT_LEN=4000}"

# 4. Enable Function URL
aws lambda create-function-url-config \
  --function-name GeoNER-API \
  --auth-type NONE \
  --cors '{"AllowOrigins": ["*"], "AllowMethods": ["GET", "POST", "OPTIONS"], "AllowHeaders": ["Content-Type"]}'

# 5. Get your Function URL
aws lambda get-function-url-config --function-name GeoNER-API
```

### Cost Estimate:
- **Memory**: 3008 MB (minimum for ML)
- **Monthly cost**: $1-5 for demo (< 100 requests/day)
- **Cold start**: 15-25 seconds (first request), then 100-500ms

---

## 2. Frontend (Vercel) - ✅ READY

### Files Prepared:
- ✅ `app/static/index_vercel.html` - Vercel-ready frontend with placeholder API URL

### Deployment Steps:
```bash
# 1. Copy frontend to your Vercel project
cp app/static/index_vercel.html /path/to/your-vercel-project/index.html

# 2. Update API URL in index.html (line 207)
# Replace: https://YOUR_LAMBDA_FUNCTION_URL.lambda-url.us-east-1.on.aws
# With: Your actual Lambda Function URL from step 5 above

# 3. Deploy to Vercel
cd /path/to/your-vercel-project
vercel --prod
```

### Cost:
- **Vercel Hobby tier**: FREE
- **Includes**: Unlimited deployments, 100GB bandwidth/month

---

## 3. Testing

### Test Lambda Endpoint:
```bash
# Health check
curl https://<your-lambda-url>.lambda-url.us-east-1.on.aws/health

# NER inference
curl -X POST https://<your-lambda-url>.lambda-url.us-east-1.on.aws/api/ner \
  -H "Content-Type: application/json" \
  -d '{"text": "Emmanuel Macron met Joe Biden in Paris.", "labels": ["PERSON", "GPE"]}'

# Test rate limiting (run 15 times quickly)
for i in {1..15}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST ...; done
# Should see: 200, 200, ..., 429, 429 (after 10 requests)
```

### Expected Responses:
- ✅ Success: HTTP 200 with entities
- ✅ Rate limit: HTTP 429 after 10 requests/minute
- ✅ Text too long: HTTP 413 for >4000 chars
- ✅ Invalid input: HTTP 422 for missing fields

---

## 4. Monitoring & Maintenance

### CloudWatch Logs:
```sql
-- Check for abuse attempts
fields @timestamp, @message
| filter @message like /429|413|Rate limit/
| sort @timestamp desc
| limit 100
```

### Adjust Rate Limits (if needed):
```bash
aws lambda update-function-configuration \
  --function-name GeoNER-API \
  --environment Variables="{...,RATE_LIMIT_REQUESTS=20,RATE_LIMIT_WINDOW=60}"
```

---

## 5. Documentation

Available guides:
- 📄 `LAMBDA_DEPLOYMENT.md` - Complete Lambda deployment guide
- 📄 `VERCEL_DEPLOYMENT.md` - Vercel frontend setup
- 📄 `SECURITY.md` - Security features and abuse prevention
- 📄 `README.md` - Project overview and usage

---

## Summary

✅ **Backend**: Lambda handler with rate limiting, input validation, model caching  
✅ **Frontend**: Vercel-ready HTML with configurable API endpoint  
✅ **Security**: Rate limiting (10 req/min), text limits (4000 chars), CORS  
✅ **Cost**: $1-5/month total (Lambda + FREE Vercel)  
✅ **Documentation**: Complete guides for deployment and security  

**Next Step**: Follow the deployment steps above to launch your demo!

---

Built by Saurabh Hadole (AVI) — ML/AI Engineer  
Portfolio: https://saurabhhadole.vercel.app/  
GitHub: https://github.com/Import-Saurabh
