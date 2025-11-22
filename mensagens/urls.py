from django.urls import path
from . import views

app_name = 'mensagens'

urlpatterns = [
    # URL para a lista de todos os canais do usuário (acessada em /mensagens/)
    path('', views.lista_canais_view, name='chat_list'),

    # 🚨 ATUALIZAÇÃO: URL para o chat de um canal específico (usando o SLUG)
    # Acessada via: /mensagens/nome-do-canal-slug/
    # O name 'canal_chat' é o que foi referenciado em users/dashboard.html
    path('<slug:slug>/', views.chat_canal_view, name='canal_chat'),
]