from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponse
from django.db.models import Q
from repositorio.models import Galeria, Curtida, Imagem
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.conf import settings
import mimetypes
import boto3
from botocore.exceptions import ClientError


class GaleriaAccessMixin:
    """
    Método que verifica se o usuário tem permissão para acessar a galeria.
    """

    def has_access(self, galeria, user):
        if galeria is None:
            return False

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
# 1. LISTAGEM PÚBLICA
# ----------------------------------------------------------------------
class GaleriaPublicaListView(ListView):
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
# 2. LISTAGEM RESTRITA
# ----------------------------------------------------------------------
class GaleriaListView(LoginRequiredMixin, GaleriaAccessMixin, ListView):
    model = Galeria
    template_name = 'galerias/lista_galerias.html'
    context_object_name = 'galerias_exclusivas'

    def get_queryset(self):
        return Galeria.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_superuser:
            from django.contrib.auth.models import Group
            user_groups = Group.objects.filter(grupo_ranieri__isnull=False).distinct()
        else:
            user_groups = user.groups.all()

        grupos_com_galerias = []

        for group in user_groups:
            galerias_do_grupo = Galeria.objects.filter(
                status='PB',
                grupos_acesso__auth_group=group
            ).prefetch_related('capa').order_by('-data_do_evento')

            if galerias_do_grupo.exists():
                for galeria in galerias_do_grupo:
                    if galeria.capa and galeria.capa.arquivo_processado:
                        try:
                            galeria.capa_proxy_url = reverse(
                                'galerias:private_media_proxy',
                                kwargs={'path': galeria.capa.arquivo_processado.name}
                            )
                        except Exception:
                            galeria.capa_proxy_url = None
                    else:
                        galeria.capa_proxy_url = None

                grupos_com_galerias.append({
                    'nome_grupo': group.name,
                    'galerias': galerias_do_grupo
                })

        context['grupos_com_galerias'] = grupos_com_galerias
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
            curtidas_pelo_usuario[imagem.pk] = imagem.curtidas.filter(
                usuario=user).exists() if user.is_authenticated else False

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
        return context


# ----------------------------------------------------------------------
# 4. INTERAÇÃO: CURTIR/DESCURTIR
# ----------------------------------------------------------------------
class CurtirView(LoginRequiredMixin, View):
    def post(self, request, imagem_pk, *args, **kwargs):
        user = request.user
        imagem = get_object_or_404(Imagem, pk=imagem_pk)

        if not GaleriaAccessMixin().has_access(imagem.galeria, user):
            return JsonResponse({'success': False, 'message': 'Acesso negado.'}, status=403)

        curtida_qs = Curtida.objects.filter(usuario=user, imagem=imagem)
        if curtida_qs.exists():
            curtida_qs.delete()
            curtiu, message = False, 'Curtida removida.'
        else:
            Curtida.objects.create(usuario=user, imagem=imagem)
            curtiu, message = True, 'Imagem curtida!'

        return JsonResponse({
            'success': True,
            'curtiu': curtiu,
            'new_count': Curtida.objects.filter(imagem=imagem).count(),
            'message': message
        })


# ----------------------------------------------------------------------
# 5. PROXY DE MÉDIA PRIVADA S3
# ----------------------------------------------------------------------
class PrivateMediaProxyView(View):
    def get(self, request, *args, **kwargs):
        file_path = kwargs.get('path')
        user = request.user

        try:
            imagem = Imagem.objects.get(arquivo_processado__endswith=file_path)
            galeria = imagem.galeria
        except (Imagem.DoesNotExist, Imagem.MultipleObjectsReturned):
            return HttpResponseBadRequest('Arquivo não encontrado.')

        if user.is_authenticated and (
                user.is_superuser or getattr(user, 'is_fotografo_master', False) or imagem.fotografo == user):
            allowed = True
        else:
            allowed = GaleriaAccessMixin().has_access(galeria, user)

        if not allowed:
            return HttpResponseForbidden('Acesso negado.')

        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            s3_response = s3_client.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                                               Key=imagem.arquivo_processado.name)
            response = HttpResponse(s3_response['Body'].read(), content_type=s3_response.get('ContentType',
                                                                                             mimetypes.guess_type(
                                                                                                 file_path)[
                                                                                                 0] or 'application/octet-stream'))
            response['Content-Length'] = s3_response.get('ContentLength')
            return response
        except Exception:
            return HttpResponseBadRequest('Erro ao acessar o armazenamento.')