FROM python:3.11
RUN apt-get update && apt-get install -y --no-install-recommends chromium openjdk-21-jre-headless iproute2 strace && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir jsonschema==4.23.0 playwright==1.51.0
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-21-jdk-headless fonts-noto-cjk && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir six==1.17.0 rfc3339-validator==0.1.4 rfc3986-validator==0.1.1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /work/tyr
CMD ["python", "-B", "/input/accept.py"]
