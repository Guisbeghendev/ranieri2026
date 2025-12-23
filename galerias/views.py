# galerias/views.py
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponse
from django.db.models import Q
from repositorio.models import Galeria, Curtida, Imagem  # Importa os modelos de dados
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.conf import settings
import os
import mimetypes
import boto3
from botocore.exceptions import ClientError
import traceback


# Mixin de Permissão para Acesso
class GaleriaAccessMixin:
    """
    Método que verifica se o usuário tem permissão para acessar a galeria.
    Retorna True se tiver acesso, False caso contrário.
    """

    def has_access(self, galeria, user):

        # Códigos de status que não devem ser acessíveis por usuários comuns
        # 'PR' (Rascunho), 'PC' (Processando), 'RV' (Revisão), 'AR' (Arquivada)
        UNPUBLISHED_STATUSES = ['PR', 'PC', 'RV', 'AR']

        # 1. Checagem de Administração/Staff
        # Superuser ou staff (fotógrafo) pode acessar TUDO.
        if user.is_staff:
            return True

        # 2. Se o status é não-publicado, negar acesso para NÃO-staffs.
        if galeria.status in UNPUBLISHED_STATUSES:
            return False

        # Neste ponto, o status é 'PB' (Publicada).

        # 3. Se for acesso público, todos (logados ou não) têm acesso.
        if galeria.acesso_publico:
            return True

        # 4. Se não for público e o usuário não estiver logado, negar acesso.
        if not user.is_authenticated:
            return False

        # 5. Acesso restrito (usuário logado): Checar grupos em comum
        user_groups_ids = user.groups.values_list('pk', flat=True)
        galeria_groups_ids = galeria.grupos_acesso.values_list('pk', flat=True)

        # Verifica se há intersecção (grupos em comum)
        if set(user_groups_ids) & set(galeria_groups_ids):
            return True

        return False


# ----------------------------------------------------------------------
# 1. Listagem de Galerias
# ----------------------------------------------------------------------
class GaleriaListView(GaleriaAccessMixin, ListView):
    model = Galeria
    template_name = 'galerias/lista_galerias.html'
    context_object_name = 'galerias_publicas'  # Definimos o nome do objeto principal

    def get_queryset(self):
        # Filtra todas as galerias publicadas (Status='PB')

        # CORREÇÃO APLICADA AQUI: Adicionado .order_by('-data_do_evento')
        queryset_base = Galeria.objects.filter(status='PB').order_by('-data_do_evento').prefetch_related('capa')

        # A. Galerias Públicas (visíveis para todos)
        galerias_publicas = queryset_base.filter(acesso_publico=True)

        # B. Galerias Restritas que o usuário tem acesso
        if self.request.user.is_authenticated:
            user = self.request.user

            # Pega os IDs dos grupos do usuário logado
            user_groups_ids = user.groups.values_list('pk', flat=True)

            # Filtra galerias que NÃO são públicas E que possuem grupos em comum com os do usuário
            galerias_exclusivas = queryset_base.filter(
                acesso_publico=False,
                grupos_acesso__pk__in=user_groups_ids
            ).distinct()

            # Combina públicas e exclusivas, garantindo distinção
            return (galerias_publicas.distinct() | galerias_exclusivas).distinct()

        else:
            # Usuário deslogado: apenas galerias públicas
            return galerias_publicas

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # O 'object_list' já contém a união de galerias públicas e exclusivas (se logado)
        todas_galerias = context['object_list']

        # CORREÇÃO CRÍTICA: Anexar a URL do Proxy da Capa para todas as galerias
        for galeria in todas_galerias:
            if galeria.capa and galeria.capa.arquivo_processado:
                try:
                    # Gera a URL segura para servir a imagem de capa (proxy)
                    # Assumimos que 'private_media_proxy' é uma rota nomeada globalmente.
                    galeria.capa_proxy_url = reverse(
                        'private_media_proxy',
                        kwargs={'path': galeria.capa.arquivo_processado.name}
                    )
                except Exception:
                    # Em caso de erro (e.g., rota não configurada), define como None
                    galeria.capa_proxy_url = None
                    traceback.print_exc()  # Útil para debug
            else:
                galeria.capa_proxy_url = None

        # Define 'galerias_publicas' e 'galerias_exclusivas' corretamente
        # Usamos filter na lista de objetos que já estão em memória (e têm o proxy_url anexado)
        context['galerias_publicas'] = [g for g in todas_galerias if g.acesso_publico]

        if self.request.user.is_authenticated:
            user = self.request.user
            # Pega os IDs dos grupos do usuário logado
            user_groups_ids = user.groups.values_list('pk', flat=True)
            user_groups_set = set(user_groups_ids)

            galerias_exclusivas = []
            for galeria in todas_galerias:
                if not galeria.acesso_publico:
                    galeria_groups_ids = galeria.grupos_acesso.values_list('pk', flat=True)
                    if set(galeria_groups_ids) & user_groups_set:
                        galerias_exclusivas.append(galeria)

            context['galerias_exclusivas'] = galerias_exclusivas

        else:
            context[
                'galerias_exclusivas'] = []  # Usamos lista vazia em vez de QuerySet vazia aqui, já que estamos operando em listas/QuerySets mistos.

        # Nota: O uso de list comprehension/iteração aqui funciona porque `todas_galerias`
        # (que é `context['object_list']`) já foi avaliada e tem o atributo `capa_proxy_url` anexado.

        return context


