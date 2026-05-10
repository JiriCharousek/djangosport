from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. Hlavní doména sportadmin.cz tě hodí na sportadmin.cz/kaminka/
    path('', RedirectView.as_view(url='/kaminka/'), name='home_redirect'),

    # 2. Vše pod prefixem /kaminka/
    path('kaminka/', include([
        # Tady bude tvůj INDEX (sportadmin.cz/kaminka/)
        path('', TemplateView.as_view(template_name='index.html'), name='index'),
        
        # Ostatní aplikace pod /kaminka/
        path('tenis/', include('tenis_app.urls')),
        path('accounts/', include('django.contrib.auth.urls')),
        path('zebricek/', include('zebricek_app.urls')),
    ])),
]