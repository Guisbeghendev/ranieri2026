from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.core.files.storage import FileSystemStorage
from django.http import Http404
from django.contrib.auth import login as auth_login
# Removido 'from django.db.models.signals import post_save' (já importado em outro lugar ou não usado diretamente aqui)

# Removidas importações de import-export e processamento manual de JSON
# from tablib import Dataset
# import json
# from io import TextIOWrapper

# Importar modelos e formulários
from .forms import (
    CustomUserCreationForm,
    UserUpdateForm,
    ProfileUpdateForm,
    Step1_EscolhaTipoForm,
    Step2_ProfessorForm,
    Step2_ColaboradorForm,
    Step2_UREForm,
    Step2_AlunoForm,
    Step2_ResponsavelForm,
    Step2_VisitanteForm,
    # Importar os formulários de Update de Registro
    RegistroProfessorUpdateForm,
    RegistroColaboradorUpdateForm,
    RegistroUREUpdateForm,
    RegistroOutrosVisitantesUpdateForm,
    RegistroAlunoUpdateForm,
    RegistroResponsavelUpdateForm,
    # Removido: CustomImportForm
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
# Removido: Importa o Resource
# from .resources import RegistroAlunoResource

# Configura o FileSystemStorage (Mantido para uso em profile_edit)
file_storage = FileSystemStorage()


# ==============================================================================
# FUNÇÕES AUXILIARES DE REGISTRO MANUAL
# ==============================================================================

def get_form_class_by_type(tipo_usuario):
    """Retorna a classe de formulário da Etapa 2 com base no tipo."""
    if tipo_usuario == CustomUserTipo.ALUNO.value:
        return Step2_AlunoForm
    elif tipo_usuario == CustomUserTipo.RESPONSAVEL.value:
        return Step2_ResponsavelForm
    elif tipo_usuario == CustomUserTipo.PROFESSOR.value:
        return Step2_ProfessorForm
    elif tipo_usuario == CustomUserTipo.COLABORADOR.value:
        return Step2_ColaboradorForm
    elif tipo_usuario == CustomUserTipo.URE.value:
        return Step2_UREForm
    elif tipo_usuario == CustomUserTipo.OUTRO_VISITANTE.value:
        return Step2_VisitanteForm
    return None


# FUNÇÃO AUXILIAR ADICIONADA: Mapeia o tipo de usuário para o Form e a Instância de Registro
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


def _create_registro_entity_manual(user, data, tipo_usuario):
    """
    Cria a Entidade de Registro e faz o vínculo NO OBJETO user em memória.
    Retorna o objeto de registro criado/buscado.
    """
    registro = None

    if tipo_usuario == CustomUserTipo.ALUNO.value:
        try:
            # Busca o objeto RegistroAluno pelo PK salvo na sessão na Etapa 2
            registro_pk = data.get('aluno_registro')
            if not registro_pk:
                raise Http404("Erro fatal: PK de Registro de Aluno ausente na sessão.")

            registro = RegistroAluno.objects.get(pk=registro_pk)
            user.registro_aluno = registro
        except RegistroAluno.DoesNotExist:
            raise Http404("Erro fatal: Registro de Aluno não encontrado no banco de dados.")

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
        # CRIAÇÃO: Apenas cria o objeto em memória.
        registro = RegistroResponsavel(
            nome_completo=f"{user.first_name} {user.last_name}"
        )
        # O M2M 'alunos' será setado no Passo 4 (finalizar)
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
# 1. FLUXO DE REGISTRO MANUAL (ETAPAS)
# ==============================================================================
# (As funções de registro step_1 a step_3 não foram modificadas.)

def registration_step_1_tipo(request):
    """
    Etapa 1: Escolha do tipo de usuário (Step1_EscolhaTipoForm).
    Armazena 'tipo_usuario' na sessão.
    """
    dados_cadastro = request.session.get('cadastro_data', {})

    if request.method == 'POST':
        # CAPTURA DIRETA do valor do radio button 'tipo_usuario'
        tipo_usuario_escolhido = request.POST.get('tipo_usuario')

        if tipo_usuario_escolhido:
            # 1. Armazena apenas o tipo e ZERA outros dados para novo fluxo
            request.session['cadastro_data'] = {'tipo_usuario': tipo_usuario_escolhido}

            # 2. Redirecionamento correto para a etapa 2
            return redirect('users:registration_step_2_complemento')
        else:
            # Se POST, mas sem tipo_usuario selecionado
            messages.error(request, "Selecione um tipo de usuário para continuar.")

    # Renderiza o template
    form = Step1_EscolhaTipoForm(initial={'tipo_usuario': dados_cadastro.get('tipo_usuario')})

    return render(request, 'cadastro/step_1_tipo_usuario.html', {'form': form})


def registration_step_2_complemento(request):
    """
    Etapa 2: Validação (Aluno/Responsável) ou Complemento (Prof/Colab/URE/Visitante).
    Armazena dados específicos do registro e/ou PKs de RegistroAluno na sessão.
    """
    dados_cadastro = request.session.get('cadastro_data', None)

    # BLOCO CRÍTICO: Se não houver dados ou o tipo, redireciona.
    if not dados_cadastro or 'tipo_usuario' not in dados_cadastro:
        messages.error(request, "Escolha seu tipo de usuário primeiro.")
        return redirect('users:registration_step_1_tipo')

    tipo_usuario = dados_cadastro['tipo_usuario']
    FormClass = get_form_class_by_type(tipo_usuario)

    # Se a FormClass for nula (tipo inválido), volta para o início.
    if not FormClass:
        messages.error(request, "Tipo de usuário inválido. Recomece o cadastro.")
        return redirect('users:registration_step_1_tipo')

    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            # 1. Salva os dados limpos do formulário na sessão
            dados_cadastro.update(form.cleaned_data)

            # 2. Tratamento especial para Aluno/Responsável (salva PKs)
            if tipo_usuario == CustomUserTipo.ALUNO.value:
                # O RegistroAluno validado existe no form.aluno_registro
                dados_cadastro['aluno_registro'] = form.aluno_registro.pk
            elif tipo_usuario == CustomUserTipo.RESPONSAVEL.value:
                # Salva as PKs dos dependentes encontrados
                dependentes_pks = [aluno.pk for aluno in form.dependentes_encontrados]
                dados_cadastro['dependentes_encontrados_pks'] = dependentes_pks

            request.session['cadastro_data'] = dados_cadastro
            request.session.modified = True

            # Próximo passo: Criação do Usuário
            return redirect('users:registration_step_3_user')
    else:
        form = FormClass(initial=dados_cadastro)

    # Redirecionamento para o template específico de cada wizard na Etapa 2
    template_map = {
        CustomUserTipo.ALUNO.value: 'cadastro/wizard_aluno/step_2_ra.html',
        CustomUserTipo.RESPONSAVEL.value: 'cadastro/wizard_responsavel/step_2_ra_multiplo.html',
        CustomUserTipo.PROFESSOR.value: 'cadastro/wizard_professor/step_2_tipo_prof.html',
        CustomUserTipo.COLABORADOR.value: 'cadastro/wizard_colaborador/step_2_funcao.html',
        CustomUserTipo.URE.value: 'cadastro/wizard_ure/step_2_funcao_livre.html',
        CustomUserTipo.OUTRO_VISITANTE.value: 'cadastro/wizard_visitante/step_2_descricao_livre.html',
    }

    # O template base do passo 2
    template_name = template_map.get(tipo_usuario, 'registration/step2_complemento.html')

    context = {
        'form': form,
        'tipo_usuario_label': CustomUserTipo(tipo_usuario).label
    }
    return render(request, template_name, context)


def registration_step_3_user(request):
    """
    Etapa 3: Criação do CustomUser (email, username, nome_completo, senha) - CustomUserCreationForm.
    Armazena os dados do usuário e a senha hasheada na sessão.
    """
    dados_cadastro = request.session.get('cadastro_data')

    if not dados_cadastro or 'tipo_usuario' not in dados_cadastro:
        messages.error(request, "Por favor, escolha o tipo de usuário antes de prosseguir.")
        return redirect('users:registration_step_1_tipo')

    # Validações extras para alunos/responsaveis se pularam o Passo 2
    if dados_cadastro['tipo_usuario'] == CustomUserTipo.ALUNO.value and 'aluno_registro' not in dados_cadastro:
        messages.error(request, "Validação de RA pendente. Complete o Passo 2.")
        return redirect('users:registration_step_2_complemento')
    if dados_cadastro[
        'tipo_usuario'] == CustomUserTipo.RESPONSAVEL.value and 'dependentes_encontrados_pks' not in dados_cadastro:
        messages.error(request, "Validação de dependentes pendente. Complete o Passo 2.")
        return redirect('users:registration_step_2_complemento')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user_data = form.cleaned_data
            user_temp = form.save(commit=False)  # Não salva, apenas hasheia a senha

            # Salva dados para recriar o usuário no Passo 4 (Finalizar)
            dados_cadastro['user_data'] = {
                'email': user_data['email'],
                'username': user_data['username'],
                'first_name': user_temp.first_name,
                'last_name': user_temp.last_name,
                'password_hash': user_temp.password,
            }

            request.session['cadastro_data'] = dados_cadastro
            request.session.modified = True

            # Redirecionamento para a Etapa 4 (Finalização)
            return redirect('users:registration_finalizar')
    else:
        initial_data = dados_cadastro.get('user_data', {})
        form = CustomUserCreationForm(initial=initial_data)

    # Redirecionamento condicional para templates de Wizard Step 3 (login)
    template_map = {
        CustomUserTipo.ALUNO.value: 'cadastro/wizard_aluno/step_3_login.html',
        CustomUserTipo.RESPONSAVEL.value: 'cadastro/wizard_responsavel/step_3_login.html',
        CustomUserTipo.PROFESSOR.value: 'cadastro/wizard_professor/step_3_login.html',
        CustomUserTipo.COLABORADOR.value: 'cadastro/wizard_colaborador/step_3_login.html',
        CustomUserTipo.URE.value: 'cadastro/wizard_ure/step_3_login.html',
        CustomUserTipo.OUTRO_VISITANTE.value: 'cadastro/wizard_visitante/step_3_login.html',
    }

    # O template base do passo 3
    template_name = template_map.get(dados_cadastro['tipo_usuario'], 'registration/step3_user.html')

    return render(request, template_name, {'form': form})


def registration_finalizar(request):
    """
    Etapa 4: Executa a transação final, salva CustomUser, Registro e Profile em branco, e autentica.
    """
    dados_cadastro = request.session.get('cadastro_data')

    if not dados_cadastro or 'user_data' not in dados_cadastro or 'tipo_usuario' not in dados_cadastro:
        messages.error(request, "O fluxo de cadastro foi interrompido ou está incompleto. Tente novamente.")
        return redirect('users:registration_step_1_tipo')

    # Só executa se ainda não tiver sido salvo (proteção contra refresh)
    if 'salvo_com_sucesso' not in dados_cadastro:

        # O signal post_save será acionado ao salvar new_user e criará o Profile em branco.
        try:
            with transaction.atomic():
                user_data = dados_cadastro['user_data']
                tipo_usuario = dados_cadastro['tipo_usuario']

                # 1. CRIA O OBJETO CustomUser (SEM SALVAR)
                new_user = CustomUser(
                    username=user_data['username'],
                    email=user_data['email'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    tipo_usuario=tipo_usuario,
                    password=user_data['password_hash'],
                )

                # 2. CRIA/BUSCA A ENTIDADE DE REGISTRO E VINCULA (Em Memória)
                registro_entity = _create_registro_entity_manual(new_user, dados_cadastro, tipo_usuario)

                # 3. SALVA AS ENTIDADES DE REGISTRO EM MEMÓRIA
                # Salva Professor, Colaborador, URE, Visitante e Responsável
                # Exclui Aluno (é buscado/existente)
                if registro_entity and tipo_usuario not in [CustomUserTipo.ALUNO.value]:
                    registro_entity.save()

                # 4. SALVA O USUÁRIO (Salva a FK do registro e aciona o signal para criar o Profile, UMA ÚNICA VEZ)
                new_user.save()

                # 5. TRATAMENTO M2M PARA RESPONSÁVEL
                if tipo_usuario == CustomUserTipo.RESPONSAVEL.value:
                    dependentes_pks = dados_cadastro.get('dependentes_encontrados_pks', [])
                    dependentes = RegistroAluno.objects.filter(pk__in=dependentes_pks)
                    # Usa o registro_entity (que já tem PK) para setar a relação M2M
                    registro_entity.alunos.set(dependentes)

                # 6. Finalização e Login
                dados_cadastro['salvo_com_sucesso'] = True
                request.session['cadastro_data'] = dados_cadastro
                auth_login(request, new_user)

                messages.success(request,
                                 f"Sua conta ({new_user.get_tipo_usuario_display()}) foi criada e você foi logado com sucesso. Bem-vindo(a)!")

        except Exception as e:
            # Exibe o erro
            messages.error(request, f"Erro ao finalizar o cadastro: {str(e)}. Tente novamente.")
            # Garante a limpeza da sessão em caso de erro fatal
            if 'cadastro_data' in request.session:
                del request.session['cadastro_data']
            return redirect('users:registration_step_1_tipo')

    # Bloco para limpeza da sessão e exibição da tela de sucesso
    if 'salvo_com_sucesso' in dados_cadastro:
        if 'cadastro_data' in request.session:
            del request.session['cadastro_data']

        # Redireciona para o template 'sucesso.html'
        return render(request, 'cadastro/sucesso.html')

    # Fallback
    return redirect('users:dashboard')


# ==============================================================================
# 2. VISTAS DE PERFIL (Mantidas para PÓS-LOGIN)
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


# ==============================================================================
# 4. VISTA DE IMPORTAÇÃO CUSTOMIZADA DE ALUNOS (REMOVIDA)
# ==============================================================================

# A view 'importacao_aluno_view' e a auxiliar 'render_import_form' foram removidas,
# pois a importação de dados via JSON foi realocada para o fluxo
# do Admin/JSONUploadAdmin no users/admin.py.