from django.urls import path

from apps.guest_meals.views import GuestMealApproveView, GuestMealListCreateView, GuestMealRejectView

urlpatterns = [
    path('', GuestMealListCreateView.as_view(), name='guest-meal-list-create'),
    path('<int:pk>/approve/', GuestMealApproveView.as_view(), name='guest-meal-approve'),
    path('<int:pk>/reject/', GuestMealRejectView.as_view(), name='guest-meal-reject'),
]
