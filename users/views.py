from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.core.files.storage import FileSystemStorage
from django.http import Http404
from django.contrib.auth import login as auth_login
from django.db.models import Q  # NOVO: Import necessário para queries complexas

# ==============================================================================
# 🎯 CORREÇÃO CRÍTICA: Importar modelos do app 'mensagens'
# ==============================================================================
from mensagens.models import Canal, UltimaLeituraUsuario, Mensagem

# Importar modelos e formulários
from .forms import (
    RegistrationAtomicForm,  # NOVO: Formulário de Cadastro Atômico
    CustomUserCreationForm,
    UserUpdateForm,
    ProfileUpdateForm,
    # Formulários de Update de Registro (Mantidos para profile_edit)
    RegistroProfessorUpdateForm,
    RegistroColaboradorUpdateForm,
    RegistroUREUpdateForm,
    RegistroOutrosVisitantesUpdateForm,
    RegistroAlunoUpdateForm,
    RegistroResponsavelUpdateForm,
)
from .models import (
    CustomUser,
    Profile,
    CustomUserTipo,
    RegistroAluno,
    # REFORMA: Importar todos os modelos de Registro.
    RegistroProfessor,
    RegistroColaborador,
    RegistroResponsavel,
    RegistroURE,
    RegistroOutrosVisitantes,
    Turma,
)

# Configura o FileSystemStorage (Mantido para uso em profile_edit)
file_storage = FileSystemStorage()


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def get_registro_info_for_edit(user):
    """
    Retorna a classe de formulário de atualização e a instância de registro,
    usando getattr para evitar RelatedObjectDoesNotExist se a instância
    OneToOne não existir.
    """
    tipo = user.tipo_usuario
    form_class = None
    registro_instance = None

    # Mapeamento do Tipo de Usuário para o Form de Update e o Objeto de Registro
    # Usando getattr para acessar as relações OneToOne de forma segura.
    # O segundo argumento (None) é o valor padrão se a relação não existir,
    # evitando o erro 'RelatedObjectDoesNotExist'.

    if tipo == CustomUserTipo.ALUNO.value:
        registro_instance = getattr(user, 'registro_aluno', None)
        if registro_instance:
            form_class = RegistroAlunoUpdateForm

    elif tipo == CustomUserTipo.PROFESSOR.value:
        registro_instance = getattr(user, 'registro_professor', None)
        if registro_instance:
            form_class = RegistroProfessorUpdateForm

    elif tipo == CustomUserTipo.COLABORADOR.value:
        registro_instance = getattr(user, 'registro_colaborador', None)
        if registro_instance:
            form_class = RegistroColaboradorUpdateForm

    elif tipo == CustomUserTipo.RESPONSAVEL.value:
        registro_instance = getattr(user, 'registro_responsavel', None)
        if registro_instance:
            form_class = RegistroResponsavelUpdateForm

    elif tipo == CustomUserTipo.URE.value:
        registro_instance = getattr(user, 'registro_ure', None)
        if registro_instance:
            form_class = RegistroUREUpdateForm

    elif tipo == CustomUserTipo.OUTRO_VISITANTE.value:
        # Acessa a relação com o nome definido (registro_visitante) ou o nome padrão
        registro_instance = getattr(user, 'registro_visitante', None)
        if not registro_instance:
            # Tenta o nome padrão do Django (nome da classe em minúsculo: registrooutrosvisitantes)
            registro_instance = getattr(user, 'registrooutrosvisitantes', None)

        if registro_instance:
            form_class = RegistroOutrosVisitantesUpdateForm

    return form_class, registro_instance


# ==============================================================================
# FUNÇÕES AUXILIARES DE ADMIN (NOVAS)
# ==============================================================================

def is_admin_or_staff(user):
    """Verifica se o usuário tem permissão para administrar (is_staff ou is_superuser)."""
    return user.is_active and (user.is_superuser or user.is_staff)


def get_pending_users_context(request):
    """Retorna o contexto de aprovação, visível apenas para Admin/Staff."""
    pendentes_context = {
        'pendentes_count': 0,
        'usuarios_pendentes': None,
        'is_admin_active': False
    }

    if is_admin_or_staff(request.user):
        pendentes_context['is_admin_active'] = True

        # Filtra usuários inativos (is_active=False) que são professores OU colaboradores
        # O filtro deve incluir qualquer tipo de usuário que exija aprovação (is_active=False na criação)
        pendentes_qs = CustomUser.objects.filter(
            is_active=False
        ).filter(
            Q(tipo_usuario=CustomUserTipo.PROFESSOR.value) |
            Q(tipo_usuario=CustomUserTipo.COLABORADOR.value)
            # Adicione outros tipos se a regra de is_active=False mudar
        )

        pendentes_context['pendentes_count'] = pendentes_qs.count()
        pendentes_context['usuarios_pendentes'] = pendentes_qs.order_by('date_joined')

    return pendentes_context


