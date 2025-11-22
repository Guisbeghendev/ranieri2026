/**
 * Arquivo: catalogo.js
 * App: sim_cozinha
 *
 * Implementa a lógica de transição e navegação do Catálogo de Eventos/Receitas
 * no formato de Livro Digital sequencial.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Elementos principais
    const contentContainer = document.querySelector('.section-alt .container');

    // Se não houver container, a página não é de catálogo ou está vazia
    if (!contentContainer) return;

    // 2. Transição de Conteúdo (Fade-In)
    // Inicializa a transição de entrada do conteúdo.
    // A classe 'fade-in' deve estar no elemento pai para que esta lógica funcione.
    const runInitialFadeIn = () => {
        // Adiciona a classe que inicia a transição (se não estiver presente)
        contentContainer.classList.add('fade-in');

        // Timeout para garantir que o DOM esteja totalmente carregado antes de remover o 'fade-in'
        setTimeout(() => {
            contentContainer.style.opacity = '1';
        }, 50); // Pequeno delay
    };

    runInitialFadeIn();

    // 3. Função de Navegação Sequencial
    const navigateChapter = (event) => {
        const link = event.currentTarget; // O link clicado (Próximo/Anterior)

        // Verifica se o botão está desabilitado (is-disabled)
        if (link.classList.contains('is-disabled')) {
            event.preventDefault();
            return;
        }

        // Adiciona classe de fade-out antes de navegar
        contentContainer.style.opacity = '0';

        // Desabilita os botões para evitar cliques duplos durante a transição
        document.querySelectorAll('.action-button').forEach(btn => {
            btn.classList.add('is-disabled');
            // Mudar o texto dos botões para feedback visual
            if (btn.id === 'btn-proximo') {
                btn.textContent = 'Carregando...';
            } else if (btn.id === 'btn-anterior') {
                btn.textContent = 'Carregando...';
            }
        });

        // Espera a transição CSS de fade-out (0.5s) e então navega
        setTimeout(() => {
            window.location.href = link.href;
        }, 500); // Deve ser igual ou maior que o tempo de transição em CSS (var(--transition) = 0.2s, mas 0.5s é mais seguro)

        // Impede a navegação padrão imediata do link
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
    // Adiciona o link de pré-busca para o próximo capítulo
    if (btnProximo && btnProximo.href) {
        const prefetchLink = document.createElement('link');
        prefetchLink.rel = 'prefetch';
        prefetchLink.href = btnProximo.href;
        document.head.appendChild(prefetchLink);
        // console.log("Prefetching: " + btnProximo.href);
    }
});