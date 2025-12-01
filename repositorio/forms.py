from django import forms
from django.db import models
from .models import Imagem, Galeria, WatermarkConfig
# Assumindo a importação necessária, baseada no seu models.py
from users.models import Grupo
from datetime import date  # Importado para DateInput


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
        # CAMPOS ATUALIZADOS: Adicionado 'data_do_evento'
        fields = ['nome', 'data_do_evento', 'descricao', 'status', 'grupos_acesso', 'watermark_config']

        widgets = {
            # Novo widget para o campo DateField para melhor experiência do usuário
            'data_do_evento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ajusta o widget para M2M de grupos
        self.fields['grupos_acesso'].widget = forms.CheckboxSelectMultiple()

        # Garante que o queryset do campo M2M esteja explicitamente definido
        self.fields['grupos_acesso'].queryset = Grupo.objects.all()

        # Opcional: Adiciona classes CSS customizadas a todos os campos (exceto Checkbox/SelectMultiple)
        # for name, field in self.fields.items():
        #     if not isinstance(field.widget, (forms.CheckboxSelectMultiple, forms.SelectMultiple)):
        #         if 'class' in field.widget.attrs:
        #             field.widget.attrs['class'] += ' form-control'
        #         else:
        #             field.widget.attrs['class'] = 'form-control'