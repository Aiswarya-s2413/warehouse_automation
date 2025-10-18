import os
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Order
import urllib.parse
from imapclient import IMAPClient
import email
from email.policy import default
from .llm_parser import get_status_from_email
from django.conf import settings

CONNECTED_MAILBOX = os.getenv("CONNECTED_MAILBOX")
WAREHOUSE_EMAIL = os.getenv("WAREHOUSE_EMAIL")
@shared_task
def send_warehouse_confirmation_email(order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return "Order not found"

    subject = f"New Order Placed: #{order.id}"

    # Prepare "mailto" link for warehouse
    confirm_subject = f"CONFIRM: Order #{order.id}"
    confirm_body = f"Order {order.id} is confirmed and ready for dispatch."

    # URL-encode
    encoded_subject = urllib.parse.quote(confirm_subject)
    encoded_body = urllib.parse.quote(confirm_body)

    mailto_link = f"mailto:{CONNECTED_MAILBOX}?subject={encoded_subject}&body={encoded_body}"

    # Plain text fallback
    message = f"""
A new order has been placed.

Order ID: {order.id}
Customer: {order.customer_name}
Product: {order.product.name}
Quantity: {order.quantity}
Total Cost: ${order.total_cost}

Please confirm this order by clicking the link sent in the email.
"""

    # HTML Email
    html_message = f"""
<html>
<body>
    <h2>New Order Placed: #{order.id}</h2>
    <p><strong>Customer:</strong> {order.customer_name}</p>
    <p><strong>Product:</strong> {order.product.name}</p>
    <p><strong>Quantity:</strong> {order.quantity}</p>
    <p><strong>Total Cost:</strong> ${order.total_cost}</p>
    <hr>
    <p>Please confirm this order is ready by clicking the button below. This will open an email for you to send.</p>
    <a href="{mailto_link}" 
       style="background-color: #4CAF50; color: white; padding: 14px 25px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; border-radius: 8px;">
       Click to Confirm Order
    </a>
</body>
</html>
"""

    send_mail(
        subject,
        message,  # plain text
        settings.EMAIL_HOST_USER,
        [WAREHOUSE_EMAIL],
        html_message=html_message,
        fail_silently=False,
    )

    return f"Confirmation email sent for Order {order.id}"

@shared_task
def check_warehouse_inbox():
    IMAP_HOST = 'imap.gmail.com'
    IMAP_USER = settings.CONNECTED_MAILBOX  # from .env/settings.py
    IMAP_PASS = settings.EMAIL_HOST_PASSWORD  # app password for the bot

    try:
        with IMAPClient(IMAP_HOST) as client:
            client.login(IMAP_USER, IMAP_PASS)
            client.select_folder('INBOX')

            messages = client.search(['UNSEEN'])
            if not messages:
                return "No new emails found."

            for uid, message_data in client.fetch(messages, 'RFC822').items():
                email_message = email.message_from_bytes(message_data[b'RFC822'], policy=default)
                subject = email_message.get('subject', '')

                # Extract email body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == 'text/plain':
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')

                if not subject and not body:
                    continue

                print(f"Processing email: {subject}")
                llm_result = get_status_from_email(subject, body)

                order_id_str = llm_result.get('order_id')
                new_status = llm_result.get('status')

                if order_id_str and new_status in ['Confirmed', 'Rejected']:
                    try:
                        order_id_clean = int("".join(filter(str.isdigit, order_id_str)))
                        order = Order.objects.get(id=order_id_clean)

                        if order.status != new_status:
                            order.status = new_status
                            order.save()
                            print(f"SUCCESS: Updated Order {order.id} to {new_status}")

                        client.add_flags(uid, [b'\\Seen'])  # mark email as read

                    except Order.DoesNotExist:
                        print(f"Error: Order ID {order_id_str} not found.")
                    except Exception as e:
                        print(f"Error updating order: {e}")
                else:
                    print(f"LLM gave unknown status for: {subject}")

            return f"Processed {len(messages)} emails."

    except Exception as e:
        return f"Error connecting to IMAP: {e}"