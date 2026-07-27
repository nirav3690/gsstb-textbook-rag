FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create user with UID 1000 for non-root runtime environments
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/app/backend \
    PORT=7860

# Copy requirements & install dependencies (using CPU PyTorch for lightweight cloud builds)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Pre-download embedding model during build to eliminate runtime download delay & timeouts
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Copy application files
COPY --chown=user:user backend /app/backend
COPY --chown=user:user frontend /app/frontend

# Create storage directories and set permissions
RUN mkdir -p /app/data/uploads /app/chroma_db && \
    chown -R user:user /app

USER user

EXPOSE 7860

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"
