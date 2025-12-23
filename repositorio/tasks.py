import os
import io
# Importações necessárias para manipular arquivos e tarefas assíncronas
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from celery import shared_task
from .models import Imagem, WatermarkConfig, Galeria
from django.conf import settings
# Importação de logging para debug
import logging
import traceback  # Necessário para registrar o traceback em caso de erro

# --- ADICIONADO PARA WEBSOCKET ---
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# --------------------------------

# Configuração de logging
logger = logging.getLogger(__name__)

# Constantes para a miniatura
THUMBNAIL_SIZE = (800, 600)  # Tamanho máximo da miniatura processada
THUMBNAIL_QUALITY = 85  # Qualidade JPEG para otimização


def aplicar_watermark(image, watermark, config):
    """
    Aplica a imagem da marca d'água na imagem principal na posição definida.
    Função auxiliar utilizada pela tarefa Celery.

    :param image: Imagem PIL (RGB ou RGBA) a ser marcada.
    :param watermark: Imagem PIL da marca d'água (RGBA).
    :param config: Instância de WatermarkConfig contendo posição e opacidade.
    :return: Imagem PIL final com a marca d'água aplicada (RGB).
    """
    img_width, img_height = image.size
    mark_width, mark_height = watermark.size

    # Proteção contra imagem da marca d'água inválida
    if mark_width <= 0 or mark_height <= 0:
        logger.warning("Marca d'água tem dimensões inválidas.")
        return image.convert("RGB")

    # 1. Redimensionamento da Watermark: Escala para 10% da largura da imagem base
    # (Ajuste para garantir que a watermark seja proporcional à imagem processada)
    scale_factor = 0.1
    target_width = img_width * scale_factor

    # Calcula a proporção de redimensionamento
    ratio = target_width / mark_width
    new_mark_width = int(mark_width * ratio)
    new_mark_height = int(mark_height * ratio)

    # Garante que as novas dimensões sejam válidas
    if new_mark_width > 0 and new_mark_height > 0:
        # Redimensionamento: Usando Image.Resampling.LANCZOS para alta qualidade
        watermark = watermark.resize((new_mark_width, new_mark_height), Image.Resampling.LANCZOS)
        mark_width, mark_height = watermark.size  # Atualiza as dimensões
    else:
        logger.warning("Marca d'água ficou muito pequena após o redimensionamento. Retornando imagem original.")
        return image.convert("RGB")

    # 2. Prepara a imagem principal para receber a watermark.
    # Converte a imagem base para RGBA para suportar a transparência da watermark.
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    # 3. Aplica a opacidade na marca d'água
    # Garante que a opacidade seja um valor válido de 0 a 100
    opacidade_int = int(config.opacidade * 255) if 0.0 <= config.opacidade <= 1.0 else 255

    # Cria uma máscara de opacidade
    alpha_channel = watermark.split()[-1]
    alpha_channel = Image.eval(alpha_channel, lambda x: x * opacidade_int // 255)
    watermark.putalpha(alpha_channel)

    # 4. Calcula a posição (Margem fixa de 20 pixels)
    margin = 20
    position = (0, 0)

    if config.posicao == 'TL':  # Top-Left
        position = (margin, margin)
    elif config.posicao == 'TR':  # Top-Right
        position = (img_width - mark_width - margin, margin)
    elif config.posicao == 'BL':  # Bottom-Left
        position = (margin, img_height - mark_height - margin)
    elif config.posicao == 'BR':  # Bottom-Right
        position = (img_width - mark_width - margin, img_height - mark_height - margin)
    elif config.posicao == 'C':  # Center
        position = ((img_width - mark_width) // 2, (img_height - mark_height) // 2)

    # 5. Cola a watermark na imagem principal (usando a própria watermark como máscara para a transparência)
    image.paste(watermark, position, watermark)

    # 6. Retorna a imagem final (convertida para RGB para salvar como JPEG)
    return image.convert("RGB")


@shared_task
def processar_imagem_task(imagem_id):
    """
    Tarefa Celery para baixar a imagem original do S3 (Privado), processá-la
    (miniatura e watermark) e fazer upload do resultado (Público).
    """
    try:
        # Tenta obter a instância da imagem com select_related para otimizar o acesso à galeria e watermark
        imagem = Imagem.objects.select_related('galeria__watermark_config').get(pk=imagem_id)
    except Imagem.DoesNotExist:
        logger.error(f"Imagem com ID {imagem_id} não encontrada.")
        return

    # 1. Atualiza o status da imagem para PROCESSANDO
    try:
        imagem.status_processamento = 'PROCESSANDO'
        imagem.save(update_fields=['status_processamento'])
        logger.info(f"Iniciando processamento da imagem: {imagem.pk} - {imagem.nome_arquivo_original}")
    except Exception as e:
        logger.error(f"Erro ao atualizar status para PROCESSANDO para imagem {imagem_id}: {e}")
        return

    try:
        # 2. Baixar o arquivo original do S3 (Privado)
        if not imagem.arquivo_original:
            raise FileNotFoundError("O campo arquivo_original está vazio.")

        # ATENÇÃO: É necessário abrir o arquivo corretamente para fazer a leitura.
        # O FileField já tem o método .open() que gerencia o acesso ao storage (S3)
        with imagem.arquivo_original.open('rb') as f:
            content = f.read()

        image_stream = io.BytesIO(content)
        # Tenta abrir a imagem
        original_img = Image.open(image_stream)

        # Corrige a orientação da imagem baseada no EXIF (evita fotos deitadas/invertidas)
        original_img = ImageOps.exif_transpose(original_img)

        # 3. Criar miniatura e otimizar (in-place)
        # Converte para RGB se necessário, garantindo que a imagem base seja tratável.
        if original_img.mode in ('L', 'P', 'CMYK', 'YCbCr', 'I', 'F'):
            original_img = original_img.convert("RGB")
        # Para RGB ou RGBA, a conversão final para JPEG/RGB será feita após a watermark.

        # Cria a miniatura (altera 'original_img' in-place)
        original_img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # A imagem base para a watermark é a miniatura gerada.
        processed_img = original_img

        # 4. Aplicar a Marca D'água (se a Galeria tiver uma configurada)
        galeria = imagem.galeria
        watermark_aplicada = False

        if galeria and galeria.watermark_config and galeria.watermark_config.arquivo_marca_dagua:
            config = galeria.watermark_config

            # Baixa a imagem da marca d'água.
            if not config.arquivo_marca_dagua:
                logger.warning(f"Marca d'água configurada na galeria {galeria.pk} mas sem arquivo.")
            else:
                # ATENÇÃO: Abre o arquivo do WatermarkConfig, que é PublicMediaStorage
                with config.arquivo_marca_dagua.open('rb') as f:
                    watermark_content = f.read()

                # A marca d'água deve ser RGBA para suportar transparência
                watermark_img = Image.open(io.BytesIO(watermark_content)).convert("RGBA")

                # Chama a função auxiliar para aplicar a watermark
                processed_img = aplicar_watermark(processed_img, watermark_img, config)
                watermark_aplicada = True
                logger.info("Marca d'água aplicada com sucesso.")

        if not watermark_aplicada:
            # Se não aplicou watermark, garante que a imagem processada seja RGB para o JPEG
            processed_img = processed_img.convert("RGB")
            logger.info("Nenhuma marca d'água configurada para aplicação.")

        # 5. Salvar a imagem processada em um buffer in-memory (JPEG)
        output_buffer = io.BytesIO()
        # Salva no formato JPEG com a qualidade definida
        processed_img.save(output_buffer, format='JPEG', quality=THUMBNAIL_QUALITY)

        # 6. Upload da imagem processada de volta para o S3 (Público)

        # Determina o nome do arquivo processado
        base, _ = os.path.splitext(imagem.nome_arquivo_original)
        # Usa a PK do registro Imagem para garantir a unicidade do nome do arquivo
        # O nome do arquivo salvo no S3 é essencial para o FileField funcionar corretamente
        file_name = f"{imagem.pk}_{base}_processed.jpg"

        # Remove o arquivo processado antigo se existir (limpeza no S3 para re-processamento)
        if imagem.arquivo_processado:
            imagem.arquivo_processado.delete(save=False)

        # Cria um ContentFile para o Django fazer o upload
        django_file = ContentFile(output_buffer.getvalue(), name=file_name)

        # Salva no campo FileField. Ele usará o PublicMediaStorage configurado.
        imagem.arquivo_processado.save(file_name, django_file, save=False)

        # 7. Atualizar status final e salvar a imagem no banco.
        imagem.status_processamento = 'PROCESSADA'

        # CORREÇÃO: Removida a atualização de status da Galeria daqui para evitar loop.
        # O Signal verificar_status_galeria_apos_processamento cuidará de mudar a galeria para 'RV'.
        imagem.save(update_fields=['status_processamento', 'arquivo_processado', 'galeria'])

        # --- NOTIFICAÇÃO WEBSOCKET APÓS SUCESSO ---
        if galeria:
            galeria.refresh_from_db()
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
        # ------------------------------------------

        logger.info(f"Processamento da Imagem {imagem_id} concluído. Arquivo: {imagem.arquivo_processado.name}")

    except Exception as e:
        # Se ocorrer qualquer erro, define o status como ERRO e registra o erro
        logger.error(f"Erro CRÍTICO no processamento da imagem {imagem_id}: {e}")
        logger.error(traceback.format_exc())  # Registra o traceback completo

        imagem.status_processamento = 'ERRO'
        # Tenta salvar o status de erro
        try:
            imagem.save(update_fields=['status_processamento'])

            # Notifica erro via WebSocket (opcional para manter sync)
            if galeria:
                galeria.refresh_from_db()
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
        except Exception as save_e:
            logger.error(f"Erro ao salvar status 'ERRO' para imagem {imagem_id}: {save_e}")