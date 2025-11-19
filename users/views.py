# users/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.core.files.storage import FileSystemStorage
from django.http import Http404
from django.contrib.auth import login as auth_login

# Importar modelos e formulários
from .forms import (
    CustomUserCreationForm,
    UserUpdateForm,
    ProfileUpdateForm,
    # Formulários do Wizard REMOVIDOS
    # Step1_EscolhaTipoForm, Step2_ProfessorForm, etc.
    # Importar os formulários de Update de Registro (Mantidos para profile_edit)
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
# FUNÇÕES AUXILIARES DE REGISTRO MANUAL (APENAS AS ESSENCIAIS)
# ==============================================================================

# FUNÇÃO REMOVIDA: get_form_class_by_type (Não é mais necessária sem Etapa 2 do Wizard)
# def get_form_class_by_type(tipo_usuario): ...

# FUNÇÃO AUXILIAR MANTIDA: Mapeia o tipo de usuário para o Form e a Instância de Registro
def get_registro_info_for_edit(user):
    """Retorna a classe de formulário de atualização e a instância de registro."""
    tipo = user.tipo_usuario
    form_class = None
    registro_instance = None

    # Mapeamento do Tipo de Usuário para o Form de Update e o Objeto de Registro
    if tipo == CustomUserTipo.ALUNO.value and user.registro_aluno:
        form_class = RegistroAlunoUpdateForm
        registro_instance = user.registro_aluno
    elif tipo == CustomUserTipo.PROFESSOR.value and user.registro_professor:
        form_class = RegistroProfessorUpdateForm
        registro_instance = user.registro_professor
    elif tipo == CustomUserTipo.COLABORADOR.value and user.registro_colaborador:
        form_class = RegistroColaboradorUpdateForm
        registro_instance = user.registro_colaborador
    elif tipo == CustomUserTipo.RESPONSAVEL.value and user.registro_responsavel:
        form_class = RegistroResponsavelUpdateForm
        registro_instance = user.registro_responsavel
    elif tipo == CustomUserTipo.URE.value and user.registro_ure:
        form_class = RegistroUREUpdateForm
        registro_instance = user.registro_ure
    elif tipo == CustomUserTipo.OUTRO_VISITANTE.value and user.registro_visitante:
        form_class = RegistroOutrosVisitantesUpdateForm
        registro_instance = user.registro_visitante

    return form_class, registro_instance


# FUNÇÃO AUXILIAR MANTIDA: _create_registro_entity_manual (Essencial para criar o registro no save final, será adaptada na nova view)
def _create_registro_entity_manual(user, data, tipo_usuario):
    """
    Cria a Entidade de Registro e faz o vínculo NO OBJETO user em memória.
    Retorna o objeto de registro criado/buscado.
    """
    registro = None

    if tipo_usuario == CustomUserTipo.ALUNO.value:
        try:
            # Busca o objeto RegistroAluno pelo PK (Agora 'data' virá do POST ÚNICO)
            # ATENÇÃO: É NECESSÁRIO MUDAR A LÓGICA DE BUSCA DO RA NA NOVA VIEW DE CADASTRO
            # POR ENQUANTO, MANTEMOS A BUSCA POR PK, ASSUMIMOS QUE O NOVO FORMULARIO FORNECE.
            registro_pk = data.get('aluno_registro')
            if not registro_pk:
                # Mudança: Na nova estratégia, o form deve validar e fornecer o objeto RegistroAluno
                # Usaremos o PK temporariamente, mas esta função será revista na nova implementação.
                # AQUI, SIMULAMOS QUE O FORMULARIO ATOMICO JÁ VALIDOU O PK
                raise Http404("Erro: PK de Registro de Aluno ausente. Nova view deve fornecer.")

            registro = RegistroAluno.objects.get(pk=registro_pk)
            user.registro_aluno = registro
        except RegistroAluno.DoesNotExist:
            raise Http404("Erro: Registro de Aluno não encontrado no banco de dados.")

    elif tipo_usuario == CustomUserTipo.PROFESSOR.value:
        registro = RegistroProfessor(
            nome_completo=f"{user.first_name} {user.last_name}",
            tipo_professor=data.get('tipo_professor')
        )
        user.registro_professor = registro

    elif tipo_usuario == CustomUserTipo.COLABORADOR.value:
        registro = RegistroColaborador(
            nome_completo=f"{user.first_name} {user.last_name}",
            funcao=data.get('funcao_colaborador')
        )
        user.registro_colaborador = registro

    elif tipo_usuario == CustomUserTipo.RESPONSAVEL.value:
        registro = RegistroResponsavel(
            nome_completo=f"{user.first_name} {user.last_name}"
        )
        user.registro_responsavel = registro

    elif tipo_usuario == CustomUserTipo.URE.value:
        registro = RegistroURE(
            nome_completo=f"{user.first_name} {user.last_name}",
            funcao=data.get('funcao_ure')
        )
        user.registro_ure = registro

    elif tipo_usuario == CustomUserTipo.OUTRO_VISITANTE.value:
        registro = RegistroOutrosVisitantes(
            nome_completo=f"{user.first_name} {user.last_name}",
            descricao=data.get('descricao_vinculo', 'Não informado')
        )
        user.registro_visitante = registro

    return registro


# ==============================================================================
# 1. FLUXO DE REGISTRO MANUAL (ETAPAS) - REMOVIDO/SUBSTITUÍDO
# ==============================================================================

# TODAS AS VIEWS DE WIZARD FORAM REMOVIDAS:
# registration_step_1_tipo -> REMOVIDA
# registration_step_2_complemento -> REMOVIDA
# registration_step_3_user -> REMOVIDA
# registration_finalizar -> REMOVIDA
#
# A NOVA VIEW DE CADASTRO SERÁ CRIADA AQUI NO PRÓXIMO PASSO DO PROJETO.

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

    return render(request, 'users/profile_edit.html', context)


class UserPasswordChangeView(PasswordChangeView):
    """
    Vista para alteração de senha.
    """
    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('users:profile')

    def form_valid(self, form):
        messages.success(self.request, 'Sua senha foi alterada com sucesso!')
        return super().form_valid(form)


# ==============================================================================
# 3. VISTA DA DASHBOARD
# ==============================================================================

@login_required
def dashboard(request):
    """
    Vista principal após o login.
    """
    context = {}
    return render(request, 'users/dashboard.html', context)