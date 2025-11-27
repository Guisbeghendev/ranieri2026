from django.contrib import admin
import json
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db import transaction, connection
from django.http import HttpResponseRedirect
from django.db.utils import IntegrityError
from django.contrib.auth.models import Group as AuthGroup
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.admin.options import flatten_fieldsets
from django.shortcuts import render
from django.urls import reverse
from django.contrib.admin import helpers

# Importa todos os modelos necessários
from .models import (
    CustomUser, Profile, RegistroAluno, Turma, Grupo, MembroGrupo, JSONUpload,
    RegistroProfessor, RegistroColaborador, RegistroResponsavel, RegistroURE,
    RegistroOutrosVisitantes, CustomUserTipo
)

User = get_user_model()


# ==============================================================================
# FORMULÁRIOS DE APOIO
# ==============================================================================

class GrupoSelectForm(forms.Form):
    """Formulário para selecionar o Grupo de Audiência para a Ação em Massa."""
    grupo = forms.ModelChoiceField(
        queryset=Grupo.objects.all(),
        label=_("Selecione o Grupo de Audiência"),
        required=True
    )


class CustomUserChangeForm(forms.ModelForm):
    """Formulário para edição individual de CustomUser, incluindo seleção de grupo."""
    grupo_selecionado = forms.ModelChoiceField(
        queryset=Grupo.objects.all(),
        required=False,
        label=_("Associar/Pré-selecionar Grupo de Audiência"),
        help_text=_("Selecione um Grupo de Audiência. O AuthGroup vinculado será adicionado ao CustomUser.")
    )

    class Meta:
        model = CustomUser
        fields = '__all__'


# ==============================================================================
# ADMIN CUSTOMIZADO PARA CustomUser (AÇÃO AUTOCONTIDA CORRIGIDA)
# ==============================================================================

class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm

    list_display = ('username', 'email', 'tipo_usuario', 'is_staff', 'get_groups')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'tipo_usuario')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    fieldsets = UserAdmin.fieldsets + (
        ('Tipos e Vínculos', {
            'fields': ('tipo_usuario', 'registro_aluno', 'registro_professor', 'registro_colaborador',
                       'registro_responsavel', 'registro_ure', 'registro_visitante', 'is_fotografo',
                       'is_fotografo_master')
        }),
        (_('Associação Direta ao Grupo de Audiência'), {
            'fields': ('grupo_selecionado',)
        }),
    )

    actions = ['add_to_group_mass']

    # --------------------------------------------------------------------------
    # MÉTODOS AUXILIARES
    # --------------------------------------------------------------------------
    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])

    get_groups.short_description = _('Grupos de Audiência (Projeto)')

    # --------------------------------------------------------------------------
    # 🎯 AÇÃO AUTOCONTIDA (IMPLEMENTAÇÃO ROBUSTA E COMPATÍVEL)
    # --------------------------------------------------------------------------

    @transaction.atomic
    def add_to_group_mass(self, request, queryset):
        """
        Ação em massa que lida com a confirmação e o processamento de forma autocontida.
        Usa SQL Direto com o nome da tabela obtido dinamicamente.
        """
        opts = self.model._meta

        # 1. Obter o nome real da tabela e colunas (CORREÇÃO CRUCIAL DO ERRO ProgrammingError)
        ThroughModel = CustomUser.groups.through
        groups_table = ThroughModel._meta.db_table  # Isso deve retornar 'users_customuser_groups'

        # Obtém o nome da coluna FK do CustomUser (ex: 'customuser_id')
        user_fk_column = ThroughModel._meta.get_field('customuser').column
        # Obtém o nome da coluna FK do AuthGroup (ex: 'group_id')
        group_fk_column = ThroughModel._meta.get_field('group').column

        # 1. VERIFICAÇÃO DE SUBMISSÃO (POST de Confirmação)
        if 'apply' in request.POST:
            form = GrupoSelectForm(request.POST)

            if form.is_valid():
                grupo = form.cleaned_data['grupo']
                auth_group = grupo.auth_group
                added_count = 0

                user_pks = queryset.values_list('pk', flat=True)

                # Gravação Isolada e Robusta (SQL Direto)
                with connection.cursor() as cursor:
                    # SQL construído com nomes de tabela e colunas obtidos dinamicamente
                    sql = f"""
                        INSERT INTO {groups_table} ({user_fk_column}, {group_fk_column})
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING;
                    """
                    auth_group_id = auth_group.pk

                    for user_id in user_pks:
                        # Passa user_id e group_id como parâmetros de segurança
                        cursor.execute(sql, [user_id, auth_group_id])
                        added_count += cursor.rowcount

                self.message_user(request,
                                  f"{added_count} CustomUsers associados com sucesso ao Grupo de Audiência '{grupo.auth_group.name}' (Processamento Concluído).")

                # Invalida o cache do Django (necessário após SQL direto)
                User.objects.all().update()

                return None

        # 2. RENDERIZAÇÃO DA TELA DE CONFIRMAÇÃO (GET ou POST com erro)

        if 'apply' not in request.POST:
            form = GrupoSelectForm()
            # Se 'apply' estava presente, mas o form não era válido, usamos o form com erros

        context = self.admin_site.each_context(request)
        context.update({
            'title': _("Associar CustomUsers Selecionados a um Grupo de Audiência"),
            'queryset': queryset,
            'action_name': 'add_to_group_mass',
            'form': form,
            'opts': opts,
            'media': self.media,
            'action_button_name': 'apply',
            'description': _(
                f'Total de {queryset.count()} usuários selecionados. Selecione o grupo de audiência para adicionar.'),
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        })

        return render(request, 'admin/action_confirmation.html', context)

    add_to_group_mass.short_description = _("Associar CustomUsers selecionados a um Grupo de Audiência")

    # --------------------------------------------------------------------------
    # MÉTODOS DE SALVAMENTO (Para Edição Individual)
    # --------------------------------------------------------------------------
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        grupo_selecionado = form.cleaned_data.get('grupo_selecionado')

        if grupo_selecionado:
            auth_group = grupo_selecionado.auth_group

            if auth_group not in obj.groups.all():
                obj.groups.add(auth_group)
                messages.success(request, _(f"Usuário '{obj.username}' associado ao grupo '{auth_group.name}'."))

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if obj:
            user_auth_groups_ids = obj.groups.values_list('id', flat=True)
            try:
                grupo_aud = Grupo.objects.filter(auth_group__id__in=user_auth_groups_ids).first()
                if grupo_aud:
                    form.base_fields['grupo_selecionado'].initial = grupo_aud
            except Exception:
                pass

        return form


