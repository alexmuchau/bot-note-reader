FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock* ./

RUN pip install uv && uv sync --frozen

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "python", "main.py"]