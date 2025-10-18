import google.generativeai as genai
import json, os

# Set your API key from .env (for demo, os.environ works)
os.environ['GOOGLE_API_KEY'] = 'YOUR_GOOGLE_API_KEY_HERE'
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

def get_status_from_email(subject, body):
    model = genai.GenerativeModel('gemini-1.5-flash')  # fast model

    prompt = f"""
    You are an order processing bot. Parse this email and extract:
    - Order ID
    - Status (Confirmed, Rejected, Unknown)

    Status rules:
    - "Ready to dispatch", "order is ready", "processing", "confirmed", "CONFIRM:" → Confirmed
    - "Out of stock", "cannot fulfill", "rejected" → Rejected
    - Otherwise → Unknown

    Email content:
    Subject: {subject}
    Body: {body}

    Respond ONLY in JSON:
    {{"order_id": "123", "status": "Confirmed"}}
    """

    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip().replace('```json', '').replace('```', '').strip()
        data = json.loads(json_text)
        if data.get('order_id') and data.get('status') in ['Confirmed', 'Rejected', 'Unknown']:
            return data
        else:
            return {"order_id": None, "status": "Unknown"}
    except Exception as e:
        print(f"LLM parsing error: {e}")
        return {"order_id": None, "status": "Unknown"}
