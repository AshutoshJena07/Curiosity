# Production Dockerfile for Curiosity AI Backend & Real-Time Dashboard
FROM python:3.11-slim

# Install system dependencies required for OpenCV, PyMuPDF, and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Setup non-root user (Hugging Face Spaces requirement)
RUN useradd -m -u 1000 user
WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure data and output directories exist with full read/write permissions
RUN mkdir -p data outputs data/annotated_images data/generated_audio data/cache && \
    chown -R 1000:1000 /app && \
    chmod -R 777 /app/data /app/outputs

USER 1000
ENV HOME=/home/user \
    PYTHONUNBUFFERED=1 \
    PORT=7860

EXPOSE 7860

# Start FastAPI application (7860 default for HF Spaces, overrideable by Render/Railway via $PORT)
CMD ["sh", "-c", "python -m uvicorn src.image_analytics.api:app --host 0.0.0.0 --port ${PORT:-7860}"]
