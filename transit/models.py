from django.db import models


class Route(models.Model):
    number = models.CharField(max_length=10, help_text="e.g. 111, 46, 102")
    destination = models.CharField(max_length=100)
    fare_estimate = models.CharField(max_length=50, help_text="e.g. 50 - 100 KES")

    def __str__(self):
        return f"{self.number} to {self.destination}"


class Stage(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_major_hub = models.BooleanField(default=False, help_text="Is this a main boarding point like Railways?")
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stages')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} ({self.route.number})"


class Contribution(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]
    TYPE_CHOICES = [('new_route', 'New Route'), ('fare_change', 'Fare Change'), ('stage_change', 'Stage Change'), ('tip', 'Tip')]

    name = models.CharField(max_length=100, blank=True, help_text="Optional — your name or nickname")
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True, related_name='contributions')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_display()} — {self.status}"
