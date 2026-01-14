(function() {
    'use strict';

    const fileInput = document.getElementById('id_arquivos');
    const uploadArea = document.getElementById('file-upload-area');
    const fileCountText = document.getElementById('file-count-text');
    const submitButton = document.getElementById('submit-button');
    const SIGN_URL = '/repositorio-admin/upload/assinar/';
    const CONFIRM_URL = '/repositorio-admin/upload/confirmar/';

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

    if (!fileInput || !uploadArea || !submitButton) return;

    // --- EVENTOS DE INTERFACE ---
    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    function handleFileSelect(e) {
        const count = e.target.files.length;
        if (count > 0) {
            fileCountText.textContent = `${count} arquivo(s) prontos para upload.`;
            submitButton.disabled = false;
        }
    }

    // --- LÓGICA DE UPLOAD SEQUENCIAL (Aproveitando do Guisbeghen) ---
    submitButton.addEventListener('click', async () => {
        const files = fileInput.files;
        const total = files.length;
        if (total === 0) return;

        submitButton.disabled = true;
        uploadArea.style.pointerEvents = 'none';

        // Processamento Sequencial para não estourar a banda e manter ordem no Celery
        for (let i = 0; i < total; i++) {
            await processFile(files[i], i + 1, total);
        }

        // Redireciona apenas após o último arquivo ser CONFIRMADO
        window.location.href = '/repositorio-admin/galerias/';
    });

    async function processFile(file, index, total) {
        try {
            updateStatus(`[${index}/${total}] Assinando: ${file.name}`);

            // 1. Assinar
            const signRes = await fetch(SIGN_URL, {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrftoken},
                body: new URLSearchParams({'nome_arquivo': file.name, 'tipo_mime': file.type || 'image/jpeg'})
            });
            const signData = await signRes.json();

            // 2. Upload Direto S3
            updateStatus(`[${index}/${total}] Enviando S3: ${file.name}`);
            const s3Res = await fetch(signData.url_assinada, {
                method: 'PUT',
                headers: {'Content-Type': file.type || 'image/jpeg'},
                body: file
            });

            if (s3Res.status !== 200) throw new Error("Falha no S3");

            // 3. Confirmar (Enviando TOTAL e ÍNDICE para o progresso do WebSocket)
            updateStatus(`[${index}/${total}] Confirmando: ${file.name}`);
            await fetch(CONFIRM_URL, {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrftoken},
                body: new URLSearchParams({
                    'imagem_id': signData.imagem_id,
                    'total_files': total,
                    'current_index': index
                })
            });

        } catch (error) {
            console.error(error);
            updateStatus(`Erro em: ${file.name}`, true);
        }
    }

    function updateStatus(msg, isError = false) {
        fileCountText.textContent = msg;
        fileCountText.style.color = isError ? 'red' : 'inherit';
    }

})();