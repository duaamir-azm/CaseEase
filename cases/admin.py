from django.contrib import admin
from .models import Case, CaseMessage

# Register your models here.

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'created_by', 'created_at']
    list_filter = ['status']  

@admin.register(CaseMessage)
class CaseMessageAdmin(admin.ModelAdmin):
    list_display = ('case', 'sender', 'message', 'file', 'timestamp')
    search_fields = ('case__title', 'sender__username', 'message')
    list_filter = ('timestamp',)