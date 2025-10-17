from rest_framework import serializers
from .models import Product, Order

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'cost']


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        # Only fields needed from the form
        fields = ['customer_name', 'customer_id', 'user_email', 'product', 'quantity']
