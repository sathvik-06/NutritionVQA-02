import os

path = r'backend\llm\mistral_client.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """            STRICT RULES:
            1. Use EXACTLY these keys: "calories", "fat", "saturated_fat", "trans_fat", "cholesterol", "sodium", "carbohydrates", "fiber", "sugar", "added_sugar", "protein", "serving_size", "is_nutrition_label".
            2. FOR "sugar": Extract 'Total Sugars'.
            3. FOR "carbohydrates": Extract 'Total Carbohydrate'.
            4. FOR "fat": Extract 'Total Fat'.
            5. Include units (g, mg) for everything except calories.
            6. If a value is on the line BELOW the nutrient name, capture it.
            7. Set "is_nutrition_label": true if this is a food label.
            8. DO NOT extract footnote numbers or references, such as the '(1)' in '% Daily Value (1)'.
            9. NEVER hallucinate or guess values based on brand names. If a value is not explicitly in the OCR text, return "N/A"."""

new_block = """            METICULOUS SEARCH RULES:
            1. Search the entire text carefully. Values and names might be separated by many lines or large spaces due to the curved surface.
            2. Use EXACTLY these keys: "calories", "fat", "saturated_fat", "trans_fat", "cholesterol", "sodium", "carbohydrates", "fiber", "sugar", "added_sugar", "protein", "serving_size", "is_nutrition_label".
            3. Include units (g, mg) for everything except calories.
            4. Set "is_nutrition_label": true if any nutrition keywords are present.
            5. DO NOT extract footnote numbers like '(1)'. Focus on the primary table values.
            6. NEVER hallucinate or guess. If the value is absolutely missing, return "N/A"."""

# Try to find the block regardless of line endings
content = content.replace(old_block.replace('\n', '\r\n'), new_block)
content = content.replace(old_block, new_block)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
