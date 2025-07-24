from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, TemplateView, ListView
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.contrib.auth.models import Group
from django.db.models import Q
from .forms import UserRegisterForm
from cases.models import Case
from django.urls import reverse
from cases.models import CaseHistory
from django_fsm import can_proceed
import json
from django.utils import timezone
from django.db.models.functions import TruncDate
from django.db.models import Count


# Auth Views

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_success_url(self):
        user = self.request.user

        if user.is_superuser:
            return reverse('admin_dashboard')
        
        if user.groups.filter(name='handler').exists():
            return reverse('handler_dashboard')
        
        # Default for normal users
        return reverse('user_dashboard')


def LogoutUser(request):
    logout(request)
    return redirect('home')


def unauthorized(request):
    return render(request, 'accounts/unauthorized.html')



class UserRegisterView(View):
    def get(self, request):
        form = UserRegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('login')
        return render(request, 'accounts/register.html', {'form': form})


# ========== Admin Views ==========

class AdminDashboardView(TemplateView):
    template_name = 'accounts/admin_dashboard.html'

    def get_percent(self, count, total):
        return int((count / total) * 100) if total else 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q')
        cases = Case.objects.all().order_by('-updated_at')
        total_cases = cases.count()
        pending_cases = cases.filter(status='Pending').count()
        approved_cases = cases.filter(status='Approved').count()
        assigned_cases = cases.exclude(status__in=['Pending', 'Approved', 'Closed']).count()
        closed_cases = cases.filter(status='Closed').count()

        if query:
            cases = cases.filter(
                Q(title__icontains=query) |
                Q(created_by__username__icontains=query) |
                Q(assigned_to__username__icontains=query)
            )
        
        today = timezone.now().date()
        days = 7
        date_list = [(today - timezone.timedelta(days=x)) for x in range(days-1, -1, -1)]
        labels = [d.strftime('%Y-%m-%d') for d in date_list]

        cases_by_day = (
            Case.objects
            .filter(created_at__date__gte=date_list[0], created_at__date__lte=date_list[-1])
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        cases_dict = {c['day'].strftime('%Y-%m-%d'): c['count'] for c in cases_by_day}
        data = [cases_dict.get(label, 0) for label in labels]

        context['cases_per_day_labels'] = json.dumps(labels) if 'labels' in locals() else '[]'
        context['cases_per_day_data'] = json.dumps(data) if 'data' in locals() else '[]'


        context.update({
            'cases': cases,
            'total_cases': cases.count(),
            'pending_cases': pending_cases,
            'approved_cases': approved_cases,
            'closed_cases': closed_cases,
            'assigned_cases': assigned_cases,  
            'users_count': get_user_model().objects.filter(is_superuser=False, is_staff=False).exclude(groups__name='handler').count(),
            'handlers_count': get_user_model().objects.filter(groups__name='handler').count(),
            'pending_percent': self.get_percent(pending_cases, total_cases),
            'approved_percent': self.get_percent(approved_cases, total_cases),
            'assigned_percent': self.get_percent(assigned_cases, total_cases),
            'closed_percent': self.get_percent(closed_cases, total_cases),

        })
        return context


class AllCasesView(TemplateView):
    template_name = 'accounts/cases/all_cases.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q')
        cases = Case.objects.all().order_by('-updated_at')

        if query:
            cases = cases.filter(
                Q(title__icontains=query) |
                Q(created_by__username__icontains=query) |
                Q(assigned_to__username__icontains=query)
            )

        context.update({
            'cases': cases,
            'total_cases': cases.count(),
            'pending_cases': cases.filter(status='Pending').count(),
            'approved_cases': cases.filter(status='Approved').count(),
            'closed_cases': cases.filter(status='Closed').count(),
            'assigned_cases': cases.exclude(status__in=['Pending', 'Approved', 'Closed']).count(),
            'users_count': get_user_model().objects.filter(is_superuser=False, is_staff=False).exclude(groups__name='handler').count(),
            'handlers_count': get_user_model().objects.filter(groups__name='handler').count(),
        })
        return context


class PendingCasesView(View):
    template_name = 'accounts/cases/pending_cases.html'

    def get(self, request):
        cases = Case.objects.filter(status='Pending')
        return render(request, self.template_name, {'cases': cases})

    def post(self, request):
        case_id = request.POST.get('case_id')
        case = get_object_or_404(Case, id=case_id)
        case.status = 'Approved'
        case.save()

        # Log approval here too
        CaseHistory.objects.create(
            case=case,
            action="Case Approved",
            performed_by=request.user
        )

        return redirect('approved_cases')

    

