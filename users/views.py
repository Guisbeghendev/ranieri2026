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


# A função auxiliar _create_registro_entity_manual FOI REMOVIDA,
# pois sua lógica foi absorvida pela nova view registration_create.


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

            # Garantimos que a criação/vínculo do Registro e do CustomUser seja atômica
            try:
                with transaction.atomic():
                    registro_obj = None

                    # 1. CRIAÇÃO OU VÍNCULO DA ENTIDADE DE REGISTRO

                    if tipo_usuario == CustomUserTipo.ALUNO.value:
                        # O form.clean já buscou e validou o objeto RegistroAluno
                        registro_obj = registros_a_vincular['aluno_registro']

                    elif tipo_usuario == CustomUserTipo.PROFESSOR.value:
                        # Cria novo RegistroProfessor
                        registro_obj = RegistroProfessor.objects.create(
                            nome_completo=nome_completo,
                            tipo_professor=data['tipo_professor']
                        )

                    elif tipo_usuario == CustomUserTipo.COLABORADOR.value:
                        # Cria novo RegistroColaborador
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
                        last_name=last_name
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
                    auth_login(request, new_user)  # Faz o login automático
                    return redirect(reverse('users:dashboard'))

            except Exception as e:
                # Se algo falhar (ex: IntegrityError ou falha no save()), o atomic reverte
                messages.error(request,
                               f'Ocorreu um erro inesperado durante o cadastro. Por favor, tente novamente. Detalhe: {e}')

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