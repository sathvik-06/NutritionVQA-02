# Local Implementation Guide (No Docker)

This guide explains how to set up and run the **NutritionVQA-RAG** project directly on your Windows machine without using Docker or Docker Desktop.

## Prerequisites

- **Python 3.10 to 3.13** installed.
- **Node.js** (Optional, for serving frontend separately, but not required with the current integrated setup).
- **Internet Access** (For downloading AI models and connecting to MongoDB Atlas).

---

## 🚀 Quick Start Steps

### 1. Create a Virtual Environment
Open PowerShell or Command Prompt in the project root (`NutritionVQA-RAG`) and run:
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 2. Install Dependencies
Install all required Python packages:
```powershell
pip install -r requirements.txt
```
> [!NOTE]
> This might take a few minutes as it downloads heavy packages like `torch`, `paddlepaddle`, and `sentence-transformers`.

### 3. Configure Environment Variables
Ensure your `.env` file is present in the root directory. It should already contain your MongoDB URI and Mistral API key.

### 4. Run the Combined Application
With your virtual environment activated, run:
```powershell
python backend/main.py
```
> [!TIP]
> I have modified `main.py` to serve the frontend automatically!

### 5. Access the App
Open your browser and navigate to:
**[http://localhost:8000](http://localhost:8000)**

---

## 🛠️ Components Status (No Docker)

| Component | Status | Note |
| :--- | :--- | :--- |
| **Backend (FastAPI)** | ✅ Ready | Started via `python backend/main.py`. |
| **Frontend (HTML/JS)** | ✅ Ready | Served integrated on port 8000. |
| **Database (MongoDB)** | ✅ Ready | Using the cloud Atlas URI in your `.env`. |
| **Cache (Redis)** | ⚠️ Optional | The app will work without Redis; caching will simply be disabled. |
| **AI Models (OCR/LLM)** | ✅ Ready | Loaded on-demand by the Python backend. |

---

## 📜 Automation Scripts

### `setup.bat` (Recommended)
You can create this file to automate the setup:
```batch
@echo off
echo Creating virtual environment...
python -m venv venv
echo Activating venv and installing requirements...
call venv\Scripts\activate
pip install -r requirements.txt
echo Setup complete!
pause
```

### `run.bat` (Recommended)
Run this to start the app anytime:
```batch
@echo off
call venv\Scripts\activate
python backend/main.py
pause
```
