# 🚀 Deployment Guide — NutritionVQA-RAG

This project is fully containerized using Docker and Docker Compose for easy deployment.

## 📋 Prerequisites
- Docker & Docker Compose installed
- MongoDB Atlas account (with a Vector Search index named `default`)
- Mistral AI API Key
- HuggingFace API Token

## 🛠️ Step 1: Configuration
Ensure you have a `.env` file in the project root with the following:
```env
MONGODB_URI=your_atlas_uri
MISTRAL_API_KEY=your_mistral_key
HF_TOKEN=your_huggingface_token
```

## 🐳 Step 2: Deployment with Docker Compose
Run the following command in the project root:
```bash
docker-compose up --build -d
```
This will start:
1.  **Backend**: FastAPI server at `http://localhost:8000`
2.  **Redis**: Caching server at `http://localhost:6379`
3.  **Frontend**: Nginx server at `http://localhost:80`

## 📊 Step 3: Populate the Database
Once the backend is running, you can manually run the ingestion script if you're NOT in a container environment, or you can use the `/ingest` shortcut if implemented. 

For the initial setup:
```bash
python backend/ingest.py
```

## 🔍 Step 4: Access the Dashboard
Open your browser and go to `http://localhost`. 
- Chat interface is ready.
- Drag-and-drop image uploads are active.
- Real-time expert nutrition AI is waiting!

## 🐳 Step 5: Stop Deployment
To stop all services:
```bash
docker-compose down
```
