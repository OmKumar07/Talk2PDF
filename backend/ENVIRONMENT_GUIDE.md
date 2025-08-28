# Talk2PDF Environment Configuration Guide

## Overview

This guide explains how to configure Talk2PDF backend for different deployment scenarios using environment files and manual host settings.

## Environment Files

### Available Configurations

1. **`.env.development`** - Local development
2. **`.env.production`** - Production deployment (Render/cloud)
3. **`.env.manual`** - Manual deployment with custom settings

### Using the Configuration Loader

Load a specific environment:

```bash
python config_loader.py dev          # Development
python config_loader.py production   # Production
python config_loader.py manual       # Manual/Custom
```

View available configurations:

```bash
python config_loader.py help
```

## Deployment Scenarios

### 1. Local Development

```bash
# Load development environment
python config_loader.py dev

# Start server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Environment Variables:**

- `ENVIRONMENT=development`
- `HOST=0.0.0.0`
- `PORT=8000`
- `DEBUG=true`
- `DOCS_ENABLED=true`

### 2. Render.com Deployment

**Step 1: Set Environment Variables in Render Dashboard**

```
GEMINI_API_KEY=your_actual_api_key
ENVIRONMENT=production
FRONTEND_URL=https://your-netlify-url.netlify.app
```

**Step 2: Deploy**

- Render will automatically use `render.yaml` configuration
- Build command loads production environment
- Server starts on PORT provided by Render

**Environment Variables:**

- `ENVIRONMENT=production`
- `HOST=0.0.0.0`
- `PORT=10000` (set by Render)
- `DEBUG=false`
- `DOCS_ENABLED=false`

### 3. Manual Host/VPS Deployment

```bash
# Load manual environment
python config_loader.py manual

# Edit .env file to customize settings
nano .env

# Start with custom settings
uvicorn app:app --host 0.0.0.0 --port 8080 --workers 4
```

**Customizable Settings:**

```env
# Server Configuration
HOST=0.0.0.0
PORT=8080

# Custom Domains
FRONTEND_URL=https://your-domain.com
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# File Upload Limits
MAX_FILE_SIZE=52428800  # 50MB

# SSL Configuration
SSL_ENABLED=true
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

## Environment Variables Reference

### Core Configuration

| Variable         | Description              | Default                 | Required |
| ---------------- | ------------------------ | ----------------------- | -------- |
| `ENVIRONMENT`    | deployment environment   | `development`           | No       |
| `GEMINI_API_KEY` | Google Gemini API key    | -                       | Yes      |
| `FRONTEND_URL`   | Frontend application URL | `http://localhost:5173` | No       |

### Server Configuration

| Variable       | Description         | Default   | Required |
| -------------- | ------------------- | --------- | -------- |
| `HOST`         | Server bind address | `0.0.0.0` | No       |
| `PORT`         | Server port         | `8000`    | No       |
| `DEBUG`        | Enable debug mode   | `true`    | No       |
| `DOCS_ENABLED` | Enable API docs     | `true`    | No       |

### CORS Configuration

| Variable          | Description                           | Default | Required |
| ----------------- | ------------------------------------- | ------- | -------- |
| `ALLOWED_ORIGINS` | Custom CORS origins (comma-separated) | -       | No       |

### File Upload

| Variable        | Description                | Default           | Required |
| --------------- | -------------------------- | ----------------- | -------- |
| `MAX_FILE_SIZE` | Maximum file size in bytes | `52428800` (50MB) | No       |

### Logging

| Variable     | Description   | Default | Required |
| ------------ | ------------- | ------- | -------- |
| `LOG_LEVEL`  | Logging level | `INFO`  | No       |
| `LOG_FORMAT` | Log format    | `text`  | No       |

### Security (Manual Deployment)

| Variable                         | Description          | Default | Required |
| -------------------------------- | -------------------- | ------- | -------- |
| `SSL_ENABLED`                    | Enable HTTPS         | `false` | No       |
| `SSL_CERT_PATH`                  | SSL certificate path | -       | No       |
| `SSL_KEY_PATH`                   | SSL private key path | -       | No       |
| `RATE_LIMIT_ENABLED`             | Enable rate limiting | `false` | No       |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Rate limit threshold | `60`    | No       |

## Example Configurations

### Development (Local)

```env
ENVIRONMENT=development
GEMINI_API_KEY=your_dev_api_key
FRONTEND_URL=http://localhost:5173
HOST=0.0.0.0
PORT=8000
DEBUG=true
DOCS_ENABLED=true
```

### Production (Render)

```env
ENVIRONMENT=production
GEMINI_API_KEY=your_prod_api_key
FRONTEND_URL=https://talk2pdf.netlify.app
HOST=0.0.0.0
PORT=10000
DEBUG=false
DOCS_ENABLED=false
MAX_FILE_SIZE=52428800
```

### Custom VPS

```env
ENVIRONMENT=production
GEMINI_API_KEY=your_prod_api_key
FRONTEND_URL=https://talk2pdf.yourdomain.com
HOST=0.0.0.0
PORT=443
DEBUG=false
DOCS_ENABLED=false
SSL_ENABLED=true
SSL_CERT_PATH=/etc/ssl/certs/talk2pdf.crt
SSL_KEY_PATH=/etc/ssl/private/talk2pdf.key
RATE_LIMIT_ENABLED=true
ALLOWED_ORIGINS=https://talk2pdf.yourdomain.com,https://www.yourdomain.com
```

## Troubleshooting

### Common Issues

1. **CORS Errors**

   - Check `FRONTEND_URL` matches your frontend domain
   - Add custom domains to `ALLOWED_ORIGINS`

2. **File Upload Fails**

   - Check `MAX_FILE_SIZE` setting
   - Verify server has enough disk space

3. **API Key Errors**

   - Ensure `GEMINI_API_KEY` is set correctly
   - Verify API key has proper permissions

4. **Port Conflicts**
   - Change `PORT` in environment file
   - Check for conflicting services

### Health Checks

Test your deployment:

```bash
# Check health endpoint
curl https://your-backend-url/health

# Check API docs (development only)
curl https://your-backend-url/docs
```

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use HTTPS** in production
3. **Enable rate limiting** for public deployments
4. **Restrict CORS origins** to your specific domains
5. **Set appropriate file size limits**
6. **Monitor logs** for suspicious activity

## Migration Guide

### From Basic Setup to Environment Configuration

1. **Backup existing `.env`**:

   ```bash
   cp .env .env.backup
   ```

2. **Choose environment type**:

   ```bash
   python config_loader.py production  # or dev/manual
   ```

3. **Update API key**:

   ```bash
   # Edit the loaded .env file
   nano .env
   # Set your actual GEMINI_API_KEY
   ```

4. **Test configuration**:
   ```bash
   uvicorn app:app --reload
   curl http://localhost:8000/health
   ```
