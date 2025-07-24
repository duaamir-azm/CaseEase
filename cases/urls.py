from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterCaseView.as_view(), name='register_case'),

    path('assign-inline/<int:case_id>/', views.AssignHandlerInlineView.as_view(), name='assign_handler_inline'),

    path('case/<int:pk>/', views.CaseDetailView.as_view(), name='case_detail'),

    path('case/<int:case_id>/get-messages/', views.get_messages, name='get_messages'),

]
