from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/kaminka/'), name='home_redirect'),

    # Zkusme to zapsat takto napřímo:
    path('kaminka/', TemplateView.as_view(template_name='index.html'), name='index'),
    path('kaminka/tenis/', include(('tenis_app.urls', 'tenis_app'))),
    path('kaminka/accounts/', include('django.contrib.auth.urls')),
    path('kaminka/zebricek/', include(('zebricek_app.urls', 'zebricek_app'))),
]

