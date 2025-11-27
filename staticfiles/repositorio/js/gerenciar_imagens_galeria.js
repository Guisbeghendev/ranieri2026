(function() {
    'use strict';

    const imageCards = document.querySelectorAll('.image-card');
    const form = document.getElementById('image-selection-form');

    if (imageCards.length === 0 || !form) return; // Sai se não houver cards ou o formulário

    /**
     * Alterna o estado de seleção visual e o checkbox.
     */
    function toggleImageSelection(event) {
        // Encontra o elemento 'image-card' clicado, garantindo que o clique foi dentro do card.
        const card = event.currentTarget;

        // Encontra o checkbox dentro do card (deve ser o único input[type="checkbox"] com name="imagens")
        const checkbox = card.querySelector('input[type="checkbox"][name="imagens"]');

        if (checkbox) {
            // Alterna o estado do checkbox
            checkbox.checked = !checkbox.checked;

            // Alterna a classe visual
            card.classList.toggle('is-selected', checkbox.checked);
        }
    }

    // Adiciona o listener de clique a cada cartão de imagem
    imageCards.forEach(card => {
        // Usa 'click' no próprio card para capturar a ação
        card.addEventListener('click', toggleImageSelection);

        // **Inicialização:** Garante que o estado visual (is-selected) reflita o estado checked
        const initialCheckbox = card.querySelector('input[type="checkbox"][name="imagens"]');
        if (initialCheckbox && initialCheckbox.checked) {
            card.classList.add('is-selected');
        }
    });

})();