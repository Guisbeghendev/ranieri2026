/**
 * Lógica JavaScript para a página de Detalhes do Tópico de Suporte.
 * Inclui:
 * 1. Rolagem automática da área de mensagens para o final (última mensagem).
 * 2. Funcionalidade de um botão flutuante 'Voltar ao Fim' que aparece ao rolar.
 * NOTA DE CORREÇÃO: O z-index do botão FIXED (no CSS) faz com que ele se sobreponha a outros elementos.
 * Para garantir que ele se esconda quando a ROLAGEM PRINCIPAL da página alcançar o header,
 * a lógica de mostrar/esconder deve considerar a rolagem do elemento INTERNO, mas a sobreposição
 * no header (um elemento com position: sticky) é puramente um problema de Z-INDEX no CSS.
 * A única mudança lógica necessária aqui é garantir que a rolagem do *elemento* interno
 * não cause problemas de foco. O código JS está, na verdade, correto para controlar o elemento interno.
 * O problema do botão sobrepondo o header já foi corrigido no CSS (z-index)
 * e o problema da barra de rolagem sobrepondo o header foi corrigido com 'max-height' no CSS.
 * O arquivo JS está correto para o seu objetivo.
 */

document.addEventListener('DOMContentLoaded', function() {
    const respostasList = document.getElementById('respostas-list');
    const scrollButton = document.getElementById('scroll-to-bottom-button');

    // 1. Rolagem Automática para o final da lista de respostas
    function scrollToBottom() {
        if (respostasList) {
            // No novo layout, a rolagem é feita via window para acompanhar o fluxo Tailwind
            setTimeout(() => {
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            }, 100);
        }
    }

    // Rola ao carregar a página
    scrollToBottom();

    // 2. Lógica do botão 'Voltar ao Fim'
    if (scrollButton) {

        // Define a altura limite para o botão aparecer
        const SCROLL_THRESHOLD = 300;

        // Função para mostrar/esconder o botão usando classes utilitárias do Tailwind
        window.addEventListener('scroll', function() {
            // A diferença entre a altura total e a posição atual do scroll.
            // Se for maior que o limite, significa que o usuário não está no fim.
            const distanceToBottom = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;

            if (distanceToBottom > SCROLL_THRESHOLD) {
                // scrollButton.classList.add('show');
                scrollButton.classList.remove('opacity-0', 'pointer-events-none');
                scrollButton.classList.add('opacity-100', 'pointer-events-auto');
            } else {
                // scrollButton.classList.remove('show');
                scrollButton.classList.add('opacity-0', 'pointer-events-none');
                scrollButton.classList.remove('opacity-100', 'pointer-events-auto');
            }
        });

        // Evento de clique no botão para rolar para o final
        scrollButton.addEventListener('click', function() {
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'smooth'
            });
        });
    }

    // Tratativa para o "confirm" que está no template
    // Nota: O HTML está usando 'return confirm(...)', que é um método antigo.
    // Em um projeto real, você usaria um modal customizado, mas mantemos o básico
    // para a funcionalidade do Django/Form.
});