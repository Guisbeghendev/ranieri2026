/**
 * Lógica JavaScript para o formulário de Criação de Tópico de Suporte.
 * Inclui:
 * 1. Validação simples dos campos antes do envio.
 * 2. Feedback visual de erro ou sucesso.
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.reset-body form');
    const submitButton = document.getElementById('submit-button');

    if (form) {
        // Encontra os campos que precisam de validação básica (assunto e mensagem)
        const assuntoField = document.getElementById('id_assunto');
        const mensagemField = document.getElementById('id_mensagem_inicial');

        // Função utilitária para exibir feedback
        function showFeedback(field, message, isError = true) {
            const feedbackElement = document.getElementById(field.id + '_feedback');
            if (feedbackElement) {
                feedbackElement.textContent = message;
                feedbackElement.style.display = 'block';
                // Remove classes anteriores
                feedbackElement.classList.remove('error', 'success');
                // Adiciona a classe correta
                feedbackElement.classList.add(isError ? 'error' : 'success');
            }
            // Adiciona/remove classe de erro visual no próprio campo (assumindo que o CSS lida com .is-invalid)
            field.classList.toggle('is-invalid', isError);
        }

        // Função principal de validação
        function validateForm() {
            let isValid = true;

            // 1. Validação do Assunto
            if (!assuntoField || assuntoField.value.trim().length < 5) {
                showFeedback(assuntoField, 'O assunto deve ter pelo menos 5 caracteres.', true);
                isValid = false;
            } else {
                showFeedback(assuntoField, '', false); // Limpa feedback
                assuntoField.classList.remove('is-invalid');
            }

            // 2. Validação da Mensagem
            if (!mensagemField || mensagemField.value.trim().length < 20) {
                showFeedback(mensagemField, 'A mensagem precisa ser mais detalhada (mínimo de 20 caracteres).', true);
                isValid = false;
            } else {
                showFeedback(mensagemField, '', false); // Limpa feedback
                mensagemField.classList.remove('is-invalid');
            }

            return isValid;
        }

        // Adiciona o listener de envio
        form.addEventListener('submit', function(event) {
            if (!validateForm()) {
                // Previne o envio se a validação falhar
                event.preventDefault();
            } else {
                // Desabilita o botão para evitar cliques duplicados
                submitButton.disabled = true;
                submitButton.textContent = 'Enviando...';
            }
        });

        // Adiciona listeners para feedback em tempo real (opcional)
        if (assuntoField) {
            assuntoField.addEventListener('input', () => validateForm());
        }
        if (mensagemField) {
            mensagemField.addEventListener('input', () => validateForm());
        }
    }
});