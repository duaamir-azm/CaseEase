from django.shortcuts import redirect
from django.urls import reverse

class RoleBasedAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.restricted_paths = {
            '/accounts/admin-dashboard/': 'admin',
            '/accounts/handler-dashboard/': 'handler',
            '/accounts/dashboard/': 'user',
        }

    def __call__(self, request):
        path = request.path
        user = request.user

        # Redirect authenticated users from login page based on role
        if user.is_authenticated and path == reverse('login'):
            if user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'handler':
                return redirect('handler_dashboard')
            elif user.role == 'user':
                return redirect('user_dashboard')

        # Restrict access based on role
        for restricted_path, required_role in self.restricted_paths.items():
            if path.startswith(restricted_path):
                if not user.is_authenticated:
                    return redirect('login')
                if user.role != required_role:
                    return redirect('unauthorized')

        return self.get_response(request)


class RoleBasedRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.path == '/accounts/login/':
            if request.user.role == 'admin':
                return redirect('admin_dashboard')
            elif request.user.role == 'user':
                return redirect('user_dashboard')
            elif request.user.role == 'handler':
                return redirect('handler_dashboard')
        
        return self.get_response(request)