from django.shortcuts import redirect

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