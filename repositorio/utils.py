import io
import os
from PIL import Image, ImageOps
from django.core.files.base import ContentFile


def aplicar_marca_dagua(imagem_pil, watermark_pil, config):
    """
    Aplica a marca d'água em uma imagem PIL baseada nas configurações do modelo.
    """
    img_rgba = imagem_pil.convert("RGBA")
    wm_rgba = watermark_pil.convert("RGBA")

    # Redimensiona marca d'água (15% da largura da imagem base)
    largura_base = img_rgba.size[0]
    wm_w = int(largura_base * 0.15)
    w_ratio = wm_w / float(wm_rgba.size[0])
    wm_h = int(float(wm_rgba.size[1]) * float(w_ratio))
    wm_rgba = wm_rgba.resize((wm_w, wm_h), Image.Resampling.LANCZOS)

    # Aplica opacidade conforme definido no WatermarkConfig
    alpha = wm_rgba.split()[3]
    alpha = alpha.point(lambda p: p * config.opacidade)
    wm_rgba.putalpha(alpha)

    # Define posição
    largura_img, altura_img = img_rgba.size
    posicoes = {
        'TL': (20, 20),
        'TR': (largura_img - wm_w - 20, 20),
        'BL': (20, altura_img - wm_h - 20),
        'BR': (largura_img - wm_w - 20, altura_img - wm_h - 20),
        'C': ((largura_img - wm_w) // 2, (altura_img - wm_h) // 2),
    }

    pos = posicoes.get(config.posicao, posicoes['BR'])

    # Overlay
    img_rgba.paste(wm_rgba, pos, wm_rgba)
    return img_rgba.convert("RGB")


def preparar_imagem_para_django(imagem_pil, nome_arquivo, qualidade=85):
    """
    Converte uma imagem PIL em um ContentFile pronto para o Django.
    """
    output = io.BytesIO()
    imagem_pil.save(output, format='JPEG', quality=qualidade, optimize=True)
    return ContentFile(output.getvalue(), name=nome_arquivo)