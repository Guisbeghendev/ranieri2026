/**
 * Arquivo: repertorio.js
 * App: coral
 * * Implementa a lógica de transição e navegação do Repertório Musical
 */

document.addEventListener('DOMContentLoaded', () => {
    const contentContainer = document.querySelector('.section-alt .container');
    if (!contentContainer) return;

    // Transição de entrada
    const runInitialFadeIn = () => {
        contentContainer.style.opacity = '0';
        contentContainer.style.transition = 'opacity 0.5s ease-in-out';

        setTimeout(() => {
            contentContainer.style.opacity = '1';
        }, 50);
    };

    runInitialFadeIn();

    // Função de Navegação
    const navigateChapter = (event) => {
        const link = event.currentTarget;

        if (link.classList.contains('is-disabled')) {
            event.preventDefault();
            return;
        }

        contentContainer.style.opacity = '0';

        document.querySelectorAll('.action-button').forEach(btn => {
            btn.classList.add('is-disabled');
            if (btn.id === 'btn-proximo') {
                btn.textContent = 'Carregando...';
            } else if (btn.id === 'btn-anterior') {
                btn.textContent = 'Carregando...';
            }
        });

        setTimeout(() => {
            window.location.href = link.href;
        }, 500);

        event.preventDefault();
    };

    const btnAnterior = document.getElementById('btn-anterior');
    const btnProximo = document.getElementById('btn-proximo');

    if (btnAnterior) btnAnterior.addEventListener('click', navigateChapter);
    if (btnProximo) btnProximo.addEventListener('click', navigateChapter);

    // Prefetch da próxima página
    if (btnProximo && btnProximo.href) {
        const prefetchLink = document.createElement('link');
        prefetchLink.rel = 'prefetch';
        prefetchLink.href = btnProximo.href;
        document.head.appendChild(prefetchLink);
    }
});