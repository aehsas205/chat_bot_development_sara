FROM python:3.10-slim

WORKDIR /app

# Install system build dependencies required for PyMuPDF & C++ extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose Render default port
EXPOSE 10000

# Execute embedding script on startup to build ChromaDB, then start FastAPI server
CMD ["sh", "-c", "python scrape_and_embed.py && uvicorn main:app --host 0.0.0.0 --port 10000"]