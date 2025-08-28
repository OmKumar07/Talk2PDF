# 🚀 Production Deployment Guide

## Prerequisites

- GitHub repository with your code
- Render account (for backend)
- Netlify account (for frontend)

## 🖥️ Backend Deployment on Render

### 1. Create New Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Use these settings:

### 2. Configuration Settings

```
Name: talk2pdf-backend
Environment: Python 3
Build Command: pip install -r backend/requirements.txt
Start Command: uvicorn app:app --host 0.0.0.0 --port $PORT --workers 2
```

### 3. Environment Variables

Set these in Render dashboard:

```
ENVIRONMENT=production
FRONTEND_URL=https://your-netlify-url.netlify.app
```

### 4. Advanced Settings

- **Root Directory**: `backend`
- **Python Version**: 3.12.0
- **Instance Type**: Starter (free tier)

## 🌐 Frontend Deployment on Netlify

### 1. Create New Site

1. Go to [Netlify Dashboard](https://app.netlify.com/)
2. Click "Add new site" → "Deploy with Git"
3. Connect your GitHub repository

### 2. Build Settings

```
Base directory: frontend
Build command: npm run build
Publish directory: frontend/dist
```

### 3. Environment Variables

Set in Netlify dashboard → Site settings → Environment variables:

```
VITE_API_URL=https://your-render-backend-url.onrender.com
VITE_ENVIRONMENT=production
```

### 4. Deploy Settings

- **Node version**: 18
- **Build timeout**: 15 minutes
- **Deploy previews**: Enabled

## 🔧 Post-Deployment Steps

### 1. Update CORS Settings

After deploying frontend, update backend environment variables:

```
FRONTEND_URL=https://your-actual-netlify-url.netlify.app
```

### 2. Update Frontend API URL

Update the production environment file:

```bash
# frontend/.env.production
VITE_API_URL=https://your-actual-render-url.onrender.com
```

### 3. Redeploy Both Services

- Redeploy Render service after updating FRONTEND_URL
- Redeploy Netlify after updating VITE_API_URL

## 🧪 Testing Production Deployment

### Health Checks

1. **Backend Health**: `https://your-render-url.onrender.com/health`
2. **Frontend**: Visit your Netlify URL
3. **API Connection**: Test file upload and question asking

### Performance Monitoring

- **Render**: Check logs and metrics in dashboard
- **Netlify**: Monitor build times and function usage
- **Frontend**: Use browser dev tools for performance

## 🔒 Security Considerations

### Backend Security

- CORS is properly configured for production
- File upload limits enforced (50MB)
- Error handling prevents information leakage
- API docs disabled in production

### Frontend Security

- Environment variables properly configured
- Security headers enabled via Netlify
- HTTPS enforced
- XSS protection enabled

## 📊 Performance Optimizations

### Backend

- Multiple uvicorn workers for concurrency
- Async background processing
- Memory-efficient batch processing
- Resource cleanup on failures

### Frontend

- Code splitting for smaller bundles
- Asset optimization and caching
- Minification enabled
- Source maps disabled in production

## 🚨 Troubleshooting

### Common Issues

1. **CORS Errors**: Verify FRONTEND_URL in Render environment
2. **API Connection Failed**: Check VITE_API_URL in Netlify
3. **Build Failures**: Verify Node/Python versions
4. **Upload Errors**: Check file size limits and storage

### Logs and Debugging

- **Render Logs**: Dashboard → Services → Logs
- **Netlify Logs**: Dashboard → Site → Functions → Logs
- **Browser Console**: Check for API errors

## 🔄 Continuous Deployment

### Automatic Deployments

- **Render**: Auto-deploys on main branch push
- **Netlify**: Auto-deploys on main branch push
- **Preview Deployments**: Netlify creates previews for PRs

### Manual Deployments

- **Render**: Dashboard → Deploy → Manual Deploy
- **Netlify**: Dashboard → Deploys → Trigger Deploy

## 📈 Scaling Considerations

### Backend Scaling

- Upgrade Render instance type for more traffic
- Consider database for persistent storage
- Implement Redis for shared processing status
- Add API rate limiting

### Frontend Scaling

- Netlify automatically handles CDN and scaling
- Consider implementing analytics
- Monitor Core Web Vitals
- Optimize images and assets

## 💰 Cost Optimization

### Free Tier Limits

- **Render**: 750 hours/month, sleeps after 15min inactivity
- **Netlify**: 100GB bandwidth, 300 build minutes/month

### Optimization Tips

- Use efficient algorithms to reduce processing time
- Implement proper caching strategies
- Monitor usage and upgrade only when needed
