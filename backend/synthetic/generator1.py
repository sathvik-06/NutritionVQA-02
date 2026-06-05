"""
Generates synthetic nutrition labels, QA pairs, and reasoning chains.
"""

import json
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

NUTRIENTS = {
    "calories": (80, 600, "kcal"),
    "total_fat": (0, 40, "g"),
    "saturated_fat": (0, 15, "g"),
    "trans_fat": (0, 3, "g"),
    "cholesterol": (0, 120, "mg"),
    "sodium": (0, 1200, "mg"),
    "total_carbohydrate": (5, 80, "g"),
    "dietary_fiber": (0, 15, "g"),
    "total_sugars": (0, 40, "g"),
    "protein": (0, 35, "g"),
    "vitamin_d": (0, 10, "mcg"),
    "calcium": (0, 400, "mg"),
    "iron": (0, 18, "mg"),
    "potassium": (0, 800, "mg"),
}

FOOD_TYPES = [
    "Cereal", "Yogurt", "Granola Bar", "Soup", "Crackers", "Juice",
    "Bread", "Pasta Sauce", "Frozen Dinner", "Chips", "Cookies",
    "Protein Bar", "Milk", "Cheese", "Ice Cream", "Oatmeal",
    "Trail Mix", "Peanut Butter", "Salad Dressing", "Canned Beans",
]

SERVING_SIZES = [
    "1 cup (240ml)", "2/3 cup (55g)", "1 bar (40g)", "1 slice (34g)",
    "2 tbsp (32g)", "1 bowl (300g)", "1 can (245g)", "1 packet (28g)",
    "3/4 cup (30g)", "1 container (150g)", "1 pouch (90g)",
]

QA_TEMPLATES = [
    {
        "type": "descriptive",
        "question": "How many calories are in a serving of {food}?",
        "answer": "A serving of {food} contains {calories} calories.",
        "reasoning": "Looking at the nutrition label, the Calories row shows {calories} per serving size of {serving_size}.",
        "field": "calories",
    },
    {
        "type": "descriptive",
        "question": "What is the total fat content in {food}?",
        "answer": "The total fat content is {total_fat}.",
        "reasoning": "The Total Fat line on the label indicates {total_fat} per serving.",
        "field": "total_fat",
    },
    {
        "type": "descriptive",
        "question": "How much protein does {food} contain?",
        "answer": "{food} contains {protein} of protein per serving.",
        "reasoning": "According to the nutrition facts, the Protein value listed is {protein}.",
        "field": "protein",
    },
    {
        "type": "descriptive",
        "question": "What is the sodium content in {food}?",
        "answer": "The sodium content is {sodium} per serving.",
        "reasoning": "The Sodium row on the nutrition label shows {sodium}.",
        "field": "sodium",
    },
    {
        "type": "reasoning",
        "question": "Is {food} a good source of fiber?",
        "answer": "{fiber_answer}",
        "reasoning": "The dietary fiber content is {dietary_fiber}. A food is considered a good source of fiber if it provides 3g or more per serving. Since {dietary_fiber} is {fiber_comparison} 3g, {food} {fiber_verdict} a good source of fiber.",
        "field": "dietary_fiber",
    },
    {
        "type": "reasoning",
        "question": "Is {food} high in sodium?",
        "answer": "{sodium_answer}",
        "reasoning": "The sodium content is {sodium}. Foods with more than 600mg sodium per serving are considered high in sodium. {sodium_val}mg is {sodium_comparison} 600mg, so {food} {sodium_verdict} high in sodium.",
        "field": "sodium",
    },
    {
        "type": "reasoning",
        "question": "What percentage of calories in {food} come from fat?",
        "answer": "About {fat_pct}% of calories come from fat.",
        "reasoning": "Total calories: {calories}. Total fat: {fat_g}g. Each gram of fat = 9 calories. Fat calories = {fat_g} x 9 = {fat_cal}. Percentage = ({fat_cal}/{calories}) x 100 = {fat_pct}%.",
        "field": "fat_percentage",
    },
]


