from django.urls import path

from apps.meals.views import MealListCreateView

urlpatterns = [
    path('', MealListCreateView.as_view(), name='meal-list-create'),
]
