// coral/static/coral/js/livro_digital_coral.js

document.addEventListener('DOMContentLoaded', () => {
    // Seleciona os elementos de navegação
    const btnAnterior = document.getElementById('btn-anterior');
    const btnProximo = document.getElementById('btn-proximo');
    const chapterContent = document.querySelector('.chapter-content');
    const cardBody = document.querySelector('.card-body');

    // 1. Efeito de carregamento/transição
    // Adiciona uma classe para animar o conteúdo do capítulo na carga da página
    if (chapterContent) {
        // Inicialmente, esconde o conteúdo ou define a opacidade para 0 via CSS.
        // Se não houver CSS, este script pode forçar um fade-in.
        chapterContent.style.opacity = 0;

        // Pequeno atraso para garantir que o DOM e o CSS estejam prontos
        setTimeout(() => {
            // Aplica uma transição suave para mostrar o conteúdo
            chapterContent.style.transition = 'opacity 0.6s ease-in-out';
            chapterContent.style.opacity = 1;
        }, 100);
    }

    // 2. Navegação por Teclas de Seta
    // Permite que o usuário use as setas do teclado para avançar ou retroceder páginas.
    document.addEventListener('keydown', (event) => {
        // Verifica se o foco não está em um campo de formulário (input, textarea)
        const isTyping = event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA';
        if (isTyping) {
            return;
        }

        // Seta para a esquerda (Anterior)
        if (event.key === 'ArrowLeft' && btnAnterior && !btnAnterior.hasAttribute('disabled')) {
            event.preventDefault(); // Impede o scroll padrão da página
            btnAnterior.click();
        }

        // Seta para a direita (Próximo)
        if (event.key === 'ArrowRight' && btnProximo && !btnProximo.hasAttribute('disabled')) {
            event.preventDefault(); // Impede o scroll padrão da página
            btnProximo.click();
        }
    });

    // 3. (Opcional) Adicionar feedback visual ao clicar nos botões
    // O Django já faz o redirecionamento, mas podemos adicionar um feedback instantâneo.
    const addLoadingEffect = (element) => {
        if (element && !element.classList.contains('is-disabled')) {
            element.classList.add('is-loading'); // Adiciona classe CSS para feedback visual (se definida)
            element.innerHTML = 'Carregando...';
        }
    };

    if (btnAnterior) {
        btnAnterior.addEventListener('click', (e) => addLoadingEffect(btnAnterior));
    }

    if (btnProximo) {
        btnProximo.addEventListener('click', (e) => addLoadingEffect(btnProximo));
    }
});