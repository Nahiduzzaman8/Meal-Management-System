from django.urls import path

from apps.deposits.views import DepositActionView, DepositListCreateView

urlpatterns = [
    path('', DepositListCreateView.as_view(), name='deposit-list-create'),
    path('<int:pk>/approve/', DepositActionView.as_view(action='approve'), name='deposit-approve'),
    path('<int:pk>/reject/', DepositActionView.as_view(action='reject'), name='deposit-reject'),
]
