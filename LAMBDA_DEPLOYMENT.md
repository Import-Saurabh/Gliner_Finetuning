# AWS Lambda Deployment Guide for GeoNER

## Architecture
- **Backend**: AWS Lambda (Container Image) with GLiNER2 model
- **Frontend**: Vercel (static hosting)
- **Connection**: Vercel frontend calls Lambda Function URL

## Cost Estimate (Cheapest Option)
- **Memory**: 3008 MB (minimum for ML models)
- **Timeout**: 30 seconds
- **Price**: ~$0.0000166667 per GB-second
- **Monthly cost**: $1-5 for demo traffic (< 100 requests/day)
- **Cold start**: 15-25 seconds on first request

## Prerequisites
1. AWS Account
2. Docker installed
3. AWS CLI configured (`aws configure`)

## Step 1: Build and Push Docker Container

```bash
# Login to Amazon ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository (run once)
aws ecr create-repository --repository-name geoner-lambda --image-scanning-configuration scanOnPush=true

# Build Docker image
docker build -t geoner-lambda .

# Tag for ECR
docker tag geoner-lambda:latest <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/geoner-lambda:latest

# Push to ECR
docker push <your-account-id>.dkr.ecr.us-east-1.amazonaws.com/geoner-lambda:latest
```

## Step 2: Create Lambda Function

```bash
# Create Lambda function with container image
aws lambda create-function \
  --function-name GeoNER-API \
  --package-type Image \
  --code ImageUri=<your-account-id>.dkr.ecr.us-east-1.amazonaws.com/geoner-lambda:latest \
  --role arn:aws:iam::<your-account-id>:role/lambda-execution-role \
  --memory-size 3008 \
  --timeout 30 \
  --environment Variables="{GLINER_BASE_MODEL=fastino/gliner2-base-v1,NER_LABELS=PERSON,GPE,ORG,EVENT,DATE,NER_THRESHOLD=0.3,MAX_TEXT_LEN=4000}"

# Grant Lambda permission to pull from ECR (if not already done)
aws lambda add-permission \
  --function-name GeoNER-API \
  --statement-id ecr-pull \
  --principal ecr.amazonaws.com \
  --action lambda:GetFunction \
  --source-arn arn:aws:ecr:us-east-1:<your-account-id>:repository/geoner-lambda
```

## Step 3: Create IAM Execution Role

Create a file `lambda-trust-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

```bash
# Create role
aws iam create-role \
  --role-name lambda-geoner-role \
  --assume-role-policy-document file://lambda-trust-policy.json

# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name lambda-geoner-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Attach ECR pull policy (if needed)
aws iam attach-role-policy \
  --role-name lambda-geoner-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

## Step 4: Enable Function URL with Rate Limiting

```bash
# Create Function URL with CORS (allows Vercel domain)
aws lambda create-function-url-config \
  --function-name GeoNER-API \
  --auth-type NONE \
  --cors '{\"AllowOrigins\": [\"*\"], \"AllowMethods\": [\"GET\", \"POST\", \"OPTIONS\"], \"AllowHeaders\": [\"Content-Type\", \"X-Amz-Date\", \"Authorization\", \"X-Api-Key\"]}'

# Get the Function URL
aws lambda get-function-url-config --function-name GeoNER-API
```

### 🔒 API Abuse Prevention (Already Implemented!)

The Lambda handler includes built-in protection:

1. **Rate Limiting**: 10 requests per minute per IP address (configurable)
   - Returns HTTP 429 when exceeded
   - Configurable via environment variables

2. **Text Length Limits**: Maximum 4000 characters per request
   - Prevents large payload attacks
   - Returns HTTP 413 when exceeded

3. **Input Validation**: 
   - Requires text field
   - Requires at least one label
   - Returns HTTP 422 for invalid requests

**To customize rate limits**, update environment variables in Lambda console or CLI:
```bash
aws lambda update-function-configuration \
  --function-name GeoNER-API \
  --environment Variables="{
    ENABLE_RATE_LIMIT=true,
    RATE_LIMIT_REQUESTS=20,
    RATE_LIMIT_WINDOW=60,
    GLINER_BASE_MODEL=fastino/gliner2-base-v1,
    NER_LABELS=PERSON,GPE,ORG,EVENT,DATE,
    NER_THRESHOLD=0.3,
    MAX_TEXT_LEN=4000
  }"
```

