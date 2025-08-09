# Fixed Dockerfile with proper SSL and networking setup
FROM python:3.12

# Set working directory
WORKDIR /app

# Install system dependencies including CA certificates and SSL tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    openssl \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

# Create a non-root user for security
# RUN useradd --create-home --shell /bin/bash app && \
#     chown -R app:app /app
# USER app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/home/app/.local/bin:${PATH}"
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt


WORKDIR /app

# Update CA certificates to fix SSL certificate verification issues
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching
# Note: requirements file is named 'requirement.txt' in this repo
COPY requirement.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirement.txt \
    # Ensure --reload works in start.sh
    && pip install --no-cache-dir watchfiles \
    # Update SSL-related packages to fix certificate verification
    && pip install --no-cache-dir --upgrade google-generativeai requests certifi urllib3

# Copy application
COPY main.py ./
COPY start.sh ./
RUN chmod +x start.sh

# Expose API port defined in start.sh (uvicorn --port 8787)
EXPOSE 8787

# Provide GOOGLE_API_KEY at runtime: `-e GOOGLE_API_KEY=...`
CMD ["sh", "./start.sh"]
