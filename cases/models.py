from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django_fsm import FSMField, transition
from simple_history.models import HistoricalRecords

# Create your models here.

class Case(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('In Progress', 'In Progress'),
        ('Waiting for Info', 'Waiting for Info'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
    ]

    status = FSMField(choices=STATUS_CHOICES, default='Pending')

    @transition(field=status, source='Pending', target='Approved')
    def approve(self):
        pass

    @transition(field=status, source='Approved', target='In Progress')
    def start_progress(self):
        pass

    @transition(field=status, source='In Progress', target='Waiting for Info')
    def wait_for_info(self):
        pass

    @transition(field=status, source='Waiting for Info', target='In Progress')
    def resume_progress(self):
        pass

    @transition(field=status, source='In Progress', target='Resolved')
    def resolve(self):
        pass

    @transition(field=status, source='Resolved', target='Closed')
    def close(self):
        pass
    

    title = models.CharField(max_length=200)
    description = models.TextField()
    # status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    location = models.CharField(max_length=200, null=True, blank=True)
    incident_date = models.DateField(null=True, blank=True)
    uploaded_file = models.FileField(upload_to='case_files/', null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    suspect_name = models.CharField(max_length=200, null=True, blank=True)
    witnesses = models.TextField(null=True, blank=True)
    progress_notes = models.TextField(null=True, blank=True)
    report_file = models.FileField(upload_to='reports/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cases_created'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cases_assigned',
        limit_choices_to={'groups__name': 'handler'}
    )
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.title} ({self.status})"



class CaseHistory(models.Model):
    case = models.ForeignKey(Case, related_name='custom_history', on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on {self.timestamp}"




class CaseMessage(models.Model):
    case = models.ForeignKey(Case, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message by {self.sender.username} in Case #{self.case.id} on {self.timestamp}"
