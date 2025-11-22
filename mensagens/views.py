import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch, Max
# 🚨 NOVO: Importa timezone para usar o horário exato da leitura
from django.utils import timezone

# Importa modelos do app `mensagens`
# 🚨 ATUALIZAÇÃO: Adicionado UltimaLeituraUsuario
from .models import Canal, Mensagem, UltimaLeituraUsuario
# Importa modelos de usuários/grupos (assumindo que o Grupo está em users.models)
from users.models import Grupo

# Importa o modelo de usuário customizado
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


@login_required
def lista_canais_view(request):
    """
    Exibe a lista de canais de chat disponíveis para o usuário logado.
    O acesso é determinado pela afiliação do usuário ao Grupo de Audiência vinculado ao Canal.
    """
    # 1. Identifica os AuthGroups do usuário logado
    user_auth_groups = request.user.groups.all()

    # 2. Encontra os modelos 'Grupo' (users.models.Grupo) que estão vinculados a esses AuthGroups
    grupos_acessiveis = Grupo.objects.filter(auth_group__in=user_auth_groups)

    # 3. Busca os Canais de chat ativos vinculados a esses Grupos acessíveis
    canais = Canal.objects.filter(
        grupo__in=grupos_acessiveis,
        ativo=True
    ).select_related('grupo', 'grupo__auth_group').order_by('nome')

    # 4. Busca a última mensagem para cada canal (para preview)
    canais_com_preview = []
    for canal in canais:
        # Busca a mensagem mais recente (apenas conteúdo e data_envio para ser rápido)
        ultima_mensagem = Mensagem.objects.filter(canal=canal).order_by('-data_envio').only('conteudo', 'data_envio',
                                                                                            'autor__username').first()

        # Anexa como atributo temporário ao objeto Canal
        canal.ultima_mensagem = ultima_mensagem
        canais_com_preview.append(canal)

    context = {
        'canais': canais_com_preview,
        'title': 'Canais de Mensagens'
    }

    # Renderiza o template para a lista de canais
    return render(request, 'mensagens/chat_list.html', context)


@login_required
def chat_canal_view(request, slug): # 🚨 ATUALIZAÇÃO: Recebe 'slug' no lugar de 'canal_id'
    """
    Renderiza a interface de chat para um canal específico e
    atualiza o registro de UltimaLeituraUsuario.
    """

    # 1. Busca o Canal pelo slug (inclui o grupo e o AuthGroup)
    try:
        canal = get_object_or_404(
            Canal.objects.select_related('grupo', 'grupo__auth_group'),
            slug=slug # 🚨 ATUALIZAÇÃO: Filtra por slug
        )
        # Obtém o AuthGroup (Group padrão do Django) associado
        auth_group = canal.grupo.auth_group
    except Exception as e:
        raise e

    # 2. Validação de Membro do Grupo (Lógica de Autorização)
    # Verifica se o CustomUser logado pertence ao AuthGroup associado ao Canal.
    is_member = request.user.groups.filter(id=auth_group.id).exists()

    if not is_member:
        # Se não for membro, levanta erro de permissão 403.
        raise PermissionDenied("Você não tem permissão para acessar este canal de chat.")

    # ==============================================================================
    # 🚨 NOVO PASSO: Rastreamento de Leitura (Limpa a notificação)
    # ==============================================================================
    # Busca o registro existente ou cria um novo, e atualiza a data/hora da última leitura.
    # O campo data_leitura em UltimaLeituraUsuario está configurado com auto_now=True,
    # então basta chamar .save() para atualizar o timestamp.
    UltimaLeituraUsuario.objects.update_or_create(
        usuario=request.user,
        canal=canal,
        # O valor `data_leitura` será atualizado automaticamente (auto_now=True)
        # Se você preferir um timestamp explícito e mais preciso:
        # defaults={'data_leitura': timezone.now()}
    )
    # Este passo é crucial, pois ao salvar, o campo auto_now=True garante que o
    # dashboard não mostrará mais notificação para este canal.
    # ==============================================================================

    # 3. BUSCA EXPLÍCITA DOS MEMBROS
    membros = auth_group.customuser_set.all().order_by('username')


    # 4. Busca o Histórico de Mensagens
    mensagens_qs = Mensagem.objects.filter(canal=canal).select_related('autor').order_by('-data_envio')[:50]
    mensagens = list(reversed(mensagens_qs))  # Converte para lista e reverte

    context = {
        'canal': canal,
        'mensagens': mensagens,
        # Passa a lista de membros obtida explicitamente
        'membros_canal': membros,
        # ID do usuário logado
        'user_id': request.user.id,
    }

    # Renderiza o template de chat
    return render(request, 'mensagens/chat.html', context)