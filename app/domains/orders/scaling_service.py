from enum import Enum
from typing import List, Any
from pydantic import BaseModel

class CustomerGoal(str, Enum):
    MAINTENANCE = "MAINTENANCE"
    FAT_LOSS = "FAT_LOSS"
    MUSCLE_GAIN = "MUSCLE_GAIN"

class BowlType(str, Enum):
    BLEND = "BLEND"
    BLOCK = "BLOCK"

class MacroTag(str, Enum):
    PROTEIN = "PROTEIN"
    CARB = "CARB"
    FAT = "FAT"
    FIBER = "FIBER"
    ADD_ON = "ADD_ON"

class ScaledIngredient(BaseModel):
    id: Any
    name: str
    macro_tag: str
    original_weight: float
    new_weight: float
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    cost: float

class ScaledBowlResult(BaseModel):
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    new_raw_material_cost: float
    final_price: float
    ingredients: List[ScaledIngredient]

def map_section_to_tag(section_name: str) -> str:
    s = section_name.upper()
    if "ADD" in s: return MacroTag.ADD_ON.value
    if "PROTEIN" in s: return MacroTag.PROTEIN.value
    if "CARB" in s: return MacroTag.CARB.value
    if "FIBER" in s: return MacroTag.FIBER.value
    if "DRESSING" in s: return MacroTag.FAT.value
    return MacroTag.CARB.value # Default fallback

