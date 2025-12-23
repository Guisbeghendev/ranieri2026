(function() {
    'use strict';

    // ----------------------------------------------------------------------
    // Variáveis de escopo
    // ----------------------------------------------------------------------
    const actionForms = document.querySelectorAll('.js-action-form');
    const deleteForm = document.getElementById('delete-form');
    // Adiciona uma verificação defensiva caso o formulário de exclusão não exista (embora deva existir)
    const csrfToken = deleteForm ? deleteForm.querySelector('[name=csrfmiddlewaretoken]').value : null;

    // ----------------------------------------------------------------------
    // CONFIGURAÇÃO WEBSOCKET (STATUS EM TEMPO REAL)
    // ----------------------------------------------------------------------
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const statusSocket = new WebSocket(
        protocol + window.location.host + '/ws/repositorio/galerias/'
    );

    statusSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        const pk = data.galeria_id;
        const newStatus = data.status_code;

        // Atualiza a linha da galeria
        updateGalleryRow(pk, newStatus);

        // Feedback visual (piscar a linha)
        const row = document.getElementById(`galeria-row-${pk}`);
        if (row) {
            row.style.transition = 'background-color 0.5s';
            row.style.backgroundColor = '#d1ecf1';
            setTimeout(() => {
                row.style.backgroundColor = '';
            }, 3000);
        }
    };

    statusSocket.onclose = function(e) {
        console.error('WebSocket de status fechado inesperadamente');
    };

    if (!actionForms.length || !csrfToken) {
        // console.warn("Forms de ação não encontrados ou CSRF token ausente.");
        return;
    }

    /**
     * Atualiza o estado visual da linha da galeria após uma ação (Publicar/Arquivar).
     * @param {number} pk - Primary Key da galeria.
     * @param {string} newStatus - O novo código de status ('PB', 'AR', etc.).
     */
    function updateGalleryRow(pk, newStatus) {
        const row = document.getElementById(`galeria-row-${pk}`);
        if (!row) return;

        // 1. Atualiza a célula de status
        const statusCell = row.querySelector('.js-status-cell');
        if (statusCell) {
            statusCell.innerHTML = createStatusBadge(newStatus);
        }

        // 2. Atualiza a seção de Ações Dinâmicas (Publicar/Arquivar)
        const actionsGroup = row.querySelector('.js-status-actions');
        if (actionsGroup) {
            actionsGroup.setAttribute('data-status', newStatus);

            // Reconstroi os botões dinâmicos com base no novo status
            actionsGroup.innerHTML = '';

            // Botão de Publicar (Mostra se não for 'PB')
            if (newStatus !== 'PB') {
                const publicarForm = createActionForm('publicar', pk, 'btn-success', 'fa-paper-plane', 'Publicar Galeria (Tornar visível)');
                actionsGroup.appendChild(publicarForm);
            }

            // Botão de Arquivar (Mostra se for 'PR' ou 'PB')
            if (newStatus === 'PR' || newStatus === 'PB') {
                const arquivarForm = createActionForm('arquivar', pk, 'btn-warning', 'fa-archive', 'Arquivar Galeria (Esconder do público)');
                actionsGroup.appendChild(arquivarForm);
            }

            // Reatacha os listeners aos novos botões
            actionsGroup.querySelectorAll('.js-action-form').forEach(form => {
                form.addEventListener('submit', handleActionSubmit);
            });
        }
    }

    /**
     * Helper para criar o HTML do badge de status.
     * @param {string} status - O código de status.
     * @returns {string} HTML do badge.
     */
    function createStatusBadge(status) {
        switch (status) {
            case 'PR':
                return '<span class="badge badge-status badge-warning">Rascunho</span>';
            case 'PB':
                return '<span class="badge badge-status badge-success">Publicada</span>';
            case 'AR':
                return '<span class="badge badge-status badge-danger">Arquivada</span>';
            case 'PC':
            case 'RV':
                return '<span class="badge badge-status badge-info">Processamento</span>';
            default:
                return '';
        }
    }

    /**
     * Helper para criar o formulário de ação (Publicar/Arquivar) dinamicamente.
     * @param {string} action - 'publicar' ou 'arquivar'.
     * @param {number} pk - Primary Key da galeria.
     * @param {string} btnClass - Classe do botão (ex: 'btn-success').
     * @param {string} iconClass - Classe do ícone (ex: 'fa-paper-plane').
     * @param {string} title - Texto do tooltip.
     * @returns {HTMLElement} O elemento form criado.
     */
    function createActionForm(action, pk, btnClass, iconClass, title) {
        // ATENÇÃO: Verifique se as URLs abaixo correspondem exatamente às suas URLs configuradas no Django.
        const url = action === 'publicar'
            ? `/repositorio-admin/galeria/publicar/${pk}/` // Ajuste a URL base conforme sua configuração de rotas
            : `/repositorio-admin/galeria/arquivar/${pk}/`;

        const formHtml = `
            <form method="post"
                  action="${url}"
                  class="d-inline js-action-form"
                  data-action="${action}"
                  data-galeria-pk="${pk}"
                  style="display: inline-block;">
                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                <button type="submit"
                        class="btn ${btnClass} btn-icon-sm js-action-button"
                        title="${title}">
                    <i class="fas ${iconClass}"></i>
                </button>
            </form>
        `;
        const div = document.createElement('div');
        div.innerHTML = formHtml.trim();
        return div.firstChild;
    }


    /**
     * Handler para submissão dos formulários de Publicar/Arquivar via AJAX.
     * @param {Event} event
     */
    function handleActionSubmit(event) {
        event.preventDefault();

        const form = event.currentTarget;
        const button = form.querySelector('.js-action-button');
        const pk = form.getAttribute('data-galeria-pk');
        const action = form.getAttribute('data-action');
        const originalHtml = button.innerHTML;

        // Desativa o botão e mostra spinner
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        fetch(form.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams(new FormData(form)) // Envia os dados do formulário
        })
        .then(response => {
            if (!response.ok) {
                // Se o status não for 2xx (ex: 400, 404, 500), lança um erro
                return response.json().then(err => { throw new Error(err.message || err.erro || 'Erro desconhecido.'); });
            }
            return response.json();
        })
        .then(data => {
            // Verifica se a resposta JSON foi bem-sucedida e se o status mudou
            if (data.status_mudou) {
                // Atualiza o DOM
                updateGalleryRow(pk, data.status);
                // Feedback visual de sucesso
                alert(data.message);
            } else {
                // Feedback visual de que o status já era o desejado
                alert(data.message);
            }
        })
        .catch(error => {
            console.error(`Erro ao executar a ação '${action}':`, error);
            alert(`Falha ao executar a ação '${action}': ${error.message}`);
        })
        .finally(() => {
            // Reativa o botão original (caso a atualização da linha tenha falhado)
            // Se updateGalleryRow funcionou, este botão foi substituído, mas mantemos o finally
            // para garantir que o estado visual do botão seja restaurado em caso de erro.
            button.disabled = false;
            if (!document.getElementById(`galeria-row-${pk}`).querySelector(`[data-action="${action}"]`)) {
                 // Se o botão não foi substituído (erro na atualização da linha), restauramos o HTML original
                 button.innerHTML = originalHtml;
            }
        });
    }

    /**
     * Função global (exposta no escopo global) para o botão de exclusão.
     * Esta função é chamada via atributo `onclick` no HTML.
     * @param {HTMLElement} element - O botão de exclusão clicado.
     */
    window.confirmDelete = function(element) {
        const galeriaPk = element.getAttribute('data-galeria-pk');
        const deleteUrl = element.getAttribute('data-delete-url');

        // Confirmação simples
        if (confirm('Tem certeza de que deseja excluir esta galeria? As imagens vinculadas serão desanexadas, mas não serão excluídas do repositório.')) {
            // Define a action do form oculto e submete
            deleteForm.action = deleteUrl;
            deleteForm.submit();
        }
    }


    // ----------------------------------------------------------------------
    // Execução
    // ----------------------------------------------------------------------

    // Adiciona o listener de submissão AJAX a todos os formulários de ação dinâmicos
    actionForms.forEach(form => {
        form.addEventListener('submit', handleActionSubmit);
    });

})();