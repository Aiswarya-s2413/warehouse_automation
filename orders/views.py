from rest_framework import generics
from .models import Product, Order
from .serializers import ProductSerializer, OrderCreateSerializer
from .tasks import send_warehouse_confirmation_email  # Celery task, we'll create later

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class OrderCreateView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer

    def perform_create(self, serializer):
        # Status defaults to 'Order Placed'
        order = serializer.save()
        # Trigger Celery task to send email
        send_warehouse_confirmation_email.delay(order.id)
