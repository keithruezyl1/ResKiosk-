"""
Inventory query handler: phrase triggers map to shelter_config.inventory items.
No embedding; returns pre-formatted answer_text for DIRECT_MATCH with article_data=None.
"""
from hub.retrieval.normalizer import normalize_query

INVENTORY_TRIGGERS = {
    "is there food": "food",
    "is food available": "food",
    "is there water": "water",
    "is water available": "water",
    "are there blankets": "blankets",
    "is there medicine": "medicine",
    "is medicine available": "medicine",
    "are there hygiene kits": "hygiene_kits",
    "is there clothing": "clothing",
    "are there diapers": "diapers",
    "are there charging ports": "charging",
    "is there a charging station": "charging",
    "are there cots": "cots",
    "what supplies are available": "all",
    "supply status": "all",
    "what do you have": "all",
    "inventory": "all",
    "may pagkain": "food",
    "may tubig": "water",
    "may kumot": "blankets",
    "may gamot": "medicine",
    "may damit": "clothing",
    "may lampin": "diapers",
    "may singsing": "charging",
    "ano ang mayroon dito": "all",
    "hay comida": "food",
    "hay agua": "water",
    "hay mantas": "blankets",
    "hay medicamentos": "medicine",
    "hay medicinas": "medicine",
    "que tienen aqui": "all",
    "shokuhin wa arimasu ka": "food",
    "mizu wa arimasu ka": "water",
    "mofu wa arimasu ka": "blankets",
    "eumsik isseoyo": "food",
    "mul isseoyo": "water",
    "ibol isseoyo": "blankets",
}

ITEM_NAMES_EN = {
    "water": "Drinking water",
    "food": "Food",
    "blankets": "Blankets",
    "medicine": "Medicine",
    "hygiene_kits": "Hygiene kits",
    "clothing": "Clothing",
    "diapers": "Diapers",
    "charging": "Charging stations",
    "cots": "Cots",
}

STATUS_PHRASES = {
    "available": "is available",
    "limited": "is available but supply is limited",
    "unavailable": "is currently not available",
    "unknown": "— current availability is unknown",
}


def check_inventory(normalized_query: str, shelter_config: dict) -> str | None:
    inventory = shelter_config.get("inventory", {})
    items = inventory.get("items", {})
    if not items:
        return None

    matched_key = None
    for phrase, item_key in INVENTORY_TRIGGERS.items():
        if phrase in normalized_query:
            matched_key = item_key
            break

    if not matched_key:
        return None

    if matched_key == "all":
        return _format_all(items)
    return _format_item(matched_key, items.get(matched_key))


def _format_item(key: str, item: dict | None) -> str:
    if not item:
        return f"There is no information available for {key.replace('_', ' ')}."
    name = ITEM_NAMES_EN.get(key, key.replace("_", " ").title())
    status = item.get("status", "unknown")
    quantity = item.get("quantity", "")
    location = item.get("location", "")
    notes = item.get("notes", "")
    phrase = STATUS_PHRASES.get(status, "— status unknown")
    parts = [f"{name} {phrase}."]
    if quantity:
        parts.append(f"Quantity: {quantity}.")
    if location:
        parts.append(f"Location: {location}.")
    if notes:
        parts.append(notes + ("." if not notes.endswith(".") else ""))
    return " ".join(parts)


def _format_all(items: dict) -> str:
    lines = ["Here is the current supply status at this evacuation center."]
    for key, item in items.items():
        name = ITEM_NAMES_EN.get(key, key.replace("_", " ").title())
        status = item.get("status", "unknown")
        qty = item.get("quantity", "")
        word = {
            "available": "available",
            "limited": "limited (low stock)",
            "unavailable": "not available",
            "unknown": "unknown",
        }.get(status, "unknown")
        line = f"{name}: {word}"
        if qty:
            line += f" ({qty})"
        lines.append(line + ".")
    return " ".join(lines)
