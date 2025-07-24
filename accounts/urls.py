from django.urls import path
from . import views

urlpatterns = [
    # -------------------- Auth --------------------
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.LogoutUser, name='logout'),
    path('register/', views.UserRegisterView.as_view(), name='register'),
    path('unauthorized/', views.unauthorized, name='unauthorized'),


    # -------------------- Dashboards --------------------
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('handler-dashboard/', views.HandlerDashboardView.as_view(), name='handler_dashboard'),
    path('dashboard/', views.UserDashboardView.as_view(), name='user_dashboard'),

    # -------------------- Admin - Case Management --------------------
    path('cases/', views.AllCasesView.as_view(), name='all_cases'),
    path('cases/pending/', views.PendingCasesView.as_view(), name='pending_cases'),
    path('cases/approved/', views.ApprovedCasesView.as_view(), name='approved_cases'),
    path('cases/assigned/', views.AdminAssignedCasesView.as_view(), name='admin_assigned_cases'),
    path('cases/closed/', views.ClosedCasesView.as_view(), name='closed_cases'),

    # -------------------- Handler - Case Views --------------------
    path('handler-dashboard/', views.HandlerDashboardView.as_view(), name='handler_dashboard'),
    path('handler/cases/', views.HandlerAllCasesView.as_view(), name='handler_all_cases'),
    path('handler/assigned/', views.HandlerAssignedCasesView.as_view(), name='handler_assigned_cases'),
    path('handler/ongoing/', views.HandlerOngoingCasesView.as_view(), name='handler_ongoing_cases'),
    path('handler/closed/', views.HandlerClosedCasesView.as_view(), name='handler_closed_cases'),
    path('handler/start/<int:pk>/', views.StartOperatingView.as_view(), name='start_operating'),
    path('handler/update-status/<int:pk>/', views.UpdateStatusView.as_view(), name='update_status'),

    # -------------------- User - Case Views --------------------
    path('user/cases/', views.UserAllCasesView.as_view(), name='user_all_cases'),
    path('user/cases/pending/', views.UserPendingCasesView.as_view(), name='user_pending_cases'),
    path('user/cases/ongoing/', views.UserOngoingCasesView.as_view(), name='user_ongoing_cases'),
    path('user/cases/closed/', views.UserClosedCasesView.as_view(), name='user_closed_cases'),

    # -------------------- Handlers --------------------
    path('handlers/', views.HandlerListView.as_view(), name='view_handlers'),
    path('handlers/add/', views.HandlerAddView.as_view(), name='add_handler'),
    path('handlers/remove/<int:pk>/', views.HandlerRemoveView.as_view(), name='remove_handler'),

    # -------------------- Users --------------------
    path('users/', views.UserListView.as_view(), name='view_users'),
    path('users/remove/<int:pk>/', views.UserRemoveView.as_view(), name='remove_user'),

    # -------------------- profile management --------------------
    path('profile/', views.ProfileView.as_view(), name='view_profile'),
    path('handler_profile/', views.UserProfileView.as_view(), name='view_user_profile'),
    path('user_profile/', views.HandlerProfileView.as_view(), name='view_handler_profile'),

]
