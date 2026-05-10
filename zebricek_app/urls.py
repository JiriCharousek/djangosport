from django.urls import path
from . import views


app_name = 'zebricek_app' 

urlpatterns = [
    path('', views.zebricek_detail, name='zebricek_index'),
    path('manualni-posun/', views.manualni_posun_hrace, name='manualni_posun'),
]

