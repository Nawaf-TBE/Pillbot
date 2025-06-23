# 🚀 Production Deployment Guide

## **Deployment Options (Ranked by Ease)**

### **1. 🌟 FastAPI Web Service (Recommended)**
**Perfect for: Production APIs, integration with other systems**

#### Quick Start (Local Testing)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the web server
python app.py
```
**Access your API at: http://localhost:8000**

**Features:**
- ✅ Professional REST API with interactive docs
- ✅ File upload and processing
- ✅ Background task processing
- ✅ Complete audit trail
- ✅ Ready for integration

---

### **2. 🐳 Docker Deployment (Production Ready)**
**Perfect for: Cloud deployment, scalability, production environments**

#### Using Docker Compose (Easiest)
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

#### Using Docker Directly
```bash
# Build image
docker build -t priorauth-api .

# Run container
docker run -d \
  -p 8000:8000 \
  -e LLAMAPARSE_API_KEY=your_key_here \
  -e GEMINI_API_KEY=your_key_here \
  -v $(pwd)/data:/app/data \
  --name priorauth-api \
  priorauth-api
```

**Features:**
- ✅ Isolated environment
- ✅ Easy scaling
- ✅ Production-ready
- ✅ Health checks included

---

### **3. ☁️ Cloud Platform Deployment**

#### **Heroku (Easiest Cloud)**
```bash
# Install Heroku CLI, then:
heroku create your-app-name
heroku config:set LLAMAPARSE_API_KEY=your_key_here
heroku config:set GEMINI_API_KEY=your_key_here
git push heroku main
```

#### **Railway** 
1. Connect your GitHub repo to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically

#### **Render**
1. Connect GitHub repo
2. Set environment variables
3. Deploy with one click

#### **DigitalOcean App Platform**
1. Connect GitHub repo
2. Configure environment variables
3. Deploy

---

## **Frontend Options**

### **Do You Need a Frontend?**

**✅ NO FRONTEND NEEDED IF:**
- API integration with existing systems
- Developer/technical users
- Programmatic access only
- Using curl/Postman for testing

**✅ FRONTEND HELPFUL IF:**
- Non-technical users
- Manual document upload workflow
- Visual feedback needed
- End-user application

### **Option 1: Use Built-in Web Interface**
Your FastAPI app includes a **beautiful web interface**:
- **Main page**: `http://localhost:8000/` 
- **Interactive API docs**: `http://localhost:8000/docs`
- **Upload and test directly in browser**

### **Option 2: Simple HTML Frontend** (Optional)
```html
<!DOCTYPE html>
<html>
<head><title>Prior Auth Processor</title></head>
<body>
    <h1>Upload Prior Authorization Document</h1>
    <form action="http://localhost:8000/process-document" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".pdf" required>
        <button type="submit">Process Document</button>
    </form>
</body>
</html>
```

---

## **Environment Configuration**

### **Required Environment Variables**
```bash
# API Keys (Required for full functionality)
LLAMAPARSE_API_KEY=your_llamaparse_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Optional Configuration
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TEMPERATURE=0.1
HOST=0.0.0.0
PORT=8000
WORKERS=1
```

### **Production .env File**
```bash
# Core API Keys
LLAMAPARSE_API_KEY=llx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Performance Settings
GEMINI_MODEL=gemini-1.5-pro  # Higher quality for production
GEMINI_TEMPERATURE=0.05      # More consistent results
LLAMAPARSE_TIMEOUT=300       # 5 minute timeout

# Server Settings
HOST=0.0.0.0
PORT=8000
WORKERS=4                    # Scale based on your server
```

---

## **API Usage Examples**

### **Upload and Process Document**
```bash
# Upload PDF for processing
curl -X POST "http://localhost:8000/process-document" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@prior_auth_document.pdf" \
  -F "extract_entities=true" \
  -F "use_ocr=true"
```

### **Check Processing Status**
```bash
# Get document status
curl "http://localhost:8000/documents/{document_id}"
```

### **List All Documents**
```bash
# List all processed documents
curl "http://localhost:8000/documents"
```

### **Download Results**
```bash
# Download processed data as JSON
curl "http://localhost:8000/documents/{document_id}/download" -o results.json
```

---

## **Integration Examples**

### **Python Client**
```python
import requests

# Upload document
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/process-document',
        files={'file': f}
    )
    doc_id = response.json()['document_id']

# Check status
status = requests.get(f'http://localhost:8000/documents/{doc_id}').json()
print(f"Status: {status['document']['status']}")
```

### **JavaScript/Node.js**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/process-document', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log('Document ID:', data.document_id));
```

---

## **Scaling and Performance**

### **Production Optimizations**
```bash
# Use multiple workers
WORKERS=4

# Use faster model for higher throughput
GEMINI_MODEL=gemini-1.5-flash

# Optimize for consistency
GEMINI_TEMPERATURE=0.05
```

### **Load Balancing with Nginx**
```nginx
upstream app {
    server priorauth-api:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## **Monitoring and Logs**

### **Health Monitoring**
```bash
# Check API health
curl http://localhost:8000/health

# Check system status
curl http://localhost:8000/status
```

### **Docker Logs**
```bash
# View real-time logs
docker-compose logs -f

# View specific service logs
docker-compose logs priorauth-api
```

### **Production Monitoring Tools**
- **Health checks**: Built-in `/health` endpoint
- **Metrics**: Can integrate with Prometheus
- **Logging**: Structured JSON logs for production
- **Alerts**: Set up monitoring on health endpoint

---

## **Security Considerations**

### **Production Security**
```bash
# Set secure CORS origins
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Use HTTPS in production
# Set up SSL certificates
# Use environment variables for secrets
```

### **API Key Security**
- ✅ Never commit API keys to git
- ✅ Use environment variables
- ✅ Rotate keys regularly
- ✅ Monitor API usage

---

## **Troubleshooting**

### **Common Issues**
1. **"API key not found"** → Check your `.env` file
2. **"Tesseract not found"** → Install Tesseract OCR system package
3. **"Port already in use"** → Change PORT environment variable
4. **"Permission denied"** → Check file permissions for data directory

### **Debug Mode**
```bash
# Run with debug logging
LOG_LEVEL=DEBUG python app.py
```

---

## **Quick Decision Guide**

**Choose FastAPI + Docker if you want:**
- ✅ Professional production deployment
- ✅ Easy scaling and management  
- ✅ Integration with other systems
- ✅ No frontend development needed

**The built-in web interface provides:**
- ✅ Interactive API documentation
- ✅ File upload testing
- ✅ Real-time processing status
- ✅ Download processed results

**🎯 Recommendation: Start with FastAPI + Docker - it's production-ready and provides everything you need!** 