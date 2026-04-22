import anthropic
import base64
import json
import re
from pathlib import Path

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are OjaMoni, a friendly AI financial assistant for Nigerian informal traders.
Your job is to extract financial data from trader messages — which may be in English, Pidgin English, Yoruba/Igbo/Hausa mixed in, or a combination.

ALWAYS return a valid JSON object. NEVER return an error. NEVER leave the trader without a warm response.

Rules for extraction:
- "k" or "K" means thousand (e.g. "20k" = 20000)
- "around", "like", "almost", "roughly" before a number is fine — use the number given
- If only expenses are mentioned (no sales), set revenue to 0
- If no numbers at all, set revenue=0, expenses=0, profit=0 and set needs_clarification=true
- If message is off-topic (questions, complaints, greetings), set is_off_topic=true
- If message is emotional/venting, set is_emotional=true
- Extract items sold as a list of strings
- biggest_expense is the single largest expense item mentioned

Return ONLY this JSON (no markdown, no explanation):
{
  "revenue": <number>,
  "expenses": <number>,
  "profit": <number>,
  "items_sold": ["item1", "item2"],
  "biggest_expense": "<expense name or empty string>",
  "insight": "<one sentence financial insight in friendly tone>",
  "summary": "<short 1-line summary of what happened today>",
  "needs_clarification": <true/false>,
  "is_off_topic": <true/false>,
  "is_emotional": <true/false>,
  "clarification_prompt": "<if needs_clarification, ask warmly for the missing info, else empty string>",
  "off_topic_response": "<if is_off_topic, answer warmly or redirect, else empty string>",
  "emotional_response": "<if is_emotional, respond with empathy and encouragement, else empty string>"
}"""


def extract_financial_data(text_input=None, image_path=None):
    """
    Extract financial data from text or image input.
    Handles messy, pidgin, vague, emotional, off-topic, and incomplete inputs.
    Always returns a dict — never raises an exception to the caller.
    """
    try:
        messages_content = []

        if image_path:
            image_data = Path(image_path).read_bytes()
            b64_image = base64.standard_b64encode(image_data).decode("utf-8")
            suffix = Path(image_path).suffix.lower()
            media_type_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".gif": "image/gif",
            }
            media_type = media_type_map.get(suffix, "image/jpeg")
            messages_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64_image,
                },
            })

        if text_input:
            messages_content.append({
                "type": "text",
                "text": f"Trader message: {text_input}"
            })
        elif image_path and not text_input:
            messages_content.append({
                "type": "text",
                "text": "Extract all financial data visible in this image."
            })

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": messages_content}],
        )

        raw_text = response.content[0].text.strip()

        # Strip markdown fences if Claude wrapped in them
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

        data = json.loads(raw_text)

        # Ensure all expected keys exist with safe defaults
        defaults = {
            "revenue": 0,
            "expenses": 0,
            "profit": 0,
            "items_sold": [],
            "biggest_expense": "",
            "insight": "",
            "summary": "",
            "needs_clarification": False,
            "is_off_topic": False,
            "is_emotional": False,
            "clarification_prompt": "",
            "off_topic_response": "",
            "emotional_response": "",
        }
        for key, default in defaults.items():
            data.setdefault(key, default)

        # Recalculate profit to be safe
        if not data["is_off_topic"] and not data["needs_clarification"]:
            data["profit"] = data["revenue"] - data["expenses"]

        return data

    except json.JSONDecodeError:
        # Claude returned something that isn't JSON — still return gracefully
        return _fallback_response("parse_error")
    except anthropic.APIError as e:
        return _fallback_response("api_error", str(e))
    except Exception as e:
        return _fallback_response("unknown_error", str(e))


def _fallback_response(reason="unknown", detail=""):
    """
    Returns a safe fallback dict when something goes wrong internally.
    The trader never sees an error — they get a warm message.
    """
    return {
        "revenue": 0,
        "expenses": 0,
        "profit": 0,
        "items_sold": [],
        "biggest_expense": "",
        "insight": "Abeg send your sales again — I wan help you track am well well!",
        "summary": "Could not read this entry",
        "needs_clarification": True,
        "is_off_topic": False,
        "is_emotional": False,
        "clarification_prompt": (
            "Ehn ehn! I no fit read that one well. "
            "Abeg tell me: how much you sell today, and how much you spend? 🙏"
        ),
        "off_topic_response": "",
        "emotional_response": "",
        "_internal_error": reason,  # for logging only, not shown to trader
        "_detail": detail,
    }


def format_response_for_trader(data: dict, trader_name: str) -> str:
    """
    Converts extracted data dict into a warm WhatsApp-style reply.
    Handles all special states: off-topic, emotional, needs clarification, normal.
    """
    name = trader_name.split()[0] if trader_name else "Oga"

    # --- Emotional message ---
    if data.get("is_emotional"):
        emotional = data.get("emotional_response", "")
        base = (
            f"Ah {name} 🤗 I hear you, and your feelings are valid.\n\n"
            f"{emotional}\n\n"
            "Every trader has hard days — the fact say you dey record means you serious about this business. "
            "We go figure it out together. 💪"
        )
        return base

    # --- Off-topic message ---
    if data.get("is_off_topic"):
        off_topic = data.get("off_topic_response", "")
        return (
            f"Hey {name}! 😊\n\n"
            f"{off_topic}\n\n"
            "Whenever you ready to record today's sales, just send am! I dey here. 📊"
        )

    # --- Needs clarification ---
    if data.get("needs_clarification"):
        clarification = data.get("clarification_prompt", "")
        return (
            f"Hello {name}! 👋\n\n"
            f"{clarification}"
        )

    # --- Normal financial entry ---
    revenue = data.get("revenue", 0)
    expenses = data.get("expenses", 0)
    profit = data.get("profit", 0)
    items = data.get("items_sold", [])
    biggest_expense = data.get("biggest_expense", "")
    insight = data.get("insight", "")
    summary = data.get("summary", "")

    profit_emoji = "🟢" if profit > 0 else ("🔴" if profit < 0 else "🟡")
    profit_label = "Profit" if profit >= 0 else "Loss"

    lines = [f"✅ *Recorded! {summary}*\n"]

    if items:
        items_str = ", ".join(items)
        lines.append(f"🛒 *Items sold:* {items_str}")

    lines.append(f"💰 *Revenue:* ₦{revenue:,.0f}")
    lines.append(f"💸 *Expenses:* ₦{expenses:,.0f}")

    if biggest_expense:
        lines.append(f"   ↳ Biggest cost: {biggest_expense}")

    lines.append(f"{profit_emoji} *{profit_label}:* ₦{abs(profit):,.0f}\n")

    if insight:
        lines.append(f"💡 {insight}")

    lines.append(f"\n_{name}, well done for recording today! Keep am up!_ 🙌")

    return "\n".join(lines)