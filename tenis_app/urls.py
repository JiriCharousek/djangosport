from django.urls import path  # <--- TENTO ŘÁDEK TI CHYBÍ
from . import views

urlpatterns = [
   
    path('', views.liga_a, name='tenis_index'),
    path('liga/A/', views.liga_a, name='liga_a'),
    path('liga/B/', views.liga_b, name='liga_b'),
    path('liga/C/', views.liga_c, name='liga_c'),
    path('liga/D/', views.liga_d, name='liga_d'),
    path('vsechny-zapasy/', views.prehled_vsech_zapasu, name='vsechny_zapasy'),
    path('pridat-hrace/', views.pridat_hrace, name='pridat_hrace'),
    path('zadat-vysledek/', views.zadat_vysledek, name='zadat_vysledek'),
    path('editovat-vysledek/<int:pk>/', views.editovat_vysledek, name='editovat_vysledek'),
    path('smazat-vysledek/<int:pk>/', views.smazat_vysledek, name='smazat_vysledek'),
    path('editovat-hrace/<int:pk>/', views.editovat_hrace, name='editovat_hrace'),
    path('smazat-hrace/<int:pk>/', views.smazat_hrace, name='smazat_hrace'),
    
    
]