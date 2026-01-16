/**
 * Arquivo: repertorio.js
 * App: coral
 * Adaptado para Tailwind v4
 */

document.addEventListener('DOMContentLoaded', () => {
    // Seletor atualizado para a estrutura do novo template
    const contentContainer = document.querySelector('.bg-surface .container');
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

        // Verifica a classe de estado desabilitado do Tailwind
        if (link.classList.contains('cursor-not-allowed')) {
            event.preventDefault();
            return;
        }

        contentContainer.style.opacity = '0';

        // Seleciona os botões de navegação
        const navButtons = [document.getElementById('btn-anterior'), document.getElementById('btn-proximo')];

        navButtons.forEach(btn => {
            if (btn) {
                btn.classList.add('opacity-50', 'cursor-not-allowed');
                btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Carregando...';
            }
        });

        setTimeout(() => {
            window.location.href = link.href;
        }, 500);

        event.preventDefault();
    };

    const btnAnterior = document.getElementById('btn-anterior');
    const btnProximo = document.getElementById('btn-proximo');

    if (btnAnterior && btnAnterior.tagName === 'A') btnAnterior.addEventListener('click', navigateChapter);
    if (btnProximo && btnProximo.tagName === 'A') btnProximo.addEventListener('click', navigateChapter);

    // Prefetch da próxima página
    if (btnProximo && btnProximo.href) {
        const prefetchLink = document.createElement('link');
        prefetchLink.rel = 'prefetch';
        prefetchLink.href = btnProximo.href;
        document.head.appendChild(prefetchLink);
    }
});