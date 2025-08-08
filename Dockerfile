FROM python:3.11

# Faster/cleaner Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first for better layer caching
# Note: requirements file is named 'requirement.txt' in this repo
COPY requirement.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirement.txt \
    # Ensure --reload works in start.sh
    && pip install --no-cache-dir watchfiles

# Copy application
COPY main.py ./
COPY start.sh ./
RUN chmod +x start.sh

# Expose API port defined in start.sh (uvicorn --port 8787)
EXPOSE 8787

# Provide GOOGLE_API_KEY at runtime: `-e GOOGLE_API_KEY=...`
CMD ["sh", "./start.sh"]
