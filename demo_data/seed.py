import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db import init_db, save_trader, save_transaction, get_trader_by_phone
from datetime import datetime, timedelta

def get_last_monday():
    today = datetime.now()
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday + 7)
    return last_monday

def seed():
    print("🌱 Seeding OjaMoni demo data...\n")

    init_db()

    save_trader("Amaka", "+2348012345678", "Food Trader")
    trader = get_trader_by_phone("+2348012345678")
    trader_id = trader["id"]
    print(f"✅ Trader created: Amaka (ID: {trader_id})\n")

    monday = get_last_monday()

    days = [
        {
            "label": "Monday",
            "date": monday,
            "revenue": 32000,
            "expenses": 18000,
            "raw_input": "Sold tomato 3 baskets, pepper, onion, crayfish. Bought new stock.",
            "ai_insight": "Good start to the week! Your tomato sales are driving revenue. Watch your restocking cost."
        },
        {
            "label": "Tuesday",
            "date": monday + timedelta(days=1),
            "revenue": 28500,
            "expenses": 17500,
            "raw_input": "Sold pepper 2 bags, tomato, palm oil. Transport and nylon expenses.",
            "ai_insight": "Solid Tuesday. Palm oil is becoming a good earner for you this week."
        },
        {
            "label": "Wednesday",
            "date": monday + timedelta(days=2),
            "revenue": 15000,
            "expenses": 19500,
            "raw_input": "Slow day. Rain scatter customers. Tomato spoil small. Still pay transport.",
            "ai_insight": "Tough day Amaka. Rain and spoilage hit you hard. Consider buying smaller tomato quantities on rainy days."
        },
        {
            "label": "Thursday",
            "date": monday + timedelta(days=3),
            "revenue": 34000,
            "expenses": 20000,
            "raw_input": "Market was full today. Sold everything. Tomato supplier increase price small.",
            "ai_insight": "Big bounce back! But notice your tomato cost is creeping up. Your supplier may be increasing prices."
        },
        {
            "label": "Friday",
            "date": monday + timedelta(days=4),
            "revenue": 41000,
            "expenses": 22000,
            "raw_input": "Friday rush. Sold tomato, pepper, onion bulk. Many customers. Expenses high too.",
            "ai_insight": "Your best revenue day! But tomato cost is now 32% of expenses. Time to negotiate with your supplier."
        },
        {
            "label": "Saturday",
            "date": monday + timedelta(days=5),
            "revenue": 38000,
            "expenses": 21000,
            "raw_input": "Good Saturday. Sold plenty. Tomato cost keep rising. Bought extra nylon and bags.",
            "ai_insight": "Strong finish. Your tomato supplier has raised prices 95% since Monday. This needs urgent attention."
        },
    ]

    print("📅 Inserting transactions:\n")

    for day in days:
        profit = day["revenue"] - day["expenses"]
        date_str = day["date"].strftime("%Y-%m-%d")

        save_transaction(
            trader_id=trader_id,
            date=date_str,
            revenue=day["revenue"],
            expenses=day["expenses"],
            profit=profit,
            raw_input=day["raw_input"],
            ai_insight=day["ai_insight"]
        )

        profit_emoji = "📈" if profit > 0 else "📉"
        print(f"  {profit_emoji} {day['label']} ({date_str})")
        print(f"     Revenue:  ₦{day['revenue']:,}")
        print(f"     Expenses: ₦{day['expenses']:,}")
        print(f"     Profit:   ₦{profit:,}")
        print()

    total_revenue = sum(d["revenue"] for d in days)
    total_expenses = sum(d["expenses"] for d in days)
    total_profit = total_revenue - total_expenses

    print("=" * 45)
    print("✅ SEED COMPLETE\n")
    print(f"  Trader:         Amaka")
    print(f"  Days seeded:    6")
    print(f"  Total Revenue:  ₦{total_revenue:,}")
    print(f"  Total Expenses: ₦{total_expenses:,}")
    print(f"  Total Profit:   ₦{total_profit:,}")
    print(f"  Tomato trend:   ₦4,000 → ₦7,800 (+95%)")
    print("=" * 45)

if __name__ == "__main__":
    seed()