# DoqToq Deployment Guide

This guide covers different deployment options for DoqToq, from local development to production environments.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Deployments](#cloud-deployments)
4. [Production Considerations](#production-considerations)
5. [Monitoring & Logging](#monitoring--logging)
6. [Security Guidelines](#security-guidelines)

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/shre-db/doqtoq.git
cd doqtoq

# Run installation script
./install.sh --method conda --dev

# Activate environment
conda activate doqtoq

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start application
streamlit run app/main.py
```

### Manual Setup

```bash
# Create conda environment
conda env create -f environment.yaml
conda activate doqtoq

# Or use pip
python -m venv doqtoq-env
source doqtoq-env/bin/activate  # On Windows: doqtoq-env\Scripts\activate
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt

# Set up pre-commit hooks (optional)
pre-commit install
```

## Docker Deployment

### Single Container

```bash
# Build image
docker build -f Dockerfile.venv -t doqtoq:latest .

# Run container
docker run -p 8501:8501 \
  -e GOOGLE_API_KEY=your_key \
  -e MISTRAL_API_KEY=your_key \
  -v $(pwd)/data:/app/data \
  doqtoq:latest
```

### Docker Compose (Recommended)

```bash
# Create .env file
cp .env.example .env
# Edit with your API keys

# Start services
docker-compose up -d

# With monitoring (optional)
docker-compose --profile monitoring up -d

# With nginx reverse proxy (production)
docker-compose --profile production up -d
```

### Docker Compose Configuration

```yaml
# docker-compose.override.yml for local development
version: '3.8'
services:
  doqtoq:
    volumes:
      - .:/app
    environment:
      - STREAMLIT_SERVER_RUNONSAVE=true
    command: streamlit run app/main.py --server.runOnSave=true
```

## Cloud Deployments

### Heroku

1. **Prepare for Heroku**

```bash
# Create Procfile
echo "web: streamlit run app/main.py --server.port=\$PORT --server.address=0.0.0.0" > Procfile

# Create runtime.txt
echo "python-3.12.0" > runtime.txt
```

2. **Deploy**

```bash
# Install Heroku CLI and login
heroku login

# Create app
heroku create your-doqtoq-app

# Set environment variables
heroku config:set GOOGLE_API_KEY=your_key
heroku config:set MISTRAL_API_KEY=your_key

# Deploy
git push heroku main
```

### Google Cloud Platform

#### Cloud Run

1. **Build and push image**

```bash
# Build for Cloud Run
docker build -t gcr.io/YOUR_PROJECT_ID/doqtoq .

# Push to registry
docker push gcr.io/YOUR_PROJECT_ID/doqtoq
```

2. **Deploy to Cloud Run**

```bash
gcloud run deploy doqtoq \
  --image gcr.io/YOUR_PROJECT_ID/doqtoq \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8501 \
  --set-env-vars GOOGLE_API_KEY=your_key,MISTRAL_API_KEY=your_key
```

#### App Engine

```yaml
# app.yaml
runtime: python312

env_variables:
  GOOGLE_API_KEY: your_key
  MISTRAL_API_KEY: your_key

handlers:
- url: /.*
  script: auto
```

### AWS

#### ECS with Fargate

1. **Create task definition**

```json
{
  "family": "doqtoq",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "doqtoq",
      "image": "your-account.dkr.ecr.region.amazonaws.com/doqtoq:latest",
      "portMappings": [
        {
          "containerPort": 8501,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GOOGLE_API_KEY",
          "value": "your_key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/doqtoq",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Elastic Beanstalk

```yaml
# .ebextensions/01_packages.config
packages:
  yum:
    python3: []
    python3-pip: []

# .ebextensions/02_python.config
container_commands:
  01_install_requirements:
    command: "pip3 install -r requirements.txt"
```

### Azure

#### Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name doqtoq \
  --image your-registry.azurecr.io/doqtoq:latest \
  --ports 8501 \
  --environment-variables GOOGLE_API_KEY=your_key MISTRAL_API_KEY=your_key \
  --cpu 1 \
  --memory 2
```

#### App Service

```yaml
# azure-pipelines.yml
trigger:
- main

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: Docker@2
  inputs:
    containerRegistry: 'myACR'
    repository: 'doqtoq'
    command: 'buildAndPush'
    Dockerfile: 'Dockerfile.venv'

- task: AzureWebAppContainer@1
  inputs:
    azureSubscription: 'mySubscription'
    appName: 'my-doqtoq-app'
    containers: 'myacr.azurecr.io/doqtoq:latest'
```

## Production Considerations

### Performance Optimization

1. **Resource Allocation**

```yaml
# docker-compose.yml
services:
  doqtoq:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

2. **Caching Strategy**

```python
# Enable vector store persistence
VECTOR_STORE_PERSIST = True
VECTOR_STORE_PATH = "/app/data/vectorstore"

# Redis for session caching (optional)
REDIS_URL = "redis://redis:6379"
```

3. **Load Balancing**

```nginx
# nginx.conf
upstream doqtoq_backend {
    server doqtoq:8501;
    server doqtoq2:8501;
    server doqtoq3:8501;
}

server {
    listen 80;
    location / {
        proxy_pass http://doqtoq_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Scaling

#### Horizontal Scaling

```yaml
# docker-compose.yml
services:
  doqtoq:
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
```

#### Auto-scaling with Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: doqtoq
spec:
  replicas: 3
  selector:
    matchLabels:
      app: doqtoq
  template:
    metadata:
      labels:
        app: doqtoq
    spec:
      containers:
      - name: doqtoq
        image: doqtoq:latest
        ports:
        - containerPort: 8501
        env:
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: doqtoq-secrets
              key: google-api-key
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: doqtoq-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: doqtoq
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Monitoring & Logging

### Application Monitoring

```yaml
# docker-compose.yml with monitoring
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./monitoring/grafana:/etc/grafana/provisioning
```

### Health Checks

```python
# app/health.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import psutil
import os

app = FastAPI()

@app.get("/health")
async def health_check():
    return JSONResponse({
        "status": "healthy",
        "memory_usage": psutil.virtual_memory().percent,
        "cpu_usage": psutil.cpu_percent(),
        "disk_usage": psutil.disk_usage('/').percent
    })

@app.get("/ready")
async def readiness_check():
    # Check if models are loaded
    if os.path.exists("/app/.model_loaded"):
        return JSONResponse({"status": "ready"})
    else:
        return JSONResponse({"status": "not ready"}, status_code=503)
```

### Logging Configuration

```python
# utils/logging_config.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_production_logging():
    """Setup structured logging for production"""

    # Create JSON formatter
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler('/app/logs/app.log')
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
```

## Security Guidelines

### Environment Variables

```bash
# Use secrets management in production
# Never commit API keys to version control

# Docker secrets
echo "your_google_api_key" | docker secret create google_api_key -
echo "your_mistral_api_key" | docker secret create mistral_api_key -
```

### Network Security

```yaml
# docker-compose.yml with network security
networks:
  doqtoq_internal:
    driver: bridge
    internal: true

  doqtoq_external:
    driver: bridge

services:
  doqtoq:
    networks:
      - doqtoq_internal
      - doqtoq_external

  database:
    networks:
      - doqtoq_internal  # Only internal network
```

### SSL/TLS Configuration

```nginx
# nginx SSL configuration
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://doqtoq:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Security Headers

```python
# Add security headers to Streamlit
import streamlit as st

def add_security_headers():
    st.markdown("""
    <script>
    // Add security headers via meta tags
    const meta_csp = document.createElement('meta');
    meta_csp.setAttribute('http-equiv', 'Content-Security-Policy');
    meta_csp.setAttribute('content', "default-src 'self'");
    document.head.appendChild(meta_csp);
    </script>
    """, unsafe_allow_html=True)
```

## Troubleshooting

### Common Deployment Issues

1. **Port binding issues**
   ```bash
   # Check if port is in use
   lsof -i :8501

   # Use different port
   streamlit run app/main.py --server.port=8502
   ```

2. **Memory issues**
   ```bash
   # Monitor memory usage
   docker stats

   # Increase memory limits
   docker run -m 4g doqtoq:latest
   ```

3. **API key issues**
   ```bash
   # Verify environment variables
   docker exec -it container_name env | grep API_KEY
   ```

### Performance Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Profile memory usage
import tracemalloc
tracemalloc.start()

# Add timing decorators
import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f} seconds")
        return result
    return wrapper
```

## Support

For deployment-specific issues:
1. Check the [troubleshooting section](#troubleshooting)
2. Review logs: `docker-compose logs doqtoq`
3. Open an issue on GitHub with deployment details
4. Join our community discussions

---

*This deployment guide is continuously updated. For the latest information, visit our [GitHub repository](https://github.com/shre-db/doqtoq).*
