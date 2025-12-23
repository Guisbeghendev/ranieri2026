from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse  # IMPORTADO REVERSE
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
from .tasks import processar_imagem_task
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
    Gera uma URL pré-assinada (PUT) para que o cliente possa enviar o arquivo
    diretamente para o S3.
    """

    def post(self, request):
        nome_arquivo_original = request.POST.get('nome_arquivo')
        mime_type = request.POST.get('tipo_mime')
        galeria_id = request.POST.get('galeria_id')

        if not nome_arquivo_original or not mime_type:
            return JsonResponse({'erro': 'Nome do arquivo e tipo MIME são obrigatórios.'}, status=400)

        galeria = None
        if galeria_id:
            if request.user.is_superuser or request.user.is_fotografo_master:
                galeria = get_object_or_404(Galeria, pk=galeria_id)
            else:
                galeria = get_object_or_404(Galeria, pk=galeria_id, fotografo=request.user)

        nome_base, extensao = os.path.splitext(nome_arquivo_original)
        extensao_limpa = extensao.lstrip('.')
        nome_arquivo_unico = f'{uuid.uuid4()}.{extensao_limpa}'

        caminho_s3 = f'repo/originais/{nome_arquivo_unico}'

        try:
            aws_key_id = settings.AWS_ACCESS_KEY_ID
            aws_secret = settings.AWS_SECRET_ACCESS_KEY
            aws_region = settings.AWS_S3_REGION_NAME
            aws_endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME

            if not bucket_name:
                raise ValueError("AWS_STORAGE_BUCKET_NAME não configurado.")

            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_key_id,
                aws_secret_access_key=aws_secret,
                region_name=aws_region,
                endpoint_url=aws_endpoint
            )

            url_assinada = s3_client.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': caminho_s3,
                    'ContentType': mime_type,
                },
                ExpiresIn=3600,  # 1 hora
                HttpMethod='PUT'
            )

            # Cria o registro Imagem no banco (status UPLOAD_PENDENTE)
            imagem = Imagem.objects.create(
                nome_arquivo_original=nome_arquivo_original,
                arquivo_original=caminho_s3,
                status_processamento='UPLOAD_PENDENTE',
                fotografo=request.user,
                galeria=galeria
            )

            return JsonResponse({
                'url_assinada': url_assinada,
                'caminho_s3': caminho_s3,
                'imagem_id': imagem.pk,
            })

        except ValueError as e:
            return JsonResponse({'erro': f'Erro de Configuração: {str(e)}'}, status=500)
        except (NoCredentialsError, PartialCredentialsError) as e:
            return JsonResponse({'erro': 'Erro de Credenciais AWS. Verifique as configurações (KEY, SECRET) no .env.'},
                                status=403)
        except ClientError as e:
            error_message = e.response.get('Error', {}).get('Message', 'Erro desconhecido do S3.')
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'AccessDenied':
                return JsonResponse(
                    {'erro': f'Acesso negado ao S3. Verifique as permissões do Bucket: {error_message}'}, status=403)
            return JsonResponse({'erro': f'Erro ao interagir com S3: {error_message}'}, status=500)
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({
                'erro': f'Erro interno ao assinar upload. Verifique as configurações S3 ou a instalação do Boto3: {type(e).__name__}'},
                status=500)


# --------------------------------------------------------------------------
# 4. View: Confirmação de Upload S3 e Disparo do Celery
# --------------------------------------------------------------------------

class ConfirmarUploadView(FotografoRequiredMixin, View):
    """
    Recebe a confirmação de sucesso do upload S3 via JavaScript,
    atualiza o status no banco e dispara a tarefa de processamento.
    """

    def post(self, request):
        imagem_id = request.POST.get('imagem_id')

        if not imagem_id:
            return JsonResponse({'erro': 'ID da imagem é obrigatório.'}, status=400)

        try:
            # 1. Recupera o objeto Imagem
            imagem = get_object_or_404(
                Imagem,
                pk=imagem_id,
                fotografo=request.user,
                status_processamento='UPLOAD_PENDENTE'
            )

            # 2. Atualiza o status para UPLOADED e salva
            imagem.status_processamento = 'UPLOADED'
            imagem.save(update_fields=['status_processamento'])

            # 3. Dispara a tarefa Celery para processamento assíncrono
            processar_imagem_task.delay(imagem.id)

            return JsonResponse({
                'sucesso': True,
                'mensagem': f'Imagem {imagem.pk} confirmada. Processamento iniciado.'
            })

        except Imagem.DoesNotExist:
            return JsonResponse({'erro': 'Imagem não encontrada ou sem permissão.'}, status=404)
        except Exception as e:
            return JsonResponse({'erro': f'Erro ao confirmar o upload: {str(e)}'}, status=500)


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

        # Superuser e Fotógrafo Master podem ver TODAS as galerias
        if user.is_superuser or user.is_fotografo_master:
            queryset = Galeria.objects.all()
        # Fotógrafo normal vê apenas as suas
        else:
            queryset = Galeria.objects.filter(fotografo=user)

        # ADIÇÃO: Otimização para carregar o objeto de capa
        queryset = queryset.select_related('capa')

        # Anota a contagem de imagens em todas as galerias
        return queryset.annotate(
            imagens_count=models.Count('imagens')
        ).order_by('-criado_em')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        q_filter = models.Q(status_processamento='PROCESSADA') & models.Q(galeria__isnull=True)

        if self.request.user.is_superuser or self.request.user.is_fotografo_master:
            pass
        else:
            q_filter &= models.Q(fotografo=self.request.user)

        context['imagens_disponiveis_count'] = Imagem.objects.filter(q_filter).count()

        context[
            'is_fotografo_master_or_superuser'] = self.request.user.is_superuser or self.request.user.is_fotografo_master

        # CORREÇÃO CRÍTICA: Itera sobre as galerias e anexa a URL do proxy da capa
        for galeria in context['object_list']:
            if galeria.capa and galeria.capa.arquivo_processado:
                try:
                    # Gera a URL segura para servir a imagem de capa (proxy)
                    galeria.capa_proxy_url = reverse(
                        'private_media_proxy',
                        kwargs={'path': galeria.capa.arquivo_processado.name}
                    )
                except Exception:
                    # Em caso de erro na geração (e.g., URL reversa não existe), define como None
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

        # CORREÇÃO: Removido 'arquivo_processado' do select_related dentro do Prefetch.
        # 'arquivo_processado' não é um campo relacional (FK/OneToOne).
        # Apenas 'fotografo' e 'galeria' podem ser usados aqui.
        galeria_qs = Galeria.objects.select_related('capa').prefetch_related(
            Prefetch(
                'imagens',
                queryset=Imagem.objects.select_related('fotografo', 'galeria').order_by('-criado_em'),
                to_attr='imagens_anexadas_list'
            )
        )

        if user.is_superuser or user.is_fotografo_master:
            galeria = get_object_or_404(
                galeria_qs,
                pk=pk
            )
        else:
            galeria = get_object_or_404(
                galeria_qs,
                pk=pk,
                fotografo=user
            )

        proprietario_filter = models.Q()
        if not user.is_superuser and not user.is_fotografo_master:
            proprietario_filter = models.Q(fotografo=user)

        # Filtro para Imagens Disponíveis para Anexo: PROCESSADA e livre (galeria__isnull=True)
        q_disponiveis = models.Q(
            status_processamento='PROCESSADA',
            galeria__isnull=True
        ) & proprietario_filter

        # Filtro para Imagens JÁ Anexadas a ESTA Galeria:
        q_anexadas = models.Q(galeria=galeria) & proprietario_filter

        # Combinação: Imagens Disponíveis OU Imagens JÁ Anexadas a ESTA Galeria
        q_final = q_disponiveis | q_anexadas

        # Busca todas as imagens que podem ser exibidas/selecionadas nesta tela
        todas_imagens_repositorio = Imagem.objects.filter(q_final).order_by('-criado_em')

        # Recalcula a lista de PKs das imagens vinculadas (usada pelo template)
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

        if user.is_superuser or user.is_fotografo_master:
            imagens_permitidas = Imagem.objects.filter(
                pk__in=imagens_selecionadas_pks,
                status_processamento='PROCESSADA'
            )
        else:
            imagens_permitidas = Imagem.objects.filter(
                pk__in=imagens_selecionadas_pks,
                status_processamento='PROCESSADA',
                fotografo=user
            )

        imagens_selecionadas_pks_finais = list(imagens_permitidas.values_list('pk', flat=True))

        with transaction.atomic():
            # 1. Desvincular as imagens que não foram selecionadas
            imagens_a_desvincular_qs = Imagem.objects.filter(galeria=galeria).exclude(
                pk__in=imagens_selecionadas_pks_finais)

            if not user.is_superuser and not user.is_fotografo_master:
                imagens_a_desvincular_qs = imagens_a_desvincular_qs.filter(fotografo=user)

            imagens_a_desvincular_qs.update(galeria=None)

            # 2. Vincular e re-processar para aplicar marca d'água
            novas_imagens = Imagem.objects.filter(pk__in=imagens_selecionadas_pks_finais)
            novas_imagens.update(galeria=galeria)

            # DISPARA O PROCESSAMENTO PARA TODAS AS SELECIONADAS PARA GARANTIR MARCA D'ÁGUA
            for img in novas_imagens:
                processar_imagem_task.delay(img.id)

        messages.success(request, f'Imagens da galeria "{galeria.nome}" atualizadas com sucesso.')
        return redirect('repositorio:gerenciar_imagens_galeria', pk=galeria.pk)


# --------------------------------------------------------------------------
# 8. NOVA VIEW: Definir Capa da Galeria (AJAX)
# --------------------------------------------------------------------------

class DefinirCapaGaleriaView(FotografoRequiredMixin, View):
    """
    Define uma Imagem específica como a capa de uma Galeria.
    Endpoint usado via AJAX a partir da tela de gerenciamento de imagens.
    """

    def post(self, request, galeria_pk, imagem_pk):
        user = request.user

        # Filtro de permissão para a Imagem
        imagem_filter = {'pk': imagem_pk, 'status_processamento': 'PROCESSADA'}
        if not user.is_superuser and not user.is_fotografo_master:
            imagem_filter['fotografo'] = user

        try:
            # 1. Recupera a Galeria (garante permissão)
            if user.is_superuser or user.is_fotografo_master:
                galeria = get_object_or_404(Galeria, pk=galeria_pk)
            else:
                galeria = get_object_or_404(Galeria, pk=galeria_pk, fotografo=user)

            # 2. Recupera a Imagem (garante que ela é permitida, processada E pertence ao usuário/Master)
            imagem = get_object_or_404(
                Imagem,
                **imagem_filter
            )

            # 3. VERIFICAÇÃO ADICIONAL: A imagem deve estar vinculada à galeria ou ser uma imagem
            # que o usuário tem permissão para anexar e está no repositório.
            if imagem.galeria != galeria:
                # Se a imagem estiver em outra galeria, não permite a capa.
                if imagem.galeria is not None:
                    return JsonResponse({
                        'sucesso': False,
                        'erro': 'A imagem selecionada já está em outra galeria e precisa ser desvinculada primeiro.'
                    }, status=400)

                # Anexa à galeria se estiver livre e for permitida.
                if imagem.status_processamento == 'PROCESSADA' and (
                        user.is_superuser or user.is_fotografo_master or imagem.fotografo == user):
                    imagem.galeria = galeria
                    imagem.save(update_fields=['galeria'])
                    processar_imagem_task.delay(imagem.id)
                else:
                    return JsonResponse({
                        'sucesso': False,
                        'erro': 'A imagem selecionada não está disponível para ser anexada e definida como capa.'
                    }, status=400)

            # GARANTE que a imagem está anexada à galeria correta.
            # Este check garante que a operação de anexo (se necessária) foi bem-sucedida antes de definir a capa.
            if imagem.galeria != galeria:
                return JsonResponse({
                    'sucesso': False,
                    'erro': 'Falha ao anexar a imagem à galeria. Operação abortada.'
                }, status=500)

            # 4. Define a capa e salva a galeria
            galeria.capa = imagem
            galeria.save(update_fields=['capa', 'alterado_em'])

            # Geração da URL do Proxy
            capa_url_proxy = reverse('private_media_proxy', kwargs={'path': imagem.arquivo_processado.name})

            return JsonResponse({
                'sucesso': True,
                'message': f'Imagem {imagem.pk} definida como capa da galeria "{galeria.nome}".',
                'capa_url': capa_url_proxy  # RETORNA A URL DO PROXY
            })

        except Imagem.DoesNotExist:
            return JsonResponse({'sucesso': False, 'erro': 'Imagem não encontrada ou não processada.'}, status=404)
        except Galeria.DoesNotExist:
            return JsonResponse({'sucesso': False, 'erro': 'Galeria não encontrada ou sem permissão.'}, status=404)
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'sucesso': False, 'erro': f'Erro interno: {str(e)}'}, status=500)


# --------------------------------------------------------------------------
# 9. View para Exclusão de Galeria
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
# 10. View para Publicação de Galeria
# --------------------------------------------------------------------------

class PublicarGaleriaView(FotografoRequiredMixin, View):
    """
    Define o status da galeria como 'PUBLICADA'.
    """

    def post(self, request, pk):
        user = request.user
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if user.is_superuser or user.is_fotografo_master:
            galeria = get_object_or_404(Galeria, pk=pk)
        else:
            galeria = get_object_or_404(Galeria, pk=pk, fotografo=user)

        publicado = galeria.publicar()

        if publicado:
            # --- NOTIFICAÇÃO WEBSOCKET ---
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
            # -----------------------------
            message = f'Galeria "{galeria.nome}" publicada com sucesso!'
        else:
            message = f'Galeria "{galeria.nome}" já estava publicada.'

        if is_ajax:
            return JsonResponse({
                'status': galeria.status,
                'message': message,
                'status_mudou': publicado
            })

        if publicado:
            messages.success(request, message)
        else:
            messages.info(request, message)

        return HttpResponseRedirect(reverse_lazy('repositorio:gerenciar_galerias'))


# --------------------------------------------------------------------------
# 11. View para Arquivamento de Galeria
# --------------------------------------------------------------------------

class ArquivarGaleriaView(FotografoRequiredMixin, View):
    """
    Define o status da galeria como 'ARQUIVADA'.
    """

    def post(self, request, pk):
        user = request.user
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if user.is_superuser or user.is_fotografo_master:
            galeria = get_object_or_404(Galeria, pk=pk)
        else:
            galeria = get_object_or_404(Galeria, pk=pk, fotografo=user)

        arquivado = galeria.arquivar()

        if arquivado:
            # --- NOTIFICAÇÃO WEBSOCKET ---
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
            # -----------------------------
            message = f'Galeria "{galeria.nome}" arquivada com sucesso!'
        else:
            message = f'Galeria "{galeria.nome}" já estava arquivada.'

        if is_ajax:
            return JsonResponse({
                'status': galeria.status,
                'message': message,
                'status_mudou': arquivado
            })

        if arquivado:
            messages.success(request, message)
        else:
            messages.info(request, message)

        return HttpResponseRedirect(reverse_lazy('repositorio:gerenciar_galerias'))