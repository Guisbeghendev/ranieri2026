(function() {
    'use strict';

    // ----------------------------------------------------------------------
    // Variáveis e Funções Essenciais (Movidas do HTML)
    // ----------------------------------------------------------------------

    /**
     * Função global para exibir o modal customizado (Substitui alert() e confirm())
     */
    function showCustomModal(title, message, type = 'info') {
        const modal = document.getElementById('custom-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalMessage = document.getElementById('modal-message');

        modalTitle.textContent = title;
        // CORREÇÃO: Usa 'text-danger' para 'error' e 'text-success' para 'success'
        modalTitle.className = type === 'error' ? 'text-danger' : 'text-success';
        modalMessage.textContent = message;

        modal.classList.remove('hidden');
        modal.querySelector('#modal-close-btn').onclick = () => {
            modal.classList.add('hidden');
        };
    }

    // Lendo a URL dinâmica do data-attribute no container principal
    const dashboardContainer = document.querySelector('.dashboard-main-container');
    const DEFINIR_CAPA_URL_TEMPLATE_RAW = dashboardContainer ? dashboardContainer.getAttribute('data-definir-capa-url-raw') : null;

    if (!DEFINIR_CAPA_URL_TEMPLATE_RAW) {
        showCustomModal('Erro Fatal', 'A URL de definição de capa não foi carregada no template HTML. Verifique o atributo data-definir-capa-url-raw.', 'error');
        return;
    }

    // CORREÇÃO CRÍTICA: O erro anterior estava na lógica de substituição de placeholder.
    // O valor '0' (placeholder) precisa ser substituído por uma string única para ser usada
    // como template dentro da função 'setGalleryCover'.
    // A regex `/0\/?$/` substituía o 0, mas dependia de como o Django gerou o reverso.
    // Usaremos a substituição simples de '0' pela string 'IMAGEM_PK' para garantir a criação do template.
    const DEFINIR_CAPA_URL_TEMPLATE = DEFINIR_CAPA_URL_TEMPLATE_RAW.replace('/0/', '/IMAGEM_PK/');

    // ----------------------------------------------------------------------
    // Inicialização de Elementos
    // ----------------------------------------------------------------------

    const imageCards = document.querySelectorAll('.image-card');
    const form = document.getElementById('image-selection-form');
    const setCoverButtons = document.querySelectorAll('.js-set-cover-btn');
    const currentCoverIdElement = document.getElementById('current-cover-id');

    // Elementos de feedback da capa atual no topo da página
    const capaThumb = document.getElementById('capa-thumb');
    const capaText = document.getElementById('capa-text');

    if (imageCards.length === 0 || !form) {
        console.warn('Elementos essenciais não encontrados para inicializar o JS.');
        return;
    }

    // ----------------------------------------------------------------------
    // Funções
    // ----------------------------------------------------------------------

    /**
     * Alterna o estado de seleção visual e o checkbox.
     */
    function toggleImageSelection(event) {
        // Encontra o elemento 'image-card' clicado
        const card = event.currentTarget;

        // Verifica se o clique foi no botão de capa para ignorar a seleção padrão
        if (event.target.closest('.js-set-cover-btn')) {
            return;
        }

        // Encontra o checkbox dentro do card
        const checkbox = card.querySelector('input[type="checkbox"][name="imagens"]');

        if (checkbox) {
            // Alterna o estado do checkbox
            checkbox.checked = !checkbox.checked;

            // Alterna a classe visual
            card.classList.toggle('is-selected', checkbox.checked);
        }
    }

    /**
     * Envia requisição AJAX para definir a capa da galeria.
     */
    function setGalleryCover(event) {
        event.preventDefault(); // Impede o submit ou a ação padrão do botão

        const button = event.currentTarget;
        const imagemPk = button.getAttribute('data-image-pk');
        const card = button.closest('.image-card');
        const imageUrl = card.getAttribute('data-image-url');
        const originalName = card.getAttribute('data-original-name');

        // Verifica se imagemPk é válido. Se for '0', o template está malformado.
        if (!imagemPk || imagemPk === '0') {
            showCustomModal('Erro de Dados', 'ID da imagem (PK) inválido ou não encontrado no botão de capa.', 'error');
            button.disabled = false;
            return;
        }


        // Usa DEFINIR_CAPA_URL_TEMPLATE e substitui o placeholder pela imagemPk
        const url = DEFINIR_CAPA_URL_TEMPLATE.replace('IMAGEM_PK', imagemPk);

        // Busca o CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        // Desativa o botão temporariamente e mostra o spinner
        button.disabled = true;
        const originalButtonContent = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.erro || `Erro de Servidor (${response.status})`);
                }).catch(() => {
                    throw new Error(`Erro na requisição: Status ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.sucesso) {
                // 1. Feedback visual customizado
                showCustomModal('Sucesso', data.message, 'success');

                // 2. Atualiza o indicador de capa (remove capa antiga e marca a nova)
                document.querySelectorAll('.image-card').forEach(c => {
                    c.classList.remove('is-cover');
                });
                card.classList.add('is-cover');

                // 3. CORREÇÃO CRÍTICA (MANTIDA): Garante que a imagem está selecionada/anexada
                const checkbox = card.querySelector('input[type="checkbox"][name="imagens"]');
                if (checkbox && !checkbox.checked) {
                    checkbox.checked = true;
                    // Garante o estado visual de seleção
                    card.classList.add('is-selected');
                }

                // 4. Atualiza o indicador de capa no topo da página
                if (capaThumb && capaText) {
                    // A view `DefinirCapaGaleriaView` retorna `capa_url`.
                    const finalImageUrl = data.capa_url || imageUrl;

                    capaThumb.src = finalImageUrl;
                    capaThumb.style.display = 'block';
                    capaText.innerHTML = `ID: ${imagemPk} (${originalName})`;

                    if (currentCoverIdElement) {
                        currentCoverIdElement.setAttribute('data-cover-id', imagemPk);
                    }
                }

            } else {
                showCustomModal('Erro', `Falha ao definir capa: ${data.erro}`, 'error');
            }
        })
        .catch(error => {
            console.error('Erro AJAX:', error);
            showCustomModal('Erro de Comunicação', error.message, 'error');
        })
        .finally(() => {
            // Reativa o botão
            button.disabled = false;
            button.innerHTML = originalButtonContent;
        });
    }

    /**
     * Verifica se existem imagens em processamento e recarrega a página se necessário.
     */
    function checkProcessingStatus() {
        const processingCards = document.querySelectorAll('.image-card:not(.status-processada):not(.status-erro)');
        if (processingCards.length > 0) {
            setTimeout(() => {
                location.reload();
            }, 5000);
        }
    }


    // ----------------------------------------------------------------------
    // Inicialização de Listeners
    // ----------------------------------------------------------------------

    // 1. Adiciona o listener de clique a cada cartão de imagem para seleção
    imageCards.forEach(card => {
        card.addEventListener('click', toggleImageSelection);
    });

    // 2. Adiciona o listener de clique a cada botão de definir capa
    setCoverButtons.forEach(button => {
        button.addEventListener('click', setGalleryCover);
    });

    // 3. Inicia verificação de status
    checkProcessingStatus();

})();