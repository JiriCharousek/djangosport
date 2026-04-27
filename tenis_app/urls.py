from django.urls import path
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Hlavní rozcestník
    path('', views.tenis_index, name='tenis_index'),
    
    # Detail konkrétní ligy (univerzální)
    path('liga/<slug:soutez_slug>/', views.detail_souteze, name='detail_souteze'),
    
    # Formuláře a akce
    path('pridat-hrace/', views.pridat_hrace, name='pridat_hrace'),
    path('zadat-vysledek/', views.zadat_vysledek, name='zadat_vysledek'),
    path('editovat-vysledek/<int:pk>/', views.editovat_vysledek, name='editovat_vysledek'),
    path('smazat-vysledek/<int:pk>/', views.smazat_vysledek, name='smazat_vysledek'),
    
    # Historie (TADY BYLA TA CHYBA - musí se jmenovat 'prehled_vsech_zapasu')
    path('historie/', views.prehled_vsech_zapasu, name='prehled_vsech_zapasu'),
    
    path('editovat-hrace/<int:pk>/', views.editovat_hrace, name='editovat_hrace'),
    path('smazat-hrace/<int:pk>/', views.smazat_hrace, name='smazat_hrace'),
    

] 
 