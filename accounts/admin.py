from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

# Register your models here.
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'role', 'phone_number', 'profile_image']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('phone_number', 'role', 'profile_image')}),

    )

admin.site.register(CustomUser, CustomUserAdmin)