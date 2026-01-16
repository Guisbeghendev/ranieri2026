// coral/static/coral/js/livro_digital_coral.js

document.addEventListener('DOMContentLoaded', () => {
    // Seleciona os elementos de navegação conforme as novas classes do Tailwind
    const btnAnterior = document.getElementById('btn-anterior');
    const btnProximo = document.getElementById('btn-proximo');
    // Adaptado para a nova estrutura de classes
    const chapterContent = document.querySelector('.prose');

    // 1. Efeito de carregamento/transição
    if (chapterContent) {
        chapterContent.style.opacity = 0;
        setTimeout(() => {
            chapterContent.style.transition = 'opacity 0.6s ease-in-out';
            chapterContent.style.opacity = 1;
        }, 100);
    }

    // 2. Navegação por Teclas de Seta
    document.addEventListener('keydown', (event) => {
        const isTyping = event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA';
        if (isTyping) return;

        // Seta para a esquerda (Anterior)
        if (event.key === 'ArrowLeft' && btnAnterior && !btnAnterior.hasAttribute('disabled')) {
            event.preventDefault();
            btnAnterior.click();
        }

        // Seta para a direita (Próximo)
        if (event.key === 'ArrowRight' && btnProximo && !btnProximo.hasAttribute('disabled')) {
            event.preventDefault();
            btnProximo.click();
        }
    });

    // 3. Feedback visual ao clicar
    const addLoadingEffect = (element) => {
        // Verifica se não tem a classe de desabilitado do Tailwind (bg-gray-300)
        if (element && !element.classList.contains('bg-gray-300')) {
            element.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Carregando...';
            element.classList.add('opacity-75', 'cursor-not-allowed');
        }
    };

    if (btnAnterior) {
        btnAnterior.addEventListener('click', () => addLoadingEffect(btnAnterior));
    }

    if (btnProximo) {
        btnProximo.addEventListener('click', () => addLoadingEffect(btnProximo));
    }
});