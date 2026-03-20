# Storage S3 con cifratura (FASE 15)

Configurazione opzionale per servire i file media su AWS S3 con cifratura server-side.

## Dipendenze

```bash
pip install django-storages boto3
```

## Settings

```python
# settings/production.py o base
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-west-1")
AWS_S3_ENCRYPTION = True
AWS_S3_OBJECT_PARAMETERS = {"ServerSideEncryption": "AES256"}
# Opzionale: SSE-KMS
# AWS_S3_OBJECT_PARAMETERS = {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": "..."}
```

## Variabili d’ambiente

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `AWS_STORAGE_BUCKET_NAME`
- `AWS_S3_REGION_NAME` (default `eu-west-1`)

I file caricati saranno cifrati a riposo su S3 (RNF-002).
