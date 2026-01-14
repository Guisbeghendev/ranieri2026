import os
import io
import logging
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Imagem, WatermarkConfig, Galeria

logger = logging.getLogger(__name__)

# Configurações otimizadas (Baseadas na robustez do Guisbeghen)
THUMBNAIL_SIZE = (800, 600)
THUMBNAIL_QUALITY = 85


@shared_task(bind=True, max_retries=3)
def processar_imagem_task(self, imagem_id, total_arquivos=1, indice_atual=1):
    """
    Tarefa reformulada para aceitar contagem de progresso e garantir
    estabilidade de memória/cor.
    """
    try:
        # Busca otimizada
        imagem = Imagem.objects.select_related('galeria__watermark_config').get(pk=imagem_id)
        galeria = imagem.galeria

        # 1. Atualiza Status Inicial
        imagem.status_processamento = 'PROCESSANDO'
        imagem.save(update_fields=['status_processamento'])

        # 2. Leitura Segura do S3
        with imagem.arquivo_original.open('rb') as f:
            content = f.read()

        # Uso de cópia em memória para evitar locks no arquivo original
        img_original = Image.open(io.BytesIO(content))
        img_original = ImageOps.exif_transpose(img_original)

        # 3. Normalização de Cor (Prevenção de quebra do Worker)
        if img_original.mode != 'RGB':
            img_original = img_original.convert('RGB')

        # 4. Geração de Miniatura
        img_proc = img_original.copy()
        img_proc.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # 5. Aplicação de Marca D'água (Lógica de Alpha do Guisbeghen)
        if galeria and hasattr(galeria, 'watermark_config') and galeria.watermark_config and galeria.watermark_config.arquivo_marca_dagua:
            config = galeria.watermark_config
            with config.arquivo_marca_dagua.open('rb') as f_wm:
                wm_img = Image.open(io.BytesIO(f_wm.read())).convert("RGBA")

            # Cálculo de escala (15% da largura)
            base_w = img_proc.size[0]
            wm_w = int(base_w * 0.15)
            w_ratio = wm_w / float(wm_img.size[0])
            wm_h = int(float(wm_img.size[1]) * float(w_ratio))
            wm_img = wm_img.resize((wm_w, wm_h), Image.Resampling.LANCZOS)

            # Aplicação de Opacidade conforme config
            alpha = wm_img.split()[3]
            alpha = alpha.point(lambda p: p * config.opacidade)
            wm_img.putalpha(alpha)

            # Posição (Ex: Bottom Right com margem)
            pos = (img_proc.size[0] - wm_w - 20, img_proc.size[1] - wm_h - 20)

            # Overlay
            temp_img = img_proc.convert("RGBA")
            temp_img.paste(wm_img, pos, wm_img)
            img_proc = temp_img.convert("RGB")

        # 6. Salvamento e Upload
        output = io.BytesIO()
        img_proc.save(output, format='JPEG', quality=THUMBNAIL_QUALITY, optimize=True)

        file_name = f"proc_{imagem.pk}_{os.path.basename(imagem.nome_arquivo_original)}"
        imagem.arquivo_processado.save(file_name, ContentFile(output.getvalue()), save=False)

        imagem.status_processamento = 'PROCESSADA'
        imagem.save(update_fields=['status_processamento', 'arquivo_processado'])

        # 7. NOTIFICAÇÃO REAL-TIME
        percentual = int((indice_atual / total_arquivos) * 100)
        channel_layer = get_channel_layer()

        group_name = f"galeria_{galeria.pk}" if galeria else f"user_{imagem.fotografo.id}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notificar_progresso",
                "imagem_id": imagem.id,
                "progresso": percentual,
                "concluidas": indice_atual,
                "total": total_arquivos,
                "status": "CONCLUIDO" if indice_atual == total_arquivos else "PROCESSANDO",
                "url_thumb": imagem.arquivo_processado.url if imagem.arquivo_processado else ""
            }
        )

    except Exception as e:
        logger.error(f"Erro na task de imagem {imagem_id}: {str(e)}")
        Imagem.objects.filter(pk=imagem_id).update(status_processamento='ERRO')
        raise self.retry(exc=e, countdown=60)