# ----------------------------------------------------------------------
# 2. Detalhe da Galeria
# ----------------------------------------------------------------------
class GaleriaDetailView(GaleriaAccessMixin, DetailView):
    model = Galeria
    template_name = 'galerias/detalhe_galeria.html'
    context_object_name = 'galeria'

    def get_queryset(self):
        # Prefetch de Imagens, do Autor, e anotação das curtidas totais (para todas as imagens da galeria)
        return Galeria.objects.prefetch_related(
            'imagens__curtidas',
            'imagens',
        ).select_related('fotografo')

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Galeria.DoesNotExist:
            return redirect(reverse('galerias:lista_galerias'))  # Redireciona se a galeria não existir

        # Verifica a permissão antes de renderizar
        if not self.has_access(self.object, request.user):
            # Se não tiver acesso, redireciona para a lista
            return redirect(reverse('galerias:lista_galerias'))

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        galeria = context['galeria']
        user = self.request.user

        # Dicionário para rastrear se o usuário logado curtiu cada imagem
        curtidas_pelo_usuario = {}

        # Total de curtidas por galeria (somando as curtidas de todas as imagens)
        curtidas_totais_galeria = 0

        # Preenche o dicionário e soma as curtidas totais
        for imagem in galeria.imagens.all():
            curtidas_count = imagem.curtidas.count()
            curtidas_totais_galeria += curtidas_count

            # Verifica se o usuário logado curtiu esta imagem específica
            if user.is_authenticated:
                curtida_existe = imagem.curtidas.filter(usuario=user).exists()
                curtidas_pelo_usuario[imagem.pk] = curtida_existe
            else:
                curtidas_pelo_usuario[imagem.pk] = False

            # ADIÇÃO NECESSÁRIA: Anexar o proxy_url a cada imagem dentro da galeria
            if imagem.arquivo_processado:
                try:
                    imagem.proxy_url = reverse(
                        'private_media_proxy',
                        kwargs={'path': imagem.arquivo_processado.name}
                    )
                except Exception:
                    imagem.proxy_url = None
                    # Aqui você pode querer logar o erro, se o reverse falhar
            else:
                imagem.proxy_url = None

        context['curtidas_totais_galeria'] = curtidas_totais_galeria
        context['curtidas_pelo_usuario'] = curtidas_pelo_usuario

        # Esta chave não é mais estritamente necessária se o proxy_url for anexado a cada Imagem,
        # mas pode ser mantida se houver outros usos no template.
        context['proxy_url_name'] = 'private_media_proxy'

        return context


