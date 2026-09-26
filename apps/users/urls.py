from django.urls import path
from apps.users import views

urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', views.RefreshView.as_view(), name='auth-refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', views.MeView.as_view(), name='auth-me'),
    path('auth/password/change/', views.PasswordChangeView.as_view(), name='auth-password-change'),
]

urlpatterns += [
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/deactivate/', views.UserDeactivateView.as_view(), name='user-deactivate'),
    path('users/<int:pk>/reactivate/', views.UserReactivateView.as_view(), name='user-reactivate'),
    path('users/<int:pk>/reset-password/', views.UserResetPasswordView.as_view(), name='user-reset-password'),
]
