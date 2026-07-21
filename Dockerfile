FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project code
COPY . .

EXPOSE 10000

# Run database setup ONCE at container start, then launch FastAPI
CMD ["sh", "-c", "python scrape_and_embed.py && uvicorn main:app --host 0.0.0.0 --port 10000"]