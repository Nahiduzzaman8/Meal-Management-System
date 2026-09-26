from django.urls import path

from apps.adjustments.views import AdjustmentListCreateView

urlpatterns = [
    path('', AdjustmentListCreateView.as_view(), name='adjustment-list-create'),
]
