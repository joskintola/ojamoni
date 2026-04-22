"""
proactive.py — OjaMoni Proactive Nudge Agent

Runs a daily background check. If a trader hasn't recorded
any transaction in 3+ days, Claude generates a personalised
nudge referencing their last profit and trend, and saves it
to the messages_log table.
"""

import anthropic
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from database.db import (
    get_all_traders,
    get_last_transaction_date,
    get_recent_transactions,
    log_message,
)

client = anthropic.Anthropic()


def generate_nudge(trader_name: str, business_type: str, last_profit: float, days_silent: int, trend: str) -> str:
    """
    Ask Claude to write a warm, personalised WhatsApp nudge
    for a trader who hasn't recorded in a while.
    """
    first_name = trader_name.split()[0]

    prompt = f"""You are OjaMoni, a friendly AI financial assistant for Nigerian informal traders.

A trader named {first_name} ({business_type} seller) has not recorded their sales in {days_silent} days.
Their last recorded profit was ₦{last_profit:,.0f}.
Their recent profit trend is: {trend}.

Write a short, warm WhatsApp nudge message (3-5 lines max) to encourage them to record today's sales.
- Use friendly Nigerian English and sprinkle in Pidgin naturally
- Reference their last profit to make it feel personal
- Be encouraging, not nagging
- End with a simple call to action
- Use 1-2 emojis max, keep it natural not spammy
- Do NOT use markdown formatting like ** or ##
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()


def calculate_trend(transactions: list) -> tuple[float, str]:
    """
    Given a list of recent transaction dicts, return:
    - last_profit: the most recent profit value
    - trend: a short human-readable trend description
    """
    if not transactions:
        return 0.0, "no recent data"

    profits = [t["profit"] for t in transactions]
    last_profit = profits[0]  # most recent first

    if len(profits) == 1:
        return last_profit, "only one day recorded"

    # Compare first half vs second half average
    mid = len(profits) // 2
    recent_avg = sum(profits[:mid]) / mid if mid else profits[0]
    older_avg = sum(profits[mid:]) / (len(profits) - mid)

    if recent_avg > older_avg * 1.1:
        trend = "improving — recent days are stronger"
    elif recent_avg < older_avg * 0.9:
        trend = "declining — recent days are weaker than before"
    else:
        trend = "stable — consistent performance"

    return last_profit, trend


def check_and_nudge_inactive_traders():
    """
    Main job: runs daily. Finds traders silent for 3+ days
    and sends them a personalised nudge via messages_log.
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 🔍 Running proactive check...")

    try:
        traders = get_all_traders()
    except Exception as e:
        print(f"  ⚠️  Could not fetch traders: {e}")
        return

    now = datetime.now()
    nudged = 0

    for trader in traders:
        trader_id = trader["id"]
        trader_name = trader["name"]
        business_type = trader.get("business_type", "general")

        try:
            last_date = get_last_transaction_date(trader_id)

            if last_date is None:
                # Never recorded — skip (don't nag brand-new users)
                continue

            # Parse the date string from SQLite
            if isinstance(last_date, str):
                last_date = datetime.fromisoformat(last_date)

            days_silent = (now - last_date).days

            if days_silent < 3:
                continue  # Still active, no nudge needed

            # Get recent transactions for trend analysis
            recent = get_recent_transactions(trader_id, days=7)
            last_profit, trend = calculate_trend(recent)

            # Generate personalised nudge
            nudge_message = generate_nudge(
                trader_name=trader_name,
                business_type=business_type,
                last_profit=last_profit,
                days_silent=days_silent,
                trend=trend,
            )

            # Save to messages_log
            log_message(trader_id, f"[OjaMoni Nudge] {nudge_message}")

            print(f"  ✅ Nudged {trader_name} (silent {days_silent} days)")
            print(f"     → {nudge_message[:80]}...")
            nudged += 1

        except Exception as e:
            print(f"  ⚠️  Error processing {trader_name}: {e}")
            continue

    print(f"  Done. {nudged} trader(s) nudged.\n")


def get_pending_nudges(trader_id: int) -> list[str]:
    """
    Returns any unsent nudge messages for a trader.
    Used by the API to deliver nudges when trader opens the app.
    """
    from database.db import get_messages_log
    messages = get_messages_log(trader_id)
    nudges = [
        m["message"].replace("[OjaMoni Nudge] ", "")
        for m in messages
        if m["message"].startswith("[OjaMoni Nudge]")
    ]
    return nudges


# --- Scheduler setup ---

scheduler = BackgroundScheduler()


def start_proactive_scheduler():
    """
    Call this from main.py on app startup.
    Runs the nudge check every day at 8:00 AM.
    Also runs once immediately on startup so you can test it.
    """
    if not scheduler.running:
        scheduler.add_job(
            check_and_nudge_inactive_traders,
            trigger="cron",
            hour=8,
            minute=0,
            id="daily_nudge",
            replace_existing=True,
        )
        scheduler.start()
        print("✅ Proactive scheduler started — daily nudge at 8:00 AM")


def stop_proactive_scheduler():
    """Call this on app shutdown."""
    if scheduler.running:
        scheduler.shutdown()
        print("🛑 Proactive scheduler stopped")


def trigger_nudge_check_now():
    """
    Manual trigger — call this from an API endpoint
    so you can demo it live without waiting for 8 AM.
    """
    check_and_nudge_inactive_traders()