class ApprovedCasesView(ListView):
    template_name = 'accounts/cases/approved_cases.html'
    context_object_name = 'cases'

    def get(self, request):
        cases = Case.objects.filter(status='Approved')
        handlers = User.objects.filter(groups__name__iexact='handler')
        
        return render(request, self.template_name, {
            'cases': cases,
            'handlers': handlers,
        })



class AdminAssignedCasesView(ListView):
    template_name = 'accounts/cases/assigned_cases.html'
    context_object_name = 'cases'

    def get_queryset(self):
        return Case.objects.exclude(status__in=['Pending', 'Approved', 'Closed'])


class ClosedCasesView(ListView):
    template_name = 'accounts/cases/closed_cases.html'
    context_object_name = 'cases'

    def get_queryset(self):
        return Case.objects.filter(status='Closed')


# ========== Handler Views ==========

class HandlerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/handler_dashboard.html'

    def get_percent(self, count, total):
        return int((count / total.count()) * 100) if total else 0

    def get_context_data(self, **kwargs):
        handler = self.request.user
        query = self.request.GET.get('q')  # get the search query

        all_cases = Case.objects.filter(assigned_to=handler)
        assigned_cases = all_cases.filter(status='Assigned').count()
        ongoing_cases = all_cases.exclude(status__in=['Assigned', 'Pending', 'Approved', 'Closed']).count()
        closed_cases = all_cases.filter(status='Closed').count()

        if query:
            all_cases = all_cases.filter(title__icontains=query)  # filter by title

        context = super().get_context_data(**kwargs)
        context.update({
            'cases': all_cases,
            'all_count': all_cases.count(),
            'assigned_count': all_cases.filter(status='Assigned').count(),
            'ongoing_count': all_cases.exclude(status__in=['Assigned', 'Pending', 'Approved', 'Closed']).count(),
            'closed_count': all_cases.filter(status='Closed').count(),
            'assigned_percent': self.get_percent(assigned_cases, all_cases),
            'ongoing_percent': self.get_percent(ongoing_cases, all_cases),
            'closed_percent': self.get_percent(closed_cases, all_cases),
        })
        return context


class HandlerAllCasesView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/handlers/all_cases.html'

    def get_context_data(self, **kwargs):
        handler = self.request.user
        query = self.request.GET.get('q')  # get the search query

        all_cases = Case.objects.filter(assigned_to=handler)

        if query:
            all_cases = all_cases.filter(title__icontains=query)  # filter by title

        context = super().get_context_data(**kwargs)
        context.update({
            'cases': all_cases,
            'all_count': all_cases.count(),
            'assigned_count': all_cases.filter(status='Assigned').count(),
            'ongoing_count': all_cases.exclude(status__in=['Assigned', 'Pending', 'Approved', 'Closed']).count(),
            'closed_count': all_cases.filter(status='Closed').count(),
        })
        return context


class HandlerAssignedCasesView(LoginRequiredMixin, ListView):
    template_name = 'accounts/handlers/assigned_cases.html'
    context_object_name = 'cases'

    def get_queryset(self):
        return Case.objects.filter(assigned_to=self.request.user, status='Assigned')


class HandlerOngoingCasesView(LoginRequiredMixin, ListView):
    template_name = 'accounts/handlers/ongoing_cases.html'
    context_object_name = 'cases'

    def get_queryset(self):
        return Case.objects.filter(assigned_to=self.request.user).exclude(status__in=['Assigned', 'Pending', 'Approved', 'Closed'])


class HandlerClosedCasesView(LoginRequiredMixin, ListView):
    template_name = 'accounts/handlers/closed_cases.html'
    context_object_name = 'cases'

    def get_queryset(self):
        return Case.objects.filter(assigned_to=self.request.user, status='Closed')


class StartOperatingView(LoginRequiredMixin, View):
    def post(self, request, pk):
        case = get_object_or_404(Case, pk=pk, assigned_to=request.user)

        case.status = 'In Progress'
        case.save()

        # Log operation start
        CaseHistory.objects.create(
            case=case,
            action="Started Operating",
            performed_by=request.user
        )
        # Log the status update
        CaseHistory.objects.create(
            case=case,
            action="Status Updated to 'In Progress'",
            performed_by=request.user
        )
        return redirect('handler_ongoing_cases')


