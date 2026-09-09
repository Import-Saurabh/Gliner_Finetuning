FROM public.ecr.aws/lambda/python:3.11

# Install system deps required for building wheels (e.g., sentencepiece needs cmake and gcc)
RUN yum install -y curl gcc-c++ make cmake tar gzip && yum clean all

WORKDIR /var/task

# Install PyTorch (CPU version only to save space) first
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.6.0+cpu

# Copy and install requirements (includes mangum)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI application (including the adapter in app/adapter/best)
COPY app/ ./app/

# Set Environment Variables
ENV PYTHONUNBUFFERED=1 \
    GLINER_BASE_MODEL=fastino/gliner2-base-v1 \
    NER_LABELS=PERSON,GPE,ORG,EVENT,DATE \
    NER_THRESHOLD=0.3 \
    MAX_TEXT_LEN=4000 \
    ENABLE_RATE_LIMIT=true \
    RATE_LIMIT_REQUESTS=10 \
    RATE_LIMIT_WINDOW=60

# Use Mangum to wrap the FastAPI app
# Format: app.main.handler refers to the 'handler' variable inside app/main.py (which is Mangum(app))
CMD ["app.main.handler"]