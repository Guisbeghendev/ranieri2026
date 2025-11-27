from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
# Importa DeleteView
from django.views.generic import View, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.db import transaction
from django import forms
from django.db import models
from users.models import Grupo

from .models import Imagem, Galeria, WatermarkConfig
from .tasks import processar_imagem_task


# --------------------------------------------------------------------------
# Mixins de Permissão
# --------------------------------------------------------------------------

class FotografoRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Exige que o usuário esteja logado e tenha permissão de Fotógrafo.
    (Assumindo que o modelo User em 'users' tem um método 'is_fotografo')
    """

    def test_func(self):
        # O usuário precisa estar autenticado (garantido por LoginRequiredMixin)
        # e ter a permissão de fotógrafo
        return self.request.user.is_authenticated and self.request.user.is_fotografo


# --------------------------------------------------------------------------
# 1. Formulário Customizado para Upload Múltiplo
# --------------------------------------------------------------------------

class MultipleFileInput(forms.ClearableFileInput):
    """Permite a seleção de múltiplos arquivos."""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Campo de formulário que aceita múltiplos arquivos."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            # Chama clean para cada item da lista (cada arquivo)
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class ImagemUploadForm(forms.Form):
    """Formulário para upload de uma ou mais imagens."""
    arquivos = MultipleFileField(
        label='Selecione Imagens (Múltiplo)',
        help_text='Selecione todos os arquivos que deseja enviar.'
    )


# --------------------------------------------------------------------------
# 2. View para Upload de Imagens (Dispara Celery)
# --------------------------------------------------------------------------

class UploadImagemView(FotografoRequiredMixin, View):
    """
    Permite o upload de múltiplos arquivos e dispara a tarefa de processamento
    para cada um, salvando o registro inicial no banco.
    """
    form_class = ImagemUploadForm
    template_name = 'repositorio/upload_imagem.html'

    def get(self, request):
        return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            arquivos = request.FILES.getlist('arquivos')
            uploaded_count = 0

            with transaction.atomic():
                for f in arquivos:
                    # 1. Cria o objeto Imagem no banco (status PENDENTE)
                    imagem = Imagem.objects.create(
                        nome_arquivo_original=f.name,
                        status_processamento='PENDENTE'
                    )

                    # 2. Faz o upload do arquivo original para o S3
                    imagem.arquivo_original.save(f.name, f, save=False)
                    imagem.status_processamento = 'UPLOADED'
                    imagem.save(update_fields=['arquivo_original', 'status_processamento'])

                    # 3. Dispara a tarefa Celery para processamento
                    processar_imagem_task.delay(imagem.id)
                    uploaded_count += 1

            messages.success(request,
                             f'{uploaded_count} imagem(ns) enviada(s) com sucesso. O processamento começará em breve.')
            return redirect('repositorio:gerenciar_galerias')

        return render(request, self.template_name, {'form': form})


# --------------------------------------------------------------------------
# 3. Formulário para Galeria (CORRIGIDO)
# --------------------------------------------------------------------------

class GaleriaForm(forms.ModelForm):
    """Formulário para criar/editar a Galeria."""

    class Meta:
        model = Galeria
        # CORRIGIDO: Campos devem ser os nomes corretos do models.py
        fields = ['nome', 'descricao', 'status', 'grupos_acesso', 'watermark_config']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['grupos_acesso'].widget = forms.CheckboxSelectMultiple()
        self.fields['nome'].label = "Título da Galeria" # Ajusta o label para o que era esperado

# --------------------------------------------------------------------------
# 4. View para Criação/Edição de Galeria
# --------------------------------------------------------------------------

class CriarGaleriaView(FotografoRequiredMixin, CreateView):
    """
    Cria uma nova galeria. Não anexa imagens aqui; isso é feito
    na GerenciarImagensGaleriaView.
    """
    model = Galeria
    form_class = GaleriaForm
    template_name = 'repositorio/criar_galeria.html'
    success_url = reverse_lazy('repositorio:gerenciar_galerias')

    def form_valid(self, form):
        form.instance.fotografo = self.request.user
        response = super().form_valid(form)
        galeria = self.object

        # CORRIGIDO: O campo é 'nome', não 'titulo'
        messages.success(self.request, f'Galeria "{galeria.nome}" criada com sucesso. Anexe as imagens agora.')

        # Redireciona para o novo painel de gerenciamento de imagens
        return redirect('repositorio:gerenciar_imagens_galeria', pk=galeria.pk)

    def get_object(self, queryset=None):
        # Permite que a mesma view seja usada para edição (UpdateView behavior)
        if 'pk' in self.kwargs:
            return get_object_or_404(Galeria, pk=self.kwargs['pk'], fotografo=self.request.user)
        return None  # Caso contrário, é uma nova criação

    # Se for edição, herda UpdateView logicamente
    def get_success_url(self):
        if self.object and self.object.pk:
            # Ao salvar a edição, retorna para a listagem
            return reverse_lazy('repositorio:gerenciar_galerias')
        return self.success_url


# --------------------------------------------------------------------------
# 5. View para Gerenciamento de Galerias (Listagem)
# --------------------------------------------------------------------------

class GerenciarGaleriasView(FotografoRequiredMixin, ListView):
    """
    Lista todas as galerias criadas pelo fotógrafo logado.
    """
    model = Galeria
    template_name = 'repositorio/gerenciar_galerias.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def get_queryset(self):
        # Filtra apenas as galerias criadas pelo usuário logado e anota o count
        return Galeria.objects.filter(fotografo=self.request.user).annotate(
            imagens_count=models.Count('imagens')
        ).order_by('-criado_em')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Inclui o número de imagens processadas que ainda não estão em nenhuma galeria
        context['imagens_disponiveis_count'] = Imagem.objects.filter(
            status_processamento='PROCESSADA',
            galeria__isnull=True,
            # (Opcional) Filtra por imagens que o fotógrafo enviou
            # fotografo_id=self.request.user.id
        ).count()
        return context


# --------------------------------------------------------------------------
# 6. View para Gerenciamento de Imagens da Galeria
# --------------------------------------------------------------------------

class GerenciarImagensGaleriaView(FotografoRequiredMixin, View):
    """
    Permite visualizar e vincular/desvincular imagens a uma galeria específica.
    Usa o template 'repositorio/gerenciar_imagens_galeria.html'.
    """
    template_name = 'repositorio/gerenciar_imagens_galeria.html'

    def get(self, request, pk):
        # Garante que a galeria exista e pertença ao fotógrafo logado
        galeria = get_object_or_404(
            Galeria.objects.prefetch_related('imagens'),
            pk=pk,
            fotografo=request.user
        )

        # 1. Imagens já vinculadas à galeria (para pré-seleção)
        imagens_vinculadas_pks = galeria.imagens.values_list('pk', flat=True)

        # 2. Todas as imagens disponíveis no repositório do fotógrafo.
        # Filtra por imagens processadas (prontas para uso) OU que já estão nesta galeria
        todas_imagens_repositorio = Imagem.objects.filter(
            status_processamento='PROCESSADA',
            # (Opcional) Filtra pelo fotógrafo (se Imagem tiver esse campo)
            # fotografo=request.user
        ).filter(
            models.Q(galeria__isnull=True) | models.Q(galeria=galeria)
        ).order_by('-criado_em')

        context = {
            'galeria': galeria,
            'todas_imagens_repositorio': todas_imagens_repositorio,
            'imagens_vinculadas_pks': list(imagens_vinculadas_pks),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        galeria = get_object_or_404(Galeria, pk=pk, fotografo=request.user)

        # Recebe a lista de PKs das imagens selecionadas (do checkbox name="imagens")
        imagens_selecionadas_pks = request.POST.getlist('imagens')

        # Converte para inteiros para segurança
        imagens_selecionadas_pks = [int(p) for p in imagens_selecionadas_pks if p.isdigit()]

        with transaction.atomic():
            # Desvincular todas as imagens que PERTENCIAM à galeria, mas não estão na lista
            Imagem.objects.filter(galeria=galeria).exclude(pk__in=imagens_selecionadas_pks).update(galeria=None)

            # Vincular as imagens selecionadas à galeria (se já não estiverem)
            Imagem.objects.filter(pk__in=imagens_selecionadas_pks).update(galeria=galeria)

        # CORRIGIDO: O campo é 'nome', não 'titulo'
        messages.success(request, f'Imagens da galeria "{galeria.nome}" atualizadas com sucesso.')
        return redirect('repositorio:gerenciar_imagens_galeria', pk=galeria.pk)


# --------------------------------------------------------------------------
# 7. View para Exclusão de Galeria (ADICIONADO)
# --------------------------------------------------------------------------

class ExcluirGaleriaView(FotografoRequiredMixin, DeleteView):
    """
    Exclui uma galeria, exigindo confirmação.
    Nota: O campo Galeria.imagens é Nullable, então as imagens vinculadas
    apenas terão o campo 'galeria' definido como NULL.
    """
    model = Galeria
    template_name = 'repositorio/excluir_galeria_confirm.html'
    success_url = reverse_lazy('repositorio:gerenciar_galerias')
    context_object_name = 'galeria'

    def get_queryset(self):
        # Garante que apenas o fotógrafo proprietário possa excluir
        return self.model.objects.filter(fotografo=self.request.user)

    def form_valid(self, form):
        # Mensagem de sucesso antes da exclusão
        messages.success(self.request, f'Galeria "{self.object.nome}" excluída com sucesso.')
        return super().form_valid(form)