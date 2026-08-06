# Deployment Architecture

## Overview

Production deployment with Kubernetes, Docker Compose, and infrastructure as code.

## Deployment Options

| Environment | Method | Use Case |
|-------------|--------|----------|
| Development | Docker Compose | Local development |
| Staging | Kubernetes (Helm) | Pre-production testing |
| Production | Kubernetes (Helm + ArgoCD) | High availability |

## Kubernetes Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KUBERNETES CLUSTER                                   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      INGRESS NAMESPACE                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │   nginx     │  │   Cert-     │  │   External  │                 │   │
│  │  │  Ingress    │  │  Manager    │  │  DNS        │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                      │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │              APPLICATION NAMESPACE                                    │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │ │
│  │  │ Frontend │  │ Backend  │  │ Workers  │  │  Cron    │  │  Init    │   │ │
│  │  │  (HPA)   │  │  (HPA)   │  │  (HPA)   │  │  Jobs    │  │  Jobs    │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  └─────────────────────────────────┼─────────────────────────────────────┘ │
│                                    │                                      │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │              DATA NAMESPACE                                        │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │ │
│  │  │PostgreSQL│  │ ChromaDB │  │  Redis   │  │ Ollama   │               │ │
│  │  │  (PVC)   │  │  (PVC)   │  │  (PVC)   │  │ (GPU)    │               │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘               │ │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                      │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │              MONITORING NAMESPACE                                   │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │ │
│  │  │Prometheus│  │ Grafana  │  │  Jaeger  │  │  Loki    │               │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘               │ │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Helm Chart Structure

```
kifpilot/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-staging.yaml
├── values-prod.yaml
├── templates/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── frontend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── ingress.yaml
│   ├── backend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── ingress.yaml
│   ├── workers/
│   │   ├── deployment.yaml
│   │   └── hpa.yaml
│   ├── database/
│   │   ├── postgres-statefulset.yaml
│   │   ├── chromadb-statefulset.yaml
│   │   ├── redis-statefulset.yaml
│   │   ├── ollama-statefulset.yaml
│   │   └── services.yaml
│   ├── monitoring/
│   │   ├── prometheus.yaml
│   │   ├── grafana.yaml
│   │   ├── jaeger.yaml
│   │   └── loki.yaml
│   ├── rbac.yaml
│   ├── network-policies.yaml
│   └── pod-disruption-budgets.yaml
└── charts/
    ├── postgresql/
    ├── redis/
    └── chromadb/
```

## Key Kubernetes Resources

### Backend Deployment

```yaml
# templates/backend/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kifpilot-backend
  labels:
    app: kifpilot-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kifpilot-backend
  template:
    metadata:
      labels:
        app: kifpilot-backend
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: kifpilot-backend
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: backend
        image: "{{ .Values.backend.image }}:{{ .Values.backend.tag }}"
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: kifpilot-config
        - secretRef:
            name: kifpilot-secrets
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: uploads
          mountPath: /app/uploads
      volumes:
      - name: uploads
        persistentVolumeClaim:
          claimName: kifpilot-uploads
---
# templates/backend/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: kifpilot-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kifpilot-backend
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

### PostgreSQL StatefulSet

```yaml
# templates/database/postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kifpilot-postgres
spec:
  serviceName: kifpilot-postgres
  replicas: 1
  selector:
    matchLabels:
      app: kifpilot-postgres
  template:
    metadata:
      labels:
        app: kifpilot-postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        ports:
        - containerPort: 5432
        envFrom:
        - secretRef:
            name: kifpilot-secrets
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "2Gi"
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        livenessProbe:
          exec:
            command: ["pg_isready", "-U", "postgres"]
          initialDelaySeconds: 30
        readinessProbe:
          exec:
            command: ["pg_isready", "-U", "postgres"]
          initialDelaySeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "fast-ssd"
      resources:
        requests:
          storage: 100Gi
```

### Ollama with GPU

```yaml
# templates/database/ollama-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kifpilot-ollama
spec:
  serviceName: kifpilot-ollama
  replicas: 1
  selector:
    matchLabels:
      app: kifpilot-ollama
  template:
    metadata:
      labels:
        app: kifpilot-ollama
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        resources:
          requests:
            cpu: "2000m"
            memory: "8Gi"
            nvidia.com/gpu: 1
          limits:
            cpu: "4000m"
            memory: "16Gi"
            nvidia.com/gpu: 1
        volumeMounts:
        - name: ollama-data
          mountPath: /root/.ollama
        env:
        - name: OLLAMA_NUM_PARALLEL
          value: "2"
        - name: OLLAMA_MAX_LOADED_MODELS
          value: "2"
      volumes:
      - name: ollama-data
        persistentVolumeClaim:
          claimName: ollama-data
  volumeClaimTemplates:
  - metadata:
      name: ollama-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "fast-ssd"
      resources:
        requests:
          storage: 50Gi
