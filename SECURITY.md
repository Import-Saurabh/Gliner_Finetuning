# SECURITY.md - API Abuse Prevention

## Overview

GeoNER Lambda includes built-in protection against API abuse to keep costs low and ensure fair usage.

## Implemented Protections

### 1. Rate Limiting
- **Default**: 10 requests per minute per IP address
- **Response**: HTTP 429 (Too Many Requests)
- **Configuration**: Environment variables

```python
# Default settings
RATE_LIMIT_REQUESTS = 10  # requests per window
RATE_LIMIT_WINDOW = 60    # seconds
ENABLE_RATE_LIMIT = true
```

### 2. Text Length Limits
- **Maximum**: 4000 characters per request
- **Response**: HTTP 413 (Payload Too Large)
- **Purpose**: Prevents large payload attacks and excessive compute time

### 3. Input Validation
- **Required fields**: `text`, at least one `label`
- **Response**: HTTP 422 (Unprocessable Entity)
- **Validation**: Type checking, empty value rejection

### 4. CORS Protection
- **Allowed origins**: Configurable (default: `*` for demo)
- **Allowed methods**: GET, POST, OPTIONS
- **Production**: Restrict to your Vercel domain

## Configuration

### Via AWS Lambda Console
1. Go to Lambda function → Configuration → Environment variables
2. Edit or add these variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_RATE_LIMIT` | `true` | Enable/disable rate limiting |
| `RATE_LIMIT_REQUESTS` | `10` | Max requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Time window in seconds |
| `MAX_TEXT_LEN` | `4000` | Maximum text length |

### Via AWS CLI
```bash
aws lambda update-function-configuration \
  --function-name GeoNER-API \
  --environment Variables="{
    ENABLE_RATE_LIMIT=true,
    RATE_LIMIT_REQUESTS=20,
    RATE_LIMIT_WINDOW=60,
    MAX_TEXT_LEN=4000
  }"
```

## Example Responses

### Rate Limit Exceeded (429)
```json
{
  "error": "Rate limit exceeded",
  "message": "Maximum 10 requests per 60 seconds",
  "retry_after": 60
}
```

### Text Too Long (413)
```json
{
  "error": "Text too long",
  "message": "Maximum length is 4000 characters",
  "current_length": 5234
}
```

### Invalid Request (422)
```json
{
  "error": "Text is required"
}
```

## Production Recommendations

For production deployments, consider adding:

1. **AWS WAF** (Web Application Firewall)
   - SQL injection protection
   - Cross-site scripting (XSS) protection
   - Geographic restrictions

2. **API Gateway**
   - Usage plans and API keys
   - Throttling at gateway level
   - Request validation

3. **Authentication**
   - JWT tokens
   - API key authentication
   - AWS Cognito integration

4. **Monitoring**
   - CloudWatch alarms for unusual traffic
   - AWS X-Ray for request tracing
   - Custom metrics for abuse detection

## Cost Protection

With rate limiting enabled:
- **Maximum cost per IP**: ~$0.0003/hour (10 req/min × 2s × 3008 MB)
- **Daily max per IP**: ~$0.007 (at 10 req/min continuously)
- **Monthly max per IP**: ~$0.22

This ensures a single malicious user cannot rack up hundreds of dollars in charges.

## Monitoring Abuse

Check CloudWatch Logs for:
- Frequent 429 responses (rate limit hits)
- Frequent 413 responses (large payloads)
- Unusual traffic patterns
- Requests from unexpected geographies

Example CloudWatch Insights query:
```sql
fields @timestamp, @message
| filter @message like /429|413|Rate limit/
| sort @timestamp desc
| limit 100
```

---

Built by Saurabh Hadole (AVI) — ML/AI Engineer  
Portfolio: https://saurabhhadole.vercel.app/  
GitHub: https://github.com/Import-Saurabh