# ==============================================================================
# CLASSES ADMIN EXISTENTES (REGISTROS)
# ==============================================================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'data_nascimento', 'cidade', 'estado')
    search_fields = ('user__username', 'user__email')


@admin.register(RegistroAluno)
class RegistroAlunoAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'ra_numero', 'turma')
    search_fields = ('nome_completo', 'ra_numero')
    list_filter = ('turma__ano_letivo', 'turma')


@admin.register(RegistroColaborador)
class RegistroColaboradorAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'funcao')
    search_fields = ('nome_completo', 'matricula_ou_identificador')
    list_filter = ('funcao', 'ativo')


@admin.register(RegistroResponsavel)
class RegistroResponsavelAdmin(admin.ModelAdmin):
    list_display = ('nome_completo',)
    search_fields = ('nome_completo',)


@admin.register(RegistroURE)
class RegistroUREAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'funcao')
    search_fields = ('nome_completo',)


@admin.register(RegistroOutrosVisitantes)
class RegistroOutrosVisitantesAdmin(admin.ModelAdmin):
    list_display = ('nome_completo',)
    search_fields = ('nome_completo',)


# ==============================================================================
# ADMIN PARA TURMA E PROFESSOR
# ==============================================================================

class ProfessorAdicionalInline(admin.TabularInline):
    model = RegistroProfessor.turmas.through
    extra = 0
    fields = ['registroprofessor']
    raw_id_fields = ['registroprofessor']
    verbose_name = _("Professor Adicional")
    verbose_name_plural = _("Professores Adicionais da Turma")


class RegistroAlunoInline(admin.TabularInline):
    """Exibe todos os alunos (RegistroAluno) da turma."""
    model = RegistroAluno
    extra = 0
    fields = ('nome_completo', 'ra_numero', 'ra_digito_verificador', 'usuario')
    readonly_fields = ('usuario',)  # O campo 'usuario' mostra se o CustomUser foi criado
    search_fields = ('nome_completo', 'ra_numero')
    verbose_name = _("Aluno da Turma")
    verbose_name_plural = _("Alunos da Turma")


class TurmaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ano_letivo', 'ativo', 'professor_regente', 'display_adicionais')
    list_filter = ('ativo', 'ano_letivo')
    search_fields = ('nome', 'professor_regente__nome_completo')
    inlines = [ProfessorAdicionalInline, RegistroAlunoInline]  # ADICIONADO RegistroAlunoInline
    fields = ('nome', 'ano_letivo', 'ativo', 'professor_regente')

    def display_adicionais(self, obj):
        return ", ".join([prof.nome_completo for prof in obj.professores_adicionais.all()])

    display_adicionais.short_description = "Professores Adicionais"


@admin.register(RegistroProfessor)
class RegistroProfessorAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'tipo_professor')
    list_filter = ('tipo_professor',)
    search_fields = ('nome_completo',)


# ==============================================================================
# ADMIN PARA GRUPOS DE AUDIÊNCIA
# ==============================================================================

@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    """Admin para o modelo Grupo, gerencia a criação do AuthGroup."""
    list_display = ('__str__', 'tipo', 'ativo', 'criado_em')
    list_filter = ('tipo', 'ativo')
    search_fields = ('auth_group__name', 'descricao')

    readonly_fields = ('criado_em', 'auth_group_name')

    fieldsets = (
        (_("Grupo (Apenas Leitura)"), {'fields': ('auth_group_name', 'criado_em')}),
        (_("Metadados"), {'fields': ('tipo', 'descricao', 'ativo')}),
    )

    def auth_group_name(self, obj):
        return obj.auth_group.name if obj.pk else _("Aguardando Criação")

    auth_group_name.short_description = _("Nome do Grupo (Chave de Permissão)")

    model_fields = ['auth_group', 'tipo', 'descricao', 'ativo']

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (_("Informações Essenciais do Grupo"), {'fields': ('nome_do_grupo', 'tipo', 'descricao', 'ativo')}),
            )
        else:
            return self.fieldsets

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            if 'fields' in kwargs:
                del kwargs['fields']

            creation_fieldsets = self.get_fieldsets(request, obj)
            fields_for_form = flatten_fieldsets(creation_fieldsets)

            model_fields_only = [f for f in fields_for_form if f in self.model_fields and f != 'auth_group']

            ModelForm = super().get_form(request, obj, fields=model_fields_only, **kwargs)

            def validate_unique_auth_group_name(value):
                # Checa se o nome existe no AuthGroup, que é a base.
                if AuthGroup.objects.filter(name=value).exists():
                    # Checa se o nome existente já tem um Grupo de Audiência vinculado.
                    if Grupo.objects.filter(auth_group__name=value).exists():
                        raise ValidationError(
                            _('Um Grupo de Audiência com este nome já existe. Por favor, escolha outro.'))

            nome_do_grupo_field = forms.CharField(
                label=_("Nome Único do Grupo (Ex: 3A_2025 ou free)"),
                max_length=80,
                help_text=_("Este nome será a chave de permissão e deve ser único."),
                required=True,
                validators=[validate_unique_auth_group_name]
            )

            ModelForm.base_fields['nome_do_grupo'] = nome_do_grupo_field

            return ModelForm

        else:
            return super().get_form(request, obj, **kwargs)

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if not change:
            nome_do_grupo = form.cleaned_data.get('nome_do_grupo')
            if nome_do_grupo:
                try:
                    auth_group, created = AuthGroup.objects.get_or_create(name=nome_do_grupo)
                    obj.auth_group = auth_group
                    super().save_model(request, obj, form, change)

                    if created:
                        messages.success(request, f"Grupo de Audiência '{nome_do_grupo}' criado e metadados salvos.")
                    else:
                        messages.warning(request,
                                         f"Grupo de Autenticação '{nome_do_grupo}' já existia. Vínculo criado e metadados salvos.")

                except IntegrityError:
                    messages.error(request, "Erro: Este AuthGroup já está vinculado a outro Grupo de Audiência.")
                    raise
                except Exception as e:
                    messages.error(request, f"Erro inesperado ao criar o grupo: {e}")
                    raise
            else:
                messages.error(request, "O nome do grupo é obrigatório.")
                raise ValidationError("O nome do grupo é obrigatório.")
        else:
            super().save_model(request, obj, form, change)
            messages.success(request, f"Metadados do Grupo de Audiência '{obj.auth_group.name}' atualizados.")


