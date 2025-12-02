from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth import get_user_model
from .models import Imagem, Galeria, WatermarkConfig

User = get_user_model()


# --------------------------------------------------------------------------
# Inlines para Galeria (para visualizar imagens)
# --------------------------------------------------------------------------

class ImagemInline(admin.TabularInline):
    model = Imagem
    extra = 0
    fields = ('nome_arquivo_original', 'status_processamento', 'criado_em')
    readonly_fields = ('nome_arquivo_original', 'status_processamento', 'criado_em')


# --------------------------------------------------------------------------
# Configuração do Admin para Imagem
# --------------------------------------------------------------------------

class ImagemAdmin(admin.ModelAdmin):
    """
    Configurações de exibição para o modelo Imagem no Admin.
    """
    # Campos exibidos na listagem
    list_display = ('nome_arquivo_original', 'status_processamento', 'galeria', 'criado_em')

    # Filtros laterais
    list_filter = ('status_processamento', 'galeria')

    # Campos pesquisáveis
    search_fields = ('nome_arquivo_original', 'galeria__nome')

    # Define campos somente leitura
    readonly_fields = ('criado_em', 'arquivo_original_url', 'arquivo_processado_url')

    def arquivo_original_url(self, obj):
        """
        Método para exibir o link do arquivo original (privado, S3).
        O .url em PrivateMediaStorage gera a URL assinada (temporária).
        """
        if obj.arquivo_original:
            # Usa format_html para retornar HTML de forma segura
            return format_html('<a href="{}" target="_blank">Visualizar Original (Privado)</a>',
                               obj.arquivo_original.url)
        return "N/A"

    arquivo_original_url.short_description = 'Arquivo Original'

    def arquivo_processado_url(self, obj):
        """
        Método para exibir o link do arquivo processado (público, S3).
        """
        if obj.arquivo_processado:
            # Usa format_html para retornar HTML de forma segura
            return format_html('<a href="{}" target="_blank">Visualizar Processado (Público)</a>',
                               obj.arquivo_processado.url)
        return "N/A"

    arquivo_processado_url.short_description = 'Arquivo Processado'


# --------------------------------------------------------------------------
# Configuração do Admin para Galeria
# --------------------------------------------------------------------------

class GaleriaAdmin(admin.ModelAdmin):
    """
    Configurações de exibição para o modelo Galeria no Admin.
    """
    # CORRIGIDO: Adiciona 'data_do_evento' e 'acesso_publico' na listagem
    list_display = ('nome', 'data_do_evento', 'acesso_publico', 'capa_display', 'fotografo', 'watermark_config', 'status', 'criado_em')

    # Filtros laterais
    # CORRIGIDO: Adiciona 'acesso_publico' aos filtros
    list_filter = ('status', 'acesso_publico', 'fotografo', 'data_do_evento')

    # Campos pesquisáveis
    search_fields = ('nome', 'descricao')

    # Edição de campos M2M (Grupos) de forma horizontal
    filter_horizontal = ('grupos_acesso',)

    # Define campos que não podem ser editados após a criação
    # CORRIGIDO: Adiciona 'data_do_evento' aos campos somente leitura (é definida pela tela de gerenciamento, não aqui)
    readonly_fields = ('criado_em', 'publicada_em', 'capa')

    # CAMPOS EXIBIDOS NO FORMULÁRIO: Adiciona 'acesso_publico'
    fieldsets = (
        (None, {
            # Adicionado 'data_do_evento'
            'fields': ('nome', 'data_do_evento', 'descricao', 'status', 'fotografo')
        }),
        ('Configurações', {
            'fields': ('watermark_config', 'capa'),
            'classes': ('collapse',),
        }),
        ('Acesso', {
            # CORRIGIDO: Adicionado 'acesso_publico' na seção de acesso
            'fields': ('acesso_publico', 'grupos_acesso',),
            'description': 'Define a visibilidade (Pública/Restrita) e quais grupos de usuários podem visualizar esta galeria.'
        }),
    )

    inlines = [ImagemInline]  # Adiciona a listagem de imagens na galeria

    # CORREÇÃO NO QUERYSET: Restringe o queryset do campo fotografo para usuários staff (com acesso ao Admin)
    def get_form(self, request, obj=None, **kwargs):
        # Acessa o formulário padrão do model admin
        form = super().get_form(request, obj, **kwargs)

        # Sobrescreve o queryset do campo 'fotografo'
        if 'fotografo' in form.base_fields:
            # Filtra para incluir apenas usuários que são Staff (têm acesso ao Admin) e estão ativos
            form.base_fields['fotografo'].queryset = User.objects.filter(
                is_staff=True, is_active=True
            ).order_by('username')
        return form

    # Define o fotógrafo automaticamente no formulário de criação/edição
    def save_model(self, request, obj, form, change):
        if not change and not obj.fotografo:
            # Associa o usuário logado como fotógrafo apenas se for staff
            if request.user.is_staff:
                obj.fotografo = request.user
        super().save_model(request, obj, form, change)

    def capa_display(self, obj):
        """Exibe a miniatura da capa da galeria na listagem."""
        if obj.capa and obj.capa.arquivo_processado:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                               obj.capa.arquivo_processado.url)
        return "Sem Capa"

    capa_display.short_description = 'Capa'


# --------------------------------------------------------------------------
# Configuração do Admin para WatermarkConfig (Configuração simples - Singleton)
# --------------------------------------------------------------------------

class WatermarkConfigAdmin(admin.ModelAdmin):
    """
    Configurações de exibição para o modelo WatermarkConfig no Admin.
    Ajustado para funcionar como um 'Singleton' (máximo 1 item).
    """
    list_display = ('nome', 'posicao', 'opacidade')
    search_fields = ('nome',)
    readonly_fields = ('criado_em', 'atualizado_em')

    # Método para desabilitar o botão de adicionar novo item se um já existe
    def has_add_permission(self, request):
        # Permite adicionar se não houver configurações, ou se for superuser
        if self.model.objects.count() >= 1 and not request.user.is_superuser:
            return False
        return super().has_add_permission(request)


# --------------------------------------------------------------------------
# Registro dos Modelos
# --------------------------------------------------------------------------

admin.site.register(Imagem, ImagemAdmin)
admin.site.register(Galeria, GaleriaAdmin)
admin.site.register(WatermarkConfig, WatermarkConfigAdmin)