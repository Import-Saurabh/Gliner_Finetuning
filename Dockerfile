FROM public.ecr.aws/lambda/python:3.11

# System deps some ML wheels need at build/runtime (kept minimal)
RUN yum install -y curl && yum clean all

WORKDIR /app

# Install Python deps first so this layer caches across code-only changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Lambda handler
COPY lambda_handler.py .

# Copy adapter to /opt/adapter/best (Lambda layer path)
COPY app/adapter/best /opt/adapter/best

ENV PYTHONUNBUFFERED=1 \
    GLINER_BASE_MODEL=fastino/gliner2-base-v1 \
    NER_LABELS=PERSON,GPE,ORG,EVENT,DATE \
    NER_THRESHOLD=0.3 \
    MAX_TEXT_LEN=4000

# Set the Lambda handler
CMD ["lambda_handler.lambda_handler"]

# Add environment variables for rate limiting (optional)
ENV ENABLE_RATE_LIMIT=true \
    RATE_LIMIT_REQUESTS=10 \
    RATE_LIMIT_WINDOW=60
