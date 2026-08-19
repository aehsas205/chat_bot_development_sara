FROM python:3.10-slim

WORKDIR /app

# Install build tools along with Chromium for headless scraping
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    chromium \
    chromium-driver \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome environment variables for Selenium
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

# Keep pre-built index intact; server boots instantly without blocking
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]