**For production**, consider adding:
- AWS WAF (Web Application Firewall) for advanced protection
- API Gateway with usage plans
- API key authentication

## Step 5: Update Frontend (Vercel)

1. **Copy the Vercel-ready frontend file**:
```bash
cp app/static/index_vercel.html /path/to/your/vercel-project/index.html
```

2. **Update the Lambda URL in the frontend**:
   
   Open `index_vercel.html` and replace line 207:
```javascript
// BEFORE:
const API_BASE = "https://YOUR_LAMBDA_FUNCTION_URL.lambda-url.us-east-1.on.aws";

// AFTER (paste your actual Lambda URL):
const API_BASE = "https://abc123xyz.lambda-url.us-east-1.on.aws";
```

3. **Deploy to Vercel**:
```bash
cd /path/to/your/vercel-project
vercel --prod
```

**Alternative**: Set as environment variable in Vercel dashboard:
- Go to Vercel Project Settings → Environment Variables
- Add `NEXT_PUBLIC_API_BASE` with your Lambda URL
- Update frontend to use `process.env.NEXT_PUBLIC_API_BASE`

## Step 6: Test the Endpoint

```bash
# Test health endpoint
curl https://<your-function-url>.lambda-url.us-east-1.on.aws/health

# Test NER endpoint
curl -X POST https://<your-function-url>.lambda-url.us-east-1.on.aws/api/ner \
  -H "Content-Type: application/json" \
  -d '{"text": "John Doe visited Paris last week.", "labels": ["PERSON", "GPE", "DATE"]}'
```

## Important Notes

### Memory & Performance
- **3008 MB**: Minimum viable, 15-25s cold start
- **4096 MB**: Recommended, 10-18s cold start (+$0.50/month)
- **6144 MB**: Optimal, 8-12s cold start (+$1.50/month)

### Cold Start Mitigation
- First request after inactivity takes 15-25 seconds
- Subsequent requests are fast (~100-500ms)
- Consider keeping warm with scheduled pings (CloudWatch Events every 5-10 min)

### Cost Optimization Tips
1. Use 3008 MB memory (minimum for ML)
2. Set timeout to 30 seconds (max needed)
3. Enable provisioned concurrency ONLY if needed ($$$)
4. Monitor with CloudWatch to right-size memory

### Troubleshooting
- **Model load failure**: Check adapter is at `/opt/adapter/best` in container
- **Timeout errors**: Increase timeout to 30s, check memory allocation
- **CORS errors**: Verify Function URL CORS config allows your Vercel domain
- **Large response**: Ensure text length < 4000 characters

## Frontend Integration Example

```javascript
const LAMBDA_URL = "https://<your-function-url>.lambda-url.us-east-1.on.aws";

async function extractEntities(text, labels) {
  const response = await fetch(`${LAMBDA_URL}/api/ner`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, labels }),
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  return await response.json();
}

// Usage
const result = await extractEntities(
  "Emmanuel Macron met Joe Biden in Paris.",
  ["PERSON", "GPE"]
);
console.log(result.entities);
```

## Total Monthly Cost Breakdown
- **Lambda compute**: $0.50-2.00 (100 requests/day × 2s avg)
- **Data transfer**: $0.01-0.10 (minimal for text API)
- **Vercel hosting**: FREE (Hobby tier)
- **Total**: **$1-5/month** for demo usage

---

## ✅ Security Features Implemented

Your GeoNER Lambda is production-ready with:

✅ **Rate Limiting**: 10 requests/minute per IP (configurable)
✅ **Text Length Limits**: Max 4000 characters
✅ **Input Validation**: Required fields, proper error codes
✅ **CORS Protection**: Configured for Vercel domain
✅ **Model Caching**: Fast subsequent requests
✅ **Error Handling**: Proper HTTP status codes

---

Built by Saurabh Hadole (AVI) — ML/AI Engineer  
Portfolio: https://saurabhhadole.vercel.app/  
GitHub: https://github.com/Import-Saurabh
