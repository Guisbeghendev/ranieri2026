/**
 * Arquivo: catalogo.js
 * App: sim_cozinha
 *
 * Implementa a lógica de transição e navegação do Catálogo de Eventos/Receitas
 * no estilo Ranieri (transições suaves e feedback visual).
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Elementos principais
    // Ajustado para o seletor do container principal do novo layout
    const contentContainer = document.querySelector('.container.mx-auto');

    if (!contentContainer) return;

    // 2. Transição de Conteúdo (Fade-In)
    const runInitialFadeIn = () => {
        contentContainer.style.opacity = '0';
        contentContainer.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
        contentContainer.style.transform = 'translateY(10px)';

        requestAnimationFrame(() => {
            contentContainer.style.opacity = '1';
            contentContainer.style.transform = 'translateY(0)';
        });
    };

    runInitialFadeIn();

    // 3. Função de Navegação Sequencial
    const navigateChapter = (event) => {
        const link = event.currentTarget;

        // Verifica se o botão está desabilitado (pelo atributo ou classe)
        if (link.hasAttribute('disabled') || link.classList.contains('cursor-not-allowed')) {
            event.preventDefault();
            return;
        }

        // Feedback visual imediato nos botões
        const allButtons = document.querySelectorAll('#btn-anterior, #btn-proximo');
        allButtons.forEach(btn => {
            btn.style.pointerEvents = 'none';
            btn.style.opacity = '0.7';
            if (btn === link) {
                const icon = btn.querySelector('i');
                if (icon) icon.className = 'fas fa-spinner fa-spin';
            }
        });

        // Efeito de saída (Fade-out e Slide-up)
        contentContainer.style.opacity = '0';
        contentContainer.style.transform = 'translateY(-10px)';

        // Navegação com delay para a transição
        setTimeout(() => {
            window.location.href = link.href;
        }, 400);

        event.preventDefault();
    };

    // 4. Atribuição de Event Listeners
    const btnAnterior = document.getElementById('btn-anterior');
    const btnProximo = document.getElementById('btn-proximo');

    if (btnAnterior) {
        btnAnterior.addEventListener('click', navigateChapter);
    }
    if (btnProximo) {
        btnProximo.addEventListener('click', navigateChapter);
    }

    // 5. Otimização de Pré-Busca (Prefetch)
    if (btnProximo && btnProximo.href && !btnProximo.hasAttribute('disabled')) {
        const prefetchLink = document.createElement('link');
        prefetchLink.rel = 'prefetch';
        prefetchLink.href = btnProximo.href;
        document.head.appendChild(prefetchLink);
    }
});