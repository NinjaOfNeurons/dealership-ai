from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx
import json
import re
from system_prompt import SYSTEM_PROMPT

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"  # change to "llama3" if preferred

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: str = "default"

# In-memory lead store (replace with DB/CRM later)
leads_db = []

def extract_lead(response_text: str, session_id: str = "default"):
    """Extract lead JSON if AI captured one"""
    match = re.search(r'<LEAD_CAPTURE>(.*?)</LEAD_CAPTURE>', response_text, re.DOTALL)
    if match:
        try:
            lead_data = json.loads(match.group(1).strip())
            leads_db.append(lead_data)
            print(f"🎯 LEAD CAPTURED: {lead_data}")
            return lead_data
        except:
            pass
    return None

def clean_response(text: str):
    """Remove the lead capture block from customer-facing response"""
    return re.sub(r'<LEAD_CAPTURE>.*?</LEAD_CAPTURE>', '', text, flags=re.DOTALL).strip()





async def push_to_n8n(lead_data: dict):
    """Fire lead to n8n webhook — non-blocking"""
    N8N_WEBHOOK = "http://localhost:5678/webhook/dealership-lead"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(N8N_WEBHOOK, json=lead_data)
            print(f"Lead pushed to n8n: {lead_data['name']}")
    except Exception as e:
        print(f"n8n push failed (non-critical): {e}")



@app.post("/chat")
async def chat(request: ChatRequest):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in request.messages]

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": messages,
            "stream": False
        })
        result = response.json()

    raw_reply = result["message"]["content"]
    lead = extract_lead(raw_reply)
    if lead:
        await push_to_n8n(lead)

    clean_reply = clean_response(raw_reply)

    return {
        "reply": clean_reply,
        "lead_captured": lead,
        "model": MODEL
    }

@app.get("/leads")
async def get_leads():
    return {"leads": leads_db, "total": len(leads_db)}

@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL}


@app.post("/leads")
async def add_lead(lead: dict):
    lead["timestamp"] = lead.get("timestamp", datetime.now().isoformat())
    leads_db.append(lead)
    await push_to_n8n(lead)
    return {"status": "ok", "lead": lead}




@app.post("/voice-chat")
async def voice_chat(request: ChatRequest):
    """Same as /chat but optimised for voice — shorter responses"""
    messages_payload = [{"role": "system", "content": SYSTEM_PROMPT + """
    
## VOICE MODE RULES
- Keep responses under 2 sentences — this is a phone call
- No bullet points, no lists — speak naturally
- Never say 'I cannot' — always offer an alternative
- Speak numbers naturally: say 'thirteen lakh' not '13,00,000'
- Always end with a question to keep conversation going
"""}]
    messages_payload += [{"role": m.role, "content": m.content} for m in request.messages]

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": messages_payload,
            "stream": False,
            "options": {"temperature": 0.7}
        })
        result = response.json()

    raw_reply = result["message"]["content"]
    lead = extract_lead(raw_reply, request.session_id)
    clean_reply = clean_response(raw_reply)

    if lead:
        await push_to_n8n(lead)

    return {"reply": clean_reply, "lead_captured": lead}





@app.post("/vapi/chat/completions")
async def vapi_endpoint(request: Request):
    """VAPI-compatible endpoint"""
    body = await request.json()
    
    # Extract messages from VAPI format
    messages = body.get("messages", [])
    session_id = body.get("call", {}).get("id", "vapi-call")
    
    # Filter to user/assistant messages only
    filtered = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("role") in ["user", "assistant"] and m.get("content")
    ]
    
    if not filtered:
        return {"choices": [{"message": {"role": "assistant", "content": "Hello! Welcome to AutoEdge Motors. I'm Aria. Are you looking to buy a new car or book a service appointment?"}}]}

    messages_payload = [{"role": "system", "content": SYSTEM_PROMPT + """
## VOICE MODE
- Max 2 short sentences per response
- Speak naturally — no bullet points, no lists
- Say numbers in words: 'thirteen lakh' not '13,00,000'
- Always end with a question
"""}]
    messages_payload += filtered

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": messages_payload,
            "stream": False,
            "options": {"temperature": 0.7}
        })
        result = response.json()

    raw_reply = result["message"]["content"]
    lead = extract_lead(raw_reply, session_id)
    clean_reply = clean_response(raw_reply)

    if lead:
        await push_to_n8n(lead)

    # Return in OpenAI-compatible format (what VAPI expects)
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": clean_reply
            }
        }]
    }

