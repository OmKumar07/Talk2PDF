# 🔑 Environment Setup Guide

## Quick Setup for Development

### 1. **Copy the Environment Template**

```bash
cd backend
cp .env.example .env
```

### 2. **Get Your Gemini API Key**

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key

### 3. **Update Your .env File**

Open `backend/.env` and update:

```env
GEMINI_API_KEY=your_actual_api_key_here
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173
```

### 4. **Install Dependencies**

```bash
cd backend
pip install -r requirements.txt
```

### 5. **Test the Setup**

```bash
python test_gemini.py
```

## Environment Variables Explained

### **GEMINI_API_KEY** (Required)

- **Purpose**: Authenticates with Google's Gemini AI service
- **Where to get**: [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Free tier**: 15 requests/minute, 1,500 requests/day
- **Security**: Never commit this to git (already in .gitignore)

### **ENVIRONMENT** (Optional)

- **Development**: `development` (default)
- **Production**: `production`
- **Purpose**: Controls CORS settings and API documentation visibility

### **FRONTEND_URL** (Optional)

- **Development**: `http://localhost:5173` (default)
- **Production**: Your actual Netlify URL
- **Purpose**: CORS configuration for API access

## Production Deployment

### **Render.com Setup**

In your Render dashboard, set these environment variables:

```
GEMINI_API_KEY=your_actual_api_key_here
ENVIRONMENT=production
FRONTEND_URL=https://your-netlify-url.netlify.app
```

### **Security Best Practices**

- ✅ Never commit `.env` files to git
- ✅ Use different API keys for dev/prod if needed
- ✅ Monitor API usage in Google AI Studio
- ✅ Rotate API keys periodically

## Troubleshooting

### **"GEMINI_API_KEY not found" Error**

1. Check if `.env` file exists in backend directory
2. Verify the file contains `GEMINI_API_KEY=your_key`
3. Restart your development server after adding the key

### **"API key invalid" Error**

1. Verify the key is copied correctly (no extra spaces)
2. Check if the key is active in Google AI Studio
3. Ensure you have API access enabled

### **Rate Limit Errors**

- Free tier: 15 requests/minute
- Wait a minute and try again
- Consider upgrading to paid tier for production

## Local Development Commands

```bash
# Start backend with .env loaded
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Test Gemini integration
python test_gemini.py

# Check environment variables
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('API Key configured:', bool(os.getenv('GEMINI_API_KEY')))"
```
