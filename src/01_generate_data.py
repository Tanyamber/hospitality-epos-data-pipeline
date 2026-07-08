"""
Hospitality Sales Data Generator
Generates 50,000 synthetic EPOS transaction records across multiple venue types.
Mirrors the kind of data an EPOS provider like Tevalis would process.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

random.seed(42)
np.random.seed(42)

# ── Venue definitions ─────────────────────────────────────────────────────────

VENUES = [
    {"id": "V001", "name": "The Crown & Anchor",     "type": "Pub",        "city": "Hull",       "region": "Yorkshire"},
    {"id": "V002", "name": "Bella Napoli",            "type": "Restaurant", "city": "Leeds",      "region": "Yorkshire"},
    {"id": "V003", "name": "The Grand Hotel",         "type": "Hotel",      "city": "York",       "region": "Yorkshire"},
    {"id": "V004", "name": "Riverside Grill",         "type": "Restaurant", "city": "Hull",       "region": "Yorkshire"},
    {"id": "V005", "name": "The Hop & Barley",        "type": "Pub",        "city": "Sheffield",  "region": "Yorkshire"},
    {"id": "V006", "name": "Sakura Japanese Kitchen", "type": "Restaurant", "city": "Manchester", "region": "Northwest"},
    {"id": "V007", "name": "The Merchant Hotel",      "type": "Hotel",      "city": "Liverpool",  "region": "Northwest"},
    {"id": "V008", "name": "Spice Garden",            "type": "Restaurant", "city": "Bradford",   "region": "Yorkshire"},
    {"id": "V009", "name": "The Tap Room",            "type": "Pub",        "city": "Wakefield",  "region": "Yorkshire"},
    {"id": "V010", "name": "Marina Brasserie",        "type": "Restaurant", "city": "Hull",       "region": "Yorkshire"},
]

# ── Menu items by venue type ──────────────────────────────────────────────────

MENU = {
    "Pub": [
        ("Pint of Lager",        "Drinks",     4.80),
        ("Pint of Ale",          "Drinks",     5.20),
        ("Glass of Wine",        "Drinks",     6.50),
        ("Soft Drink",           "Drinks",     3.20),
        ("Fish & Chips",         "Mains",     13.50),
        ("Beef Burger",          "Mains",     14.00),
        ("Pie of the Day",       "Mains",     12.50),
        ("Ploughman's Lunch",    "Mains",     11.00),
        ("Garlic Bread",         "Starters",   5.50),
        ("Soup of the Day",      "Starters",   6.00),
        ("Sticky Toffee Pudding","Desserts",   7.00),
        ("Cheese & Biscuits",    "Desserts",   8.00),
        ("Crisps",               "Snacks",     1.50),
        ("Mixed Nuts",           "Snacks",     2.00),
    ],
    "Restaurant": [
        ("Sparkling Water",      "Drinks",     3.50),
        ("House Red Wine",       "Drinks",     7.50),
        ("House White Wine",     "Drinks",     7.50),
        ("Craft Beer",           "Drinks",     6.00),
        ("Bruschetta",           "Starters",   8.50),
        ("Prawn Cocktail",       "Starters",   9.50),
        ("Caesar Salad",         "Starters",   9.00),
        ("Ribeye Steak",         "Mains",     28.00),
        ("Salmon Fillet",        "Mains",     22.00),
        ("Mushroom Risotto",     "Mains",     17.00),
        ("Pasta Carbonara",      "Mains",     16.50),
        ("Margherita Pizza",     "Mains",     14.00),
        ("Tiramisu",             "Desserts",   8.50),
        ("Panna Cotta",          "Desserts",   8.00),
        ("Gelato",               "Desserts",   7.00),
    ],
    "Hotel": [
        ("Room Service Breakfast","Food",      22.00),
        ("Full English",         "Food",       16.00),
        ("Club Sandwich",        "Food",       18.00),
        ("Caesar Salad",         "Food",       15.00),
        ("Afternoon Tea",        "Food",       35.00),
        ("Mini Bar Beer",        "Drinks",      6.50),
        ("Mini Bar Wine",        "Drinks",      9.00),
        ("Cocktail",             "Drinks",     12.00),
        ("Coffee",               "Drinks",      4.50),
        ("Spa Treatment",        "Spa",        65.00),
        ("Gym Day Pass",         "Leisure",    15.00),
        ("Laundry Service",      "Services",   12.00),
        ("Late Checkout",        "Services",   30.00),
    ],
}

PAYMENT_METHODS = ["Card", "Card", "Card", "Cash", "Contactless", "Contactless", "App"]

# ── Transaction generator ─────────────────────────────────────────────────────

def random_datetime(start_date, end_date, venue_type):
    """Generate a realistic transaction time based on venue type."""
    delta = end_date - start_date
    random_day = start_date + timedelta(days=random.randint(0, delta.days))

    if venue_type == "Hotel":
        hour = random.choices(
            range(7, 23),
            weights=[8,6,4,3,3,4,6,8,10,10,8,6,5,4,4,5], k=1)[0]
    elif venue_type == "Pub":
        hour = random.choices(
            range(11, 24),
            weights=[2,2,3,4,5,6,8,10,10,10,8,6,4], k=1)[0]
    else:  # Restaurant
        hour = random.choices(
            range(11, 23),
            weights=[3,4,8,10,5,3,3,5,8,10,4,2], k=1)[0]

    minute  = random.randint(0, 59)
    second  = random.randint(0, 59)
    return random_day.replace(hour=hour, minute=minute, second=second)


def generate_transactions(n=50000):
    start_date = datetime(2024, 1, 1)
    end_date   = datetime(2024, 12, 31)
    rows = []

    for i in range(1, n + 1):
        venue        = random.choice(VENUES)
        menu_items   = MENU[venue["type"]]
        item         = random.choice(menu_items)
        item_name, category, unit_price = item
        quantity     = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]

        # Weekend uplift
        ts           = random_datetime(start_date, end_date, venue["type"])
        price_mult   = 1.15 if ts.weekday() >= 4 else 1.0
        unit_price   = round(unit_price * price_mult, 2)
        total_amount = round(unit_price * quantity, 2)

        # Occasional discount
        discount_pct = random.choices([0, 5, 10, 15], weights=[75, 12, 8, 5])[0]
        discount_amt = round(total_amount * discount_pct / 100, 2)
        final_amount = round(total_amount - discount_amt, 2)

        rows.append({
            "transaction_id":   f"TXN{i:06d}",
            "venue_id":         venue["id"],
            "venue_name":       venue["name"],
            "venue_type":       venue["type"],
            "city":             venue["city"],
            "region":           venue["region"],
            "transaction_date": ts.date(),
            "transaction_time": ts.time(),
            "transaction_ts":   ts,
            "item_name":        item_name,
            "category":         category,
            "quantity":         quantity,
            "unit_price":       unit_price,
            "gross_amount":     total_amount,
            "discount_pct":     discount_pct,
            "discount_amount":  discount_amt,
            "net_amount":       final_amount,
            "payment_method":   random.choice(PAYMENT_METHODS),
            "is_weekend":       ts.weekday() >= 5,
            "day_of_week":      ts.strftime("%A"),
            "month":            ts.strftime("%B"),
            "month_num":        ts.month,
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("Generating 50,000 hospitality transaction records...")
    df = generate_transactions(50000)

    os.makedirs("data", exist_ok=True)
    df.to_csv("data/hospitality_transactions.csv", index=False)

    print(f"Done. Shape: {df.shape}")
    print(f"\nVenue breakdown:\n{df['venue_name'].value_counts()}")
    print(f"\nCategory breakdown:\n{df['category'].value_counts()}")
    print(f"\nTotal revenue: £{df['net_amount'].sum():,.2f}")
    print("\nSample rows:")
    print(df.head(3).to_string())
