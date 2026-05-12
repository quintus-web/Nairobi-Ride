from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('route/<int:pk>/', views.route_detail, name='route_detail'),
    path('explore/', views.explore, name='explore'),
    path('contribute/', views.contribute, name='contribute'),
]
