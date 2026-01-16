// historia/static/historia/js/livro_digital.js

document.addEventListener('DOMContentLoaded', function() {
    const chapterContent = document.querySelector('.chapter-content');
    const btnAnterior = document.getElementById('btn-anterior');
    const btnProximo = document.getElementById('btn-proximo');

    // Seleciona botões de navegação ignorando os desabilitados (bg-gray-300)
    const navButtons = [btnAnterior, btnProximo].filter(btn => btn && !btn.hasAttribute('disabled'));

    // 1. EFEITO FADE-IN NA CARGA DO CAPÍTULO
    if (chapterContent) {
        chapterContent.style.opacity = '0';
        chapterContent.style.transition = 'opacity 0.5s ease-in-out';
        setTimeout(() => {
            chapterContent.style.opacity = '1';
        }, 100);
    }

    // 2. ADICIONA COMPORTAMENTO DE LOADING NOS CLIQUES
    navButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            if (chapterContent) {
                chapterContent.style.opacity = '0';
            }

            // Desabilita os botões e altera visual para feedback
            navButtons.forEach(b => {
                b.classList.add('opacity-50', 'cursor-not-allowed');
                b.setAttribute('disabled', 'true');
                b.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Carregando...';
            });

            const targetHref = button.href;
            setTimeout(() => {
                window.location.href = targetHref;
            }, 300);

            event.preventDefault();
        });
    });

    // 3. NAVEGAÇÃO POR TECLAS DE SETA
    document.addEventListener('keydown', (event) => {
        const isTyping = event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA';
        if (isTyping) return;

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
    if (btnProximo && btnProximo.tagName === 'A') {
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = btnProximo.href;
        document.head.appendChild(link);
    }
});