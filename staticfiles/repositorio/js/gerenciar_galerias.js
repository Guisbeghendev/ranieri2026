(function() {
    'use strict';

    const deleteForm = document.getElementById('delete-form');
    // Removido o elemento deletePkInput pois a URL completa será passada

    /**
     * Função chamada ao clicar no botão de lixeira.
     * @param {HTMLElement} buttonElement O botão que foi clicado.
     */
    window.confirmDelete = function(buttonElement) {
        // CORRIGIDO: Obter a URL completa do botão, gerada pela tag {% url %} do Django no template
        const deleteUrl = buttonElement.getAttribute('data-delete-url');

        if (!deleteUrl) {
            console.error("URL de exclusão da Galeria não encontrada.");
            return;
        }

        const confirmation = confirm("Tem certeza de que deseja EXCLUIR esta galeria? Esta ação é irreversível.");

        if (confirmation) {
            // Define a action do formulário usando a URL gerada pelo Django (sem hardcode)
            deleteForm.action = deleteUrl;

            deleteForm.submit();
        }
    };

})();