# class UpdateStatusView(LoginRequiredMixin, View):
#     def post(self, request, pk):
#         new_status = request.POST.get('status')
#         case = get_object_or_404(Case, pk=pk, assigned_to=request.user)

#         case.status = new_status
#         case.save()

#         # Log status change
#         CaseHistory.objects.create(
#             case=case,
#             action=f"Status Updated to '{new_status}'",
#             performed_by=request.user
#         )
#         return redirect('handler_ongoing_cases')


class UpdateStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        new_status = request.POST.get('status')
        case = get_object_or_404(Case, pk=pk, assigned_to=request.user)

        # FSM Transition Mapping
        transition_map = {
            'Approved': case.approve,
            'In Progress': case.start_progress,
            'Waiting for Info': case.wait_for_info,
            'In Progress': case.resume_progress,
            'Resolved': case.resolve,
            'Closed': case.close,
        }

        transition = transition_map.get(new_status)

        if transition:
            if can_proceed(transition):
                transition()     # run the FSM method
                case.save()      # save the new state
                CaseHistory.objects.create(
                    case=case,
                    action=f"Status updated to '{new_status}' via FSM",
                    performed_by= request.user
                )
                messages.success(request, f"Status changed to '{new_status}'.")
            else:
                messages.error(request, f"Invalid status transition to '{new_status}'.")
        else:
            messages.error(request, f"Unknown status '{new_status}'.")

        return redirect('handler_ongoing_cases')

# ========== User Views ==========

class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/user_dashboard.html'

    def get_context_data(self, **kwargs):
        user = self.request.user
        query = self.request.GET.get('q')  # Get the search input
        
        all_cases = Case.objects.filter(created_by=user)

        if query:
            all_cases = all_cases.filter(
                Q(title__icontains=query) | 
                Q(assigned_to__username__icontains=query)
            )

        context = super().get_context_data(**kwargs)
        context.update({
            'cases': all_cases,
            'all_count': all_cases.count(),
            'pending_count': all_cases.filter(status='Pending').count(),
            'ongoing_count': all_cases.exclude(status__in=['Pending','Closed']).count(),
            'closed_count': all_cases.filter(status='Closed').count(),
        })
        return context


class UserAllCasesView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/users/all_cases.html'

    def get_context_data(self, **kwargs):
        user = self.request.user
        query = self.request.GET.get('q')  # Get the search input
        
        all_cases = Case.objects.filter(created_by=user)

        if query:
            all_cases = all_cases.filter(
                Q(title__icontains=query) | 
                Q(assigned_to__username__icontains=query)
            )

        context = super().get_context_data(**kwargs)
        context.update({
            'cases': all_cases,
            'all_count': all_cases.count(),
            'ongoing_count': all_cases.exclude(status='Closed').count(),
            'closed_count': all_cases.filter(status='Closed').count(),
        })
        return context


class UserPendingCasesView(LoginRequiredMixin, ListView):
    template_name = 'accounts/users/pending_cases.html'
    context_object_name = 'cases'

    def get_queryset(self):
        return Case.objects.filter(created_by=self.request.user, status='Pending')
    

class UserOngoingCasesView(LoginRequiredMixin, ListView):
    template_name = 'accounts/users/ongoing_cases.html'
    context_object_name = 'cases'

    def get_queryset(self):
        return Case.objects.filter(created_by=self.request.user).exclude(status__in=['Pending', 'Closed'])


class UserClosedCasesView(LoginRequiredMixin, ListView):
    template_name = 'accounts/users/closed_cases.html'
    context_object_name = 'cases'

    def get_queryset(self):
        return Case.objects.filter(created_by=self.request.user, status='Closed')


# ========== Admin User & Handler Management ==========

class HandlerListView(ListView):
    template_name = 'accounts/handlers/view_handlers.html'
    context_object_name = 'handlers'

    def get_queryset(self):
        return get_user_model().objects.filter(
            is_superuser=False,
            is_staff=False,
            groups__name='handler'
        )


class HandlerAddView(View):
    def get(self, request):
        return render(request, 'accounts/handlers/add_handler.html')

    def post(self, request):
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone_number = request.POST.get('phone_number') 

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('add_handler')

        user = User.objects.create_user(username=username, email=email, password=password, role='handler')
        user.phone_number = phone_number
        user.save()

        # Automatically assign to 'handler' group
        handler_group, created = Group.objects.get_or_create(name='handler')
        user.groups.add(handler_group)
        user.save()

        messages.success(request, "Handler added and assigned to handler group.")
        return redirect('view_handlers')