# ----------------------------------------------------------------------
# 3. Interação: Curtir/Descurtir
# ----------------------------------------------------------------------
class CurtirView(LoginRequiredMixin, View):

    def post(self, request, imagem_pk, *args, **kwargs):
        user = request.user

        # 1. Tenta obter a imagem ou retorna 404
        imagem = get_object_or_404(Imagem, pk=imagem_pk)
        galeria = imagem.galeria

        # 2. Checagem de permissão: Verifica se o usuário logado pode acessar a galeria da imagem
        if not GaleriaAccessMixin().has_access(galeria, user):
            return JsonResponse({'success': False, 'message': 'Acesso negado à galeria desta imagem.'}, status=403)

        # 3. Lógica Curtir/Descurtir
        try:
            # Tenta remover a curtida (Descurtir)
            curtida = Curtida.objects.get(usuario=user, imagem=imagem)
            curtida.delete()
            curtiu = False
            message = 'Curtida removida.'

        except Curtida.DoesNotExist:
            # Cria a curtida (Curtir)
            Curtida.objects.create(usuario=user, imagem=imagem)
            curtiu = True
            message = 'Imagem curtida!'

        # 4. Retorna a nova contagem de curtidas
        new_count = Curtida.objects.filter(imagem=imagem).count()

        return JsonResponse({
            'success': True,
            'curtiu': curtiu,
            'new_count': new_count,
            'message': message
        })


# ----------------------------------------------------------------------
# 4. Proxy de Média Privada S3 (Nova View)
# ----------------------------------------------------------------------
class PrivateMediaProxyView(View):
    """
    View para servir arquivos de mídia privada do S3, checando permissões.
    A URL esperada deve ser: /media-s3-proxy/<path:path>
    O 'path' na URL é o caminho do arquivo no S3.
    """

    # Configurações do S3
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    def get(self, request, *args, **kwargs):
        # O 'path' é o caminho completo do arquivo no S3 (e na base de dados)
        file_path = kwargs.get('path')
        user = request.user

        # 1. Tenta encontrar o objeto Imagem baseado no caminho do arquivo
        try:
            # Busca pelo campo 'arquivo_processado' que armazena o caminho/nome do arquivo no S3.
            imagem = Imagem.objects.get(arquivo_processado__endswith=file_path)
            galeria = imagem.galeria
        except Imagem.DoesNotExist:
            return HttpResponseBadRequest('Arquivo não encontrado na base de dados.')

        # 2. Checagem de Permissão: Verifica se o usuário tem acesso à galeria da imagem
        # Se a galeria é pública, o GaleriaAccessMixin retorna True, mesmo para não logados.
        if not GaleriaAccessMixin().has_access(galeria, user):
            return HttpResponseForbidden(
                'Acesso negado à galeria. O usuário deve estar logado ou pertencer ao grupo correto.')

        # 3. Obtenção do Arquivo do S3 e Serviço (Streaming)
        try:
            # Usar 'imagem.arquivo_processado.name' como a chave do S3
            s3_object_key = imagem.arquivo_processado.name

            s3_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_object_key)

            content_type = s3_response.get('ContentType',
                                           mimetypes.guess_type(file_path)[0] or 'application/octet-stream')
            content_length = s3_response.get('ContentLength')

            response = HttpResponse(
                s3_response['Body'].read(),
                content_type=content_type,
            )
            response['Content-Length'] = content_length

            return response

        except ClientError as e:
            # Erro do S3 (ex: Arquivo não existe no bucket)
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return HttpResponseBadRequest(f'Arquivo não encontrado no serviço de armazenamento.')
            # Outros erros do S3
            return HttpResponseBadRequest(f'Erro ao acessar o armazenamento: {error_code}')
        except Exception as e:
            return HttpResponseBadRequest(f'Erro interno: {str(e)}')