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
# Novo: Tamanho para a miniatura de grade (preview rápido)
GRID_THUMB_SIZE = (300, 300)


@shared_task(bind=True, max_retries=3)
def processar_imagem_task(self, imagem_id, total_arquivos=1, indice_atual=1):
    """
    Tarefa reformulada para aceitar contagem de progresso e garantir
    estabilidade de memória/cor, gerando imagem processada e thumbnail.
    """
    try:
        # Busca otimizada com select_related para evitar queries N+1
        imagem = Imagem.objects.select_related('galeria__watermark_config').get(pk=imagem_id)
        galeria = imagem.galeria

        # 1. Atualiza Status Inicial
        imagem.status_processamento = 'PROCESSANDO'
        imagem.save(update_fields=['status_processamento'])

        # 2. Leitura Segura do Storage (S3 ou Local)
        with imagem.arquivo_original.open('rb') as f:
            content = f.read()

        # Uso de cópia em memória para evitar locks no arquivo original
        img_original = Image.open(io.BytesIO(content))
        img_original = ImageOps.exif_transpose(img_original)

        # 3. Normalização de Cor (Prevenção de quebra do Worker por perfis ICC)
        if img_original.mode != 'RGB':
            img_original = img_original.convert('RGB')

        # --- GERAÇÃO DA MINIATURA DE GRADE (GRID THUMBNAIL) ---
        img_grid = img_original.copy()
        img_grid.thumbnail(GRID_THUMB_SIZE, Image.Resampling.LANCZOS)
        out_grid = io.BytesIO()
        img_grid.save(out_grid, format='JPEG', quality=70, optimize=True)
        thumb_name = f"thumb_{imagem.pk}.jpg"

        # Salvamento parcial (save=False) para persistir tudo em um único save final
        imagem.thumbnail.save(thumb_name, ContentFile(out_grid.getvalue()), save=False)

        # 4. Geração da Imagem de Visualização (Processada/Watermarked)
        img_proc = img_original.copy()
        img_proc.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # 5. Aplicação de Marca D'água (Lógica de Alpha do Guisbeghen)
        if galeria and hasattr(galeria,
                               'watermark_config') and galeria.watermark_config and galeria.watermark_config.arquivo_marca_dagua:
            config = galeria.watermark_config
            with config.arquivo_marca_dagua.open('rb') as f_wm:
                wm_img = Image.open(io.BytesIO(f_wm.read())).convert("RGBA")

            # Cálculo de escala (15% da largura da imagem base)
            base_w = img_proc.size[0]
            wm_w = int(base_w * 0.15)
            w_ratio = wm_w / float(wm_img.size[0])
            wm_h = int(float(wm_img.size[1]) * float(w_ratio))
            wm_img = wm_img.resize((wm_w, wm_h), Image.Resampling.LANCZOS)

            # Aplicação de Opacidade conforme configuração do modelo
            alpha = wm_img.split()[3]
            alpha = alpha.point(lambda p: p * (config.opacidade if hasattr(config, 'opacidade') else 0.5))
            wm_img.putalpha(alpha)

            # Posição (Bottom Right com margem de 20px)
            pos = (img_proc.size[0] - wm_w - 20, img_proc.size[1] - wm_h - 20)

            # Overlay com conversão para RGBA para suportar transparência na colagem
            temp_img = img_proc.convert("RGBA")
            temp_img.paste(wm_img, pos, wm_img)
            img_proc = temp_img.convert("RGB")

        # 6. Salvamento da Imagem Processada
        output = io.BytesIO()
        img_proc.save(output, format='JPEG', quality=THUMBNAIL_QUALITY, optimize=True)

        file_name = f"proc_{imagem.pk}_{os.path.basename(imagem.nome_arquivo_original)}"
        imagem.arquivo_processado.save(file_name, ContentFile(output.getvalue()), save=False)

        # 7. Finalização do Objeto
        imagem.status_processamento = 'PROCESSADA'
        imagem.save(update_fields=['status_processamento', 'arquivo_processado', 'thumbnail'])

        # 8. NOTIFICAÇÃO REAL-TIME (Channels)
        percentual = int((indice_atual / total_arquivos) * 100)
        channel_layer = get_channel_layer()

        # Roteamento via Slug se disponível, senão ID da galeria ou fotógrafo
        if galeria and galeria.slug:
            group_id = galeria.slug
        elif galeria:
            group_id = galeria.pk
        else:
            group_id = f"user_{imagem.fotografo.id}"

        group_name = f"galeria_{group_id}"

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notificar_progresso",
                "imagem_id": imagem.id,
                "progresso": percentual,
                "concluidas": indice_atual,
                "total": total_arquivos,
                "status": "CONCLUIDO" if indice_atual == total_arquivos else "PROCESSANDO",
                "url_thumb": imagem.thumbnail.url if imagem.thumbnail else (
                    imagem.arquivo_processado.url if imagem.arquivo_processado else "")
            }
        )

    except Exception as e:
        logger.error(f"Erro crítico na task de imagem {imagem_id}: {str(e)}")
        Imagem.objects.filter(pk=imagem_id).update(status_processamento='ERRO')
        # Retry em caso de falha de conexão ou I/O
        raise self.retry(exc=e, countdown=60)