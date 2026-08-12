FROM python:3.10-slim

WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .


EXPOSE 10000


#CMD ["sh", "-c", "python scrape_and_embed.py && uvicorn main:app --host 0.0.0.0 --port 10000"]


# FIXED: Removed 'python scrape_and_embed.py' so it uses your pre-built 58-chunk database!
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]