@login_required
@user_passes_test(is_admin_or_staff)
@transaction.atomic
def admin_approve_user(request, user_id):
    """
    View para ativar um usuário específico via link no dashboard do admin.
    """
    user_to_approve = get_object_or_404(CustomUser, pk=user_id)

    # Garante que estamos ativando apenas contas inativas que deveriam ser aprovadas manualmente
    if not user_to_approve.is_active and (
            user_to_approve.tipo_usuario == CustomUserTipo.PROFESSOR.value or
            user_to_approve.tipo_usuario == CustomUserTipo.COLABORADOR.value
    ):
        user_to_approve.is_active = True
        user_to_approve.save()
        messages.success(request,
                         f'Usuário {user_to_approve.username} ({user_to_approve.get_tipo_usuario_display()}) ativado com sucesso.')
        # 🎯 CORREÇÃO: Adicionado () em get_tipo_usuario_display() para evitar functools.partial
    else:
        messages.warning(request, f'Usuário {user_to_approve.username} não precisa de aprovação.')

    # Redireciona de volta para o dashboard
    return redirect(reverse('users:dashboard'))


# ==============================================================================
# 🎯 NOVA FUNÇÃO AUXILIAR: BUSCAR NOTIFICAÇÕES DE CHAT (CORRIGIDA)
# ==============================================================================

def get_chat_notifications(user):
    """
    Retorna uma QuerySet de canais onde há mensagens mais novas
    do que a última vez que o usuário leu (UltimaLeituraUsuario).
    """
    # 1. Busca todos os canais que o usuário pertence (Filtra Canais cujo Grupo tem o usuário logado)
    # 🚨 CORREÇÃO DO VALUERROR: Substituída a sintaxe '...__user=user' pela sintaxe '...__in=user.groups.all()'
    # para garantir que o filtro receba uma coleção de objetos Group, conforme esperado pelo Django.
    channels_qs = Canal.objects.filter(grupo__auth_group__in=user.groups.all())
    canais_nao_lidos = []

    for channel in channels_qs:
        # Tenta encontrar o registro de última leitura do usuário para este canal
        # 🚨 CORRIGIDO: Usa UltimaLeituraUsuario, campo 'usuario' e campo 'canal'
        last_read_obj = UltimaLeituraUsuario.objects.filter(usuario=user, canal=channel).first()

        # 2. Encontra a data da última mensagem no canal
        # 🚨 CORRIGIDO: Usa Mensagem e campo 'data_envio'
        latest_message = Mensagem.objects.filter(canal=channel).order_by('-data_envio').first()

        if latest_message:
            # Se não houver registro de leitura OU se a última mensagem for mais nova que o last_read
            # 🚨 CORRIGIDO: Usa o campo 'data_leitura'
            if not last_read_obj or latest_message.data_envio > last_read_obj.data_leitura:
                # 3. Se houver nova mensagem, adiciona o canal à lista
                canais_nao_lidos.append(channel)

    # Retorna uma lista dos objetos Canal que têm novas mensagens
    return canais_nao_lidos


# ==============================================================================
# 1. FLUXO DE REGISTRO ATÔMICO (PÁGINA ÚNICA) - NOVO
# ==============================================================================

