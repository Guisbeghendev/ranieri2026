from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'users'

urlpatterns = [
    # ROTAS DE AUTENTICAÇÃO (Login e Logout)
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    # ROTAS DE CADASTRO
    path('register/', views.registration_create, name='register'),

    # ROTAS DE REDEFINIÇÃO DE SENHA (Mantidas)
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='users/password_reset_form.html',
            email_template_name='users/password_reset_email.html'
        ),
        name='password_reset'
    ),
    path(
        'password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
        name='password_reset_complete'
    ),

    # ROTAS DE PERFIL
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('password_change/', views.UserPasswordChangeView.as_view(
        template_name='users/password_change_form.html',
        success_url='/users/profile/'
    ), name='password_change'),

    # ROTA DA DASHBOARD
    path('dashboard/', views.dashboard, name='dashboard'),

    # 🎯 NOVA ROTA DE APROVAÇÃO ADMINISTRATIVA
    path('aprovar/<int:user_id>/', views.admin_approve_user, name='admin_approve_user'),
]