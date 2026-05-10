from django.urls import path
from . import views

# Namespace aplikace
app_name = 'zebricek_app' 

urlpatterns = [
    # Cesta pro hlavní stránku žebříčku
    #path('', views.zebricek_detail, name='zebricek_index'),
    path('', views.zebricek_index, name='zebricek_index')
    
    # Cesta pro manuální posun
    path('manualni-posun/', views.manualni_posun_hrace, name='manualni_posun'),
]