def registration_create(request):
    """
    Nova vista de cadastro. Processa todas as trilhas em uma única transação atômica.
    """
    if request.method == 'POST':
        form = RegistrationAtomicForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data
            tipo_usuario = data['tipo_usuario']
            nome_completo = data['nome_completo']
            registros_a_vincular = data['registros_a_vincular']

            # Define se a conta deve ser ativa (Regra: Professor e Colaborador exigem aprovação manual)
            is_active_initial = not (
                    tipo_usuario == CustomUserTipo.PROFESSOR.value or
                    tipo_usuario == CustomUserTipo.COLABORADOR.value
            )

            try:
                with transaction.atomic():
                    registro_obj = None

                    # 1. CRIAÇÃO OU VÍNCULO DA ENTIDADE DE REGISTRO

                    if tipo_usuario == CustomUserTipo.ALUNO.value:
                        # O form.clean já buscou e validou o objeto RegistroAluno
                        registro_obj = registros_a_vincular['aluno_registro']

                    elif tipo_usuario == CustomUserTipo.PROFESSOR.value:
                        # CORREÇÃO: Usa o objeto RegistroProfessor encontrado pelo forms.py
                        if 'professor_registro' in registros_a_vincular:
                            registro_obj = registros_a_vincular['professor_registro']
                            # Atualiza o campo específico do objeto pré-existente
                            registro_obj.tipo_professor = data['tipo_professor']
                            registro_obj.save()
                        # Se não estiver no 'registros_a_vincular', o form.clean() já lançou um erro.

                    elif tipo_usuario == CustomUserTipo.COLABORADOR.value:
                        # REVERTIDO: Cria novo RegistroColaborador (com is_active=False por padrão)
                        registro_obj = RegistroColaborador.objects.create(
                            nome_completo=nome_completo,
                            funcao=data['funcao_colaborador']
                        )

                    elif tipo_usuario == CustomUserTipo.RESPONSAVEL.value:
                        # Cria novo RegistroResponsavel e adiciona dependentes
                        registro_obj = RegistroResponsavel.objects.create(
                            nome_completo=nome_completo
                        )
                        # O M2M é salvo APÓS o objeto, mas como estamos no atomic block, é seguro
                        if 'dependentes' in registros_a_vincular:
                            registro_obj.alunos.set(registros_a_vincular['dependentes'])

                    elif tipo_usuario == CustomUserTipo.URE.value:
                        # Cria novo RegistroURE
                        registro_obj = RegistroURE.objects.create(
                            nome_completo=nome_completo,
                            funcao=data['funcao_ure']
                        )

                    elif tipo_usuario == CustomUserTipo.OUTRO_VISITANTE.value:
                        # Cria novo RegistroOutrosVisitantes
                        registro_obj = RegistroOutrosVisitantes.objects.create(
                            nome_completo=nome_completo,
                            descricao=data['descricao_vinculo']
                        )

                    # 2. CRIAÇÃO DO CUSTOMUSER e VÍNCULO

                    # Mapeia nome_completo para first_name e last_name
                    partes_nome = nome_completo.split(' ', 1)
                    first_name = partes_nome[0]
                    last_name = partes_nome[1] if len(partes_nome) > 1 else ''

                    new_user = CustomUser.objects.create_user(
                        username=data['username'],
                        email=data['email'],
                        password=data['password'],
                        tipo_usuario=tipo_usuario,
                        first_name=first_name,
                        last_name=last_name,
                        # Aplica a regra de aprovação manual
                        is_active=is_active_initial
                    )

                    # 3. Faz o link OneToOne
                    if registro_obj:
                        if tipo_usuario == CustomUserTipo.ALUNO.value:
                            new_user.registro_aluno = registro_obj
                        elif tipo_usuario == CustomUserTipo.PROFESSOR.value:
                            new_user.registro_professor = registro_obj
                        elif tipo_usuario == CustomUserTipo.COLABORADOR.value:
                            new_user.registro_colaborador = registro_obj
                        elif tipo_usuario == CustomUserTipo.RESPONSAVEL.value:
                            new_user.registro_responsavel = registro_obj
                        elif tipo_usuario == CustomUserTipo.URE.value:
                            new_user.registro_ure = registro_obj
                        elif tipo_usuario == CustomUserTipo.OUTRO_VISITANTE.value:
                            new_user.registro_visitante = registro_obj

                        # Salva o vínculo no CustomUser
                        # NOTE: Este save dispara o post_save que cria o Profile
                        new_user.save()

                        # O signal post_save cuidará da criação do Profile.

                    messages.success(request, f'Cadastro concluído com sucesso! Bem-vindo(a), {first_name}.')

                    if is_active_initial:
                        # Se ativo (Aluno, Responsável, URE, Outros), faz o login automático
                        auth_login(request, new_user)
                        return redirect(reverse('users:dashboard'))
                    else:
                        # Se inativo (Professor ou Colaborador), informa sobre a aprovação
                        messages.info(request,
                                      f"Sua conta de {new_user.get_tipo_usuario_display()} foi criada e está pendente de aprovação administrativa. Você será notificado após a ativação.")
                        # 🎯 CORREÇÃO: Adicionado () em get_tipo_usuario_display() para evitar functools.partial
                        return redirect(reverse('users:login'))  # Redireciona para a página de login


            except Exception as e:
                # Se algo falhar (ex: IntegrityError ou falha no save()), o atomic reverte
                messages.error(request,
                               f'Ocorreu um erro inesperado durante o cadastro. Por favor, tente novamente.')
                # Opcional: print(e) para debug

        # Se o form não for válido (inclui erros do clean()), re-renderiza
        else:
            messages.error(request, 'Por favor, corrija os erros indicados no formulário.')

    else:
        # GET request
        form = RegistrationAtomicForm()

    context = {
        'form': form
    }
    return render(request, 'users/register.html', context)


