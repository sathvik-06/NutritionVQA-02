FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    git-lfs \
    ffmpeg \
    libsm6 \
    libxext6 \
    cmake \
    rsync \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install

COPY requirements.txt .

RUN pip install --no-cache-dir pip -U && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
