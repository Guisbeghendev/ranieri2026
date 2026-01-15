from django import forms
from django.db import models
from .models import Imagem, Galeria, WatermarkConfig
from users.models import Grupo
from datetime import date

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
        # Campos definidos conforme seu models.py
        fields = ['nome', 'data_do_evento', 'descricao', 'status', 'acesso_publico', 'grupos_acesso', 'watermark_config']

        widgets = {
            'data_do_evento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ajusta o widget para M2M de grupos
        self.fields['grupos_acesso'].widget = forms.CheckboxSelectMultiple()

        # Garante que o queryset do campo M2M esteja explicitamente definido
        self.fields['grupos_acesso'].queryset = Grupo.objects.all()