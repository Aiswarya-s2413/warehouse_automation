import google.generativeai as genai
import json
import os
import re
import logging

logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

def get_status_from_email(subject, body):
    """
    Parse email content to extract order ID and status.
    Returns: {"order_id": "123", "status": "Confirmed|Rejected|Unknown"}
    """
    model = genai.GenerativeModel('models/gemini-2.0-flash') 

    prompt = f"""
You are an order processing bot. Parse this email and extract:
- Order ID (numeric only, no symbols)
- Status (must be one of: Confirmed, Rejected, Unknown)

Status rules:
- "Ready to dispatch", "order is ready", "processing", "confirmed", "CONFIRM:" → Confirmed
- "Out of stock", "cannot fulfill", "rejected" → Rejected
- If unclear → Unknown

Email:
Subject: {subject}
Body: {body}

Return ONLY valid JSON with no markdown formatting:
{{"order_id": "123", "status": "Confirmed"}}
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Remove markdown code blocks if present
        text = re.sub(r'^```(?:json)?|\n```$', '', text, flags=re.MULTILINE).strip()
        
        # Find JSON object
        json_match = re.search(r'\{[^{}]*\}', text)
        if not json_match:
            logger.warning(f"No JSON found in LLM response: {text}")
            return fallback_parse(subject, body)
        
        data = json.loads(json_match.group())
        
        # Clean and validate order_id
        order_id = data.get('order_id', '').strip()
        # Remove common prefixes/symbols
        order_id = re.sub(r'^[#\s]*', '', str(order_id))
        order_id = re.sub(r'[^\d]', '', order_id)  # Keep only digits
        
        status = data.get('status', 'Unknown')
        
        # Validate status
        if status not in ['Confirmed', 'Rejected', 'Unknown']:
            logger.warning(f"Invalid status '{status}', defaulting to Unknown")
            status = 'Unknown'
        
        result = {
            "order_id": order_id if order_id else None,
            "status": status
        }
        
        logger.info(f"LLM parsed: order_id={result['order_id']}, status={result['status']}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}. Response: {text if 'text' in locals() else 'N/A'}")
        return fallback_parse(subject, body)
    except Exception as e:
        logger.exception(f"LLM parsing error: {e}")
        return fallback_parse(subject, body)


def fallback_parse(subject, body):
    """
    Fallback parser using regex patterns when LLM fails.
    """
    logger.info("Using fallback regex parser")
    
    combined_text = f"{subject} {body}".lower()
    
    # Extract order ID - look for patterns like "Order #123", "Order 123", "#123"
    order_id_match = re.search(r'order\s*#?(\d+)|#(\d+)', combined_text, re.IGNORECASE)
    order_id = None
    if order_id_match:
        order_id = order_id_match.group(1) or order_id_match.group(2)
    
    # Determine status
    status = 'Unknown'
    confirm_keywords = ['confirm', 'ready', 'dispatch', 'processing', 'fulfilled']
    reject_keywords = ['reject', 'out of stock', 'cannot fulfill', 'cancel']
    
    if any(keyword in combined_text for keyword in confirm_keywords):
        status = 'Confirmed'
    elif any(keyword in combined_text for keyword in reject_keywords):
        status = 'Rejected'
    
    logger.info(f"Fallback parsed: order_id={order_id}, status={status}")
    return {"order_id": order_id, "status": status}