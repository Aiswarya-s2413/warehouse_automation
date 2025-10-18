import os
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Order
import urllib.parse
from imapclient import IMAPClient
from imapclient import exceptions as imap_exceptions
import email
from email.policy import default
from .llm_parser import get_status_from_email
from .models import Order
import socket
import logging

logger = logging.getLogger(__name__)

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

@shared_task(bind=True, max_retries=3)
def check_warehouse_inbox(self):
    IMAP_HOST = getattr(settings, 'IMAP_HOST', 'imap.gmail.com')
    IMAP_PORT = getattr(settings, 'IMAP_PORT', 993)
    IMAP_USER = getattr(settings, 'CONNECTED_MAILBOX', None)
    IMAP_PASS = getattr(settings, 'IMAP_PASSWORD', None)

    if not all([IMAP_USER, IMAP_PASS]):
        msg = "IMAP credentials missing; please set CONNECTED_MAILBOX and IMAP_PASSWORD in .env"
        logger.error(msg)
        return msg

    try:
        with IMAPClient(IMAP_HOST, port=IMAP_PORT, use_uid=True, ssl=True) as client:
            client.login(IMAP_USER, IMAP_PASS)
            client.select_folder('INBOX')

            messages = client.search(['UNSEEN'])
            if not messages:
                logger.debug("No new messages")
                return "No new emails found."

            fetched = client.fetch(messages, ['RFC822'])
            processed = 0

            for uid, data in fetched.items():
                raw = data.get(b'RFC822')
                if not raw:
                    continue
                email_message = email.message_from_bytes(raw, policy=default)
                subject = email_message.get('subject', '') or ''
                body = ''

                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == 'text/plain' and not part.get_filename():
                            try:
                                body = part.get_content().strip()
                            except Exception:
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    try:
                        body = email_message.get_content().strip()
                    except Exception:
                        body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')

                if not (subject.strip() or body.strip()):
                    client.add_flags(uid, [b'\\Seen'])
                    continue

                logger.info(f"Processing email UID={uid} Subject={subject[:120]}")
                llm_result = get_status_from_email(subject, body)
                order_id_str = llm_result.get('order_id')
                new_status = llm_result.get('status')

                if order_id_str and new_status in ['Confirmed', 'Rejected']:
                    try:
                        # The LLM should return a clean ID.
                        order = Order.objects.get(id=int(order_id_str))
                        if order.status != new_status:
                            order.status = new_status
                            order.save()
                            logger.info(f"Updated Order {order.id} => {new_status}")
                        else:
                            logger.debug(f"Order {order.id} already {order.status}")
                        processed += 1
                        client.add_flags(uid, [b'\\Seen'])
                    except Order.DoesNotExist:
                        logger.warning(f"Order ID {order_id_str} not found in DB")
                        client.add_flags(uid, [b'\\Seen'])
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid Order ID format received: {order_id_str}")
                        client.add_flags(uid, [b'\\Seen'])
                    except Exception as e:
                        logger.error(f"Error updating order from email UID={uid}: {e}", exc_info=True)
                        client.add_flags(uid, [b'\\Seen'])
                else:
                    logger.info(f"LLM unknown or no order id for email UID={uid}; marking seen")
                    client.add_flags(uid, [b'\\Seen'])

            return f"Processed {processed} emails."

    except socket.gaierror as e:
        logger.warning(f"Network error connecting to IMAP: {e}. Retrying in 60s...")
        self.retry(exc=e, countdown=60)

    except imap_exceptions.LoginError as e:
        logger.error(f"IMAP Login failed for {IMAP_USER}: {e}")
        return f"Error connecting to IMAP: {e}"
    except Exception as e:
        logger.exception("Unexpected error when checking IMAP")
        return f"Error connecting to IMAP: {e}"