# ==============================================================================
# 2. VISTAS DE PERFIL (MANTIDAS para PÓS-LOGIN)
# ==============================================================================

@login_required
def profile_view(request):
    """
    Vista para apenas VISUALIZAR as informações do perfil.
    """
    try:
        user_profile = request.user.profile
    except Profile.DoesNotExist:
        # Se por algum motivo o profile não foi criado, tenta criá-lo (fallback)
        Profile.objects.get_or_create(user=request.user)
        user_profile = request.user.profile

    context = {
        'user_profile': user_profile,
        'user': request.user
    }
    return render(request, 'users/profile.html', context)


@login_required
def profile_edit(request):
    """
    Vista para EDITAR as informações do CustomUser, do Profile E do Registro Específico.
    """
    # 1. Tenta carregar o Profile
    try:
        profile_instance = request.user.profile
    except Profile.DoesNotExist:
        messages.warning(request, 'Seu perfil está sendo criado. Por favor, tente novamente.')
        return redirect('users:profile')

    # 2. Obtém a classe do Form de Registro e a instância de Registro (RegistroAluno, etc.)
    # Esta chamada agora é mais robusta contra RelatedObjectDoesNotExist (corrigida na auxiliar)
    RegistroFormClass, registro_instance = get_registro_info_for_edit(request.user)
    registro_form = None  # Inicializa o formulário de registro como None

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=profile_instance
        )

        # 3. Processa o Formulário de Registro (se existir)
        if RegistroFormClass and registro_instance:
            registro_form = RegistroFormClass(request.POST, instance=registro_instance)

        # 4. VALIDAÇÃO MÚLTIPLA
        is_registro_valid = (registro_form is None) or registro_form.is_valid()

        if user_form.is_valid() and profile_form.is_valid() and is_registro_valid:

            with transaction.atomic():
                user_form.save()
                profile_form.save()

                # 5. Salva o Formulário de Registro (se existir e for válido)
                if registro_form:
                    registro_form.save()

            messages.success(request, 'Seu perfil foi atualizado com sucesso!')
            # CORREÇÃO NA REDIREÇÃO DE SUCESSO: Garantir o namespace, embora já estivesse correto
            return redirect('users:profile')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')

    else:
        # 6. Carregamento dos Formulários GET
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile_instance)

        # 7. Carrega o Formulário de Registro (se existir)
        if RegistroFormClass and registro_instance:
            registro_form = RegistroFormClass(instance=registro_instance)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        # 8. Adiciona o formulário de registro específico ao contexto
        'registro_form': registro_form
    }

    # CORREÇÃO NA RENDERIZAÇÃO: Usar o template correto, que já estava aqui
    return render(request, 'users/profile_edit.html', context)


class UserPasswordChangeView(PasswordChangeView):
    """
    Vista para alteração de senha.
    """
    # 🎯 CORREÇÃO: Revertido para o nome do template que existe no disco (registration/password_change_form.html),
    # pois o usuário recusou mover o arquivo e o nome 'users/...' causou TemplateDoesNotExist.
    # OBS: O template do Admin PODE ser carregado se 'django.contrib.admin' estiver listado antes de 'users' em settings.py.
    template_name = 'registration/password_change_form.html'  # <--- CORREÇÃO APLICADA AQUI
    success_url = reverse_lazy('users:profile')

    def form_valid(self, form):
        messages.success(self.request, 'Sua senha foi alterada com sucesso!')
        return super().form_valid(form)


# ==============================================================================
# 3. VISTA DA DASHBOARD (ATUALIZADA)
# ==============================================================================

@login_required
def dashboard(request):
    """
    Vista principal após o login. Adiciona o contexto administrativo e de chat.
    """
    context = {}

    # Adiciona o contexto de aprovação se o usuário for Admin/Staff
    context.update(get_pending_users_context(request))

    # 🎯 NOVO: Adiciona a lista de canais com mensagens não lidas
    canais_nao_lidos_list = get_chat_notifications(request.user)
    context['canais_nao_lidos'] = canais_nao_lidos_list

    return render(request, 'users/dashboard.html', context)