# ==============================================================================
# ADMIN PARA UPLOAD E PROCESSAMENTO DE JSON
# ==============================================================================

@admin.register(JSONUpload)
class JSONUploadAdmin(admin.ModelAdmin):
    list_display = ('turma', 'json_file', 'uploaded_at')
    fields = ('turma', 'json_file',)
    list_filter = ('turma',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        file_path = obj.json_file.path
        create_count = 0
        update_count = 0
        error_count = 0

        turma_selecionada = obj.turma

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise ValueError("O JSON deve ser uma lista de objetos (alunos).")

            for item in data:
                nome_completo = item.get('nome_completo')
                ra_numero = item.get('ra_numero')
                ra_digito_verificador = item.get('ra_digito_verificador')

                if not ra_numero or not ra_digito_verificador:
                    error_count += 1
                    continue

                try:
                    # Atualiza ou cria o RegistroAluno
                    aluno, created = RegistroAluno.objects.update_or_create(
                        ra_numero=ra_numero,
                        ra_digito_verificador=ra_digito_verificador,
                        defaults={
                            'nome_completo': nome_completo,
                            'turma': turma_selecionada
                        }
                    )

                    # CORREÇÃO APLICADA: NENHUM CustomUser ou Profile é criado aqui.

                    if created:
                        create_count += 1
                    else:
                        update_count += 1

                except IntegrityError:
                    messages.error(request, f"Erro de integridade ao processar RA '{ra_numero}'.")
                    error_count += 1
                except Exception as e:
                    messages.error(request, f"Erro desconhecido ao processar RA '{ra_numero}': {e}")
                    error_count += 1

            msg = (f"Processamento concluído: {create_count} registros criados. "
                   f"{update_count} registros atualizados (turma ou nome). "
                   f"({error_count} erros)")
            if error_count == 0:
                messages.success(request, msg)
            else:
                messages.warning(request, msg)


        except json.JSONDecodeError:
            messages.error(request, "Falha: O arquivo não é um JSON válido.")
        except ValueError as ve:
            messages.error(request, f"Falha na estrutura: {ve}")
        except Exception as e:
            messages.error(request, f"Erro inesperado no processamento do arquivo: {e}")
        finally:
            try:
                obj.json_file.delete(save=False)
            except Exception:
                pass

            obj.delete()

        return HttpResponseRedirect("../")


# ==============================================================================
# ADMIN PARA MEMBROGRUPO (AUDITORIA)
# ==============================================================================

@admin.register(MembroGrupo)
class MembroGrupoAdmin(admin.ModelAdmin):
    """Admin simplificado, apenas para visualização e gerenciamento do link Registro -> Grupo."""
    list_display = ('grupo', 'display_registro')
    list_filter = ('grupo__auth_group__name',)
    search_fields = ('grupo__auth_group__name', 'aluno__nome_completo', 'professor__nome_completo')
    raw_id_fields = ('aluno', 'professor', 'colaborador', 'responsavel', 'ure', 'visitante', 'grupo')

    fieldsets = (
        (_("Grupo de Audiência"), {'fields': ('grupo',)}),
        (_("Registro Associado (Selecione APENAS UM - Opcional)"), {
            'fields': ('aluno', 'professor', 'colaborador', 'responsavel', 'ure', 'visitante'),
            'description': _(
                "Este é um registro de auditoria. Para associar o USUÁRIO ao GRUPO, use a tela de CustomUsers.")
        }),
    )

    def display_registro(self, obj):
        """Retorna o nome e o tipo de registro associado (Aluno, Professor, etc.) para lista."""
        registro = obj.registro
        if registro:
            return f"{registro.nome_completo} ({registro.__class__.__name__.replace('Registro', '')})"
        return _("Nenhum registro associado")

    display_registro.short_description = _("Registro Associado")


# ==============================================================================
# REGISTRO FINAL DOS MODELOS (Usando admin.site.register)
# ==============================================================================

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Turma, TurmaAdmin)