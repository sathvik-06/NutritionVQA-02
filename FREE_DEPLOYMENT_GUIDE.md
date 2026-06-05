# 🚀 Fully Free Deployment Guide for Nutrition VQA

Since your application uses heavy Machine Learning models (PaddleOCR / PyTorch), standard free tiers like Render or Heroku (which offer only 512MB of RAM) **will crash**. 

To host this for **100% free**, you must split the application:
1. **Frontend (HTML/JS/CSS):** Deploy on **Vercel**
2. **Backend (FastAPI + OCR):** Deploy on **Hugging Face Spaces** (They give 16GB of RAM for free!)

---

## Part 1: Deploying the Backend on Hugging Face Spaces (Free ML Hosting)

Hugging Face Spaces allows you to host Python APIs inside Docker containers for free.

### Step 1: Create a Hugging Face Account
1. Go to [Hugging Face](https://huggingface.co/) and create a free account.
2. Go to your profile and click **New Space**.
3. Name it `nutritionvqa-backend`.
4. Select **Docker** as the Space SDK, and choose the **Blank** template.
5. Set Space Hardware to **Free (2 vCPU, 16GB RAM)**.
6. Click **Create Space**.

### Step 2: Add your Backend Code
In your new Hugging Face Space, click **Files** -> **Add file** -> **Upload files**, and upload the following:
* Your entire `backend/` folder.
* Your `requirements.txt` file.
* Your `.env` file (Actually, it's better to add these as "Secrets" in the Space settings).

### Step 3: Create a `Dockerfile`
In your Hugging Face Space, click **Add file** -> **Create a new file**. Name it `Dockerfile` and paste this exact code:

```dockerfile
FROM python:3.11-slim

# Install system dependencies required for OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy requirements and install them
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY --chown=user . .

# Expose port 7860 (Hugging Face default)
EXPOSE 7860

# Run the FastAPI app on port 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

### Step 4: Add your Secrets
1. Go to **Settings** in your Hugging Face Space.
2. Scroll down to **Variables and secrets**.
3. Add your `MISTRAL_API_KEY`, `MONGODB_URI` (Use MongoDB Atlas free tier for cloud database), etc.

*Your backend will now build and launch! Once it says "Running", click the three dots at the top right -> **Embed this Space** to find your direct API URL (it will look like `https://yourusername-nutritionvqa-backend.hf.space`).*

---

## Part 2: Deploying the Frontend on Vercel (Free & Lightning Fast)

Now that your backend is running, you need to point your frontend to it and deploy.

### Step 1: Update API URLs in your Frontend
Open your `frontend/js/app.js` and `frontend/js/auth.js` files. 
Change the base URL from `http://localhost:8000` to your new Hugging Face API URL:
```javascript
const API_BASE_URL = 'https://yourusername-nutritionvqa-backend.hf.space';
```

### Step 2: Deploy to Vercel
1. Go to [Vercel](https://vercel.com/) and create a free account (sign in with GitHub).
2. Click **Add New** -> **Project**.
3. Import your `NutritionVQA-RAG` GitHub repository.
4. **Important Configuration:**
   * In the "Framework Preset", leave it as **Other**.
   * In the "Root Directory", click edit and select your `frontend/` folder.
5. Click **Deploy**.

## 🎉 Done!
Your Frontend is now live on a `.vercel.app` domain, making API requests to your **Free 16GB RAM** Hugging Face backend, which processes the OCR and connects to your cloud MongoDB database.