async def scale_bowl(bowl: Any, target_calories: float, customer_goal: str) -> ScaledBowlResult:
    if target_calories <= 0:
        raise ValueError("Target calories must be greater than zero.")
    if not bowl.ingredients:
        raise ValueError("Bowl has no ingredients to scale.")

    addon_calories = 0.0
    addon_cost = 0.0
    adjustable_ingredients = []
    working_ingredients = []

    for item in bowl.ingredients:
        ing = item.ingredient
        if not ing: continue
        
        # Calculate base values for this BowlIngredient in the bowl
        base_ratio = float(item.weight_g_or_ml / ing.total_weight) if ing.total_weight and ing.total_weight > 0 else 0
        
        b_cals = float(ing.total_calories) * base_ratio
        b_pro = float(ing.total_protein) * base_ratio
        b_carb = float(ing.total_carbs) * base_ratio
        b_fat = float(ing.total_fat) * base_ratio
        b_fib = float(ing.total_fiber) * base_ratio
        b_cost = float(ing.total_price) * base_ratio
        
        # Use BowlSection enum name
        section_name = item.section_name.name if hasattr(item.section_name, 'name') else str(item.section_name)
        tag = map_section_to_tag(section_name)

        obj = {
            "item_id": item.id,
            "name": ing.name,
            "tag": tag,
            "orig_weight": float(item.weight_g_or_ml),
            "new_weight": float(item.weight_g_or_ml),
            "cals": b_cals,
            "pro": b_pro,
            "carb": b_carb,
            "fat": b_fat,
            "fib": b_fib,
            "cost": b_cost
        }

        if tag == MacroTag.ADD_ON.value:
            addon_calories += b_cals
            addon_cost += b_cost
        else:
            adjustable_ingredients.append(obj)
            
        working_ingredients.append(obj)

    adjustable_target = max(0.0, target_calories - addon_calories)
    base_adjustable_calories = sum(i["cals"] for i in adjustable_ingredients)
    
    # Check if string matching or Enum matching
    b_type = bowl.bowl_type.name if hasattr(bowl.bowl_type, 'name') else str(bowl.bowl_type)
    is_blend = b_type == BowlType.BLEND.value or customer_goal.lower().replace("_", " ") == CustomerGoal.MAINTENANCE.value.lower().replace("_", " ")
    
    if is_blend:
        multiplier = adjustable_target / base_adjustable_calories if base_adjustable_calories > 0 else 1.0
        for w in working_ingredients:
            if w["tag"] != MacroTag.ADD_ON.value:
                w["new_weight"] = w["orig_weight"] * multiplier
    else:
        if customer_goal.lower().replace("_", " ") == CustomerGoal.FAT_LOSS.value.lower().replace("_", " "):
            carb_reduction_factor = 0.60 
            for w in working_ingredients:
                if w["tag"] == MacroTag.CARB.value:
                    w["new_weight"] = w["orig_weight"] * carb_reduction_factor
            
            current_adj_calories = 0.0
            for w in working_ingredients:
                if w["tag"] != MacroTag.ADD_ON.value:
                    ratio = w["new_weight"] / w["orig_weight"] if w["orig_weight"] > 0 else 0
                    current_adj_calories += w["cals"] * ratio
                    
            deficit = adjustable_target - current_adj_calories
            
            if deficit > 0:
                protein_items = [w for w in working_ingredients if w["tag"] == MacroTag.PROTEIN.value]
                
                if not protein_items:
                    # Fallback to blend scaling if no protein items
                    mult = adjustable_target / current_adj_calories if current_adj_calories > 0 else 1.0
                    for w in working_ingredients:
                        if w["tag"] != MacroTag.ADD_ON.value:
                            w["new_weight"] *= mult
                else:
                    # Distribute deficit calories across protein items
                    total_orig_protein_weight = sum(p["orig_weight"] for p in protein_items)
                    for p in protein_items:
                        share = (p["orig_weight"] / total_orig_protein_weight) if total_orig_protein_weight > 0 else (1.0 / len(protein_items))
                        calories_to_add = deficit * share
                        
                        # How many calories are in 1g of this ingredient?
                        cal_per_g = p["cals"] / p["orig_weight"] if p["orig_weight"] > 0 else 0
                        if cal_per_g > 0:
                            p["new_weight"] += (calories_to_add / cal_per_g)
            elif deficit < 0:
                mult = adjustable_target / current_adj_calories if current_adj_calories > 0 else 1.0
                for w in working_ingredients:
                    if w["tag"] != MacroTag.ADD_ON.value:
                        w["new_weight"] *= mult

        elif customer_goal.lower().replace("_", " ") == CustomerGoal.MUSCLE_GAIN.value.lower().replace("_", " "):
            fiber_reduction_factor = 0.80
            for w in working_ingredients:
                if w["tag"] == MacroTag.FIBER.value:
                    w["new_weight"] = w["orig_weight"] * fiber_reduction_factor
            
            current_adj_calories = 0.0
            for w in working_ingredients:
                if w["tag"] != MacroTag.ADD_ON.value:
                    ratio = w["new_weight"] / w["orig_weight"] if w["orig_weight"] > 0 else 0
                    current_adj_calories += w["cals"] * ratio
                    
            deficit = adjustable_target - current_adj_calories
            
            if deficit > 0:
                protein_items = [w for w in working_ingredients if w["tag"] == MacroTag.PROTEIN.value]
                carb_items = [w for w in working_ingredients if w["tag"] == MacroTag.CARB.value]
                
                if not protein_items or not carb_items:
                    # Fallback to blend scaling
                    mult = adjustable_target / current_adj_calories if current_adj_calories > 0 else 1.0
                    for w in working_ingredients:
                        if w["tag"] != MacroTag.ADD_ON.value:
                            w["new_weight"] *= mult
                else:
                    protein_deficit = deficit * 0.5
                    carb_deficit = deficit * 0.5
                    
                    total_orig_protein_weight = sum(p["orig_weight"] for p in protein_items)
                    for p in protein_items:
                        share = (p["orig_weight"] / total_orig_protein_weight) if total_orig_protein_weight > 0 else (1.0 / len(protein_items))
                        calories_to_add = protein_deficit * share
                        cal_per_g = p["cals"] / p["orig_weight"] if p["orig_weight"] > 0 else 0
                        if cal_per_g > 0:
                            p["new_weight"] += (calories_to_add / cal_per_g)
                            
                    total_orig_carb_weight = sum(c["orig_weight"] for c in carb_items)
                    for c in carb_items:
                        share = (c["orig_weight"] / total_orig_carb_weight) if total_orig_carb_weight > 0 else (1.0 / len(carb_items))
                        calories_to_add = carb_deficit * share
                        cal_per_g = c["cals"] / c["orig_weight"] if c["orig_weight"] > 0 else 0
                        if cal_per_g > 0:
                            c["new_weight"] += (calories_to_add / cal_per_g)
            elif deficit < 0:
                mult = adjustable_target / current_adj_calories if current_adj_calories > 0 else 1.0
                for w in working_ingredients:
                    if w["tag"] != MacroTag.ADD_ON.value:
                        w["new_weight"] *= mult

    final_calories = 0.0
    final_protein = 0.0
    final_carbs = 0.0
    final_fat = 0.0
    final_fiber = 0.0
    new_raw_material_cost = 0.0
    scaled_ingredients = []

    for w in working_ingredients:
        orig_w = w["orig_weight"]
        new_w = max(0.0, w["new_weight"])
        ratio = (new_w / orig_w) if orig_w > 0 else 0.0
        
        scaled_cals = w["cals"] * ratio
        scaled_protein = w["pro"] * ratio
        scaled_carbs = w["carb"] * ratio
        scaled_fat = w["fat"] * ratio
        scaled_fiber = w["fib"] * ratio
        scaled_cost = w["cost"] * ratio
        
        final_calories += scaled_cals
        final_protein += scaled_protein
        final_carbs += scaled_carbs
        final_fat += scaled_fat
        final_fiber += scaled_fiber
        new_raw_material_cost += scaled_cost
        
        scaled_ingredients.append(
            ScaledIngredient(
                id=w["item_id"],
                name=w["name"],
                macro_tag=w["tag"],
                original_weight=round(orig_w, 2),
                new_weight=round(new_w, 2),
                calories=round(scaled_cals, 2),
                protein=round(scaled_protein, 2),
                carbs=round(scaled_carbs, 2),
                fat=round(scaled_fat, 2),
                fiber=round(scaled_fiber, 2),
                cost=round(scaled_cost, 2)
            )
        )
        
    packaging_cost = float(getattr(bowl, "packaging_cost", 0.0) or getattr(bowl, "fixed_cost", 0.0) or 0.0)
    final_price = new_raw_material_cost + packaging_cost

    return ScaledBowlResult(
        total_calories=round(final_calories, 2),
        total_protein=round(final_protein, 2),
        total_carbs=round(final_carbs, 2),
        total_fat=round(final_fat, 2),
        total_fiber=round(final_fiber, 2),
        new_raw_material_cost=round(new_raw_material_cost, 2),
        final_price=round(final_price, 2),
        ingredients=scaled_ingredients
    )