class HandlerRemoveView(View):
    def get(self, request, pk):
        handler = get_object_or_404(get_user_model(), pk=pk)
        return render(request, 'accounts/confirm_delete.html', {
            'object': handler,
            'type': 'handler',
        })

    def post(self, request, pk):
        handler = get_object_or_404(get_user_model(), pk=pk)
        if handler.groups.filter(name='handler').exists():
            handler.delete()
        return redirect('view_handlers')


class UserListView(ListView):
    template_name = 'accounts/users/view_users.html'
    context_object_name = 'users'

    def get_queryset(self):
        return get_user_model().objects.filter(is_superuser=False, is_staff=False).exclude(groups__name='handler')


class UserRemoveView(View):
    def get(self, request, pk):
        user = get_object_or_404(get_user_model(), pk=pk)
        return render(request, 'accounts/confirm_delete.html', {
            'object': user,
            'type': 'user',
        })

    def post(self, request, pk):
        user = get_object_or_404(get_user_model(), pk=pk)
        if not user.is_superuser:
            user.delete()
        return redirect('view_users')


# ========== Profile Management ==========

# ========== Admin Profile ==========

User = get_user_model()

@method_decorator(login_required, name='dispatch')
class ProfileView(TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['form'] = PasswordChangeForm(user=user)

        if user.is_superuser:
            context['back_url'] = 'admin_dashboard'
        elif user.groups.filter(name='handler').exists():
            context['back_url'] = 'handler_dashboard'
        else:
            context['back_url'] = 'user_dashboard'

        return context

    def post(self, request, *args, **kwargs):
        user = request.user

        if 'username' in request.POST:  # Edit Profile Form Submitted
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            if request.FILES.get('profile_image'):
                user.profile_image = request.FILES.get('profile_image')
            user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('view_profile')

        elif 'old_password' in request.POST:  # Change Password Form Submitted
            form = PasswordChangeForm(user=user, data=request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect('view_profile')
            else:
                messages.error(request, "Please correct the errors below.")
                context = self.get_context_data()
                context['form'] = form
                return self.render_to_response(context)
            


# ========== Handler Profile ==========

@method_decorator(login_required, name='dispatch')
class HandlerProfileView(TemplateView):
    template_name = 'accounts/handler_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['form'] = PasswordChangeForm(user=user)

        if user.is_superuser:
            context['back_url'] = 'admin_dashboard'
        elif user.groups.filter(name='handler').exists():
            context['back_url'] = 'handler_dashboard'
        else:
            context['back_url'] = 'user_dashboard'

        return context

    def post(self, request, *args, **kwargs):
        user = request.user

        if 'username' in request.POST:  # Edit Profile Form Submitted
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            if request.FILES.get('profile_image'):
                user.profile_image = request.FILES.get('profile_image')
            user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('view_handler_profile')

        elif 'old_password' in request.POST:  # Change Password Form Submitted
            form = PasswordChangeForm(user=user, data=request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect('view_handler_profile')
            else:
                messages.error(request, "Please correct the errors below.")
                context = self.get_context_data()
                context['form'] = form
                return self.render_to_response(context)


# ========== User Profile ==========

@method_decorator(login_required, name='dispatch')
class UserProfileView(TemplateView):
    template_name = 'accounts/user_profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['form'] = PasswordChangeForm(user=user)

        if user.is_superuser:
            context['back_url'] = 'admin_dashboard'
        elif user.groups.filter(name='handler').exists():
            context['back_url'] = 'handler_dashboard'
        else:
            context['back_url'] = 'user_dashboard'

        return context

    def post(self, request, *args, **kwargs):
        user = request.user

        if 'username' in request.POST:  # Edit Profile Form Submitted
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            if request.FILES.get('profile_image'):
                user.profile_image = request.FILES.get('profile_image')
            user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('view_user_profile')

        elif 'old_password' in request.POST:  # Change Password Form Submitted
            form = PasswordChangeForm(user=user, data=request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect('view_user_profile')
            else:
                messages.error(request, "Please correct the errors below.")
                context = self.get_context_data()
                context['form'] = form
                return self.render_to_response(context)