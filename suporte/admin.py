from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group

from .models import Topico, MensagemSuporte, TopicoStatus

# ==============================================================================
# 0. CONSTANTE DE GRUPO E PERMISSÃO
# ==============================================================================

# Defina o nome do grupo que terá acesso total aos Tópicos
grupo_suporte = "Equipe de Suporte"


# ==============================================================================
# 1. INLINES (Para ver as Mensagens dentro do TópicoAdmin)
# ==============================================================================

class MensagemSuporteInline(admin.TabularInline):
    """Exibe as mensagens dentro da tela de detalhes do Tópico."""
    model = MensagemSuporte
    extra = 0  # Não adiciona linhas vazias automaticamente
    readonly_fields = ('autor', 'conteudo', 'timestamp')
    can_delete = False

    # Limita o formulário de adição de mensagens, se necessário
    fields = ('autor', 'conteudo', 'timestamp')


# ==============================================================================
# 2. ADMIN PARA TÓPICO
# ==============================================================================

@admin.register(Topico)
class TopicoAdmin(admin.ModelAdmin):
    list_display = ('id', 'assunto_preview', 'criador', 'status', 'admin_responsavel', 'criado_em')
    list_display_links = ('assunto_preview',)
    list_filter = ('status', 'criado_em', 'admin_responsavel__username')
    search_fields = ('assunto', 'criador__username', 'mensagens__conteudo')
    date_hierarchy = 'criado_em'

    raw_id_fields = ('criador', 'admin_responsavel')
    readonly_fields = ('criado_em', 'atualizado_em', 'criador')

    inlines = [MensagemSuporteInline]

    fieldsets = (
        (_("Informações do Tópico"), {
            'fields': ('assunto', 'criador', 'criado_em', 'atualizado_em')
        }),
        (_("Fluxo de Trabalho e Responsabilidade"), {
            'fields': ('status', 'admin_responsavel')
        }),
    )

    def get_queryset(self, request):
        """
        Garante que apenas a Equipe de Suporte/Staff/Superuser veja todos os tópicos.
        O acesso de usuário comum à listagem é feito via views.py
        """
        qs = super().get_queryset(request)

        # Filtro para Superuser e Staff
        if request.user.is_superuser or request.user.is_staff:
            return qs

        # Caso contrário, retorna um queryset vazio no Admin,
        # pois o acesso de usuário final é via front-end (views.py)
        return qs.none()

    def save_model(self, request, obj, form, change):
        """
        Sobrescreve save_model para definir o admin_responsavel
        e atualizar o status na primeira interação ou atribuição.
        """
        if not change:
            # Garante que o criador seja setado (embora a criação seja via front-end, isso é uma segurança)
            # CORREÇÃO: Verifica obj.criador_id em vez de obj.criador para evitar RelatedObjectDoesNotExist
            if not obj.criador_id:
                obj.criador = request.user
            obj.status = TopicoStatus.NOVO

        # Lógica de fluxo de trabalho para o admin/suporte
        if obj.admin_responsavel and obj.status == TopicoStatus.NOVO:
            # Se um responsável foi atribuído e o status era Novo, muda para Em Atendimento
            obj.status = TopicoStatus.EM_ATENDIMENTO

        super().save_model(request, obj, form, change)

    def assunto_preview(self, obj):
        return obj.assunto[:50] + '...' if len(obj.assunto) > 50 else obj.assunto

    assunto_preview.short_description = _("Assunto")


# ==============================================================================
# 3. ADMIN PARA MENSAGEMSUPORTE
# ==============================================================================

@admin.register(MensagemSuporte)
class MensagemSuporteAdmin(admin.ModelAdmin):
    list_display = ('topico_id', 'autor', 'conteudo_preview', 'timestamp')
    list_filter = ('topico__assunto', 'autor')
    search_fields = ('conteudo', 'topico__assunto', 'autor__username')
    date_hierarchy = 'timestamp'

    raw_id_fields = ('topico', 'autor')
    readonly_fields = ('timestamp',)

    def conteudo_preview(self, obj):
        return obj.conteudo[:70] + '...' if len(obj.conteudo) > 70 else obj.conteudo

    conteudo_preview.short_description = _("Conteúdo")


# ==============================================================================
# 4. HOOK DE PERMISSÃO (Função que verifica se o usuário é da Equipe de Suporte)
# ==============================================================================

def is_suporte(user):
    """Verifica se o usuário pertence ao grupo 'Equipe de Suporte'."""
    return user.groups.filter(name=grupo_suporte).exists()


# Sobrescreve as permissões padrão dos modelos para a Equipe de Suporte (e Staff/Superuser)
class SuporteBaseAdmin(admin.ModelAdmin):
    """Classe base para gerenciar permissões no admin do app suporte."""

    def has_module_permission(self, request):
        """Permite que apenas staff/superuser e Equipe de Suporte vejam o módulo."""
        if request.user.is_superuser or request.user.is_staff:
            return True
        return is_suporte(request.user)

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


# Desregistra e registra novamente os modelos com a permissão base (Opcional, mas seguro)
admin.site.unregister(Topico)
admin.site.unregister(MensagemSuporte)


@admin.register(Topico)
class TopicoAdmin(SuporteBaseAdmin, TopicoAdmin):
    """Combina as permissões base com a administração do Tópico."""
    pass


@admin.register(MensagemSuporte)
class MensagemSuporteAdmin(SuporteBaseAdmin, MensagemSuporteAdmin):
    """Combina as permissões base com a administração de MensagensSuporte."""
    pass