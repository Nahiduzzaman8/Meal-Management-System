from django.urls import path

from apps.reports.views import BalancesReportView, MembersReportView, MonthlyReportView

urlpatterns = [
    path('monthly/', MonthlyReportView.as_view(), name='report-monthly'),
    path('members/', MembersReportView.as_view(), name='report-members'),
    path('balances/', BalancesReportView.as_view(), name='report-balances'),
]
