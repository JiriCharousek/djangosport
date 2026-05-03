from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
# core/urls.py
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView



urlpatterns = [
    path('admin/', admin.site.urls),
    path('tenis/', include('tenis_app.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('fotbal/', include('fotbal_app.urls')),  # Přidaná cesta pro fotbal
    # Tento řádek přidá login, logout, ale HLAVNĚ password_reset cesty:
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Tato řádka zobrazí index.html na hlavní doméně
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    

]