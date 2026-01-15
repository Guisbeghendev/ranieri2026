from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import View, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.db import transaction
from django import forms
from django.db import models
import boto3
from django.conf import settings
import uuid
import os
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from users.models import Grupo
from django.contrib.auth import get_user_model
import traceback
from django.db.models import Prefetch

# --- ADICIONADO PARA WEBSOCKET ---
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
# --------------------------------

from .models import Imagem, Galeria, WatermarkConfig
from .tasks import processar_imagem_task, girar_imagem_task  # Importação da nova task
from .forms import GaleriaForm

User = get_user_model()


# --------------------------------------------------------------------------
# Mixins de Permissão
# --------------------------------------------------------------------------

class FotografoRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Exige que o usuário esteja logado e tenha permissão de Fotógrafo (ou Superuser).
    """

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
                user.is_superuser or user.is_fotografo_master or user.is_fotografo
        )


# --------------------------------------------------------------------------
# 1. Formulário Customizado para Upload Múltiplo (MANTIDO AQUI)
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
# 2. View para Upload de Imagens (Apenas GET para renderizar)
# --------------------------------------------------------------------------

class UploadImagemView(FotografoRequiredMixin, View):
    """
    Renderiza o template de upload.
    O POST é ignorado (ou simplificado), pois o upload será tratado via JS e S3.
    """
    form_class = ImagemUploadForm
    template_name = 'repositorio/upload_imagem.html'

    def get(self, request):
        return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request):
        messages.info(request, "O upload direto está sendo processado. Acompanhe o status.")
        return redirect('repositorio:gerenciar_galerias')


# --------------------------------------------------------------------------
# 3. View: Assinar o Upload S3 (Para JS obter URL pré-assinada)
# --------------------------------------------------------------------------

class AssinarUploadView(FotografoRequiredMixin, View):
    """
    Gera URL pré-assinada e cria o registro com status inicial.
    """

    def post(self, request):
        try:
            nome_arquivo_original = request.POST.get('nome_arquivo')
            mime_type = request.POST.get('tipo_mime')
            galeria_id = request.POST.get('galeria_id')

            ext = os.path.splitext(nome_arquivo_original)[1]
            nome_unico = f"{uuid.uuid4()}{ext}"
            caminho_s3 = f"repo/originais/{nome_unico}"

            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
                config=boto3.session.Config(signature_version='s3v4')
            )

            # CORREÇÃO: Estrutura correta para o FormData do JS
            post_data = s3_client.generate_presigned_post(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=caminho_s3,
                Fields={"Content-Type": mime_type},
                Conditions=[{"Content-Type": mime_type}],
                ExpiresIn=3600
            )

            imagem = Imagem.objects.create(
                nome_arquivo_original=nome_arquivo_original,
                arquivo_original=caminho_s3,
                status_processamento='UPLOAD_PENDENTE',
                fotografo=request.user,
                galeria_id=galeria_id if galeria_id else None
            )

            return JsonResponse({
                'url_assinada': post_data['url'],
                'campos_assinados': post_data['fields'],
                'imagem_id': imagem.pk,
            })
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)


# --------------------------------------------------------------------------
# 4. View: Confirmação de Upload S3 e Disparo do Celery
# --------------------------------------------------------------------------

class ConfirmarUploadView(FotografoRequiredMixin, View):
    """
    REFORMULADA: Recebe confirmação do JS e dispara Celery com SEGURANÇA.
    """

    def post(self, request):
        imagem_id = request.POST.get('imagem_id')
        total_arquivos = int(request.POST.get('total_files', 1))
        indice_atual = int(request.POST.get('current_index', 1))

        if not imagem_id:
            return JsonResponse({'erro': 'ID da imagem é obrigatório.'}, status=400)

        try:
            with transaction.atomic():
                imagem = get_object_or_404(
                    Imagem,
                    pk=imagem_id,
                    fotografo=request.user,
                    status_processamento='UPLOAD_PENDENTE'
                )

                imagem.status_processamento = 'UPLOADED'
                imagem.save(update_fields=['status_processamento'])

                # CORREÇÃO: Passagem explícita de argumentos na lambda para evitar closure issues
                transaction.on_commit(
                    lambda i_id=imagem.id, t=total_arquivos, idx=indice_atual:
                    processar_imagem_task.delay(
                        imagem_id=i_id,
                        total_arquivos=t,
                        indice_atual=idx
                    )
                )

            return JsonResponse({
                'sucesso': True,
                'imagem_id': imagem.id,
                'mensagem': f'Arquivo {indice_atual}/{total_arquivos} pronto para processamento.'
            })

        except Exception as e:
            return JsonResponse({'erro': f'Erro ao confirmar: {str(e)}'}, status=500)


# --------------------------------------------------------------------------
# 5. View para Criação/Edição de Galeria
# --------------------------------------------------------------------------

class CriarGaleriaView(FotografoRequiredMixin, CreateView):
    model = Galeria
    form_class = GaleriaForm
    template_name = 'repositorio/criar_galeria.html'
    success_url = reverse_lazy('repositorio:gerenciar_galerias')

    def form_valid(self, form):
        form.instance.fotografo = self.request.user
        response = super().form_valid(form)
        galeria = self.object

        messages.success(self.request, f'Galeria "{galeria.nome}" criada com sucesso. Anexe as imagens agora.')

        return redirect('repositorio:gerenciar_imagens_galeria', pk=galeria.pk)

    def get_object(self, queryset=None):
        if 'pk' in self.kwargs:
            return get_object_or_404(Galeria, pk=self.kwargs['pk'], fotografo=self.request.user)
        return None

    def get_success_url(self):
        if self.object and self.object.pk:
            return reverse_lazy('repositorio:gerenciar_galerias')
        return self.success_url


# --------------------------------------------------------------------------
# 6. View para Gerenciamento de Galerias (Listagem)
# --------------------------------------------------------------------------

class GerenciarGaleriasView(FotografoRequiredMixin, ListView):
    model = Galeria
    template_name = 'repositorio/gerenciar_galerias.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or user.is_fotografo_master:
            queryset = Galeria.objects.all()
        else:
            queryset = Galeria.objects.filter(fotografo=user)

        queryset = queryset.select_related('capa')

        return queryset.annotate(
            imagens_count=models.Count('imagens')
        ).order_by('-criado_em')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        q_filter = models.Q(status_processamento='PROCESSADA') & models.Q(galeria__isnull=True)

        if not (self.request.user.is_superuser or self.request.user.is_fotografo_master):
            q_filter &= models.Q(fotografo=self.request.user)

        context['imagens_disponiveis_count'] = Imagem.objects.filter(q_filter).count()
        context[
            'is_fotografo_master_or_superuser'] = self.request.user.is_superuser or self.request.user.is_fotografo_master

        for galeria in context['object_list']:
            if galeria.capa and galeria.capa.arquivo_processado:
                try:
                    galeria.capa_proxy_url = reverse(
                        'private_media_proxy',
                        kwargs={'path': galeria.capa.arquivo_processado.name}
                    )
                except Exception:
                    galeria.capa_proxy_url = None
            else:
                galeria.capa_proxy_url = None

        return context


# --------------------------------------------------------------------------
# 7. View para Gerenciamento de Imagens da Galeria
# --------------------------------------------------------------------------

class GerenciarImagensGaleriaView(FotografoRequiredMixin, View):
    template_name = 'repositorio/gerenciar_imagens_galeria.html'

    def get(self, request, pk):
        user = request.user

        galeria_qs = Galeria.objects.select_related('capa').prefetch_related(
            Prefetch(
                'imagens',
                queryset=Imagem.objects.select_related('fotografo', 'galeria').order_by('-criado_em'),
                to_attr='imagens_anexadas_list'
            )
        )

        if user.is_superuser or user.is_fotografo_master:
            galeria = get_object_or_404(galeria_qs, pk=pk)
        else:
            galeria = get_object_or_404(galeria_qs, pk=pk, fotografo=user)

        proprietario_filter = models.Q()
        if not user.is_superuser and not user.is_fotografo_master:
            proprietario_filter = models.Q(fotografo=user)

        q_disponiveis = models.Q(
            status_processamento__in=['PROCESSADA', 'UPLOADED', 'PROCESSANDO', 'ERRO'],
            galeria__isnull=True
        ) & proprietario_filter

        q_anexadas = models.Q(galeria=galeria) & proprietario_filter
        q_final = q_disponiveis | q_anexadas

        todas_imagens_repositorio = Imagem.objects.filter(q_final).order_by('-criado_em')
        imagens_vinculadas_pks = todas_imagens_repositorio.filter(galeria=galeria).values_list('pk', flat=True)

        context = {
            'galeria': galeria,
            'todas_imagens_repositorio': todas_imagens_repositorio,
            'imagens_vinculadas_pks': list(imagens_vinculadas_pks),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        user = request.user

        if user.is_superuser or user.is_fotografo_master:
            galeria = get_object_or_404(Galeria, pk=pk)
        else:
            galeria = get_object_or_404(Galeria, pk=pk, fotografo=user)

        imagens_selecionadas_pks = request.POST.getlist('imagens')
        imagens_selecionadas_pks = [int(p) for p in imagens_selecionadas_pks if p.isdigit()]

        status_permitidos = ['PROCESSADA', 'UPLOADED', 'PROCESSANDO', 'ERRO']

        proprietario_filter = models.Q()
        if not user.is_superuser and not user.is_fotografo_master:
            proprietario_filter = models.Q(fotografo=user)

        imagens_permitidas = Imagem.objects.filter(
            pk__in=imagens_selecionadas_pks,
            status_processamento__in=status_permitidos
        ).filter(proprietario_filter)

        imagens_selecionadas_pks_finais = list(imagens_permitidas.values_list('pk', flat=True))

        with transaction.atomic():
            imagens_a_desvincular_qs = Imagem.objects.filter(galeria=galeria).exclude(
                pk__in=imagens_selecionadas_pks_finais)

            if not user.is_superuser and not user.is_fotografo_master:
                imagens_a_desvincular_qs = imagens_a_desvincular_qs.filter(fotografo=user)

            imagens_a_desvincular_qs.update(galeria=None)
            imagens_permitidas.update(galeria=galeria)

            def disparar_tasks(ids):
                for img_id in ids:
                    processar_imagem_task.delay(img_id)

            transaction.on_commit(lambda: disparar_tasks(imagens_selecionadas_pks_finais))

        messages.success(request, f'Imagens da galeria "{galeria.nome}" atualizadas com sucesso.')
        return redirect('repositorio:gerenciar_imagens_galeria', pk=galeria.pk)


# --------------------------------------------------------------------------
# 8. View: Definir Capa da Galeria (AJAX)
# --------------------------------------------------------------------------

class DefinirCapaGaleriaView(FotografoRequiredMixin, View):
    def post(self, request, galeria_pk, imagem_pk):
        user = request.user
        imagem_filter = {'pk': imagem_pk, 'status_processamento': 'PROCESSADA'}
        if not user.is_superuser and not user.is_fotografo_master:
            imagem_filter['fotografo'] = user

        try:
            if user.is_superuser or user.is_fotografo_master:
                galeria = get_object_or_404(Galeria, pk=galeria_pk)
            else:
                galeria = get_object_or_404(Galeria, pk=galeria_pk, fotografo=user)

            imagem = get_object_or_404(Imagem, **imagem_filter)

            if imagem.galeria != galeria:
                if imagem.galeria is not None:
                    return JsonResponse({
                        'sucesso': False,
                        'erro': 'A imagem selecionada já está em outra galeria.'
                    }, status=400)

                with transaction.atomic():
                    imagem.galeria = galeria
                    imagem.save(update_fields=['galeria'])
                    transaction.on_commit(lambda i_id=imagem.id: processar_imagem_task.delay(i_id))

            galeria.capa = imagem
            galeria.save(update_fields=['capa', 'alterado_em'])

            capa_url_proxy = reverse('private_media_proxy', kwargs={'path': imagem.arquivo_processado.name})

            return JsonResponse({
                'sucesso': True,
                'message': f'Capa definida com sucesso.',
                'capa_url': capa_url_proxy
            })

        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


# --------------------------------------------------------------------------
# 9. View para Rotação de Imagem (AJAX)
# --------------------------------------------------------------------------

class GirarImagemView(FotografoRequiredMixin, View):
    """
    View para solicitar a rotação de uma imagem no S3 via Celery + Pillow.
    """

    def post(self, request, pk):
        user = request.user
        proprietario_filter = {'pk': pk}
        if not user.is_superuser and not user.is_fotografo_master:
            proprietario_filter['fotografo'] = user

        imagem = get_object_or_404(Imagem, **proprietario_filter)

        # Altera o status para mostrar as barras de progresso no frontend
        imagem.status_processamento = 'PROCESSANDO'
        imagem.save(update_fields=['status_processamento'])

        # Dispara a task de rotação (90 graus sentido horário)
        girar_imagem_task.delay(imagem_id=imagem.id, graus=-90)

        return JsonResponse({
            'sucesso': True,
            'mensagem': 'A rotação da imagem foi iniciada.'
        })


# --------------------------------------------------------------------------
# 10. View para Exclusão de Galeria
# --------------------------------------------------------------------------

class ExcluirGaleriaView(FotografoRequiredMixin, DeleteView):
    model = Galeria
    template_name = 'repositorio/excluir_galeria_confirm.html'
    success_url = reverse_lazy('repositorio:gerenciar_galerias')
    context_object_name = 'galeria'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_fotografo_master:
            return self.model.objects.all()
        return self.model.objects.filter(fotografo=user)

    def form_valid(self, form):
        messages.success(self.request, f'Galeria "{self.object.nome}" excluída com sucesso.')
        return super().form_valid(form)


# --------------------------------------------------------------------------
# 11. View para Publicação de Galeria
# --------------------------------------------------------------------------

class PublicarGaleriaView(FotografoRequiredMixin, View):
    def post(self, request, pk):
        user = request.user
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if user.is_superuser or user.is_fotografo_master:
            galeria = get_object_or_404(Galeria, pk=pk)
        else:
            galeria = get_object_or_404(Galeria, pk=pk, fotografo=user)

        publicado = galeria.publicar()

        if publicado:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "galerias_status_updates",
                {
                    "type": "status_update",
                    "galeria_id": galeria.pk,
                    "status_code": galeria.status,
                    "status_display": galeria.get_status_display()
                }
            )
            message = f'Galeria "{galeria.nome}" publicada com sucesso!'
        else:
            message = f'Galeria "{galeria.nome}" já estava publicada.'

        if is_ajax:
            return JsonResponse({'status': galeria.status, 'message': message, 'status_mudou': publicado})

        messages.success(request, message) if publicado else messages.info(request, message)
        return HttpResponseRedirect(reverse('repositorio:gerenciar_galerias'))


# --------------------------------------------------------------------------
# 12. View para Arquivamento de Galeria
# --------------------------------------------------------------------------

class ArquivarGaleriaView(FotografoRequiredMixin, View):
    def post(self, request, pk):
        user = request.user
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if user.is_superuser or user.is_fotografo_master:
            galeria = get_object_or_404(Galeria, pk=pk)
        else:
            galeria = get_object_or_404(Galeria, pk=pk, fotografo=user)

        arquivado = galeria.arquivar()

        if arquivado:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "galerias_status_updates",
                {
                    "type": "status_update",
                    "galeria_id": galeria.pk,
                    "status_code": galeria.status,
                    "status_display": galeria.get_status_display()
                }
            )
            message = f'Galeria "{galeria.nome}" arquivada com sucesso!'
        else:
            message = f'Galeria "{galeria.nome}" já estava arquivada.'

        if is_ajax:
            return JsonResponse({'status': galeria.status, 'message': message, 'status_mudou': arquivado})

        messages.success(request, message) if arquivado else messages.info(request, message)
        return HttpResponseRedirect(reverse('repositorio:gerenciar_galerias'))