from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'tenis_app'

urlpatterns = [
    # Hlavní rozcestník
    path('', views.tenis_index, name='tenis_index'),
    
    # --- AUTENTIZACE A RESET HESLA ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset_form.html',
        email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt'
    ), name='password_reset'),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),
    # ---------------------------------

    # Detail konkrétní ligy
    path('liga/<slug:soutez_slug>/', views.detail_souteze, name='detail_souteze'),
    
    # Formuláře a akce
    path('pridat-hrace/', views.pridat_hrace, name='pridat_hrace'),
    path('zadat-vysledek/', views.zadat_vysledek, name='zadat_vysledek'),
    path('editovat-vysledek/<int:pk>/', views.editovat_vysledek, name='editovat_vysledek'),
    path('smazat-vysledek/<int:pk>/', views.smazat_vysledek, name='smazat_vysledek'),
    
    path('historie/', views.prehled_vsech_zapasu, name='prehled_vsech_zapasu'),
    
    path('editovat-hrace/<int:pk>/', views.editovat_hrace, name='editovat_hrace'),
    path('smazat-hrace/<int:pk>/', views.smazat_hrace, name='smazat_hrace'),
    
    path('admin-tools/', views.admin_tools_view, name='admin_tools'),
    path('run-admin-tool/', views.admin_tools_launcher, name='admin_tools_launcher'),
]