from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import sqlite3, os, json, time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'changeme_secret')

DB = 'data/messages.db'

def init_db():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 sender TEXT,
                 inbound TEXT,
                 outbound TEXT,
                 state TEXT,
                 created_at TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="Inzend — WhatsApp Bot (FastAPI scaffold)")

class ProviderPayload(BaseModel):
    # Generic shape for inbound webhook payloads; adapt per provider
    From: str | None = None
    Body: str | None = None
    MessageSid: str | None = None
    Raw: dict | None = None

def save_message(sender, inbound, outbound, state):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('INSERT INTO messages (sender, inbound, outbound, state, created_at) VALUES (?,?,?,?,?)',
              (sender, inbound, outbound, json.dumps(state), datetime.utcnow()))
    conn.commit()
    conn.close()

def load_last_state(sender):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT state FROM messages WHERE sender = ? ORDER BY id DESC LIMIT 1', (sender,))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return {}
    return {}

def send_outbound_message(sender, text):
    # placeholder: swap for Twilio / provider code (httpx or SDK)
    # For now we just log and return True for success
    print(f"[Outbound] -> {sender}: {text}")
    return True

@app.post('/webhook')
async def webhook(request: Request):
    # Basic secret check (optional)
    secret = request.headers.get('X-WEBHOOK-SECRET') or request.query_params.get('secret')
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    data = await request.json()
    # Try to normalize incoming payloads (Twilio uses 'From' and 'Body')
    payload = ProviderPayload(**{k: data.get(k) for k in ['From','Body','MessageSid']})
    sender = (payload.From or data.get('from') or 'unknown').strip()
    inbound = (payload.Body or data.get('body') or '').strip()

    # load last state
    state = load_last_state(sender) or {}

    # Very small finite-state bot
    outbound = ""
    if not state.get('step'):
        outbound = """Hi 👋 I am the automated assistant.
Reply with:
1 - Book a demo
2 - Pricing
3 - Talk to human"""
        state = {'step': 'menu'}
    elif state.get('step') == 'menu':
        if inbound == '1':
            outbound = "Great — to book a demo, please share your name and preferred date."
            state['step'] = 'collect_demo_info'
        elif inbound == '2':
            outbound = "We offer tiered packages starting at $2,000. Reply 'docs' for an overview."
            state['step'] = 'menu'
        elif inbound == '3':
            outbound = "One moment — I will route you to a human. Please provide your email."
            state['step'] = 'handoff'
        else:
            outbound = "Sorry, I didn't understand. Reply with 1, 2 or 3."
            state['step'] = 'menu'
    elif state.get('step') == 'collect_demo_info':
        # store user's reply as demo metadata
        state['demo_info'] = inbound
        outbound = "Thanks — a human will follow up within one business day. Reply 'menu' to see options."
        state['step'] = 'complete'
    elif state.get('step') == 'handoff':
        state['handoff_contact'] = inbound
        outbound = "Thanks — a human will contact you. Reply 'menu' to return to main options."
        state['step'] = 'complete'
    else:
        outbound = "Reply 'menu' to see options again."
        state['step'] = 'menu'

    # send (placeholder)
    ok = send_outbound_message(sender, outbound)
    save_message(sender, inbound, outbound, state)
    return { 'ok': ok, 'outbound': outbound }

@app.get('/health')
async def health():
    return { 'status': 'ok', 'ts': time.time() }
