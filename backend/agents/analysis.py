"""
analysis.py — OjaMoni Weekly Analysis Agent

Pulls 7 days of transactions from SQLite, sends them to Claude
for deep reasoning, and returns a full business narrative in
both English and Pidgin.
"""

import json
import re
import anthropic
from backend.database.db import get_recent_transactions

client = anthropic.Anthropic()


def analyze_weekly_performance(trader_id: int, trader_name: str, business_type: str) -> dict:
    """
    Pull last 7 days of transactions and ask Claude to reason
    across them. Returns a structured analysis dict.
    """
    transactions = get_recent_transactions(trader_id, days=7)

    if not transactions:
        return _empty_analysis(trader_name)

    # Build a readable summary of the week for Claude
    tx_lines = []
    for tx in transactions:
        line = (
            f"Date: {tx['date']} | "
            f"Revenue: ₦{tx['revenue']:,.0f} | "
            f"Expenses: ₦{tx['expenses']:,.0f} | "
            f"Profit: ₦{tx['profit']:,.0f} | "
            f"Notes: {tx['raw_input']}"
        )
        tx_lines.append(line)

    tx_summary = "\n".join(tx_lines)

    total_revenue = sum(t["revenue"] for t in transactions)
    total_expenses = sum(t["expenses"] for t in transactions)
    total_profit = sum(t["profit"] for t in transactions)
    best_day = max(transactions, key=lambda t: t["profit"])
    worst_day = min(transactions, key=lambda t: t["profit"])

    prompt = f"""You are OjaMoni, an AI financial analyst for Nigerian informal traders.

Trader: {trader_name}
Business type: {business_type}
Period: Last 7 days

Transaction data:
{tx_summary}

Weekly totals:
- Total Revenue: ₦{total_revenue:,.0f}
- Total Expenses: ₦{total_expenses:,.0f}
- Total Profit: ₦{total_profit:,.0f}
- Best day profit: ₦{best_day['profit']:,.0f} on {best_day['date']}
- Worst day profit: ₦{worst_day['profit']:,.0f} on {worst_day['date']}

Analyse this trader's week deeply and return ONLY a JSON object with these exact keys:
{{
  "overall_health": "Good" or "Fair" or "Poor",
  "health_score": <number 1-100>,
  "weekly_narrative": "<3-4 sentence summary in clear friendly English>",
  "weekly_narrative_pidgin": "<same summary but in Nigerian Pidgin English>",
  "key_finding_1": "<most important finding>",
  "key_finding_2": "<second finding>",
  "key_finding_3": "<third finding>",
  "action_1": "<most important action to take next week>",
  "action_2": "<second action>",
  "profit_trend": "improving" or "declining" or "stable",
  "biggest_opportunity": "<one specific opportunity you see in the data>",
  "warning": "<one risk or warning sign, or empty string if none>"
}}

Be specific — reference actual numbers from the data. Keep it warm and Nigerian in tone.
Return ONLY the JSON, no markdown, no explanation."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        analysis = json.loads(raw)

        # Add computed totals for the frontend
        analysis["total_revenue"] = total_revenue
        analysis["total_expenses"] = total_expenses
        analysis["total_profit"] = total_profit
        analysis["days_recorded"] = len(transactions)
        analysis["trader_name"] = trader_name

        return analysis

    except Exception as e:
        print(f"Analysis error: {e}")
        return _empty_analysis(trader_name)


def format_weekly_report(analysis: dict, trader_name: str) -> str:
    """
    Formats the analysis dict into a readable WhatsApp-style report.
    """
    name = trader_name.split()[0]

    health = analysis.get("overall_health", "Fair")
    score = analysis.get("health_score", 0)
    health_emoji = {"Good": "🟢", "Fair": "🟡", "Poor": "🔴"}.get(health, "🟡")

    total_revenue = analysis.get("total_revenue", 0)
    total_expenses = analysis.get("total_expenses", 0)
    total_profit = analysis.get("total_profit", 0)
    days = analysis.get("days_recorded", 0)
    trend = analysis.get("profit_trend", "stable")
    trend_emoji = {"improving": "📈", "declining": "📉", "stable": "➡️"}.get(trend, "➡️")

    narrative = analysis.get("weekly_narrative", "")
    narrative_pidgin = analysis.get("weekly_narrative_pidgin", "")

    finding_1 = analysis.get("key_finding_1", "")
    finding_2 = analysis.get("key_finding_2", "")
    finding_3 = analysis.get("key_finding_3", "")

    action_1 = analysis.get("action_1", "")
    action_2 = analysis.get("action_2", "")

    opportunity = analysis.get("biggest_opportunity", "")
    warning = analysis.get("warning", "")

    lines = [
        f"📊 *OjaMoni Weekly Report — {name}*",
        f"_{days} days recorded_\n",
        f"{health_emoji} *Business Health: {health}* ({score}/100)",
        f"{trend_emoji} *Profit Trend: {trend.title()}*\n",
        f"💰 *Revenue:* ₦{total_revenue:,.0f}",
        f"💸 *Expenses:* ₦{total_expenses:,.0f}",
        f"{'🟢' if total_profit >= 0 else '🔴'} *Net Profit:* ₦{total_profit:,.0f}\n",
        f"📝 *What happened this week:*",
        f"{narrative}\n",
        f"🗣️ *In Pidgin:*",
        f"_{narrative_pidgin}_\n",
        f"🔍 *Key Findings:*",
        f"1. {finding_1}",
        f"2. {finding_2}",
        f"3. {finding_3}\n",
        f"✅ *Actions for next week:*",
        f"→ {action_1}",
        f"→ {action_2}\n",
    ]

    if opportunity:
        lines.append(f"💡 *Opportunity:* {opportunity}\n")

    if warning:
        lines.append(f"⚠️ *Watch out:* {warning}\n")

    lines.append(f"_Keep going {name}! Every naira recorded is progress._ 💪")

    return "\n".join(lines)


def _empty_analysis(trader_name: str) -> dict:
    """Returned when there's no data or Claude fails."""
    return {
        "overall_health": "Fair",
        "health_score": 0,
        "weekly_narrative": "No transactions recorded this week. Start recording your daily sales so OjaMoni can track your progress!",
        "weekly_narrative_pidgin": "You never record anything this week o! Abeg start to dey send your sales every day so we fit help you track your money.",
        "key_finding_1": "No data recorded this week",
        "key_finding_2": "Daily recording helps you spot patterns",
        "key_finding_3": "Even rough estimates are better than nothing",
        "action_1": "Record today's sales right now — just send a quick message",
        "action_2": "Set a daily reminder to send your sales at close of business",
        "profit_trend": "stable",
        "biggest_opportunity": "Start recording consistently to unlock real insights",
        "warning": "",
        "total_revenue": 0,
        "total_expenses": 0,
        "total_profit": 0,
        "days_recorded": 0,
        "trader_name": trader_name,
    }