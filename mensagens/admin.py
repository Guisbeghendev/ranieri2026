from django.contrib import admin
from .models import Canal, Mensagem
from django.utils.translation import gettext_lazy as _


# ==============================================================================
# ADMIN PARA CANAL
# ==============================================================================

@admin.register(Canal)
class CanalAdmin(admin.ModelAdmin):
    list_display = ('nome', 'grupo_nome', 'criador_nome', 'ativo', 'criado_em')
    list_filter = ('ativo', 'criado_em', 'grupo__tipo')
    search_fields = ('nome', 'grupo__auth_group__name')
    raw_id_fields = ('grupo', 'criador')

    # Campo 'grupo' deve ser somente leitura se o objeto já existir (criado por signal).
    # O campo 'criado_em' também é readonly.
    readonly_fields = ('criado_em',)

    fieldsets = (
        (_("Informações do Canal"), {'fields': ('nome', 'grupo', 'criador', 'ativo', 'criado_em')}),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)

        # Se for uma alteração (obj existe), torna 'grupo' e 'criador' somente leitura
        if obj:
            fields += ('grupo', 'criador')

        return fields

    def save_model(self, request, obj, form, change):
        if not change and not obj.criador:
            # Garante que o criador seja o usuário logado se o objeto estiver sendo criado manualmente
            obj.criador = request.user
        super().save_model(request, obj, form, change)

    def grupo_nome(self, obj):
        return obj.grupo.auth_group.name

    grupo_nome.short_description = 'Grupo Associado'

    def criador_nome(self, obj):
        return obj.criador.get_full_name() or obj.criador.username

    criador_nome.short_description = 'Criador'


# ==============================================================================
# ADMIN PARA MENSAGEM (CORREÇÃO DE INTEGRITYERROR)
# ==============================================================================

@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ('autor_nome', 'canal_nome', 'conteudo_preview', 'data_envio')
    list_filter = ('canal', 'data_envio')
    search_fields = ('autor__username', 'conteudo')
    date_hierarchy = 'data_envio'

    # Mensagens são histórico. Os campos 'autor' e 'data_envio' são preenchidos
    # automaticamente e 'canal' é essencial, então todos devem ser readonly na alteração.
    readonly_fields = ('autor', 'data_envio')

    # O campo 'timestamp' no seu modelo deve ser 'data_envio' (conforme o erro)
    # ou vice-versa, mas vou manter a correção baseada no erro reportado.
    fieldsets = (
        (_("Detalhes da Mensagem"), {'fields': ('canal', 'conteudo', 'autor', 'data_envio')}),
    )

    # Adiciona a relação Many-to-One ao 'canal' e 'autor' no raw_id_fields.
    raw_id_fields = ('canal', 'autor')

    def save_model(self, request, obj, form, change):
        if not change:
            # CORREÇÃO CRUCIAL: Preenche o campo 'autor' com o usuário logado antes de salvar.
            # Isso impede o IntegrityError.
            obj.autor = request.user
        super().save_model(request, obj, form, change)

    def canal_nome(self, obj):
        return obj.canal.nome

    canal_nome.short_description = 'Canal'

    def autor_nome(self, obj):
        return obj.autor.get_full_name() or obj.autor.username

    autor_nome.short_description = 'Autor'

    def conteudo_preview(self, obj):
        return obj.conteudo[:70] + '...' if len(obj.conteudo) > 70 else obj.conteudo

    conteudo_preview.short_description = 'Conteúdo'

# Remova o 'timestamp' do list_display do MensagemAdmin e substitua por 'data_envio'.
# O erro reportou 'data_envio', mas seu admin usa 'timestamp'.
# Mantenho a correção usando 'data_envio' para compatibilidade com o log que você postou.