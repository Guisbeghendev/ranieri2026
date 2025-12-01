(function() {
    'use strict';

    // 1. Elementos DOM
    const fileInput = document.getElementById('id_arquivos');
    const uploadArea = document.getElementById('file-upload-area');
    const fileCountText = document.getElementById('file-count-text');
    const submitButton = document.getElementById('submit-button');
    const uploadForm = document.getElementById('upload-form');

    // URLs dos endpoints Django
    // CORREÇÃO: As rotas devem incluir o prefixo principal 'repositorio-admin/'
    // e o prefixo 'upload/' para corresponder ao repositorio/urls.py corrigido.
    const SIGN_URL = '/repositorio-admin/upload/assinar/';
    const CONFIRM_URL = '/repositorio-admin/upload/confirmar/';

    // Função utilitária para obter o token CSRF
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');


    if (!fileInput || !uploadArea || !submitButton || !uploadForm) return;

    // --- 1. CONFIGURAÇÃO BÁSICA E DRAG/DROP ---

    // Associa o input de arquivo à área clicável
    uploadArea.addEventListener('click', function() {
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
            uploadArea.style.borderColor = 'var(--laranja-medio1)';
        } else {
            fileCountText.textContent = `Nenhum arquivo selecionado.`;
            uploadArea.classList.remove('has-files');
            uploadArea.style.borderColor = 'var(--color-border-dark)';
            submitButton.disabled = true;
        }
    }

    // Funcionalidade de Drag and Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Realce
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        uploadArea.style.borderColor = 'var(--laranja-medio1)';
        uploadArea.style.backgroundColor = 'var(--color-background-hover)';
    }

    function unhighlight() {
        if (!uploadArea.classList.contains('has-files')) {
             uploadArea.style.borderColor = 'var(--color-border-dark)';
             uploadArea.style.backgroundColor = 'white';
        }
    }

    uploadArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        fileInput.files = files;

        const changeEvent = new Event('change');
        fileInput.dispatchEvent(changeEvent);

        unhighlight();
    }


    // --- 2. LÓGICA DE UPLOAD DIRETO PARA S3 ---

    submitButton.addEventListener('click', startUpload);

    /**
     * Inicia o processo de upload assíncrono para o S3.
     */
    async function startUpload() {
        const files = fileInput.files;
        if (files.length === 0) return;

        // Desabilitar interação
        submitButton.disabled = true;
        uploadArea.style.pointerEvents = 'none';

        fileCountText.textContent = `Iniciando upload de ${files.length} arquivo(s)...`;

        const uploadPromises = [];

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            uploadPromises.push(processFile(file, i, files.length));
        }

        try {
            // Espera todos os uploads serem concluídos
            const results = await Promise.allSettled(uploadPromises);

            // Verifica o sucesso
            const successfulUploads = results.filter(r => r.status === 'fulfilled' && r.value && r.value.success);

            if (successfulUploads.length > 0) {
                // CORREÇÃO: Redireciona para o painel de galerias (usando o prefixo correto)
                // A URL de redirecionamento é: /repositorio-admin/galerias/
                window.location.href = '/repositorio-admin/galerias/';
            } else {
                fileCountText.textContent = 'Falha em todos os uploads. Tente novamente.';
            }

            fileCountText.textContent = `Upload de ${successfulUploads.length} arquivo(s) concluído. Processamento iniciado.`;

        } catch (error) {
            console.error("Erro geral no processo de upload:", error);
            fileCountText.textContent = `Erro crítico no upload. Consulte o console.`;
        } finally {
            // Reabilita o input e botão (se houver arquivos)
            uploadArea.style.pointerEvents = 'auto';
            submitButton.disabled = (fileInput.files.length === 0);
        }
    }

    /**
     * Processa um único arquivo: obtém a URL assinada, faz o upload para o S3 e confirma no Django.
     */
    async function processFile(file, index, total) {
        let imagem_id = null; // Variável para rastrear o ID em caso de falha intermediária

        try {
            // 1. Solicita a URL pré-assinada ao Django
            fileCountText.textContent = `[${index + 1}/${total}] Solicitando URL para ${file.name}...`;

            const signResponse = await fetch(SIGN_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrftoken,
                },
                body: new URLSearchParams({
                    'nome_arquivo': file.name,
                    'tipo_mime': file.type || 'application/octet-stream',
                })
            });

            if (!signResponse.ok) {
                const errorData = await signResponse.json();
                throw new Error(`Erro ao assinar: ${errorData.erro || signResponse.statusText}`);
            }

            const data = await signResponse.json();
            const { url_assinada, imagem_id: received_id, caminho_s3 } = data;
            imagem_id = received_id; // Armazena o ID para confirmação

            // 2. Faz o upload direto para o S3 usando a URL assinada (Requisição PUT)
            fileCountText.textContent = `[${index + 1}/${total}] Enviando ${file.name} para o S3...`;

            const s3UploadResponse = await fetch(url_assinada, {
                method: 'PUT',
                headers: {
                    'Content-Type': file.type || 'application/octet-stream',
                },
                body: file
            });

            if (s3UploadResponse.status !== 200) {
                throw new Error(`Falha no upload S3: Status ${s3UploadResponse.status}`);
            }

            // 3. Confirma o upload no Django (chamando a nova ConfirmarUploadView)
            fileCountText.textContent = `[${index + 1}/${total}] Upload S3 OK. Confirmando no servidor...`;

            const confirmResponse = await fetch(CONFIRM_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrftoken,
                },
                body: new URLSearchParams({
                    'imagem_id': imagem_id
                })
            });

            if (!confirmResponse.ok) {
                 const errorData = await confirmResponse.json();
                 throw new Error(`Erro ao confirmar no Django: ${errorData.erro || confirmResponse.statusText}`);
            }

            // 4. Sucesso!
            fileCountText.textContent = `[${index + 1}/${total}] Sucesso: ${file.name} (Processamento iniciado).`;

            // Retorna o sucesso e o ID para o Promise.allSettled
            return { success: true, id: imagem_id, path: caminho_s3 };

        } catch (error) {
            console.error(`Erro ao processar o arquivo ${file.name}:`, error);
            fileCountText.textContent = `[${index + 1}/${total}] Falha em ${file.name}.`;
            // Rejeita a promise para que Promise.allSettled possa rastrear a falha
            throw error;
        }
    }
})();