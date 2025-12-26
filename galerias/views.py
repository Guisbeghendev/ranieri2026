# galerias/views.py
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponse
from django.db.models import Q
from repositorio.models import Galeria, Curtida, Imagem
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.conf import settings
import os
import mimetypes
import boto3
from botocore.exceptions import ClientError
import traceback


class GaleriaAccessMixin:
    """
    Método que verifica se o usuário tem permissão para acessar a galeria.
    Retorna True se tiver acesso, False caso contrário.
    """

    def has_access(self, galeria, user):
        if user.is_authenticated and user.is_superuser:
            return galeria.status == 'PB'

        if galeria.status != 'PB':
            return False

        if galeria.acesso_publico:
            return True

        if not user.is_authenticated:
            return False

        user_auth_groups = user.groups.all()
        return galeria.grupos_acesso.filter(auth_group__in=user_auth_groups).exists()


# ----------------------------------------------------------------------
# 1. LISTAGEM PÚBLICA (Independente de Login)
# ----------------------------------------------------------------------
class GaleriaPublicaListView(ListView):
    """
    View para exibir APENAS galerias públicas.
    Template: galerias/lista_publicas.html
    """
    model = Galeria
    template_name = 'galerias/lista_publicas.html'
    context_object_name = 'galerias'

    def get_queryset(self):
        return Galeria.objects.filter(
            status='PB',
            acesso_publico=True
        ).order_by('-data_do_evento').prefetch_related('capa')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for galeria in context['galerias']:
            if galeria.capa and galeria.capa.arquivo_processado:
                try:
                    galeria.capa_proxy_url = reverse(
                        'galerias:private_media_proxy',
                        kwargs={'path': galeria.capa.arquivo_processado.name}
                    )
                except Exception:
                    galeria.capa_proxy_url = None
        return context


# ----------------------------------------------------------------------
# 2. LISTAGEM RESTRITA (Apenas para Usuários Logados)
# ----------------------------------------------------------------------
class GaleriaListView(LoginRequiredMixin, GaleriaAccessMixin, ListView):
    """
    View para exibir galerias exclusivas (restritas aos grupos do usuário).
    Uma galeria aparece aqui se o usuário pertencer ao grupo vinculado,
    mesmo que ela também seja marcada como pública.
    Template: galerias/lista_galerias.html
    """
    model = Galeria
    template_name = 'galerias/lista_galerias.html'
    context_object_name = 'galerias_exclusivas'

    def get_queryset(self):
        user = self.request.user
        queryset_base = Galeria.objects.filter(
            status='PB'
        ).order_by('-data_do_evento').prefetch_related('capa', 'grupos_acesso__auth_group')

        if user.is_superuser:
            # Superuser vê tudo o que tem grupo vinculado (cumulativo com público ou não)
            return queryset_base.filter(grupos_acesso__isnull=False).distinct()

        # Filtra galerias que pertencem aos grupos do usuário
        return queryset_base.filter(
            grupos_acesso__auth_group__in=user.groups.all()
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for galeria in context['galerias_exclusivas']:
            if galeria.capa and galeria.capa.arquivo_processado:
                try:
                    galeria.capa_proxy_url = reverse(
                        'galerias:private_media_proxy',
                        kwargs={'path': galeria.capa.arquivo_processado.name}
                    )
                except Exception:
                    galeria.capa_proxy_url = None
        return context


# ----------------------------------------------------------------------
# 3. DETALHE DA GALERIA
# ----------------------------------------------------------------------
class GaleriaDetailView(GaleriaAccessMixin, DetailView):
    model = Galeria
    template_name = 'galerias/detalhe_galeria.html'
    context_object_name = 'galeria'

    def get_queryset(self):
        return Galeria.objects.prefetch_related(
            'imagens__curtidas',
            'imagens',
        ).select_related('fotografo')

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Galeria.DoesNotExist:
            return redirect(reverse('galerias:lista_publicas'))

        if not self.has_access(self.object, request.user):
            return redirect(reverse('galerias:lista_publicas'))

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        galeria = context['galeria']
        user = self.request.user

        curtidas_pelo_usuario = {}
        curtidas_totais_galeria = 0

        for imagem in galeria.imagens.all():
            curtidas_count = imagem.curtidas.count()
            curtidas_totais_galeria += curtidas_count

            if user.is_authenticated:
                curtida_existe = imagem.curtidas.filter(usuario=user).exists()
                curtidas_pelo_usuario[imagem.pk] = curtida_existe
            else:
                curtidas_pelo_usuario[imagem.pk] = False

            if imagem.arquivo_processado:
                try:
                    imagem.proxy_url = reverse(
                        'galerias:private_media_proxy',
                        kwargs={'path': imagem.arquivo_processado.name}
                    )
                except Exception:
                    imagem.proxy_url = None
            else:
                imagem.proxy_url = None

        context['curtidas_totais_galeria'] = curtidas_totais_galeria
        context['curtidas_pelo_usuario'] = curtidas_pelo_usuario
        context['proxy_url_name'] = 'private_media_proxy'

        return context


# ----------------------------------------------------------------------
# 4. INTERAÇÃO: CURTIR/DESCURTIR
# ----------------------------------------------------------------------
class CurtirView(LoginRequiredMixin, View):
    def post(self, request, imagem_pk, *args, **kwargs):
        user = request.user
        imagem = get_object_or_404(Imagem, pk=imagem_pk)
        galeria = imagem.galeria

        if not GaleriaAccessMixin().has_access(galeria, user):
            return JsonResponse({'success': False, 'message': 'Acesso negado.'}, status=403)

        curtida_qs = Curtida.objects.filter(usuario=user, imagem=imagem)
        if curtida_qs.exists():
            curtida_qs.delete()
            curtiu = False
            message = 'Curtida removida.'
        else:
            Curtida.objects.create(usuario=user, imagem=imagem)
            curtiu = True
            message = 'Imagem curtida!'

        new_count = Curtida.objects.filter(imagem=imagem).count()

        return JsonResponse({
            'success': True,
            'curtiu': curtiu,
            'new_count': new_count,
            'message': message
        })


# ----------------------------------------------------------------------
# 5. PROXY DE MÉDIA PRIVADA S3
# ----------------------------------------------------------------------
class PrivateMediaProxyView(View):
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    def get(self, request, *args, **kwargs):
        file_path = kwargs.get('path')
        user = request.user

        try:
            imagem = Imagem.objects.get(arquivo_processado__endswith=file_path)
            galeria = imagem.galeria
        except (Imagem.DoesNotExist, Imagem.MultipleObjectsReturned):
            return HttpResponseBadRequest('Arquivo não encontrado.')

        if not GaleriaAccessMixin().has_access(galeria, user):
            return HttpResponseForbidden('Acesso negado.')

        try:
            s3_object_key = imagem.arquivo_processado.name
            s3_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_object_key)

            content_type = s3_response.get('ContentType',
                                           mimetypes.guess_type(file_path)[0] or 'application/octet-stream')
            content_length = s3_response.get('ContentLength')

            response = HttpResponse(s3_response['Body'].read(), content_type=content_type)
            response['Content-Length'] = content_length
            return response

        except ClientError as e:
            return HttpResponseBadRequest('Erro ao acessar o armazenamento.')
        except Exception as e:
            return HttpResponseBadRequest(f'Erro interno.')