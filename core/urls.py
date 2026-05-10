from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView # Toto potřebujeme pro index.html
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Hlavní stránka
    #path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('', RedirectView.as_view(url='/tenis/liga/26_kaminka_leto_D/'), name='home'),
    
    # Ostatní aplikace
    path('tenis/', include('tenis_app.urls')),
    path('fotbal/', include('fotbal_app.urls')),
    
    # Autentizace (přihlašování, reset hesla)
    path('accounts/', include('django.contrib.auth.urls')),
    
    path('zebricek/', include('zebricek_app.urls')),
    
    
] 

