(function() {
    'use strict';

    // A função showCustomModal é definida no template HTML e deve estar disponível aqui
    if (typeof showCustomModal !== 'function') {
        console.error("Erro: A função showCustomModal não está definida. O modal de feedback não funcionará.");
    }

    const imageCards = document.querySelectorAll('.image-card');
    const form = document.getElementById('image-selection-form');
    const setCoverButtons = document.querySelectorAll('.js-set-cover-btn');
    const currentCoverIdElement = document.getElementById('current-cover-id');

    // Elementos de feedback da capa atual no topo da página
    const capaThumb = document.getElementById('capa-thumb');
    const capaText = document.getElementById('capa-text');

    // URL template é definido no HTML
    // NOTA: O bloco <script> no HTML garante que esta constante existe no escopo global (window) ou no topo do script.
    const DEFINIR_CAPA_URL_TEMPLATE = window.DEFINIR_CAPA_URL_TEMPLATE;


    if (imageCards.length === 0 || !form) {
        console.warn('Elementos essenciais não encontrados para inicializar o JS.');
        return;
    }

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
        const originalName = card.getAttribute('data-original-name'); // Pego do data-attribute no HTML


        if (!DEFINIR_CAPA_URL_TEMPLATE) {
            showCustomModal('Erro de Configuração', 'A URL de definição de capa não foi configurada corretamente. Contate o suporte.', 'error');
            return;
        }

        // CORREÇÃO: Substituímos o PLACEHOLDER de STRING 'IMAGEM_PK' pelo valor real do PK.
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
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest', // Indica que é uma requisição AJAX
                'X-CSRFToken': csrfToken
            },
            // Corpo vazio é suficiente
            body: ''
        })
        .then(response => {
            if (!response.ok) {
                // Tenta ler o erro do JSON de resposta (se o servidor o enviou)
                return response.json().then(err => {
                    throw new Error(err.erro || `Erro de Servidor (${response.status})`);
                }).catch(() => {
                    // Lança um erro genérico se o corpo não for JSON
                    throw new Error(`Erro na requisição: Status ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.sucesso) {
                // 1. Feedback visual customizado (Substitui alert())
                showCustomModal('Sucesso', data.message, 'success');

                // 2. Atualiza o indicador de capa (remove de todos e adiciona ao novo)
                document.querySelectorAll('.image-card').forEach(c => {
                    c.classList.remove('is-cover');
                });
                card.classList.add('is-cover');

                // 3. Garante que a imagem está selecionada (anexada)
                const checkbox = card.querySelector('input[type="checkbox"][name="imagens"]');
                if (checkbox && !checkbox.checked) {
                    checkbox.checked = true;
                    card.classList.add('is-selected');
                }

                // 4. Atualiza o indicador de capa no topo da página
                if (capaThumb && capaText) {
                    capaThumb.src = imageUrl;
                    // Garante que a miniatura da capa aparece se estava oculta
                    capaThumb.style.display = 'block';
                    capaText.innerHTML = `ID: ${imagemPk} (${originalName})`;

                    // Atualiza o ID da capa para referência futura
                    if (currentCoverIdElement) {
                        currentCoverIdElement.setAttribute('data-cover-id', imagemPk);
                    }
                }

            } else {
                // O servidor retornou 200, mas o campo 'sucesso' é falso
                showCustomModal('Erro', `Falha ao definir capa: ${data.erro}`, 'error');
            }
        })
        .catch(error => {
            console.error('Erro AJAX:', error);
            // 5. Exibe o erro de comunicação ou servidor (Substitui alert())
            showCustomModal('Erro de Comunicação', error.message, 'error');
        })
        .finally(() => {
            // Reativa o botão e restaura o conteúdo original
            button.disabled = false;
            button.innerHTML = originalButtonContent;
        });
    }


    // ----------------------------------------------------------------------
    // Inicialização
    // ----------------------------------------------------------------------

    // 1. Adiciona o listener de clique a cada cartão de imagem para seleção
    imageCards.forEach(card => {
        card.addEventListener('click', toggleImageSelection);
    });

    // 2. Adiciona o listener de clique a cada botão de definir capa
    setCoverButtons.forEach(button => {
        button.addEventListener('click', setGalleryCover);
    });

})();