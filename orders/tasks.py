from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Order
import urllib.parse

# This is the email inbox your other Celery task will monitor
CONNECTED_MAILBOX = "your-warehouse-bot-inbox@gmail.com"
WAREHOUSE_EMAIL = "warehouse-team-email@example.com"

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
