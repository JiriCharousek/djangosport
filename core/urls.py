from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView # Toto potřebujeme pro index.html

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Hlavní stránka
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Ostatní aplikace
    path('tenis/', include('tenis_app.urls')),
    path('fotbal/', include('fotbal_app.urls')),
    
    # Autentizace (přihlašování, reset hesla)
    path('accounts/', include('django.contrib.auth.urls')),
] # <--- Tady smí být jen jedna tahle závorka!