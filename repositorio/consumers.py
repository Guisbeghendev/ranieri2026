import json
from channels.generic.websocket import AsyncWebsocketConsumer


class GaleriaConsumer(AsyncWebsocketConsumer):
    """
    Consumer reativo para progresso de upload e status de galeria.
    Utiliza o slug da galeria para identificação do grupo.
    """

    async def connect(self):
        # 1. Grupo Global (Lista de Galerias)
        self.global_group = "galerias_status_updates"

        # 2. Grupo Específico
        self.galeria_slug = self.scope.get('url_route', {}).get('kwargs', {}).get('slug')

        if self.galeria_slug:
            self.specific_group = f"galeria_{self.galeria_slug}"
        else:
            # Caso não tenha slug, define como lista_geral para bater com a rota ws/repositorio/galerias/
            self.specific_group = "galeria_lista_geral"

        await self.channel_layer.group_add(self.global_group, self.channel_name)
        if self.specific_group:
            await self.channel_layer.group_add(self.specific_group, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'global_group'):
            await self.channel_layer.group_discard(self.global_group, self.channel_name)
        if hasattr(self, 'specific_group') and self.specific_group:
            await self.channel_layer.group_discard(self.specific_group, self.channel_name)

    async def status_update(self, event):
        """Atualiza a cor/texto do badge na lista de galerias."""
        await self.send(text_data=json.dumps({
            'type': 'status_galeria',
            'galeria_id': event.get('galeria_id'),
            'status_display': event.get('status_display'),
            'status_code': event.get('status_code')
        }))

    async def notificar_progresso(self, event):
        """
        Envia progresso individual da imagem.
        """
        await self.send(text_data=json.dumps({
            'type': 'progresso_imagem',
            'imagem_id': event.get('imagem_id'),
            'progresso': event.get('progress'),
            'status': event.get('status'),
            'url_thumb': event.get('url_thumb'),
            'arquivo_processado': event.get('arquivo_processado')
        }))

    async def notify_status(self, event):
        """
        Handler para mensagens do tipo 'notify_status' enviadas pelas tasks.
        """
        await self.send(text_data=json.dumps(event['data']))