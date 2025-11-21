// historia/static/historia/js/livro_digital.js

document.addEventListener('DOMContentLoaded', function() {
    const chapterContent = document.querySelector('.chapter-content');
    const navButtons = document.querySelectorAll('.chapter-navigation .action-button');

    // 1. EFEITO FADE-IN NA CARGA DO CAPÍTULO
    // Adiciona uma classe de fade-in no carregamento para a transição inicial
    if (chapterContent) {
        chapterContent.classList.add('fade-in-start');
        setTimeout(() => {
            chapterContent.classList.add('fade-in-end');
            // Remove a classe inicial após a transição
            chapterContent.classList.remove('fade-in-start');
        }, 100);
    }

    // 2. ADICIONA COMPORTAMENTO DE LOADING/TRANSITION NOS CLIQUES
    // Isso simula a "virada de página" antes do recarregamento da view Django.
    navButtons.forEach(button => {
        // Ignora botões desabilitados
        if (button.classList.contains('is-disabled')) {
            return;
        }

        button.addEventListener('click', function(event) {
            const isBack = button.id === 'btn-anterior';

            // 2.1. Inicia o efeito de saída (Fade-Out)
            if (chapterContent) {
                // Adiciona uma classe para animar o conteúdo para fora (ex: slide left/right + fade)
                chapterContent.style.opacity = 0;

                // Opcional: Adicionar classe CSS que define a direção da transição
                // chapterContent.classList.add(isBack ? 'slide-right' : 'slide-left');

                // Desabilita os botões para evitar cliques duplos durante a transição
                navButtons.forEach(b => {
                    b.classList.add('is-disabled');
                    b.setAttribute('disabled', 'true');
                    b.textContent = 'Carregando...'; // Feedback visual
                });
            }

            // 2.2. Permite que o link original seja seguido após um pequeno atraso (para a animação)
            // Se você quisesse fazer uma SPA (sem reload), faria a chamada fetch() aqui.
            // Como estamos fazendo um reload clássico de Django, só atrasamos.
            setTimeout(() => {
                // Deixa o evento seguir para o href
                window.location.href = button.href;
            }, 300); // 300ms de atraso para o fade-out visual

            // Impede a ação padrão imediata do link
            event.preventDefault();
        });
    });

    // 3. PRÉ-BUSCA (PREFETCH) DO PRÓXIMO CAPÍTULO
    // Para tornar a navegação mais rápida. Apenas para o próximo.
    const btnProximo = document.getElementById('btn-proximo');
    if (btnProximo && !btnProximo.classList.contains('is-disabled')) {
        const nextUrl = btnProximo.href;

        // Cria um link invisível para acionar a pré-busca do navegador
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = nextUrl;
        document.head.appendChild(link);

        console.log(`[Historia] Prefetching: ${nextUrl}`);
    }

});