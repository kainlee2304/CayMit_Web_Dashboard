FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM python:3.11-slim AS runtime
WORKDIR /app/backend
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY models/ /app/models/
COPY --from=frontend-builder /build/out/ ./frontend/
ENV FRONTEND_DIR=frontend UPLOAD_DIR=/data/uploads
VOLUME ["/data/uploads"]
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
