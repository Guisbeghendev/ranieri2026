document.addEventListener('DOMContentLoaded', function() {
    // 1. Inicialização de Lightbox ou Visualizador Simples
    const imagens = document.querySelectorAll('.galeria-item');

    imagens.forEach(img => {
        img.addEventListener('click', function() {
            const fullResUrl = this.getAttribute('data-proxy-url');
            if (fullResUrl) {
                abrirVisualizador(fullResUrl);
            }
        });
    });

    // 2. Função para abrir o modal de visualização
    function abrirVisualizador(url) {
        // Exemplo básico: assume a existência de um modal no template
        const modalImg = document.querySelector('#modalImagemFull');
        if (modalImg) {
            modalImg.src = url;
            // Lógica para disparar o modal (Bootstrap ou Custom)
            $('#modalVisualizacao').modal('show');
        } else {
            // Fallback caso não queira usar modal complexo
            window.open(url, '_blank');
        }
    }
});