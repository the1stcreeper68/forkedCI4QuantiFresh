import json
import os
import time
from datetime import date, timedelta
from dotenv import load_dotenv
from modules.ai.AI_manager import AIManager
from modules.ai.OpenRouterProvider import OpenRouterProvider
from modules.core.Cart import Cart
from modules.core.CartItem import CartItem
from modules.core.ConsumptionHistory import ConsumptionHistory
from modules.core.ConsumptionRecord import ConsumptionRecord
from modules.core.Fridge import Fridge
from modules.core.FridgeItem import FridgeItem
from modules.core.Household import Household
from modules.core.Person import Person

# REAL API CONNECTION TEST (not a mock provider).
# Replace the sample values below to test different household situations.
DAYS_UNTIL_NEXT_PURCHASE = 7
REMARKS = "We will eat at home most days this week. Avoid excess perishables."

HOUSEHOLD_DATA = [
    {"Person_ID": 1, "Name": "Zi", "Age": 23, "Gender": "Male", "Dietary_Restriction": "muslim"},
    {"Person_ID": 2, "Name": "Alice", "Age": 40, "Gender": "Female", "Dietary_Restriction": "muslim"},
    {"Person_ID": 3, "Name": "Bob", "Age": 18, "Gender": "Male", "Dietary_Restriction": "muslim"},
    {"Person_ID": 4, "Name": "Charlie", "Age": 18, "Gender": "Male", "Dietary_Restriction": "Halal"},
]

# Two realistic 7-day consumption periods for a three-person household.
HISTORY_DATA = [
    {"Item_Name": "milk", "Quantity": 1.5, "Unit": "l", "Date_Range": 7, "Remarks": "none"},
    {"Item_Name": "eggs", "Quantity": 8, "Unit": "pcs", "Date_Range": 7, "Remarks": "none"},
    {"Item_Name": "rice", "Quantity": 1.0, "Unit": "kg", "Date_Range": 7, "Remarks": "none"},
    {"Item_Name": "bananas", "Quantity": 6, "Unit": "pcs", "Date_Range": 7, "Remarks": "none"},
    {"Item_Name": "milk", "Quantity": 1.8, "Unit": "l", "Date_Range": 7, "Remarks": "none"},
    {"Item_Name": "eggs", "Quantity": 10, "Unit": "pcs", "Date_Range": 7, "Remarks": "none"},
    {"Item_Name": "rice", "Quantity": 1.2, "Unit": "kg", "Date_Range": 7, "Remarks": "none"},
    {"Item_Name": "bananas", "Quantity": 5, "Unit": "pcs", "Date_Range": 7, "Remarks": "none"},
]

# Expiry dates are relative to today so the sample stays valid over time.
# One expired batch intentionally checks the AI Manager's exclusion warning.
FRIDGE_DATA = [
    {"Item_Name": "milk", "Quantity": 1.0, "Unit": "l", "Purchased_Days_Ago": 2, "Expires_In_Days": 3, "Remarks": "opened"},
    {"Item_Name": "eggs", "Quantity": 6, "Unit": "pcs", "Purchased_Days_Ago": 3, "Expires_In_Days": 14, "Remarks": "none"},
    {"Item_Name": "rice", "Quantity": 1.5, "Unit": "kg", "Purchased_Days_Ago": 5, "Expires_In_Days": 180, "Remarks": "none"},
    {"Item_Name": "bananas", "Quantity": 3, "Unit": "pcs", "Purchased_Days_Ago": 2, "Expires_In_Days": 3, "Remarks": "none"},
    {"Item_Name": "yogurt", "Quantity": 1, "Unit": "pcs", "Purchased_Days_Ago": 10, "Expires_In_Days": -1, "Remarks": "expired sample"},
]

GROCERY_DATA = [
    {"Item_Name": "milk", "Quantity": 3.0, "Unit": "l"},
    {"Item_Name": "eggs", "Quantity": 12, "Unit": "pcs"},
    {"Item_Name": "rice", "Quantity": 2.0, "Unit": "kg"},
    {"Item_Name": "bread", "Quantity": 2, "Unit": "pcs"},
    {"Item_Name": "bananas", "Quantity": 10, "Unit": "pcs"},
    {"Item_Name": "yogurt", "Quantity": 4, "Unit": "pcs"},
    {"Item_Name": "pork", "Quantity": 2.0, "Unit": "kg"},
    {"Item_Name": "alcohol", "Quantity": 2.0, "Unit": "l"},
]

def make_inputs():
    household = Household()
    for row in HOUSEHOLD_DATA:
        household.add_member(Person.from_dict(row))

    history = ConsumptionHistory()
    for row in HISTORY_DATA:
        history.add_record(ConsumptionRecord.from_dict(row))

    fridge = Fridge()
    today = date.today()
    for row in FRIDGE_DATA:
        fridge.add_item(FridgeItem(
            row["Item_Name"], row["Quantity"], row["Unit"],
            (today - timedelta(days=row["Purchased_Days_Ago"])).isoformat(),
            (today + timedelta(days=row["Expires_In_Days"])).isoformat(),
            row["Remarks"],
        ))

    cart = Cart()
    for row in GROCERY_DATA:
        cart.add_item(CartItem.from_dict(row))
    return household, history, fridge, cart


def main():
    load_dotenv()
    required = ("API_KEY", "API_URL", "API_CONN_URL", "AI_MODEL", "AI_BACKUP_MODEL")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print("Missing .env settings: " + ", ".join(missing))
        return 1

    household, history, fridge, cart = make_inputs()
    print("=== AI Manager REAL API CONNECTION Test ===", flush=True)
    print(f"Household members: {len(household.get_members())}")
    print(f"Consumption records: {len(history.to_dicts())}")
    print(f"Fridge batches: {len(fridge.get_items())}")
    print(f"Planned groceries: {len(cart.get_items())}")
    print("Planned grocery list:")
    print(json.dumps([item.to_dict() for item in cart.get_items()], indent=2))

    manager = AIManager(OpenRouterProvider())
    start = time.perf_counter()
    try:
        result, error = manager.get_ai_recommendations(
            household_info=household,
            consumption_history=history,
            fridge_stock=fridge,
            purchase_stock=cart,
            remarks=REMARKS,
            days_until_next=DAYS_UNTIL_NEXT_PURCHASE,
            notify=lambda message: print(message, flush=True),
        )
    except Exception as exc:
        print(f"AI Manager raised {type(exc).__name__}: {exc}")
        return 1
    finally:
        print(f"Elapsed time: {time.perf_counter() - start:.2f}s", flush=True)

    if error or result is None:
        print(f"REAL API TEST FAILED: {error or 'No response'}")
        return 1

    print("\nValidated AI response:")
    print(json.dumps(result, indent=2, default=str))
    recommendations = result["Recommendations_List"]
    if len(recommendations) != len(cart.get_items()):
        print("FAILED: recommendation count does not match cart")
        return 1
    for item, rec in zip(cart.get_items(), recommendations):
        if (item.name, item.quantity, item.unit) != (
            rec["Item_Name"], rec["Planned_Quantity"], rec["Unit"]
        ):
            print(f"FAILED: grocery identity/order mismatch for {item.name}")
            return 1
        if not item.is_enhanced():
            print(f"FAILED: AI recommendation not attached to {item.name}")
            return 1

    print("\nPASSED: Live API response validated; item order and AI attachments verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
