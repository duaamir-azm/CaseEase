from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .models import Case
from .forms import CaseForm, CaseMessageForm
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import CaseHistory, CaseMessage, Case
from simple_history.utils import update_change_reason
from django.http import JsonResponse
from django.contrib import messages as django_messages
from django.utils import timezone


# Create your views here.


class RegisterCaseView(LoginRequiredMixin, CreateView):
    model = Case
    form_class = CaseForm
    template_name = 'cases/register_case.html'
    success_url = reverse_lazy('user_dashboard')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        # Log registration
        CaseHistory.objects.create(
            case=self.object,
            action="Case Registered",
            performed_by=None if self.object.is_anonymous else self.request.user
        )

        return response




# class CaseDetailView(DetailView):
#     model = Case
#     template_name = 'cases/case_detail.html'
#     context_object_name = 'case'

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['history'] = self.object.history.order_by('-timestamp')
#         return context

class CaseDetailView(LoginRequiredMixin, DetailView):
    model = Case
    template_name = 'cases/case_detail.html'
    context_object_name = 'case'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        case = self.object

        # Check permission
        user = self.request.user
        context['can_message'] = (
            user == case.created_by or 
            user == case.assigned_to or 
            user.is_superuser
        )

        context['messages'] = case.messages.order_by('timestamp')
        context['message_form'] = CaseMessageForm()
        context['history'] = case.custom_history.order_by('-timestamp')

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        case = self.object
        user = request.user

        # Restrict access
        if not (user == case.created_by or user == case.assigned_to or user.is_superuser):
            django_messages.error(request, "You do not have permission to send messages for this case.")
            return redirect('case_detail', pk=case.pk)

        form = CaseMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message_text = form.cleaned_data.get('message', '').strip()
            uploaded_file = request.FILES.get('file')

            if not message_text and not uploaded_file:
                django_messages.error(request, "You can't send an empty message.")
                return redirect('case_detail', pk=case.pk)

            case_message = form.save(commit=False)
            case_message.case = case
            case_message.sender = user
            case_message.timestamp = timezone.now()
            case_message.save()

            # If a file is uploaded, add to history
            if case_message.file:
                file_name = case_message.file.name.replace("chat_files/", "")
                file_url = case_message.file.url  # ← Proper way to get the URL
                sender = case_message.sender
                # Get first group name if exists, else empty string
                group_name = sender.groups.first().name if sender.groups.exists() else ""
                performed_by = None if case.is_anonymous and group_name != "handler" and not sender.is_superuser else user
                CaseHistory.objects.create(
                    case=case,
                    action=f'A file uploaded: <a href="{file_url}" target="_blank">{file_name}</a>',
                    performed_by=performed_by
                )

            return redirect('case_detail', pk=case.pk)

        context = self.get_context_data()
        context['message_form'] = form
        return self.render_to_response(context)




@login_required
def get_messages(request, case_id):
    case = get_object_or_404(Case, id=case_id)
    messages = case.messages.order_by('timestamp')

    data = []
    for msg in messages:
        data.append({
            'user': msg.sender.username,
            'text': msg.message,
            'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return JsonResponse({'messages': data})



# User = get_user_model()

# class AssignHandlerInlineView(LoginRequiredMixin, View):
#     def post(self, request, case_id):
#         case = get_object_or_404(Case, id=case_id)
#         handler_id = request.POST.get("assigned_to")  # matches form field name

#         if handler_id:
#             handler = get_object_or_404(User, id=handler_id)
#             case.assigned_to = handler  # assumes model field is assigned_to
#             case.status = 'Assigned'
#             case.save()
#             # Log in case history
#             CaseHistory.objects.create(
#                 case=case,
#                 action=f'Case assigned to {case.assigned_to}',
#                 performed_by=request.user
#             )

#         return redirect('approved_cases')


from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Case, CaseHistory

User = get_user_model()

class AssignHandlerInlineView(LoginRequiredMixin, View):
    def post(self, request, case_id):
        case = get_object_or_404(Case, id=case_id)
        handler_id = request.POST.get("assigned_to")  # matches form field name

        if handler_id:
            handler = get_object_or_404(User, id=handler_id)
            case.assigned_to = handler
            case.status = 'Assigned'  # optional custom status
            case.save()

            # Log in case history
            CaseHistory.objects.create(
                case=case,
                action=f'Case assigned to {case.assigned_to}',
                performed_by=request.user
            )

            # WhatsApp redirect
            if handler.phone_number:
                phone = handler.phone_number.replace("+", "")
                message = f"Hello {handler.username}, a new case ({case.title}) has been assigned to you. Please check the portal."
                whatsapp_url = f"https://wa.me/{phone}?text={message.replace(' ', '%20')}"
                return redirect(whatsapp_url)

        return redirect('approved_cases')
