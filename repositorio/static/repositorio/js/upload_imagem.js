(function() {
    'use strict';

    const fileInput = document.getElementById('id_arquivos');
    const uploadArea = document.getElementById('file-upload-area');
    const fileCountText = document.getElementById('file-count-text');
    const submitButton = document.getElementById('submit-button');

    // CORREÇÃO: Pega as URLs dos data-attributes ou do formulário para evitar caminhos fixos
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

    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    function handleFileSelect(e) {
        const count = e.target.files.length;
        if (count > 0) {
            fileCountText.textContent = `${count} arquivo(s) prontos para upload.`;
            submitButton.disabled = false;
        }
    }

    submitButton.addEventListener('click', async () => {
        const files = fileInput.files;
        const total = files.length;
        if (total === 0) return;

        submitButton.disabled = true;
        uploadArea.style.pointerEvents = 'none';

        for (let i = 0; i < total; i++) {
            await processFile(files[i], i + 1, total);
        }

        window.location.href = '/repositorio-admin/galerias/';
    });

    async function processFile(file, index, total) {
        try {
            updateStatus(`[${index}/${total}] Assinando: ${file.name}`);

            const signRes = await fetch(SIGN_URL, {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrftoken},
                body: new URLSearchParams({'nome_arquivo': file.name, 'tipo_mime': file.type || 'image/jpeg'})
            });
            const signData = await signRes.json();

            // CORREÇÃO: S3 POST Upload (Exigido pelo Boto3 presigned POST)
            updateStatus(`[${index}/${total}] Enviando S3: ${file.name}`);
            const formData = new FormData();
            // Adiciona todos os campos da assinatura (policy, signature, etc)
            Object.entries(signData.campos_assinados).forEach(([key, value]) => {
                formData.append(key, value);
            });
            formData.append('file', file);

            const s3Res = await fetch(signData.url_assinada, {
                method: 'POST',
                body: formData
            });

            if (!s3Res.ok) throw new Error("Falha no upload S3");

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