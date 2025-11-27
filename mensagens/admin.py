from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
import csv
import datetime
from django import forms
from django.template.response import TemplateResponse
from django.contrib import messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME

from .models import Canal, Mensagem, UltimaLeituraUsuario


# ==============================================================================
# 0. FORMULÁRIO PARA AÇÃO DE EXPORTAÇÃO
# ==============================================================================

class ExportarMensagensForm(forms.Form):
    data_inicial = forms.DateField(
        label=_("Data Inicial"),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text=_("AAAA-MM-DD. Inclui a partir do início deste dia.")
    )
    data_final = forms.DateField(
        label=_("Data Final"),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text=_("AAAA-MM-DD. Inclui até o final deste dia.")
    )
    # Campo oculto para garantir que os itens selecionados sejam mantidos
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)


# ==============================================================================
# 1. FUNÇÃO DE EXPORTAÇÃO (ACTION) - TRATAMENTO DE DATAS CUSTOMIZADAS
# ==============================================================================

def exportar_mensagens_dos_canais_csv(modeladmin, request, queryset_canais):
    """
    Exporta Mensagens dos Canais selecionados, usando um formulário de confirmação
    para definir o período customizado (Data Inicial e Data Final).
    """
    # -----------------------------------------------------------------
    # Caso 1: Ação clicada - Mostra o formulário de datas
    # -----------------------------------------------------------------
    if 'apply' not in request.POST:
        if not queryset_canais.exists():
            messages.error(request, _("Selecione pelo menos um canal para exportar."))
            return

        form = ExportarMensagensForm(initial={'_selected_action': request.POST.getlist(ACTION_CHECKBOX_NAME)})

        return TemplateResponse(request, 'admin/exportar_confirmacao.html', {
            'channels': queryset_canais,
            'form': form,
            'title': _("Definir Período de Auditoria e Exportar Mensagens"),
            'media': modeladmin.media,
            'action_name': 'exportar_mensagens_dos_canais_csv',
            'opts': modeladmin.model._meta,
        })

    # -----------------------------------------------------------------
    # Caso 2: Formulário de datas submetido - Executa a exportação
    # -----------------------------------------------------------------
    else:
        form = ExportarMensagensForm(request.POST)

        if form.is_valid():
            data_inicial = form.cleaned_data.get('data_inicial')
            data_final = form.cleaned_data.get('data_final')

            # INÍCIO DA LÓGICA DE EXPORTAÇÃO
            data_hora_agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"relatorio_auditoria_canais_{data_hora_agora}.csv"

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'

            # 🎯 CORREÇÃO DE DETALHE: Usar ponto e vírgula (;) como delimitador para compatibilidade com Excel em pt-BR
            writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_ALL)

            writer.writerow([
                _('ID Mensagem'), _('Data/Hora de Envio'), _('Canal'),
                _('Grupo Associado'), _('ID Autor'), _('Autor (Username)'), _('Conteúdo')
            ])

            canal_ids = queryset_canais.values_list('id', flat=True)
            mensagens_queryset = Mensagem.objects.filter(canal_id__in=canal_ids)

            # APLICAÇÃO DO FILTRO DE DATAS CUSTOMIZADAS
            if data_inicial:
                mensagens_queryset = mensagens_queryset.filter(data_envio__date__gte=data_inicial)

            if data_final:
                mensagens_queryset = mensagens_queryset.filter(data_envio__date__lte=data_final)

            if not mensagens_queryset.exists():
                messages.warning(request, _("Nenhuma mensagem encontrada para o período selecionado."))
                from django.shortcuts import redirect
                return redirect(f'admin:mensagens_canal_changelist')

            mensagens_queryset = mensagens_queryset.order_by(
                'canal__nome', 'data_envio'
            ).select_related(
                'canal', 'autor', 'canal__grupo', 'canal__grupo__auth_group'
            )

            # Iteração e escrita no CSV
            for mensagem in mensagens_queryset:
                try:
                    nome_grupo = mensagem.canal.grupo.auth_group.name
                except AttributeError:
                    nome_grupo = "N/A (Grupo Inexistente)"

                writer.writerow([
                    mensagem.pk,
                    mensagem.data_envio.strftime("%Y-%m-%d %H:%M:%S"),
                    mensagem.canal.nome,
                    nome_grupo,
                    mensagem.autor.pk,
                    mensagem.autor.username,
                    mensagem.conteudo,
                ])

            return response
        else:
            messages.error(request, _("Erro nos dados do formulário de período. Verifique as datas."))
            return

    messages.error(request, _("Ocorreu um erro desconhecido na exportação."))
    return


exportar_mensagens_dos_canais_csv.short_description = _("Exportar Mensagens (Período Customizado)")


# ==============================================================================
# ADMIN PARA CANAL
# ==============================================================================

@admin.register(Canal)
class CanalAdmin(admin.ModelAdmin):
    list_display = ('nome', 'grupo_nome', 'criador_nome', 'ativo', 'criado_em')
    list_filter = (
        'ativo',
        'criado_em',
        'grupo__tipo',
    )
    search_fields = ('nome', 'grupo__auth_group__name')
    raw_id_fields = ('grupo', 'criador')

    actions = [exportar_mensagens_dos_canais_csv]

    readonly_fields = ('criado_em',)

    fieldsets = (
        (_("Informações do Canal"), {'fields': ('nome', 'grupo', 'criador', 'ativo', 'criado_em', 'slug')}),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj:
            # CORREÇÃO: Remove 'criador' para permitir que seja editável na página de alteração.
            # O campo 'criador' foi removido desta lista para permitir a alteração do criador
            # em canais existentes.
            fields = list(fields)  # Converte para lista para permitir manipulação

            # Adiciona os campos que devem ser somente leitura na edição
            readonly = ('grupo', 'slug')
            fields.extend(readonly)

            # Remove 'criador' da lista se estiver presente para permitir a edição
            if 'criador' in fields:
                fields.remove('criador')

            return tuple(fields)  # Retorna como tupla
        return fields

    def save_model(self, request, obj, form, change):
        if not change and not obj.criador:
            obj.criador = request.user
        super().save_model(request, obj, form, change)

    def grupo_nome(self, obj):
        try:
            return obj.grupo.auth_group.name
        except AttributeError:
            return "N/A"

    grupo_nome.short_description = 'Grupo Associado'

    def criador_nome(self, obj):
        # CORREÇÃO: Verifica se obj.criador não é None antes de acessar atributos.
        if obj.criador:
            return obj.criador.get_full_name() or obj.criador.username
        return _("N/A (Sem Criador)")

    criador_nome.short_description = 'Criador'


# ==============================================================================
# ADMIN PARA MENSAGEM (RESTANTE DO CÓDIGO INALTERADO)
# ==============================================================================

@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ('autor_nome', 'canal_nome', 'conteudo_preview', 'data_envio')
    list_filter = ('canal', 'data_envio', 'autor')
    search_fields = ('autor__username', 'conteudo', 'canal__nome')
    date_hierarchy = 'data_envio'
    readonly_fields = ('autor', 'data_envio')
    raw_id_fields = ('canal', 'autor')

    def save_model(self, request, obj, form, change):
        if not change:
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


# ==============================================================================
# ADMIN PARA UltimaLeituraUsuario
# ==============================================================================

@admin.register(UltimaLeituraUsuario)
class UltimaLeituraUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'canal', 'data_leitura')
    list_filter = ('canal', 'data_leitura')
    search_fields = ('usuario__username', 'canal__nome')
    date_hierarchy = 'data_leitura'
    raw_id_fields = ('usuario', 'canal')