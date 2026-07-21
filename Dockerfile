FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for PyMuPDF & ChromaDB
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install all packages directly
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy remaining project files
COPY . .

# Pre-build vector store during image creation
RUN python scrape_and_embed.py

# Expose port and launch application
EXPOSE 10000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]