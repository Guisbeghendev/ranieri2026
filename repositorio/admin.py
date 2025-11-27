from django.contrib import admin
from .models import Imagem, Galeria, WatermarkConfig


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
    # CORRIGIDO: Removido 'alterado_em', pois o modelo Imagem só tem 'criado_em'.
    readonly_fields = ('criado_em', 'arquivo_original_url', 'arquivo_processado_url')

    def arquivo_original_url(self, obj):
        """Método para exibir o link do arquivo original no Admin."""
        if obj.arquivo_original:
            return f'<a href="{obj.arquivo_original.url}" target="_blank">Visualizar Original</a>'
        return "N/A"

    arquivo_original_url.short_description = 'Arquivo Original'
    arquivo_original_url.allow_tags = True

    def arquivo_processado_url(self, obj):
        """Método para exibir o link do arquivo processado no Admin."""
        if obj.arquivo_processado:
            return f'<a href="{obj.arquivo_processado.url}" target="_blank">Visualizar Processado</a>'
        return "N/A"

    arquivo_processado_url.short_description = 'Arquivo Processado'
    arquivo_processado_url.allow_tags = True


# --------------------------------------------------------------------------
# Configuração do Admin para Galeria
# --------------------------------------------------------------------------

class GaleriaAdmin(admin.ModelAdmin):
    """
    Configurações de exibição para o modelo Galeria no Admin.
    """
    # Campos exibidos na listagem
    list_display = ('nome', 'fotografo', 'watermark_config', 'status', 'criado_em')

    # Filtros laterais
    list_filter = ('status', 'fotografo')

    # Campos pesquisáveis
    search_fields = ('nome', 'descricao')

    # Edição de campos M2M (Grupos) de forma horizontal
    filter_horizontal = ('grupos_acesso',)

    # Define campos que não podem ser editados após a criação
    # CORRIGIDO: 'alterado_em' não existe em Galeria. Usando 'publicada_em' como campo de leitura.
    readonly_fields = ('criado_em', 'publicada_em')

    # Define o fotógrafo automaticamente no formulário de criação/edição, se for Admin
    def save_model(self, request, obj, form, change):
        if not change:
            # Associa o usuário logado como fotógrafo apenas na criação
            obj.fotografo = request.user
        super().save_model(request, obj, form, change)


# --------------------------------------------------------------------------
# Configuração do Admin para WatermarkConfig (Configuração simples)
# --------------------------------------------------------------------------

class WatermarkConfigAdmin(admin.ModelAdmin):
    """
    Configurações de exibição para o modelo WatermarkConfig no Admin.
    """
    # CORRIGIDO (E108): 'texto_watermark' não existe. Usando 'posicao', que existe no modelo.
    list_display = ('nome', 'posicao', 'opacidade')
    # CORRIGIDO: 'texto_watermark' não existe. Removido de search_fields ou use 'nome'.
    search_fields = ('nome',)
    # CORRIGIDO (E035): 'alterado_em' mudado para o nome correto do modelo, que é 'atualizado_em'.
    readonly_fields = ('criado_em', 'atualizado_em')


# --------------------------------------------------------------------------
# Registro dos Modelos
# --------------------------------------------------------------------------

admin.site.register(Imagem, ImagemAdmin)
admin.site.register(Galeria, GaleriaAdmin)
admin.site.register(WatermarkConfig, WatermarkConfigAdmin)