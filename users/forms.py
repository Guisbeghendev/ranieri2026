from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q
from django.contrib.auth.models import Group as AuthGroup # NOVO IMPORT

from .models import (
    CustomUser,
    CustomUserTipo,
    TipoProfessor,
    FuncaoColaborador,
    RegistroProfessor,
    RegistroColaborador,
    RegistroAluno,
    RegistroResponsavel,
    RegistroURE,
    RegistroOutrosVisitantes,
    Profile,
    Turma,
    Grupo # NOVO IMPORT
)
from django.utils.translation import gettext_lazy as _


# ==============================================================================
# 1. Formulários de Autenticação Padrão (ADMIN/BACKEND)
# ==============================================================================

class CustomUserCreationForm(UserCreationForm):
    """
    Formulário base para criação de novos usuários (Mantido para uso em Admin ou Testes).
    """
    nome_completo = forms.CharField(max_length=255, required=True, label="Nome Completo")
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = CustomUser
        # Campos básicos de login e identificação
        fields = ('username', 'email', 'nome_completo')
        field_classes = {'username': forms.CharField}

    def save(self, commit=True):
        user = super().save(commit=False)
        partes_nome = self.cleaned_data['nome_completo'].split(' ', 1)
        user.first_name = partes_nome[0]
        user.last_name = partes_nome[1] if len(partes_nome) > 1 else ''

        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Formulário para edição de usuários (Admin/Gestão)."""

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_fotografo', 'is_fotografo_master')


# ==============================================================================
# 2. Formulário de Cadastro Atômico (PÁGINA ÚNICA) - NOVO
# ==============================================================================

class RegistrationAtomicForm(forms.Form):
    """
    Formulário único para cadastro, combinando login, tipo de usuário e campos de registro.
    A validação é feita de forma condicional no método clean().
    """

    # --- 2.1. Campos Comuns (CustomUser) ---

    tipo_usuario = forms.ChoiceField(
        choices=[
            (CustomUserTipo.ALUNO.value, CustomUserTipo.ALUNO.label),
            (CustomUserTipo.PROFESSOR.value, CustomUserTipo.PROFESSOR.label),
            (CustomUserTipo.COLABORADOR.value, CustomUserTipo.COLABORADOR.label),
            (CustomUserTipo.RESPONSAVEL.value, CustomUserTipo.RESPONSAVEL.label),
            (CustomUserTipo.URE.value, CustomUserTipo.URE.label),
            (CustomUserTipo.OUTRO_VISITANTE.value, CustomUserTipo.OUTRO_VISITANTE.label),
        ],
        label="Eu sou:",
        widget=forms.RadioSelect(attrs={'class': 'tipo-usuario-select'}),
        required=True
    )

    nome_completo = forms.CharField(max_length=255, required=True, label="Nome:")
    username = forms.CharField(max_length=150, required=True, label="Username (Login)")
    email = forms.EmailField(required=True, label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Senha")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirmar Senha")

    # --- 2.2. Campos Específicos (Registro*) - TODOS required=False inicialmente ---

    # ALUNO / RESPONSÁVEL (Validação por RA)
    # TRILHA ALUNO: Label estática. A label do RESPONSÁVEL será aplicada em __init__ dinamicamente.
    ra_numero = forms.CharField(max_length=20, required=False, label="RA - somente números")
    ra_digito_verificador = forms.CharField(max_length=2, required=False, label="Dígito")

    # PROFESSOR
    tipo_professor = forms.ChoiceField(
        choices=TipoProfessor.choices,
        label="Seu Papel como Professor",
        required=False,
        # CORREÇÃO: Adicionar opção vazia e widget customizado para evitar falha do ChoiceField
        initial='',
        widget=forms.Select(choices=[('', '---------')] + list(TipoProfessor.choices))
    )

    # COLABORADOR
    funcao_colaborador = forms.ChoiceField(
        choices=FuncaoColaborador.choices,
        label="Sua Função como Colaborador",
        required=False,
        # CORREÇÃO: Adicionar opção vazia e widget customizado para evitar falha do ChoiceField
        initial='',
        widget=forms.Select(choices=[('', '---------')] + list(FuncaoColaborador.choices))
    )

    # URE
    funcao_ure = forms.CharField(max_length=100, required=False, label="Sua Função ou Cargo na URE")

    # OUTRO VISITANTE
    descricao_vinculo = forms.CharField(max_length=255, required=False, label="Descreva brevemente seu vínculo")

    def __init__(self, *args, **kwargs):
        """
        Ajusta as labels dos campos RA/Dígito dinamicamente se o formulário for submetido
        (is_bound) e o tipo de usuário for Responsável (TRILHA RESPONSÁVEL).
        """
        super().__init__(*args, **kwargs)

        # Se o formulário foi submetido, verificamos o tipo de usuário para aplicar a label correta.
        if self.is_bound:
            tipo_usuario = self.data.get('tipo_usuario')

            if tipo_usuario == CustomUserTipo.RESPONSAVEL.value:
                # TRILHA RESPONSÁVEL: Aplica a label longa
                self.fields['ra_numero'].label = "RA de um aluno pelo qual é responsável - somente números"
                # ra_digito_verificador já é 'Dígito'

    def clean(self):
        """
        Executa a validação condicional com base no tipo_usuario.
        Se um RA válido for encontrado, o objeto RegistroAluno é salvo em cleaned_data.
        """
        cleaned_data = super().clean()
        tipo_usuario = cleaned_data.get('tipo_usuario')

        # 1. Validação de Senhas
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            # Uso de self.add_error para evitar que a validação falhe imediatamente
            self.add_error('password_confirm', ValidationError("As senhas não coincidem.", code='password_mismatch'))

        # 2. Validação de Usuário Único (Manual, pois não é ModelForm)
        username = cleaned_data.get('username')
        email = cleaned_data.get('email')

        if username and CustomUser.objects.filter(username=username).exists():
            self.add_error('username', ValidationError("Este username já está em uso.", code='username_exists'))

        if email and CustomUser.objects.filter(email=email).exists():
            self.add_error('email', ValidationError("Este email já está em uso.", code='email_exists'))

        # 3. Validação Condicional do Registro

        # Objeto auxiliar para armazenar os registros encontrados ou criados temporariamente.
        registros_encontrados = {}
        nome = cleaned_data.get("nome_completo")  # Armazenado para uso nas buscas abaixo

        # --- A. ALUNO (Requer RA) ---
        if tipo_usuario == CustomUserTipo.ALUNO.value:
            ra_num = cleaned_data.get("ra_numero")
            ra_dig = cleaned_data.get("ra_digito_verificador")

            if not ra_num or not ra_dig:
                self.add_error('ra_numero', ValidationError("O RA (Número e Dígito) é obrigatório para alunos."))

            elif ra_num and ra_dig:
                try:
                    aluno_registro = RegistroAluno.objects.get(
                        ra_numero=ra_num,
                        ra_digito_verificador=ra_dig
                    )

                    # Checa se o RegistroAluno já está vinculado a um CustomUser
                    if hasattr(aluno_registro, 'usuario') and aluno_registro.usuario:
                        self.add_error(
                            'ra_numero',
                            ValidationError("Este RA já está vinculado a um usuário ativo no sistema.",
                                            code='ra_already_linked')
                        )
                    else:
                        registros_encontrados['aluno_registro'] = aluno_registro

                except RegistroAluno.DoesNotExist:
                    self.add_error(
                        'ra_numero',
                        ValidationError(
                            "RA não encontrado. Seu registro oficial ainda não está disponível no sistema.",
                            code='ra_not_found'
                        )
                    )


        # --- B. RESPONSÁVEL (Requer pelo menos um RA válido) ---
        elif tipo_usuario == CustomUserTipo.RESPONSAVEL.value:
            dependentes_encontrados = []

            # Validação do primeiro RA (obrigatório para Responsáveis)
            ra1_num = cleaned_data.get("ra_numero")
            ra1_dig = cleaned_data.get("ra_digito_verificador")

            if not ra1_num or not ra1_dig:
                self.add_error('ra_numero',
                               ValidationError("O RA de pelo menos um dependente é obrigatório para responsáveis."))

            elif ra1_num and ra1_dig:
                try:
                    aluno = RegistroAluno.objects.get(ra_numero=ra1_num, ra_digito_verificador=ra1_dig)
                    dependentes_encontrados.append(aluno)
                    registros_encontrados['dependentes'] = dependentes_encontrados
                except RegistroAluno.DoesNotExist:
                    self.add_error('ra_numero',
                                   ValidationError(
                                       "O RA do Dependente Obrigatório não foi encontrado no sistema de registros.",
                                       code='ra_not_found_required'
                                   )
                                   )

            # NOTE: Neste formulário atômico simplificado, optamos por coletar apenas um RA
            # para o Responsável, para manter a página única mais limpa.


        # --- C. PROFESSOR (Requer tipo_professor e busca por nome) ---
        elif tipo_usuario == CustomUserTipo.PROFESSOR.value:
            tipo = cleaned_data.get("tipo_professor")

            if not tipo:
                self.add_error('tipo_professor', ValidationError("O papel do Professor é obrigatório."))

            # Executa a busca somente se o tipo estiver preenchido (para evitar erros duplos)
            if nome and tipo:
                try:
                    professor_registro = RegistroProfessor.objects.get(
                        nome_completo__iexact=nome  # Busca exata, ignorando caixa alta/baixa
                    )

                    # 1. Checa se o RegistroProfessor já está vinculado
                    if hasattr(professor_registro, 'usuario') and professor_registro.usuario:
                        self.add_error(
                            'nome_completo',
                            ValidationError("Este nome já está vinculado a um usuário ativo no sistema.",
                                            code='registro_already_linked')
                        )
                    else:
                        # 2. Armazena o registro encontrado para ser vinculado na view
                        registros_encontrados['professor_registro'] = professor_registro

                except RegistroProfessor.DoesNotExist:
                    self.add_error(
                        'nome_completo',
                        ValidationError(
                            "Nome não encontrado no registro de Professores. Verifique a digitação ou contate a administração.",
                            code='registro_not_found'
                        )
                    )
                except RegistroProfessor.MultipleObjectsReturned:
                    # Risco assumido: Colisão de nomes. Ação imediata é bloquear o cadastro.
                    self.add_error(
                        'nome_completo',
                        ValidationError(
                            "Colisão de nomes. Mais de um Professor encontrado. Contate a administração para resolver a duplicidade.",
                            code='name_collision'
                        )
                    )


        # --- D. COLABORADOR (Requer funcao_colaborador) ---
        elif tipo_usuario == CustomUserTipo.COLABORADOR.value:
            funcao = cleaned_data.get("funcao_colaborador")
            if not funcao:
                self.add_error('funcao_colaborador', ValidationError("A função do Colaborador é obrigatória."))


        # --- E. URE (Requer funcao_ure) ---
        elif tipo_usuario == CustomUserTipo.URE.value:
            funcao = cleaned_data.get("funcao_ure")
            if not funcao:
                self.add_error('funcao_ure', ValidationError("A função na URE é obrigatória."))

        # --- F. OUTRO VISITANTE (Requer descricao_vinculo) ---
        elif tipo_usuario == CustomUserTipo.OUTRO_VISITANTE.value:
            descricao = cleaned_data.get("descricao_vinculo")
            if not descricao:
                self.add_error('descricao_vinculo', ValidationError("A descrição do vínculo é obrigatória."))

        # Salva registros encontrados (ou temporariamente armazenados) para uso na View
        cleaned_data['registros_a_vincular'] = registros_encontrados

        return cleaned_data


# ==============================================================================
# 3. Formulários de Atualização de Perfil (Pós-Login) - MANTIDOS
# ==============================================================================

class UserUpdateForm(forms.ModelForm):
    """Formulário para atualização dos dados básicos do CustomUser no perfil."""

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name']
        labels = {
            'first_name': 'Primeiro Nome',
            'last_name': 'Sobrenome',
            'username': 'Username (Login)',
            'email': 'Email',
        }


class ProfileUpdateForm(forms.ModelForm):
    """
    Formulário para atualização dos dados complementares do Profile (Pós-Login).
    """

    class Meta:
        model = Profile
        fields = [
            'data_nascimento',
            'whatsapp',
            'outro_contato',
            'endereco',
            'cidade',
            'estado',
            'foto_perfil',
            'bio',
        ]
        labels = {
            'data_nascimento': "Data de Nascimento",
            'whatsapp': "Número WhatsApp",
            'outro_contato': "Outro Contato (Ex: Telefone Fixo)",
            'endereco': "Endereço Completo",
            'cidade': "Cidade",
            'estado': "Estado (UF)",
            'foto_perfil': "Foto de Perfil",
            'bio': "Mini-biografia ou Status",
        }
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
        }


# ==============================================================================
# 4. Formulários de Atualização de Registro (Pós-Login) - MANTIDOS
# ==============================================================================

class RegistroProfessorUpdateForm(forms.ModelForm):
    """Atualiza dados específicos de RegistroProfessor."""

    class Meta:
        model = RegistroProfessor
        fields = ['tipo_professor']
        labels = {
            'tipo_professor': 'Tipo de Professor',
        }


class RegistroColaboradorUpdateForm(forms.ModelForm):
    """Atualiza dados específicos de RegistroColaborador."""

    class Meta:
        model = RegistroColaborador
        fields = ['funcao', 'matricula_ou_identificador']
        labels = {
            'funcao': 'Função no Colégio',
            'matricula_ou_identificador': 'Matrícula ou Identificador',
        }


class RegistroUREUpdateForm(forms.ModelForm):
    """Atualiza dados específicos de RegistroURE."""

    class Meta:
        model = RegistroURE
        fields = ['funcao']
        labels = {
            'funcao': 'Função ou Cargo na URE',
        }


class RegistroOutrosVisitantesUpdateForm(forms.ModelForm):
    """Atualiza dados específicos de RegistroOutrosVisitantes."""

    class Meta:
        model = RegistroOutrosVisitantes
        fields = ['descricao']
        labels = {
            'descricao': 'Descrição do Vínculo',
        }


class RegistroAlunoUpdateForm(forms.ModelForm):
    """Atualiza dados específicos de RegistroAluno."""

    class Meta:
        model = RegistroAluno
        fields = ['nome_completo']
        labels = {
            'nome_completo': 'Nome Completo Registrado (na ficha)',
        }


class RegistroResponsavelUpdateForm(forms.ModelForm):
    """Atualiza dados específicos de RegistroResponsavel."""

    class Meta:
        model = RegistroResponsavel
        fields = ['nome_completo']
        labels = {
            'nome_completo': 'Nome Completo do Responsável',
        }


# ==============================================================================
# 5. Formulário Customizado para Admin (GrupoCreationForm) - NOVO
# ==============================================================================

def validate_unique_auth_group_name(value):
    """Valida se o nome do grupo do Django já existe."""
    if AuthGroup.objects.filter(name=value).exists():
        raise ValidationError(_('Um grupo com este nome já existe. Por favor, escolha outro.'))

class GrupoCreationForm(forms.ModelForm):
    """
    Formulário usado na view de criação de GrupoAdmin.
    Adiciona o campo virtual 'nome_do_grupo' e exclui 'auth_group'.
    """
    nome_do_grupo = forms.CharField(
        label=_("Nome Único do Grupo (Ex: 3A_2025 ou free)"),
        max_length=80,
        help_text=_("Este nome será a chave de permissão (AuthGroup.name) e deve ser único."),
        required=True,
        validators=[validate_unique_auth_group_name]
    )

    class Meta:
        model = Grupo
        # Exclui auth_group, que será preenchido no save_model, e usa campos do modelo.
        # Os campos explícitos em fields garantem a ordem correta no formulário
        fields = ('nome_do_grupo', 'tipo', 'descricao', 'ativo')
        exclude = ('auth_group',)