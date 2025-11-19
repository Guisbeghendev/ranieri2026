# users/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q
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
    Turma
)
from django.utils.translation import gettext_lazy as _


# ==============================================================================
# 1. Formulários de Autenticação Padrão (AGORA, USADO APENAS PARA ADMIN/BACKEND)
# ==============================================================================

class CustomUserCreationForm(UserCreationForm):
    """
    Formulário base para criação de novos usuários (Mantido para uso em Admin ou Testes).
    A lógica de criação de cadastro principal será feita por um novo formulário composto.
    """
    # Mantido o mapeamento básico para evitar quebras no Django Admin.
    nome_completo = forms.CharField(max_length=255, required=True, label="Nome Completo")
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = CustomUser
        # Campos básicos de login e identificação
        fields = ('username', 'email', 'nome_completo')
        field_classes = {'username': forms.CharField}

    # MÉTODO SAVE REESCRITO: Remove a lógica complexa de commit=False e skip_link_validation do Wizard
    def save(self, commit=True):
        user = super().save(commit=False)

        # Mapeia nome_completo para os campos padrão do AbstractUser
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
# 2. Formulários do Wizard (Step 1, Step 2) - REMOVIDOS
# ==============================================================================

# O Step1_EscolhaTipoForm (Router) FOI REMOVIDO.
# As classes Step2_* (Step2_AlunoForm, Step2_ResponsavelForm, etc.) FORAM REMOVIDAS.
# Toda a lógica de clean() de múltiplos RAs e validação de vínculo foi eliminada.

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