```

## Configuration

### ConfigMap

```yaml
# templates/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kifpilot-config
data:
  APP_ENV: "production"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  DATABASE_URL: "postgresql+asyncpg://postgres:$(POSTGRES_PASSWORD)@kifpilot-postgres:5432/kifpilot"
  CHROMA_PERSIST_DIR: "/data/chroma"
  OLLAMA_BASE_URL: "http://kifpilot-ollama:11434"
  OLLAMA_CHAT_MODEL: "qwen3.5:4b"
  OLLAMA_EMBED_MODEL: "nomic-embed-text"
  CORS_ORIGINS: '["https://app.example.com"]'
  MAX_FILE_SIZE_MB: "50"
  RETRIEVAL_MIN_SCORE: "0.3"
  RETRIEVAL_MAX_CONTEXT: "8000"
  RERANKER_ENABLED: "true"
  RERANKER_MODEL_NAME: "cross-encoder/ms-marco-MiniLM-L-6-v2"
  CONTEXT_COMPRESSION_ENABLED: "true"
  CONTEXT_COMPRESSION_MAX_TOKENS: "8000"
```

### Secrets

```yaml
# templates/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: kifpilot-secrets
type: Opaque
stringData:
  SECRET_KEY: "CHANGE_ME_IN_PRODUCTION_MIN_32_CHARS"
  POSTGRES_PASSWORD: "CHANGE_ME"
  POSTGRES_USER: "postgres"
  POSTGRES_DB: "kifpilot"
```

## Network Policies

```yaml
# templates/network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
spec:
  podSelector:
    matchLabels:
      app: kifpilot-backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: kifpilot-postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: kifpilot-chromadb
    ports:
    - protocol: TCP
      port: 8000
  - to:
    - podSelector:
        matchLabels:
          app: kifpilot-ollama
    ports:
    - protocol: TCP
      port: 11434
  - to:
    - podSelector:
        matchLabels:
          app: kifpilot-redis
    ports:
    - protocol: TCP
      port: 6379
  - to: []  # Allow DNS
    ports:
    - protocol: UDP
      port: 53
```

## Ingress

```yaml
# templates/backend/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: kifpilot-backend-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.example.com
    secretName: kifpilot-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: kifpilot-backend
            port:
              number: 8000
```

## ArgoCD Application

```yaml
# argocd/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: kifpilot
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/kifpilot/kifpilot-helm
    targetRevision: main
    path: kifpilot
    helm:
      valueFiles:
      - values-prod.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: kifpilot-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

## Docker Compose (Development)

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: kifpilot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  chromadb:
    image: chromadb/chroma:0.4.22
    volumes:
      - chroma_data:/data
    ports:
      - "8001:8000"
    environment:
      CHROMA_SERVER_HOST: 0.0.0.0
      CHROMA_SERVER_HTTP_PORT: 8000

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    deploy:
      resources:
        reservations:
          devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/kifpilot
      CHROMA_PERSIST_DIR: /data/chroma
      OLLAMA_BASE_URL: http://ollama:11434
    volumes:
      - ./backend:/app
      - uploads:/app/uploads
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      chromadb:
        condition: service_started
      ollama:
        condition: service_started

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    environment:
      VITE_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    depends_on:
      - backend

volumes:
  postgres_data:
  chroma_data:
  ollama_data:
  redis_data:
  uploads:
```

## Production Checklist

- [ ] Secrets rotated and stored in Vault/Sealed Secrets
- [ ] TLS certificates via cert-manager
- [ ] Network policies applied
- [ ] Resource limits and requests set
- [ ] HPA configured for all deployments
- [ ] Pod disruption budgets configured
- [ ] Backup schedules for PostgreSQL, ChromaDB, uploads
- [ ] Monitoring dashboards imported
- [ ] Alerting rules configured
- [ ] Log aggregation to Loki
- [ ] Distributed tracing to Jaeger
- [ ] Load testing completed
- [ ] Chaos engineering experiments run
- [ ] Runbook documentation complete
- [ ] Disaster recovery tested