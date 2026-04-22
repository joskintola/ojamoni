import os
import sys
import shutil
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db import (
    init_db, get_trader_by_phone, get_all_traders,
    save_transaction, get_recent_transactions,
    get_last_transaction_date, log_message, get_messages_log
)
from backend.agents.ingestion import extract_financial_data, format_response_for_trader
from backend.agents.analysis import analyze_weekly_performance, format_weekly_report
from backend.agents.voice import process_voice_note

load_dotenv()

app = FastAPI(title="OjaMoni API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

init_db()


def get_trader_or_404(trader_id: int):
    from backend.database.db import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traders WHERE id = ?", (trader_id,))
    trader = cursor.fetchone()
    conn.close()
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    return dict(trader)


@app.get("/")
def root():
    return {"status": "OjaMoni is running 🚀"}


@app.get("/traders")
def list_traders():
    traders = get_all_traders()
    return {"traders": traders}


@app.post("/message")
def send_message(trader_id: int = Form(...), text: str = Form(...)):
    trader = get_trader_or_404(trader_id)

    # Log trader's message
    log_message(trader_id, text, sender="trader")

    # Check if asking for weekly report
    if "weekly report" in text.lower():
        analysis = analyze_weekly_performance(
            trader_id, trader["name"], trader["business_type"]
        )
        reply = format_weekly_report(analysis, trader["name"])
        log_message(trader_id, reply, sender="ojamoni")
        return {"reply": reply, "type": "weekly_report"}

    # Otherwise process as financial input
    data = extract_financial_data(text_input=text)
    reply = format_response_for_trader(data, trader["name"])

    # Save transaction
    save_transaction(
        trader_id=trader_id,
        date=datetime.now().strftime("%Y-%m-%d"),
        revenue=data.get("revenue", 0),
        expenses=data.get("expenses", 0),
        profit=data.get("profit", 0),
        raw_input=text,
        ai_insight=data.get("insight", "")
    )

    log_message(trader_id, reply, sender="ojamoni")
    return {"reply": reply, "type": "transaction", "data": data}


@app.post("/upload-image")
def upload_image(trader_id: int = Form(...), file: UploadFile = File(...)):
    trader = get_trader_or_404(trader_id)

    # Save uploaded image
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Process with Claude vision
    data = extract_financial_data(image_path=file_path)
    reply = format_response_for_trader(data, trader["name"])

    save_transaction(
        trader_id=trader_id,
        date=datetime.now().strftime("%Y-%m-%d"),
        revenue=data.get("revenue", 0),
        expenses=data.get("expenses", 0),
        profit=data.get("profit", 0),
        raw_input=f"[Image: {file.filename}]",
        ai_insight=data.get("insight", "")
    )

    log_message(trader_id, f"[Sent image: {file.filename}]", sender="trader")
    log_message(trader_id, reply, sender="ojamoni")
    return {"reply": reply, "type": "image", "data": data}


@app.post("/voice-note")
def upload_voice(trader_id: int = Form(...), file: UploadFile = File(...)):
    trader = get_trader_or_404(trader_id)

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    data, reply = process_voice_note(file_path, trader["name"])

    if data:
        save_transaction(
            trader_id=trader_id,
            date=datetime.now().strftime("%Y-%m-%d"),
            revenue=data.get("revenue", 0),
            expenses=data.get("expenses", 0),
            profit=data.get("profit", 0),
            raw_input=f"[Voice note: {file.filename}]",
            ai_insight=data.get("insight", "")
        )

    log_message(trader_id, f"[Sent voice note]", sender="trader")
    log_message(trader_id, reply, sender="ojamoni")
    return {"reply": reply, "type": "voice"}


@app.get("/weekly-report/{trader_id}")
def weekly_report(trader_id: int):
    trader = get_trader_or_404(trader_id)
    analysis = analyze_weekly_performance(
        trader_id, trader["name"], trader["business_type"]
    )
    report = format_weekly_report(analysis, trader["name"])
    log_message(trader_id, report, sender="ojamoni")
    return {"report": report, "analysis": analysis}


@app.get("/chat-history/{trader_id}")
def chat_history(trader_id: int):
    trader = get_trader_or_404(trader_id)
    messages = get_messages_log(trader_id)
    return {"trader": trader, "messages": messages}


@app.post("/trigger-nudge/{trader_id}")
def trigger_nudge(trader_id: int):
    """Demo endpoint — triggers proactive nudge manually"""
    trader = get_trader_or_404(trader_id)
    last_date = get_last_transaction_date(trader_id)
    transactions = get_recent_transactions(trader_id, days=7)

    if not transactions:
        nudge = f"Hey {trader['name']}! 👋 You haven't recorded any sales yet. Send me your first entry and let's start tracking your business!"
    else:
        last_profit = transactions[0]["profit"]
        profit_emoji = "📈" if last_profit > 0 else "📉"
        nudge = f"Hey {trader['name']}! 👋 You haven't recorded since {last_date}. Your last profit was {profit_emoji} ₦{abs(last_profit):,.0f}. Don't lose track of your money — send today's sales when you're ready! 💪"

    log_message(trader_id, nudge, sender="ojamoni")
    return {"nudge": nudge}