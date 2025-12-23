from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Retorna o valor para uma chave específica de um dicionário."""
    return dictionary.get(key)