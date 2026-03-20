# Certificati SSL per AXDOC (FASE 15)

## Let's Encrypt (produzione)

```bash
certbot certonly --nginx -d yourdomain.com
# I certificati saranno in /etc/letsencrypt/live/yourdomain.com/
# Copia fullchain.pem e privkey.pem in nginx/ssl/cert.pem e key.pem
# oppure monta il volume letsencrypt nel container nginx
```

## Self-signed per test locale

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem \
  -subj "/C=IT/ST=Italia/L=Milano/O=Test/CN=localhost"
```

Poi avvia con: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`  
e verifica con: `curl -k https://localhost/api/health/`
