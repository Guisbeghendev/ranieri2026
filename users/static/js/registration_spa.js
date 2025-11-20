/*
* Arquivo: registration_spa.js
* Objetivo: Gerenciar a lógica de Single Page Application (SPA) para o formulário de cadastro,
* mostrando ou ocultando campos com base no tipo de usuário selecionado.
* CORREÇÃO: Força a visibilidade dos blocos se houver um erro de validação do Django (status 200).
*/

document.addEventListener('DOMContentLoaded', () => {
    // 1. Elementos de Referência
    const form = document.getElementById('registration-form');
    // Seleciona todos os inputs radio que compõem o campo tipo_usuario
    const tipoUsuarioRadios = form.querySelectorAll('input[name="tipo_usuario"]');
    const registroEspecificoBlock = document.getElementById('registro-especifico-fields');
    const credenciaisBlock = document.getElementById('credenciais-fields');
    const submitButton = document.getElementById('submit-button');

    // Verifica se há erros de validação no formulário (para uso na lógica de inicialização)
    const hasErrorElement = form.querySelector('.form-error');

    // Mapeamento dos campos específicos para cada tipo de usuário.
    const fieldMap = {
        'ALUNO': ['ra_numero', 'ra_digito_verificador'], // Chaves devem ser os valores do Django
        'RESPONSAVEL': ['ra_numero', 'ra_digito_verificador'],
        'PROFESSOR': ['tipo_professor'],
        'COLABORADOR': ['funcao_colaborador'],
        'URE': ['funcao_ure'],
        'OUTRO_VISITANTE': ['descricao_vinculo'] // Chaves devem ser os valores do Django
    };

    // Todos os grupos de campos específicos que são condicionalmente exibidos/ocultados.
    const allSpecificFields = form.querySelectorAll('#registro-especifico-fields .form-group');

    function updateFormVisibility(selectedType) {

        // --- 1. Lógica Corrigida: Força a exibição se houver um erro ---

        // Se houver um tipo selecionado OU se houver erros na página (POST 200)
        if (selectedType || hasErrorElement) {
            // Mostra os blocos específicos e credenciais para que os erros do Django sejam visíveis
            registroEspecificoBlock.classList.remove('js-hidden');
            credenciaisBlock.classList.remove('js-hidden');
            // Habilita o botão de submissão
            submitButton.classList.remove('is-disabled');
        } else {
            // Oculta tudo e desabilita o botão se NADA estiver selecionado E NÃO houver erros
            registroEspecificoBlock.classList.add('js-hidden');
            credenciaisBlock.classList.add('js-hidden');
            submitButton.classList.add('is-disabled');
            // Retorna imediatamente se não houver um tipo selecionado (para evitar erros abaixo)
            return;
        }

        // --- 2. Lógica de Ocultação/Exibição dos Campos Individuais ---

        // Se não houver um selectedType (mas houver erro), ocultamos os campos individuais.
        // O Bloco Principal (registroEspecificoBlock) permanece visível, mas os campos internos somem,
        // garantindo que, se o erro estiver no tipo_usuario, os campos não apareçam incorretamente.
        const requiredFields = fieldMap[selectedType] || [];

        allSpecificFields.forEach(fieldGroup => {
            let isRequired = false;

            const inputs = fieldGroup.querySelectorAll('input, select, textarea');

            inputs.forEach(input => {
                if (input.name && requiredFields.includes(input.name)) {
                    isRequired = true;
                }
            });

            // Se o campo for requerido ou se ele contiver um erro de validação (para forçar a visibilidade)
            if (isRequired || fieldGroup.querySelector('.form-error')) {
                fieldGroup.classList.remove('js-hidden');
            } else {
                fieldGroup.classList.add('js-hidden');
            }
        });
    }

    // 3. Listener de Eventos (Nenhuma alteração)
    tipoUsuarioRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            updateFormVisibility(e.target.value);
        });

        const radioContainer = radio.closest('.radio-option');
        if (radioContainer) {
            radioContainer.addEventListener('click', (event) => {
                if (event.target !== radio && !radio.checked) {
                    radio.checked = true;
                    radio.dispatchEvent(new Event('change'));
                }
            });
        }
    });

    // 4. Inicialização (Simplificada e Corrigida)
    const initiallySelectedRadio = form.querySelector('input[name="tipo_usuario"]:checked');
    const selectedValue = initiallySelectedRadio ? initiallySelectedRadio.value : null;

    // Chama a função com o valor selecionado (ou null) para inicializar a UI e forçar visibilidade em caso de erro.
    updateFormVisibility(selectedValue);

});