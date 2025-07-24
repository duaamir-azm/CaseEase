from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
ROLE_CHOICES = (
    ('admin', 'Admin'),
    ('user', 'User'),
    ('handler', 'Case Handler')
)

class CustomUser(AbstractUser):
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True) 


    def __str__(self):
        return f'{self.username} ({self.role})'