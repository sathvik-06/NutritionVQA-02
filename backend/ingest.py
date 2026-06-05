import os
import sys
import json
import logging
import pickle
import numpy as np

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("ingest")

# Add backend dir to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    logger.error(f"Required libraries missing: {e}. Please ensure sentence-transformers and faiss-cpu are installed.")
    sys.exit(1)

# Paths
INDEX_DIR = os.path.join(backend_dir, "rag", "faiss_index")
INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss")
METADATA_PATH = os.path.join(INDEX_DIR, "metadata.pkl")

# High-quality offline fallback dataset representing common Nutrition QA pairs
OFFLINE_DATA = [
    {
        "question": "What is the recommended daily intake of sodium for adults?",
        "answer": "The American Heart Association (AHA) recommends no more than 2,300 milligrams (mg) a day and moving toward an ideal limit of no more than 1,500 mg per day for most adults, especially those with high blood pressure.",
        "context": "Sodium daily limits for adults, blood pressure guidelines, cardiovascular health."
    },
    {
        "question": "How many calories are in one gram of protein, carbohydrate, and fat?",
        "answer": "Proteins and carbohydrates both provide 4 calories per gram. Fats are much more energy-dense, providing 9 calories per gram. Alcohol provides 7 calories per gram.",
        "output": "Macronutrient caloric density: 4 kcal/g for protein/carbs, 9 kcal/g for fats."
    },
    {
        "question": "What is high fructose corn syrup and is it worse than regular sugar?",
        "answer": "High fructose corn syrup (HFCS) is a liquid sweetener made from cornstarch. Nutritionally, it is very similar to table sugar (sucrose), which is 50% fructose and 50% glucose. While both should be limited to prevent obesity and diabetes, research shows little metabolic difference between the two.",
        "context": "Added sweeteners, fructose vs glucose, metabolic health, obesity and diabetes risk."
    },
    {
        "question": "Why is dietary fiber important and what is the daily recommendation?",
        "answer": "Dietary fiber promotes digestive health, helps control blood sugar levels, lowers cholesterol, and aids in weight management by increasing satiety. The daily recommendation is 25 grams for women and 38 grams for men, or about 14 grams per 1,000 calories.",
        "context": "Digestive wellness, satiety, fiber recommendation, cholesterol management."
    },
    {
        "question": "What is the difference between saturated, unsaturated, and trans fats?",
        "answer": "Saturated fats (solid at room temperature) can raise LDL cholesterol and should be kept below 10% of total calories. Unsaturated fats (liquid, like olive oil) are heart-healthy and improve cholesterol profiles. Trans fats (partially hydrogenated oils) are highly harmful, raising bad cholesterol and lowering good cholesterol, and should be completely avoided.",
        "context": "Fat types, lipids, cardiovascular health, unsaturated vs saturated vs trans fats."
    },
    {
        "question": "How do you read a nutrition label to identify hidden sugars?",
        "answer": "To identify hidden sugars, look at the ingredients list for terms like high fructose corn syrup, anhydrous dextrose, cane crystals, dextrose, fructose, maltose, sucrose, honey, maple syrup, agave, or fruit juice concentrates. Check the 'Added Sugars' line under Total Carbohydrates.",
        "context": "Label literacy, ingredients reading, added sugars, sucrose variations."
    },
    {
        "question": "What are the key nutrition guidelines for diabetes management?",
        "answer": "Managing diabetes involves prioritizing complex carbohydrates with a low glycemic index (whole grains, legumes, non-starchy vegetables), monitoring portion sizes, pairing carbs with protein or fat to slow absorption, and strictly limiting added sugars (less than 25g/day).",
        "context": "Diabetes care, carbohydrate quality, insulin regulation, low glycemic index foods."
    },
    {
        "question": "Is cholesterol on nutrition labels bad for cardiovascular health?",
        "answer": "Dietary cholesterol (found in animal products like eggs and shellfish) has a relatively small impact on blood cholesterol levels for most people compared to saturated and trans fats. However, people with diabetes or existing heart disease should still moderate their dietary cholesterol intake.",
        "context": "Cardiovascular risk, dietary lipids, blood cholesterol response."
    },
    {
        "question": "What does 'gluten-free' mean and who needs to follow it?",
        "answer": "Gluten-free means the product contains no gluten, a protein found in wheat, barley, rye, and triticale. It is essential for individuals with celiac disease, an autoimmune condition where gluten damages the small intestine, and those with non-celiac gluten sensitivity.",
        "context": "Gluten restrictions, celiac disease, wheat protein allergens."
    },
    {
        "question": "How does high sodium intake affect blood pressure and the cardiovascular system?",
        "answer": "Excess sodium draws water into the bloodstream, increasing the total volume of blood in the blood vessels. This extra volume increases blood pressure (hypertension), putting extra strain on the heart and arteries, which increases the risk of stroke, heart failure, and heart disease.",
        "context": "Hypertension mechanisms, fluid balance, sodium, stroke and heart disease risk."
    }
]

