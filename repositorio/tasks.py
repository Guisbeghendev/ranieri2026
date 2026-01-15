import os
import io
import logging
import time
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.urls import reverse
from .models import Imagem, WatermarkConfig, Galeria

logger = logging.getLogger(__name__)

# Configurações otimizadas
THUMBNAIL_SIZE = (800, 600)
THUMBNAIL_QUALITY = 85
GRID_THUMB_SIZE = (300, 300)


def enviar_progresso_websocket(imagem_id, progresso, status, galeria=None, fotografo_id=None, url_thumb=None,
                               arquivo_processado=None):
    """
    Função auxiliar para centralizar o envio de notificações via Channels.
    Inclui url_thumb e arquivo_processado para atualização imediata no front-end.
    """
    channel_layer = get_channel_layer()

    if galeria and galeria.slug:
        group_id = galeria.slug
    elif galeria:
        group_id = galeria.pk
    else:
        group_id = f"user_{fotografo_id}"

    group_name = f"galeria_{group_id}"
    global_group = "galerias_status_updates"
    lista_geral_group = "galeria_lista_geral"

    # Timestamp para forçar refresh de cache no front-end em caso de rotação
    ts = int(time.time())
    url_thumb_forced = f"{url_thumb}?t={ts}" if url_thumb else None
    url_proc_forced = f"{arquivo_processado}?t={ts}" if arquivo_processado else None

    data = {
        "type": "notificar_progresso",
        "imagem_id": imagem_id,
        "progress": progresso,
        "status": status,
        "url_thumb": url_thumb_forced,
        "arquivo_processado": url_proc_forced,
    }

    # Envia para o grupo específico da galeria
    async_to_sync(channel_layer.group_send)(group_name, data)

    # Envia para o grupo global de status
    async_to_sync(channel_layer.group_send)(global_group, data)

    # Envia para o grupo de lista geral (para resolver erro de rota na listagem)
    async_to_sync(channel_layer.group_send)(lista_geral_group, data)


@shared_task(bind=True, max_retries=3)
def processar_imagem_task(self, imagem_id, total_arquivos=1, indice_atual=1):
    try:
        imagem = Imagem.objects.select_related('galeria__watermark_config').get(pk=imagem_id)
        galeria = imagem.galeria

        enviar_progresso_websocket(imagem_id, 10, 'PROCESSANDO', galeria, imagem.fotografo.id)

        imagem.status_processamento = 'PROCESSANDO'
        imagem.save(update_fields=['status_processamento'])

        with imagem.arquivo_original.open('rb') as f:
            content = f.read()

        img_original = Image.open(io.BytesIO(content))
        img_original = ImageOps.exif_transpose(img_original)

        if img_original.mode != 'RGB':
            img_original = img_original.convert('RGB')

        enviar_progresso_websocket(imagem_id, 40, 'PROCESSANDO', galeria, imagem.fotografo.id)

        # GRID THUMBNAIL
        img_grid = img_original.copy()
        img_grid.thumbnail(GRID_THUMB_SIZE, Image.Resampling.LANCZOS)
        out_grid = io.BytesIO()
        img_grid.save(out_grid, format='JPEG', quality=70, optimize=True)

        if imagem.thumbnail:
            imagem.thumbnail.delete(save=False)

        thumb_name = f"thumb_{imagem.pk}.jpg"
        imagem.thumbnail.save(thumb_name, ContentFile(out_grid.getvalue()), save=False)

        # IMAGE PROCESSADA
        img_proc = img_original.copy()
        img_proc.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # WATERMARK
        if galeria and hasattr(galeria,
                               'watermark_config') and galeria.watermark_config and galeria.watermark_config.arquivo_marca_dagua:
            config = galeria.watermark_config
            with config.arquivo_marca_dagua.open('rb') as f_wm:
                wm_img = Image.open(io.BytesIO(f_wm.read())).convert("RGBA")

            base_w = img_proc.size[0]
            wm_w = int(base_w * 0.15)
            w_ratio = wm_w / float(wm_img.size[0])
            wm_h = int(float(wm_img.size[1]) * float(w_ratio))
            wm_img = wm_img.resize((wm_w, wm_h), Image.Resampling.LANCZOS)

            alpha = wm_img.split()[3]
            alpha = alpha.point(lambda p: p * (config.opacidade if hasattr(config, 'opacidade') else 0.5))
            wm_img.putalpha(alpha)

            pos = (img_proc.size[0] - wm_w - 20, img_proc.size[1] - wm_h - 20)
            temp_img = img_proc.convert("RGBA")
            temp_img.paste(wm_img, pos, wm_img)
            img_proc = temp_img.convert("RGB")

        enviar_progresso_websocket(imagem_id, 80, 'PROCESSANDO', galeria, imagem.fotografo.id)

        output = io.BytesIO()
        img_proc.save(output, format='JPEG', quality=THUMBNAIL_QUALITY, optimize=True)

        if imagem.arquivo_processado:
            imagem.arquivo_processado.delete(save=False)

        file_name = f"proc_{imagem.pk}_{os.path.basename(imagem.nome_arquivo_original)}"
        imagem.arquivo_processado.save(file_name, ContentFile(output.getvalue()), save=False)

        imagem.status_processamento = 'PROCESSADA'
        imagem.save(update_fields=['status_processamento', 'arquivo_processado', 'thumbnail'])

        # Gera a URL atualizada para o front-end
        nova_url = reverse('private_media_proxy', kwargs={'path': imagem.thumbnail.name})
        url_proc = reverse('private_media_proxy', kwargs={'path': imagem.arquivo_processado.name})

        enviar_progresso_websocket(
            imagem_id, 100, 'PROCESSADA', galeria, imagem.fotografo.id,
            url_thumb=nova_url, arquivo_processado=url_proc
        )

    except Exception as e:
        logger.error(f"Erro na task {imagem_id}: {str(e)}")
        Imagem.objects.filter(pk=imagem_id).update(status_processamento='ERRO')
        enviar_progresso_websocket(imagem_id, 0, 'ERRO')
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def girar_imagem_task(self, imagem_id, graus):
    """
    Task para girar a imagem original e disparar o re-processamento da visualização.
    """
    try:
        imagem = Imagem.objects.select_related('galeria').get(pk=imagem_id)
        enviar_progresso_websocket(imagem_id, 20, 'PROCESSANDO', imagem.galeria, imagem.fotografo.id)

        # 1. Abre a original
        with imagem.arquivo_original.open('rb') as f:
            img = Image.open(io.BytesIO(f.read()))

        # 2. Gira
        img = img.rotate(graus, expand=True)

        # 3. Salva de volta na original (S3/Local)
        buffer = io.BytesIO()
        format_img = 'JPEG' if imagem.arquivo_original.name.lower().endswith(('jpg', 'jpeg')) else 'PNG'
        img.save(buffer, format=format_img, quality=100)

        nome_original = os.path.basename(imagem.arquivo_original.name)
        imagem.arquivo_original.delete(save=False)
        imagem.arquivo_original.save(
            nome_original,
            ContentFile(buffer.getvalue()),
            save=False
        )

        enviar_progresso_websocket(imagem_id, 50, 'PROCESSANDO', imagem.galeria, imagem.fotografo.id)

        # 4. Chama o processamento de visualização (Watermark/Thumb) de forma síncrona/imediata
        processar_imagem_task.run(imagem_id)

    except Exception as e:
        logger.error(f"Erro ao girar imagem {imagem_id}: {str(e)}")
        Imagem.objects.filter(pk=imagem_id).update(status_processamento='ERRO')
        enviar_progresso_websocket(imagem_id, 0, 'ERRO')