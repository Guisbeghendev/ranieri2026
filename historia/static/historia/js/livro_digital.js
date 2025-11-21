// coral/static/coral/js/livro_digital_coral.js

document.addEventListener('DOMContentLoaded', function() {
    const chapterContent = document.querySelector('.chapter-content');
    // Seleciona todos os botões de navegação que devem ter a ação de carregamento
    const navButtons = document.querySelectorAll('.chapter-navigation .action-button');

    const btnAnterior = document.getElementById('btn-anterior');
    const btnProximo = document.getElementById('btn-proximo');

    // 1. EFEITO FADE-IN NA CARGA DO CAPÍTULO
    // Adiciona uma classe de fade-in no carregamento para a transição inicial
    if (chapterContent) {
        // Assume que o CSS tem a classe .fade-in-start (opacidade 0) e .fade-in-end (opacidade 1 + transition)
        chapterContent.classList.add('fade-in-start');
        setTimeout(() => {
            chapterContent.classList.add('fade-in-end');
            // Remove a classe inicial após a transição
            chapterContent.classList.remove('fade-in-start');
        }, 100);
    }

    // 2. ADICIONA COMPORTAMENTO DE LOADING/TRANSITION NOS CLIQUES
    navButtons.forEach(button => {
        // Ignora botões que são de fato desabilitados (sem href)
        if (!button.href) {
            return;
        }

        button.addEventListener('click', function(event) {
            // Oculta o conteúdo com fade-out
            if (chapterContent) {
                chapterContent.style.opacity = 0;

                // Desabilita os botões para evitar cliques duplos durante a transição
                navButtons.forEach(b => {
                    b.classList.add('is-disabled');
                    b.setAttribute('disabled', 'true');
                    b.textContent = 'Carregando...'; // Feedback visual
                });
            }

            // Permite que o link original seja seguido após um pequeno atraso (para a animação)
            setTimeout(() => {
                window.location.href = button.href;
            }, 300); // 300ms de atraso

            // Impede a ação padrão imediata do link
            event.preventDefault();
        });
    });

    // 3. Navegação por Teclas de Seta (mantida do código anterior)
    document.addEventListener('keydown', (event) => {
        const isTyping = event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA';
        if (isTyping) {
            return;
        }

        if (event.key === 'ArrowLeft' && btnAnterior && !btnAnterior.hasAttribute('disabled')) {
            event.preventDefault();
            btnAnterior.click();
        }

        if (event.key === 'ArrowRight' && btnProximo && !btnProximo.hasAttribute('disabled')) {
            event.preventDefault();
            btnProximo.click();
        }
    });

    // 4. PRÉ-BUSCA (PREFETCH) DO PRÓXIMO CAPÍTULO
    if (btnProximo && !btnProximo.classList.contains('is-disabled')) {
        const nextUrl = btnProximo.href;

        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = nextUrl;
        document.head.appendChild(link);

        console.log(`[Coral] Prefetching: ${nextUrl}`);
    }

});