from django import forms
from .models import Case, CaseMessage
from django.contrib.auth import get_user_model


User = get_user_model()


class CaseForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = [
            'title',
            'description',
            'location',
            'incident_date',
            'uploaded_file',
            'is_anonymous',
            'suspect_name',
            'witnesses',
        ]
        widgets = {
            'incident_date': forms.DateInput(attrs={'type': 'date'}),
        }




class AssignHandlerForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = ['assigned_to']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = User.objects.filter(groups__name__iexact='handler')




class CaseMessageForm(forms.ModelForm):
    class Meta:
        model = CaseMessage
        fields = ['message', 'file']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Type your message...',
                'class': 'form-control'
            }),
        }