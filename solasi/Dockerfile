FROM python:3.12-alpine
RUN apk add --no-cache tzdata
RUN pip install --no-cache-dir aiohttp==3.10.5
ARG BUILD_VERSION=""
ENV SOLASI_VERSION=${BUILD_VERSION}
COPY app /app
WORKDIR /app
CMD ["python", "-u", "/app/main.py"]
