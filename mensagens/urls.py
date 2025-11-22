from django.urls import path
from . import views

app_name = 'mensagens'

urlpatterns = [
    # URL para a lista de todos os canais do usuário (acessada em /mensagens/)
    path('', views.lista_canais_view, name='chat_list'),

    # URL para o chat de um canal específico (acessada em /mensagens/<id>/)
    path('<int:canal_id>/', views.chat_canal_view, name='canal'),
]