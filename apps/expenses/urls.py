from django.urls import path

from apps.expenses.views import ExpenseDeleteView, ExpenseDetailView, ExpenseListCreateView

urlpatterns = [
    path('', ExpenseListCreateView.as_view(), name='expense-list-create'),
    path('<int:pk>/', ExpenseDetailView.as_view(), name='expense-detail'),
    path('<int:pk>/delete/', ExpenseDeleteView.as_view(), name='expense-delete'),
]