def load_nutrition_qa():
    """Load from HuggingFace dataset, fall back to offline data if unavailable."""
    logger.info("Attempting to load 'yyupenn/NutritionQA' dataset from HuggingFace...")
    try:
        from datasets import load_dataset
        # We specify a small timeout to prevent hanging in restricted network environments
        dataset = load_dataset("yyupenn/NutritionQA", split="train", download_mode="reuse_dataset_if_exists")
        
        docs = []
        for i, item in enumerate(dataset):
            question = item.get("question", "").strip()
            answer = item.get("answer", "").strip()
            # Some datasets have 'context' or 'ocr' or similar
            context = item.get("context", "").strip() or item.get("ocr", "").strip()
            
            if question and answer:
                docs.append({
                    "question": question,
                    "answer": answer,
                    "context": context
                })
        
        if docs:
            logger.info(f"✅ Successfully loaded {len(docs)} records from HuggingFace.")
            return docs
        else:
            raise ValueError("No valid question-answer records found in loaded HF dataset.")
            
    except Exception as e:
        logger.warning(f"⚠️ Could not load HuggingFace dataset ({e}). Using high-quality offline fallback dataset.")
        return OFFLINE_DATA

def main():
    logger.info("🚀 Starting RAG Ingestion Pipeline...")
    
    # 1. Load Data
    records = load_nutrition_qa()
    
    # 2. Format Documents
    formatted_docs = []
    for r in records:
        q = r["question"]
        a = r["answer"]
        c = r.get("context", "")
        
        doc_text = f"Question: {q}\nAnswer: {a}"
        if c:
            doc_text += f"\nContext: {c}"
            
        formatted_docs.append({
            "text": doc_text,
            "metadata": {
                "question": q,
                "answer": a,
                "additional_context": c
            }
        })
        
    logger.info(f"Loaded {len(formatted_docs)} documents for vector indexing.")
    
    # 3. Generate Embeddings
    logger.info("🧠 Loading Sentence-Transformer model ('all-MiniLM-L6-v2')...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    texts = [doc["text"] for doc in formatted_docs]
    logger.info("Computing embeddings for documents (this may take a moment)...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    
    # 4. Store in FAISS
    dimension = embeddings.shape[1]
    logger.info(f"Initializing FAISS index with dimension {dimension}...")
    
    # Using simple IndexFlatL2 for L2 distance (or IndexFlatIP for Cosine similarity)
    # L2 is the standard index. We normalize vectors if we want cosine.
    # Let's normalize embeddings for Cosine search
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized_embeddings = embeddings / (norms + 1e-10)
    
    index = faiss.IndexFlatIP(dimension)  # Inner Product (Cosine distance on normalized vectors)
    index.add(normalized_embeddings)
    
    # 5. Save persistently
    os.makedirs(INDEX_DIR, exist_ok=True)
    
    logger.info(f"Saving FAISS index to: {INDEX_PATH}")
    faiss.write_index(index, INDEX_PATH)
    
    logger.info(f"Saving document metadata to: {METADATA_PATH}")
    with open(METADATA_PATH, "wb") as f:
        pickle.dump(formatted_docs, f)
        
    logger.info("✅ Data ingestion complete! Vector database is fully populated.")

if __name__ == "__main__":
    main()
