from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.db.models import Q # Import Q para consultas complexas
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
    Profile
)


# ==============================================================================
# 1. Formulários de Autenticação Padrão (Usado no Step 3 de TODOS os Wizards)
# ==============================================================================

class CustomUserCreationForm(UserCreationForm):
    """
    Formulário para a criação de novos usuários (Usado em Step 3).
    Coleta dados básicos de login (username, senha, email) e nome completo.
    """
    nome_completo = forms.CharField(max_length=255, required=True, label="Nome Completo")
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = CustomUser
        # Campos básicos de login e identificação
        fields = ('username', 'email', 'nome_completo')
        field_classes = {'username': forms.CharField}

    def save(self, commit=True):
        """
        Sobrescreve save para mapear 'nome_completo' para 'first_name'/'last_name'.
        """
        user = super().save(commit=False)

        # Mapeia nome_completo para os campos padrão do AbstractUser
        partes_nome = self.cleaned_data['nome_completo'].split(' ', 1)
        user.first_name = partes_nome[0]
        user.last_name = partes_nome[1] if len(partes_nome) > 1 else ''

        # O 'tipo_usuario' e o vínculo de registro serão definidos na view do Wizard
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Formulário para edição de usuários (Admin/Gestão)."""
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_fotografo', 'is_fotografo_master')


# ==============================================================================
# 2. Formulários do Wizard - Step 1 (Router)
# ==============================================================================

class Step1_EscolhaTipoForm(forms.Form):
    """
    Step 1: O usuário escolhe o tipo principal de identidade para iniciar a trilha.
    """
    # Excluímos 'ADMIN' pois este é um papel de gestão.
    choices = [
        (CustomUserTipo.ALUNO.value, CustomUserTipo.ALUNO.label),
        (CustomUserTipo.PROFESSOR.value, CustomUserTipo.PROFESSOR.label),
        (CustomUserTipo.COLABORADOR.value, CustomUserTipo.COLABORADOR.label),
        (CustomUserTipo.RESPONSAVEL.value, CustomUserTipo.RESPONSAVEL.label),
        (CustomUserTipo.URE.value, CustomUserTipo.URE.label),
        (CustomUserTipo.OUTRO_VISITANTE.value, CustomUserTipo.OUTRO_VISITANTE.label),
    ]

    tipo_usuario = forms.ChoiceField(
        choices=choices,
        label="Eu sou:",
        widget=forms.RadioSelect
    )


# ==============================================================================
# 3. Formulários do Wizard - Step 2 (Validação e Coleta Específica)
# ==============================================================================

class Step2_AlunoForm(forms.Form):
    """
    Step 2 - Aluno: Validação obrigatória do RA e verificação de vínculo.
    """
    ra_numero = forms.CharField(
        max_length=20,
        required=True,
        label="RA (Registro do Aluno) - Número"
    )
    ra_digito_verificador = forms.CharField(
        max_length=2,
        required=True,
        label="RA - Dígito Verificador"
    )

    def clean(self):
        """Valida se o RA existe e se já não está vinculado a um CustomUser."""
        cleaned_data = super().clean()
        ra_numero = cleaned_data.get("ra_numero")
        ra_digito_verificador = cleaned_data.get("ra_digito_verificador")

        if ra_numero and ra_digito_verificador:
            try:
                # Procura por qualquer RegistroAluno que corresponda ao RA
                aluno_registro = RegistroAluno.objects.get(
                    ra_numero=ra_numero,
                    ra_digito_verificador=ra_digito_verificador
                )

                # Verifica se existe um CustomUser já vinculado
                if hasattr(aluno_registro, 'usuario') and aluno_registro.usuario is not None:
                    raise ValidationError(
                        "Este RA já está vinculado a um usuário ativo no sistema.",
                        code='ra_already_linked'
                    )

                # Salva o objeto RegistroAluno no form para ser usado na View de criação do CustomUser (Step 3)
                self.aluno_registro = aluno_registro

            except RegistroAluno.DoesNotExist:
                raise ValidationError(
                    "RA não encontrado. Seu registro oficial ainda não está disponível no sistema.",
                    code='ra_not_found'
                )
        return cleaned_data


class Step2_ResponsavelForm(forms.Form):
    """
    Step 2 - Responsável: Requer pelo menos um RA válido de dependente.
    """
    ra_numero_1 = forms.CharField(
        max_length=20,
        required=True,
        label="RA do Aluno Dependente (Obrigatório)"
    )
    ra_digito_verificador_1 = forms.CharField(
        max_length=2,
        required=True,
        label="Dígito Verificador (Obrigatório)"
    )

    # Campos opcionais para múltiplos dependentes
    ra_numero_2 = forms.CharField(max_length=20, required=False, label="RA do 2º Dependente")
    ra_digito_verificador_2 = forms.CharField(max_length=2, required=False, label="Dígito do 2º Dependente")
    ra_numero_3 = forms.CharField(max_length=20, required=False, label="RA do 3º Dependente")
    ra_digito_verificador_3 = forms.CharField(max_length=2, required=False, label="Dígito do 3º Dependente")

    def clean(self):
        """Valida e coleta os RAs válidos, garantindo que pelo menos um exista."""
        cleaned_data = super().clean()

        dependentes_encontrados = []
        ra1_num = cleaned_data.get("ra_numero_1")
        ra1_dig = cleaned_data.get("ra_digito_verificador_1")

        # 1. Validar o primeiro RA (obrigatório)
        if ra1_num and ra1_dig:
            try:
                aluno1 = RegistroAluno.objects.get(ra_numero=ra1_num, ra_digito_verificador=ra1_dig)
                # Verifica se o aluno já está vinculado a outro Responsável (opcional, mas bom para evitar duplicidade)
                # Note: Um Responsável PODE ter múltiplos registros, mas um aluno só deve ter um Responsável 'Master'
                # Por simplicidade, faremos a verificação de vínculo na View de criação.
                dependentes_encontrados.append(aluno1)
            except RegistroAluno.DoesNotExist:
                raise ValidationError(
                    "O RA do Aluno Dependente Obrigatório não foi encontrado no sistema de registros.",
                    code='ra_not_found_required'
                )
        else:
            # Não deve ocorrer se ambos são required=True, mas é um fallback
            raise ValidationError("O preenchimento do primeiro RA é obrigatório para responsáveis.")

        # 2. Validar RAs opcionais
        for i in range(2, 4):
            ra_num = cleaned_data.get(f"ra_numero_{i}")
            ra_dig = cleaned_data.get(f"ra_digito_verificador_{i}")

            if ra_num and ra_dig:
                try:
                    aluno = RegistroAluno.objects.get(ra_numero=ra_num, ra_digito_verificador=ra_dig)
                    if aluno not in dependentes_encontrados:
                        dependentes_encontrados.append(aluno)
                except RegistroAluno.DoesNotExist:
                    # RAs opcionais não precisam levantar ValidationError, apenas são ignorados
                    pass

        # 3. Salva a lista de objetos RegistroAluno no form (para uso na View)
        self.dependentes_encontrados = dependentes_encontrados

        return cleaned_data


class Step2_ProfessorForm(forms.Form):
    """
    Step 2 - Professor: Coleta o tipo específico de Professor.
    """
    tipo_professor = forms.ChoiceField(
        choices=TipoProfessor.choices,
        label="Qual é o seu papel como Professor?",
        required=True
    )

    def clean_tipo_professor(self):
        """Impede a seleção de 'OUTROS' se a regra for mais restritiva."""
        tipo = self.cleaned_data['tipo_professor']
        if tipo == TipoProfessor.OUTROS:
            # Adiciona uma mensagem de aviso/restrição se necessário, mas permite por enquanto.
            pass
        return tipo


class Step2_ColaboradorForm(forms.Form):
    """
    Step 2 - Colaborador: Coleta a função específica do Colaborador.
    """
    funcao_colaborador = forms.ChoiceField(
        choices=FuncaoColaborador.choices,
        label="Qual é a sua função como Colaborador?",
        required=True
    )


class Step2_UREForm(forms.Form):
    """
    Step 2 - URE: Informa a função específica (campo de texto livre).
    """
    funcao_ure = forms.CharField(
        max_length=100,
        required=True,
        label="Qual é a sua função ou cargo na URE?"
    )


class Step2_VisitanteForm(forms.Form):
    """
    Step 2 - Outro Visitante: Informa o vínculo ou descrição (campo de texto livre).
    """
    descricao_vinculo = forms.CharField(
        max_length=255,
        required=True,
        label="Descreva brevemente seu vínculo ou interesse no colégio"
    )

# ==============================================================================
# 4. Formulários de Atualização de Perfil (Pós-Login)
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
    Alinhado com o models.py, usando 'endereco' como campo único de texto.
    """
    class Meta:
        model = Profile
        fields = [
            'data_nascimento',
            'whatsapp',
            'outro_contato',
            'endereco', # Campo 'endereco' como único (TextField)
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
# 5. Formulários de Atualização de Registro (Pós-Login) - ADICIONADO
# ==============================================================================

class RegistroProfessorUpdateForm(forms.ModelForm):
    """Atualiza dados específicos de RegistroProfessor."""
    class Meta:
        model = RegistroProfessor
        # Excluindo 'nome_completo' pois deve ser editado pelo UserUpdateForm (first/last name)
        # e 'turmas' que é ManyToMany, geralmente editado em tela separada ou admin.
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
        # Alunos geralmente não editam RA ou Turma após o registro.
        # Adicionando nome completo (se a view for permitir)
        fields = ['nome_completo']
        labels = {
            'nome_completo': 'Nome Completo Registrado (na ficha)',
        }


class RegistroResponsavelUpdateForm(forms.ModelForm):
    """Atualiza dados específicos de RegistroResponsavel."""
    # O campo 'alunos' (ManyToManyField) é complexo e deve ser editado à parte.
    # Não há campos simples para edição, mas a classe é criada para ser base.
    class Meta:
        model = RegistroResponsavel
        fields = ['nome_completo']
        labels = {
            'nome_completo': 'Nome Completo do Responsável',
        }