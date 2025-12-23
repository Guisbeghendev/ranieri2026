// galerias/js/simple_lightbox.js - USANDO O ELEMENTO NATIVO <DIALOG>

(function() {
    'use strict';

    const modal = document.getElementById("simple-lightbox-modal");
    const modalImage = document.getElementById("lightbox-image");
    const modalCaption = document.getElementById("lightbox-caption");
    const imageTriggers = document.querySelectorAll(".lightbox-trigger");
    const closeBtn = modal ? modal.querySelector(".lightbox-close") : null;

    if (!modal) return; // Sai se o modal não existir

    // ----------------------------------------------------------------------
    // Abrir o Modal
    // ----------------------------------------------------------------------
    imageTriggers.forEach(trigger => {
        trigger.addEventListener('click', function(event) {
            event.preventDefault();

            const imageUrl = this.getAttribute('href');
            const imageTitle = this.getAttribute('data-title') || 'Imagem';

            modalImage.src = imageUrl;
            modalCaption.textContent = imageTitle;

            // MÉTODO CRÍTICO: showModal() coloca o elemento na camada superior
            modal.showModal();
            // O navegador cuida automaticamente de desativar a rolagem do body.
        });
    });

    // ----------------------------------------------------------------------
    // Fechar o Modal
    // ----------------------------------------------------------------------

    // Ao clicar no botão de fechar (X)
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.close();
        });
    }

    // Fechar ao clicar no fundo (backdrop)
    // O evento 'click' no <dialog> só dispara no backdrop se o cursor estiver fora do conteúdo.
    modal.addEventListener('click', (event) => {
        // Verifica se o clique foi no próprio backdrop ou no elemento <dialog> fora do conteúdo
        if (event.target === modal) {
            modal.close();
        }
    });

    // A tecla ESC funciona automaticamente com showModal(), sem necessidade de código extra.

})();