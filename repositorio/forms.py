from django import forms
from django.db import models
from .models import Imagem, Galeria, WatermarkConfig
# Assumindo a importação necessária, baseada no seu models.py
from users.models import Grupo


# --------------------------------------------------------------------------
# 1. Formulário Customizado para Upload Múltiplo
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
            # Chama clean para cada item da lista (cada arquivo)
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
# 2. Formulário para Galeria (Baseado no models.py)
# --------------------------------------------------------------------------

class GaleriaForm(forms.ModelForm):
    """Formulário para criar/editar a Galeria."""

    class Meta:
        model = Galeria
        # Campos conforme o models.py fornecido:
        fields = ['nome', 'descricao', 'status', 'grupos_acesso', 'watermark_config']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajusta o widget para M2M de grupos
        self.fields['grupos_acesso'].widget = forms.CheckboxSelectMultiple()

        # CORREÇÃO: Garante que o queryset do campo M2M esteja explicitamente definido
        # para buscar todos os objetos do modelo Grupo, garantindo que as opções apareçam.
        self.fields['grupos_acesso'].queryset = Grupo.objects.all()