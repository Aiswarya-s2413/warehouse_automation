from django.db import models

from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255)
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('Order Placed', 'Order Placed'),
        ('Confirmed', 'Confirmed'),
        ('Dispatched', 'Dispatched'),
        ('Cancelled', 'Cancelled'),
    ]

    # Form Fields
    customer_name = models.CharField(max_length=255)
    customer_id = models.CharField(max_length=100)
    user_email = models.EmailField()
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    
    # Auto-calculated & Status
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Order Placed')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-calculate total cost before saving
        self.total_cost = self.product.cost * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.id} for {self.customer_name}"

