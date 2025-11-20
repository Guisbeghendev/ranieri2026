/*
* Arquivo: registration_spa.js
* Objetivo: Gerenciar a lógica de Single Page Application (SPA) para o formulário de cadastro,
* mostrando ou ocultando campos com base no tipo de usuário selecionado.
* CORREÇÃO: Alterada a lógica para buscar e atualizar a tag <label> diretamente.
*/

document.addEventListener('DOMContentLoaded', () => {
    // 1. Elementos de Referência
    const form = document.getElementById('registration-form');
    // Seleciona todos os inputs radio que compõem o campo tipo_usuario
    const tipoUsuarioRadios = form.querySelectorAll('input[name="tipo_usuario"]');
    const registroEspecificoBlock = document.getElementById('registro-especifico-fields');
    const credenciaisBlock = document.getElementById('credenciais-fields');
    const submitButton = document.getElementById('submit-button');

    // Elemento da Label do RA que será atualizado (Busca a label usando o ID do campo 'id_ra_numero')
    // O Django gera a label com o atributo 'for' apontando para o id do campo.
    const raLabelElement = form.querySelector('label[for="id_ra_numero"]');

    // Textos das Labels (Nota: Mantenha o texto idêntico ao do forms.py, se necessário)
    const LABEL_ALUNO = 'RA - somente números:'; // Django adiciona ':'
    const LABEL_RESPONSAVEL = 'RA de um aluno pelo qual é responsável - somente números:';

    // Verifica se há erros de validação no formulário (para uso na lógica de inicialização)
    const hasErrorElement = form.querySelector('.form-error');

    // Mapeamento dos campos específicos para cada tipo de usuário.
    const fieldMap = {
        'ALUNO': ['ra_numero', 'ra_digito_verificador'],
        'RESPONSAVEL': ['ra_numero', 'ra_digito_verificador'],
        'PROFESSOR': ['tipo_professor'],
        'COLABORADOR': ['funcao_colaborador'],
        'URE': ['funcao_ure'],
        'OUTRO_VISITANTE': ['descricao_vinculo']
    };

    // Todos os grupos de campos específicos que são condicionalmente exibidos/ocultados.
    const allSpecificFields = form.querySelectorAll('#registro-especifico-fields .form-group');

    function updateFormVisibility(selectedType) {

        // --- 1. Lógica Corrigida: Força a exibição se houver um erro ---
        if (selectedType || hasErrorElement) {
            registroEspecificoBlock.classList.remove('js-hidden');
            credenciaisBlock.classList.remove('js-hidden');
            submitButton.classList.remove('is-disabled');
        } else {
            registroEspecificoBlock.classList.add('js-hidden');
            credenciaisBlock.classList.add('js-hidden');
            submitButton.classList.add('is-disabled');
            return;
        }

        // --- 2. Lógica de Atualização da Label do RA (CORREÇÃO) ---
        if (raLabelElement) {
            if (selectedType === 'RESPONSAVEL') {
                raLabelElement.textContent = LABEL_RESPONSAVEL;
            } else {
                raLabelElement.textContent = LABEL_ALUNO;
            }
        }


        // --- 3. Lógica de Ocultação/Exibição dos Campos Individuais ---
        const requiredFields = fieldMap[selectedType] || [];

        allSpecificFields.forEach(fieldGroup => {
            let isRequired = false;
            const fieldName = fieldGroup.dataset.fieldName;

            if (fieldName && requiredFields.includes(fieldName)) {
                 isRequired = true;
            }

            // Se o campo for requerido ou se ele contiver um erro de validação
            if (isRequired || fieldGroup.querySelector('.form-error')) {
                fieldGroup.classList.remove('js-hidden');
            } else {
                fieldGroup.classList.add('js-hidden');
            }
        });
    }

    // 4. Listener de Eventos
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

    // 5. Inicialização
    const initiallySelectedRadio = form.querySelector('input[name="tipo_usuario"]:checked');
    const selectedValue = initiallySelectedRadio ? initiallySelectedRadio.value : null;

    updateFormVisibility(selectedValue);

});