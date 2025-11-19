from django.contrib import admin
import json
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.db.utils import IntegrityError

from .models import (
    CustomUser, Profile, RegistroAluno, Turma, Grupo, MembroGrupo, JSONUpload,
    RegistroProfessor, RegistroColaborador, RegistroResponsavel, RegistroURE, RegistroOutrosVisitantes
)

User = get_user_model()


# ==============================================================================
# CLASSES ADMIN EXISTENTES (Mantidas)
# ==============================================================================

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'tipo_usuario', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        (('Tipos e Vínculos', {
            'fields': ('tipo_usuario', 'registro_aluno', 'registro_professor', 'registro_colaborador',
                       'registro_responsavel', 'registro_ure', 'registro_visitante', 'is_fotografo',
                       'is_fotografo_master')}),)
    )


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'data_nascimento', 'cidade', 'estado')
    search_fields = ('user__username', 'user__email')


# NOVO: Inline para exibir os alunos dentro da Turma
class RegistroAlunoInline(admin.TabularInline):
    model = RegistroAluno
    extra = 0
    fields = ('nome_completo', 'ra_numero', 'ra_digito_verificador')
    readonly_fields = ('nome_completo', 'ra_numero', 'ra_digito_verificador')
    can_delete = False


# NOVO INLINE: Para gerenciar o Many-to-Many reverso (professores_adicionais)
class ProfessorAdicionalInline(admin.TabularInline):
    model = RegistroProfessor.turmas.through
    extra = 0
    fields = ['registroprofessor']
    raw_id_fields = ['registroprofessor']
    verbose_name = _("Professor Adicional")
    verbose_name_plural = _("Professores Adicionais da Turma")


class TurmaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ano_letivo', 'ativo', 'professor_regente', 'display_adicionais')
    list_filter = ('ativo', 'ano_letivo')
    search_fields = ('nome', 'professor_regente__nome_completo')

    # CORREÇÃO: Ordem invertida - Professores Adicionais aparecerão antes dos Alunos.
    inlines = [ProfessorAdicionalInline, RegistroAlunoInline]

    fields = ('nome', 'ano_letivo', 'ativo', 'professor_regente')

    def display_adicionais(self, obj):
        return ", ".join([prof.nome_completo for prof in obj.professores_adicionais.all()])

    display_adicionais.short_description = "Professores Adicionais"


class RegistroProfessorAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'tipo_professor')
    list_filter = ('tipo_professor',)
    search_fields = ('nome_completo',)


# ==============================================================================
# ADMIN PARA UPLOAD E PROCESSAMENTO DE JSON (Novo)
# ==============================================================================

@admin.register(JSONUpload)
class JSONUploadAdmin(admin.ModelAdmin):
    """
    Interface Admin para fazer upload de arquivos JSON.
    A lógica de seeding/atualização de usuários é executada no save_model.
    """
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
        success_count = 0
        update_count = 0
        create_count = 0
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
                    aluno, created = RegistroAluno.objects.update_or_create(
                        ra_numero=ra_numero,
                        ra_digito_verificador=ra_digito_verificador,
                        defaults={
                            'nome_completo': nome_completo,
                            'turma': turma_selecionada
                        }
                    )

                    if created:
                        create_count += 1
                    else:
                        update_count += 1

                    success_count += 1

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
            obj.json_file.delete(save=False)
            obj.delete()

        return HttpResponseRedirect("../")


# ==============================================================================
# REGISTROS NO ADMIN
# ==============================================================================

@admin.register(RegistroAluno)
class RegistroAlunoAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'ra_numero', 'turma')
    search_fields = ('nome_completo', 'ra_numero')
    list_filter = ('turma__ano_letivo', 'turma')


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Profile, ProfileAdmin)

# Registros dos demais modelos
admin.site.register(Turma, TurmaAdmin)
admin.site.register(RegistroProfessor, RegistroProfessorAdmin)
admin.site.register(RegistroColaborador)
admin.site.register(RegistroResponsavel)
admin.site.register(RegistroURE)
admin.site.register(RegistroOutrosVisitantes)
admin.site.register(Grupo)
admin.site.register(MembroGrupo)