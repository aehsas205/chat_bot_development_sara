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

"""To resolve the 512MB memory crash issues on Render and ensure complete PDF data coverage,(we cant install pypdf )
I have optimized our deployment pipeline. Instead of re-scraping and embedding on every server startup,
the app now directly loads our pre-built vector database (58 chunks) from the repository.
This makes deployments significantly faster and stable, and whenever we have new website content or PDFs,
we can simply re-embed locally and push the updated database.""""