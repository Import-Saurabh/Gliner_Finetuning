FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies required for building Python packages
RUN yum install -y \
    curl \
    gcc-c++ \
    make \
    cmake \
    tar \
    gzip \
    && yum clean all \
    && rm -rf /var/cache/yum

WORKDIR /var/task

# Install CPU-only PyTorch
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.6.0+cpu

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application and bundled adapter
COPY app/ ./app/

# AWS Lambda filesystem is read-only except /tmp.
# Force HOME and all Hugging Face / Transformers caches to /tmp.
ENV HOME=/tmp \
    HF_HOME=/tmp/huggingface \
    HF_HUB_CACHE=/tmp/huggingface/hub \
    TRANSFORMERS_CACHE=/tmp/huggingface/transformers \
    HUGGINGFACE_HUB_CACHE=/tmp/huggingface/hub \
    XDG_CACHE_HOME=/tmp/cache \
    PYTHONUNBUFFERED=1 \
    GLINER_BASE_MODEL=fastino/gliner2-base-v1 \
    NER_LABELS=PERSON,GPE,ORG,EVENT,DATE \
    NER_THRESHOLD=0.3 \
    MAX_TEXT_LEN=4000 \
    ENABLE_RATE_LIMIT=true \
    RATE_LIMIT_REQUESTS=10 \
    RATE_LIMIT_WINDOW=60

# Mangum handler for AWS Lambda
CMD ["app.main.handler"]
