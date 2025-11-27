(function() {
    'use strict';

    // 1. Elementos DOM
    const fileInput = document.getElementById('id_arquivos');
    const uploadArea = document.getElementById('file-upload-area');
    const fileCountText = document.getElementById('file-count-text');
    const submitButton = document.getElementById('submit-button');

    if (!fileInput || !uploadArea || !submitButton) return;

    // Associa o input de arquivo à área clicável
    uploadArea.addEventListener('click', function() {
        // Clicar na área visual dispara o clique no input real
        fileInput.click();
    });

    // Adiciona o listener para o evento de mudança (seleção manual ou via drop)
    fileInput.addEventListener('change', handleFileSelect);

    /**
     * Atualiza o feedback visual e o botão de submissão ao selecionar arquivos.
     */
    function handleFileSelect(event) {
        const files = event.target.files;
        const count = files.length;

        if (count > 0) {
            fileCountText.textContent = `${count} arquivo(s) selecionado(s) pronto(s) para upload.`;
            uploadArea.classList.add('has-files');
            submitButton.disabled = false;
        } else {
            fileCountText.textContent = `Nenhum arquivo selecionado.`;
            uploadArea.classList.remove('has-files');
            // Remove o estilo de sucesso se a seleção for limpa
            uploadArea.style.borderColor = 'var(--color-border-dark)';
            uploadArea.style.backgroundColor = 'white';
            submitButton.disabled = true;
        }
    }

    // 2. Funcionalidade de Drag and Drop (Vanilla JS)

    // Lista de eventos para prevenir o comportamento padrão do navegador
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Realça a área quando arrastar está ativo
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });

    // Remove o realce quando arrastar sai ou solta
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        // Adiciona um realce suave
        uploadArea.style.borderColor = 'var(--laranja-medio1)';
        uploadArea.style.backgroundColor = 'var(--color-background-hover)';
    }

    function unhighlight() {
        // Restaura a cor, a menos que já tenha arquivos selecionados
        if (!uploadArea.classList.contains('has-files')) {
             uploadArea.style.borderColor = 'var(--color-border-dark)';
             uploadArea.style.backgroundColor = 'white';
        }
    }

    // Manipula a soltura dos arquivos
    uploadArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        // Atribui os arquivos soltos ao input de arquivo
        fileInput.files = files;

        // Dispara o evento 'change' para atualizar o feedback visual e o botão
        const changeEvent = new Event('change');
        fileInput.dispatchEvent(changeEvent);

        unhighlight();
    }

})();