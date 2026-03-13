FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libgobject-2.0-0 \
    libglib2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Smoke test: catches missing system libs at build time (not first request)
# WeasyPrint lazy-loads libgobject, libcairo, libpango at first write_pdf() call.
# Without this, docker build succeeds but first POST /convert crashes.
RUN python -c "from weasyprint import HTML; HTML(string='<p>test</p>').write_pdf()"

COPY main.py .
COPY fixture.json .

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
