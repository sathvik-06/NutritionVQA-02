"""Download HF datasets for offline training (optional)."""
import os

def main():
    from datasets import load_dataset
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "hf_datasets"))
    os.makedirs(root, exist_ok=True)
    load_dataset("yyupenn/NutritionQA").save_to_disk(os.path.join(root, "NutritionQA"))
    load_dataset("openfoodfacts/nutrition-table-detection").save_to_disk(
        os.path.join(root, "nutrition-table-detection")
    )
    print("Datasets saved under", root)

if __name__ == "__main__":
    main()
