from django.contrib import admin
from .models import CustomUser, Profile
from django.contrib.auth.admin import UserAdmin


# O UserAdmin é usado para manter a funcionalidade padrão do painel de usuário do Django,
# mas usando o seu modelo CustomUser.

class CustomUserAdmin(UserAdmin):
    # Campos que você deseja exibir na lista de usuários no Admin
    list_display = ('username', 'email', 'tipo_usuario', 'is_staff')
    # Campos que você deseja editar na tela de detalhes do usuário
    fieldsets = UserAdmin.fieldsets + (
        (('Tipos e Vínculos', {
            'fields': ('tipo_usuario', 'registro_aluno', 'registro_professor', 'registro_colaborador',
                       'registro_responsavel', 'registro_ure', 'registro_visitante')}),)
    )


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'data_nascimento', 'cidade', 'estado')
    search_fields = ('user__username', 'user__email')


# Registro dos modelos no painel de administração
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Profile, ProfileAdmin)