from django.urls import path
from .views import ProductListView, OrderCreateView

urlpatterns = [
    path('products/', ProductListView.as_view(), name='product-list'),
    path('orders/create/', OrderCreateView.as_view(), name='order-create'),
]
