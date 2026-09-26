from django.urls import path
from apps.months import views

urlpatterns = [
    path('', views.MonthCreateView.as_view(), name='month-create'),
    path('<int:pk>/open/', views.MonthOpenView.as_view(), name='month-open'),
    path('<int:pk>/close/', views.MonthCloseView.as_view(), name='month-close'),
    path('<int:pk>/members/', views.MonthMembersView.as_view(), name='month-members'),
    path('<int:pk>/manager/', views.ManagerAssignView.as_view(), name='manager-assign'),
]
