FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INSIGHTFACE_HOME=/app/data/dbdata/insightface

WORKDIR /app

# libgl1/libglib2.0-0 are required by opencv; build-essential to compile insightface
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# CPU-only torch/torchvision first: ultralytics would otherwise pull multi-GB
# CUDA wheels, which are useless on the demo machine and slow down the build.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.4.1 torchvision==0.19.1
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
