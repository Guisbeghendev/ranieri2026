// galerias/js/alpine_lightbox.js
// Script de inicialização Alpine.js para o Lightbox da Galeria

document.addEventListener('alpine:init', () => {
    Alpine.data('galleryLightbox', () => ({
        isOpen: false,
        currentIndex: 0,
        gallery: [], // Array que armazenará { url, title } de todas as imagens

        // 1. Inicializa: Popula a array 'gallery' e configura os listeners
        initTriggers() {
            // Seleciona todos os links marcados para abrir o lightbox
            const triggers = document.querySelectorAll('.lightbox-trigger');

            // Popula a array 'gallery' com os dados necessários
            this.gallery = Array.from(triggers).map(trigger => ({
                url: trigger.getAttribute('href'),
                title: trigger.getAttribute('data-title'),
            }));

            // Adiciona listener de clique para cada miniatura
            triggers.forEach(trigger => {
                trigger.addEventListener('click', (e) => {
                    e.preventDefault();
                    // O data-index (forloop.counter0 no Django) diz qual imagem abrir
                    const index = parseInt(trigger.getAttribute('data-index'));
                    this.openLightbox(index);
                });
            });

            // Adiciona listeners globais para navegação por teclado
            window.addEventListener('keydown', (e) => {
                if (!this.isOpen) return; // Só navega se o modal estiver aberto

                if (e.key === 'ArrowRight' || e.key === ' ') {
                    e.preventDefault(); // Impede rolagem ou ação padrão da barra de espaço
                    this.nextImage();
                } else if (e.key === 'ArrowLeft') {
                    e.preventDefault(); // Impede rolagem ou ação padrão
                    this.prevImage();
                }
            });
        },

        // 2. Propriedade Computada: Retorna os dados da imagem atualmente selecionada
        get currentImage() {
            return this.gallery[this.currentIndex] || { url: '', title: '' };
        },

        // 3. Ações
        openLightbox(index) {
            this.currentIndex = index;
            this.isOpen = true;
            // Bloqueia a rolagem do fundo
            document.body.classList.add('modal-open');
        },

        closeLightbox() {
            this.isOpen = false;
            // Restaura a rolagem do fundo
            document.body.classList.remove('modal-open');
        },

        nextImage() {
            if (this.currentIndex < this.gallery.length - 1) {
                this.currentIndex++;
            }
        },

        prevImage() {
            if (this.currentIndex > 0) {
                this.currentIndex--;
            }
        }
    }));
});