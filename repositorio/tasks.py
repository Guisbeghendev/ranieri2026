import os
import io
from PIL import Image
from django.core.files.base import ContentFile
from celery import shared_task
from .models import Imagem, WatermarkConfig
from django.conf import settings

# Constantes para a miniatura
THUMBNAIL_SIZE = (800, 600)  # Tamanho máximo da miniatura processada
THUMBNAIL_QUALITY = 85  # Qualidade JPEG para otimização


@shared_task
def processar_imagem_task(imagem_id):
    """
    Tarefa Celery para baixar a imagem original do S3, processá-la
    (miniatura e watermark) e fazer upload do resultado.
    """
    try:
        imagem = Imagem.objects.get(pk=imagem_id)
    except Imagem.DoesNotExist:
        # Se a imagem não existe mais, apenas finaliza a tarefa
        print(f"Erro: Imagem com ID {imagem_id} não encontrada.")
        return

    # 1. Atualiza o status da imagem para PROCESSANDO
    imagem.status_processamento = 'PROCESSANDO'
    imagem.save(update_fields=['status_processamento'])
    print(f"Iniciando processamento da imagem: {imagem.nome_arquivo_original}")

    try:
        # 2. Baixar o arquivo original do S3 (usando o sistema de arquivos do Django)
        # O arquivo é lido diretamente do S3 para a memória (content)
        with imagem.arquivo_original.open('rb') as f:
            content = f.read()

        image_stream = io.BytesIO(content)
        original_img = Image.open(image_stream).convert("RGB")

        # 3. Criar miniatura e otimizar (Primeiro processamento)

        # Redimensionamento: Usando Image.Resampling.LANCZOS para alta qualidade
        original_img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        processed_img = original_img  # Imagem base para a watermark

        # 4. Aplicar a Marca D'água (se a Galeria tiver uma configurada)
        galeria = imagem.galeria
        if galeria and galeria.watermark_config:
            config = galeria.watermark_config

            # Baixa a imagem da marca d'água (também do S3, se for o caso)
            with config.arquivo_marca_dagua.open('rb') as f:
                watermark_content = f.read()

            watermark_img = Image.open(io.BytesIO(watermark_content)).convert("RGBA")

            # Chama a função auxiliar para aplicar a watermark
            processed_img = aplicar_watermark(processed_img, watermark_img, config)

        # 5. Salvar a imagem processada em um buffer in-memory
        output_buffer = io.BytesIO()
        processed_img.save(output_buffer, format='JPEG', quality=THUMBNAIL_QUALITY)

        # 6. Upload da imagem processada de volta para o S3

        # Determina o nome do arquivo processado
        # Ex: "original_name.jpg" -> "original_name_processed.jpg"
        base, ext = os.path.splitext(imagem.nome_arquivo_original)
        file_name = f"{base}_processed.jpg"

        # Cria um ContentFile para o Django fazer o upload
        django_file = ContentFile(output_buffer.getvalue(), name=file_name)

        # Salva no campo FileField, o que dispara o upload para o S3
        # O save=False é usado aqui porque salvaremos a instância logo em seguida (Ponto 7)
        imagem.arquivo_processado.save(file_name, django_file, save=False)

        # 7. Atualizar status final e salvar a imagem no banco.
        # ESTE SAVE DISPARA O SIGNAL DE VERIFICAÇÃO DA GALERIA (Ponto 5)
        imagem.status_processamento = 'PROCESSADA'
        imagem.save(update_fields=['status_processamento', 'arquivo_processado'])
        print(f"Processamento concluído e arquivo salvo: {file_name}")

    except Exception as e:
        print(f"Erro inesperado durante o processamento da imagem {imagem_id}: {e}")
        # Se ocorrer qualquer erro, define o status como ERRO
        imagem.status_processamento = 'ERRO'
        imagem.save(update_fields=['status_processamento'])


def aplicar_watermark(image, watermark, config):
    """
    Aplica a imagem da marca d'água na imagem principal na posição definida.
    Função auxiliar utilizada pela tarefa Celery.
    """
    img_width, img_height = image.size
    mark_width, mark_height = watermark.size

    # 1. Redimensionamento da Watermark: Escala para 10% da largura da imagem base
    scale_factor = min(0.1, img_width / mark_width)
    new_mark_width = int(mark_width * scale_factor)
    new_mark_height = int(mark_height * scale_factor)

    if new_mark_width > 0 and new_mark_height > 0:
        watermark = watermark.resize((new_mark_width, new_mark_height), Image.Resampling.LANCZOS)
        mark_width, mark_height = watermark.size  # Atualiza as dimensões

    # 2. Cria uma camada transparente e cola a imagem principal nela
    transparent_layer = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    transparent_layer.paste(image, (0, 0))

    # 3. Aplica a opacidade na marca d'água
    alpha = watermark.split()[-1]
    alpha = Image.eval(alpha, lambda x: x * config.opacidade)
    watermark.putalpha(alpha)

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

    # 5. Cola a watermark na camada transparente
    transparent_layer.paste(watermark, position, watermark)

    # 6. Retorna a imagem final (convertida para RGB para salvar como JPEG)
    return transparent_layer.convert("RGB")