class SyntheticGenerator:
    """Generates synthetic nutrition data with QA pairs."""

    def __init__(self, seed: int = 42):
        random.seed(seed)

    def generate_label(self) -> dict:
        food = random.choice(FOOD_TYPES)
        serving = random.choice(SERVING_SIZES)
        label = {"food_name": food, "serving_size": serving}

        for nutrient, (lo, hi, unit) in NUTRIENTS.items():
            val = round(random.uniform(lo, hi), 1)
            if unit in ("g", "mg", "mcg"):
                label[nutrient] = f"{val}{unit}"
            else:
                label[nutrient] = str(int(val))

        # Ensure saturated + trans <= total fat
        tf = float(label["total_fat"].replace("g", ""))
        sf = min(float(label["saturated_fat"].replace("g", "")), tf * 0.6)
        trf = min(float(label["trans_fat"].replace("g", "")), tf - sf)
        label["saturated_fat"] = f"{round(sf,1)}g"
        label["trans_fat"] = f"{round(trf,1)}g"

        # Ensure sugars + fiber <= carbs
        tc = float(label["total_carbohydrate"].replace("g", ""))
        sug = min(float(label["total_sugars"].replace("g", "")), tc * 0.7)
        fib = min(float(label["dietary_fiber"].replace("g", "")), tc - sug)
        label["total_sugars"] = f"{round(sug,1)}g"
        label["dietary_fiber"] = f"{round(fib,1)}g"

        return label

    def generate_qa_pair(self, label: dict) -> dict:
        tmpl = random.choice(QA_TEMPLATES)
        food = label["food_name"]

        if tmpl["type"] == "descriptive":
            val = label.get(tmpl["field"], "N/A")
            q = tmpl["question"].format(food=food)
            a = tmpl["answer"].format(food=food, **{tmpl["field"]: val})
            r = tmpl["reasoning"].format(
                food=food, serving_size=label["serving_size"],
                **{tmpl["field"]: val}
            )
        elif tmpl["field"] == "dietary_fiber":
            fib = float(label["dietary_fiber"].replace("g", ""))
            q = tmpl["question"].format(food=food)
            a_text = f"Yes, with {label['dietary_fiber']} of fiber." if fib >= 3 else f"No, it only has {label['dietary_fiber']} of fiber."
            r = tmpl["reasoning"].format(
                food=food, dietary_fiber=label["dietary_fiber"],
                fiber_comparison="≥" if fib >= 3 else "<",
                fiber_verdict="is" if fib >= 3 else "is not",
                fiber_answer=a_text
            )
            a = a_text
        elif tmpl["field"] == "sodium":
            sod = float(label["sodium"].replace("mg", ""))
            q = tmpl["question"].format(food=food)
            a_text = f"Yes, with {label['sodium']}." if sod > 600 else f"No, it has {label['sodium']}."
            r = tmpl["reasoning"].format(
                food=food, sodium=label["sodium"], sodium_val=sod,
                sodium_comparison=">" if sod > 600 else "≤",
                sodium_verdict="is" if sod > 600 else "is not",
                sodium_answer=a_text
            )
            a = a_text
        else:  # fat_percentage
            cal = int(label["calories"])
            fat_g = float(label["total_fat"].replace("g", ""))
            fat_cal = round(fat_g * 9, 1)
            pct = round((fat_cal / max(cal, 1)) * 100, 1)
            q = tmpl["question"].format(food=food)
            a = f"About {pct}% of calories come from fat."
            r = tmpl["reasoning"].format(
                food=food, calories=cal, fat_g=fat_g,
                fat_cal=fat_cal, fat_pct=pct
            )

        label_text = self._label_to_text(label)
        return {
            "question": q, "answer": a, "reasoning": r,
            "context": label_text, "food_name": food,
            "label_data": label,
        }

    def _label_to_text(self, label: dict) -> str:
        lines = [
            f"Nutrition Facts - {label['food_name']}",
            f"Serving Size: {label['serving_size']}",
            f"Calories: {label['calories']}",
        ]
        skip = {"food_name", "serving_size", "calories"}
        for k, v in label.items():
            if k not in skip:
                name = k.replace("_", " ").title()
                lines.append(f"{name}: {v}")
        return "\n".join(lines)

    def generate_dataset(self, n: int = 100) -> list[dict]:
        logger.info(f"Generating {n} synthetic QA pairs...")
        dataset = []
        for _ in range(n):
            label = self.generate_label()
            qa = self.generate_qa_pair(label)
            dataset.append(qa)
        logger.info(f"Generated {len(dataset)} QA pairs.")
        return dataset

    def save_dataset(self, dataset: list, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        logger.info(f"Dataset saved to {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gen = SyntheticGenerator()
    data = gen.generate_dataset(200)
    out = Path(__file__).parent.parent.parent / "faiss_index" / "synthetic_data.json"
    gen.save_dataset(data, str(out))
    print(f"\nSample entry:\n{json.dumps(data[0], indent=2)}")