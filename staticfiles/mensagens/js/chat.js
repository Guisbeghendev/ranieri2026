// Variáveis de escopo
let chatSocket = null;
let canalId = null;
let currentUserId = null;

// DOM Elements
let chatLogWrapper = null;
let chatLog = null;
let messageInput = null;
let messageSubmit = null;
// NOVO: Elemento para a lista de membros na sidebar
let membersListWrapper = null;
// NOVO: Elementos da sidebar e toggle
let sidebarElement = null; // O elemento <aside id="members-sidebar">
let sidebarToggleButton = null; // O botão de toggle <button id="sidebar-toggle-button">
let mainContent = null; // O conteúdo principal, usado como backdrop em mobile para fechar a sidebar

// Constante para o breakpoint de mobile/desktop
const MOBILE_BREAKPOINT = 768; // Deve corresponder ao @media (max-width: 768px) no CSS

// ======================================================================
// HANDLERS DO WEBSOCKET
// ======================================================================

// 1. Conexão Aberta
function onWsOpen(e) {
    console.log("WS Status: Connection opened.");
    toggleSubmitButton();
    if (messageInput) messageInput.placeholder = "Digite sua mensagem...";
    scrollToBottom();
}

// 2. Recebimento de Mensagem
function onWsMessage(e) {
    const data = JSON.parse(e.data);

    console.log("WS Mensagem Recebida:", data);

    if (data.type === 'chat_message') {
        const messageData = data;
        const isUserMessage = currentUserId && (messageData.user_id == currentUserId);

        removeEmptyLogMessage();

        const messageElement = createMessageElement(messageData, isUserMessage);

        if (chatLogWrapper) {
            chatLogWrapper.appendChild(messageElement);
        }
        scrollToBottom();

    } else if (data.type === 'user_join') {
        // NOVO: Usuário entrou no canal (websocket)
        console.log(`[SIDEBAR] Usuário ${data.display_name} entrou.`);
        // Chamada da função para adicionar visualmente o membro
        addMemberToSidebar(data);

    } else if (data.type === 'user_leave') {
        // NOVO: Usuário saiu do canal (websocket)
        console.log(`[SIDEBAR] Usuário ${data.display_name} saiu.`);
        // Chamada da função para remover visualmente o membro
        removeMemberFromSidebar(data.user_id);

    } else {
         console.log("Mensagem de log ou tipo desconhecido:", data);
    }
}

// 3. Conexão Fechada
function onWsClose(e) {
    console.error('WS Status: Chat socket closed unexpectedly. Code:', e.code, 'Reason:', e.reason);
    if (messageSubmit) messageSubmit.disabled = true;
    if (messageInput) messageInput.placeholder = "Conexão perdida. Atualize a página.";
}

// 4. Erro de Conexão
function onWsError(e) {
    console.error('WS Status: Chat socket error:', e);
    if (messageSubmit) messageSubmit.disabled = true;
    if (messageInput) messageInput.placeholder = "Erro de conexão. Atualize a página.";
}


// ======================================================================
// FUNÇÕES AUXILIARES DE CHAT (MENSAGENS, INPUT)
// ======================================================================

function scrollToBottom() {
    // Usa setTimeout para garantir que a rolagem ocorra após a renderização completa da mensagem.
    setTimeout(() => {
        if (chatLog) {
            chatLog.scrollTop = chatLog.scrollHeight;
        }
    }, 100);
}

function formatTime(dateString) {
    const date = new Date(dateString);
    if (!isNaN(date.getTime())) {
        let hours = date.getHours().toString().padStart(2, '0');
        let minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }
    return dateString;
}

function removeEmptyLogMessage() {
    const emptyMessage = document.querySelector('.chat-empty-log-message');
    if (emptyMessage) {
        emptyMessage.remove();
    }
}

function createMessageElement(messageData, isUserMessage) {
    const listItem = document.createElement('li');
    // Classes de alinhamento
    listItem.className = `chat-message-row chat-message-${isUserMessage ? 'user' : 'other'}`;

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${isUserMessage ? 'user-message' : 'other-message'}`;

    const senderSpan = document.createElement('span');
    senderSpan.className = 'message-sender';
    senderSpan.textContent = isUserMessage ? 'Você' : messageData.autor_nome;

    const contentP = document.createElement('p');
    // REMOVIDA: 'break-words whitespace-pre-wrap' - MANTENDO APENAS A CLASSE ESSENCIAL
    contentP.className = 'message-content';
    contentP.textContent = messageData.conteudo;

    const timestampSpan = document.createElement('span');
    timestampSpan.className = 'message-timestamp';
    timestampSpan.textContent = formatTime(messageData.timestamp);

    bubble.appendChild(senderSpan);
    bubble.appendChild(contentP);
    bubble.appendChild(timestampSpan);
    listItem.appendChild(bubble);

    return listItem;
}

function toggleSubmitButton() {
    // Habilita se: 1. Tiver texto E 2. O WebSocket estiver aberto
    const hasText = messageInput && messageInput.value.trim().length > 0;
    const isSocketOpen = chatSocket && chatSocket.readyState === WebSocket.OPEN;

    if (messageSubmit) {
        messageSubmit.disabled = !(hasText && isSocketOpen);
    }
}

function sendMessage() {
    const message = messageInput.value.trim();
    if (message.length === 0 || !chatSocket || chatSocket.readyState !== WebSocket.OPEN) {
        console.warn("Tentativa de envio falhou: Vazio ou WS Fechado/Inválido.");
        return;
    }

    const payload = JSON.stringify({
        'type': 'message',
        'message': message
    });

    console.log("WS Enviando:", payload);
    chatSocket.send(payload);

    messageInput.value = '';
    messageSubmit.disabled = true;
}

// ======================================================================
// FUNÇÕES AUXILIARES DE SIDEBAR (MEMBROS E TOGGLE)
// ======================================================================

/**
 * Função auxiliar para fechar a sidebar quando o clique ocorre fora dela (no mainContent).
 * @param {Event} event - O objeto de evento de clique.
 */
function closeSidebarOnOutsideClick(event) {
    // Verifica se o clique não foi na sidebar e nem no botão de toggle
    if (sidebarElement && sidebarToggleButton && mainContent) {
        // Verifica se a largura da tela é de mobile (onde o backdrop se aplica)
        if (window.innerWidth <= MOBILE_BREAKPOINT && !sidebarElement.contains(event.target) && !sidebarToggleButton.contains(event.target)) {
            // Fecha a sidebar
            sidebarElement.classList.remove('is-open');
            sidebarToggleButton.setAttribute('aria-expanded', 'false');
            // Remove este listener imediatamente após o fechamento
            mainContent.removeEventListener('click', closeSidebarOnOutsideClick);
        }
    }
}

/**
 * Função para alternar a visibilidade da sidebar (usada no mobile).
 */
function toggleSidebar() {
    if (sidebarElement && sidebarToggleButton && mainContent) {
        // Alterna a classe 'is-open' que o CSS usa para mostrar/esconder
        const is_open = sidebarElement.classList.toggle('is-open');

        // Alterna o atributo aria-expanded para acessibilidade
        sidebarToggleButton.setAttribute('aria-expanded', is_open);

        // Se estiver aberto, adiciona um listener para fechar ao clicar no fundo
        if (is_open) {
            // Adiciona um listener no conteúdo principal para fechar ao clicar fora da sidebar
            mainContent.addEventListener('click', closeSidebarOnOutsideClick);
        } else {
            // Remove o listener quando a sidebar é fechada (se não foi removido pelo closeSidebarOnOutsideClick)
            mainContent.removeEventListener('click', closeSidebarOnOutsideClick);
        }
    }
}

/**
 * Lógica para garantir que a sidebar seja fechada automaticamente se o usuário
 * redimensionar a janela de mobile para desktop.
 */
function handleResize() {
    if (window.innerWidth > MOBILE_BREAKPOINT) {
        if (sidebarElement && sidebarElement.classList.contains('is-open')) {
            // Se a tela for desktop e a sidebar estiver aberta, feche-a
            sidebarElement.classList.remove('is-open');
            if (sidebarToggleButton) {
                sidebarToggleButton.setAttribute('aria-expanded', 'false');
            }
            // Garante que o listener de clique fora seja removido
            if (mainContent) {
                mainContent.removeEventListener('click', closeSidebarOnOutsideClick);
            }
        }
    }
}


function createUserMemberElement(memberData) {
    const isCurrentUser = memberData.user_id == currentUserId;

    // 1. Elemento Principal
    const memberItem = document.createElement('div');
    // Adiciona o data-id para fácil remoção/identificação
    memberItem.dataset.userId = memberData.user_id;
    memberItem.className = `chat-member-item ${isCurrentUser ? 'chat-member-current' : 'chat-member-other'}`;

    // 2. Avatar
    const avatar = document.createElement('div');
    avatar.className = 'chat-member-avatar';
    // Se 'initials' vier do backend (consumers.py), usa; senão, fallback.
    avatar.textContent = memberData.initials || (memberData.username ? memberData.username[0].toUpperCase() : '?');

    // 3. Info
    const info = document.createElement('div');
    info.className = 'chat-member-info';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'chat-member-name';
    // Usa display_name ou username
    nameSpan.textContent = memberData.display_name || memberData.username;
    nameSpan.title = memberData.display_name || memberData.username;

    if (isCurrentUser) {
        const youSpan = document.createElement('span');
        youSpan.className = 'chat-member-you';
        youSpan.textContent = '(Você)';
        nameSpan.appendChild(youSpan);
    }

    info.appendChild(nameSpan);

    // 4. Status Online
    // NOTA: O CSS para .chat-member-status-online já simula o ponto verde
    const status = document.createElement('div');
    status.className = 'chat-member-status-online';
    status.title = 'Online';

    // 5. Montagem
    memberItem.appendChild(avatar);
    memberItem.appendChild(info);
    memberItem.appendChild(status);

    return memberItem;
}

function addMemberToSidebar(memberData) {
    if (!membersListWrapper) return;

    // Verifica se o membro já está na lista (pode ser o caso se o HTML já o renderizou)
    const existingMember = membersListWrapper.querySelector(`[data-user-id="${memberData.user_id}"]`);

    if (existingMember) {
        // Se já existir, apenas garante que o ponto online está lá
        return;
    }

    // Cria o novo elemento de membro
    const newMemberElement = createUserMemberElement(memberData);

    // Adiciona ao topo (ou onde você preferir na ordem)
    membersListWrapper.prepend(newMemberElement);
}

function removeMemberFromSidebar(userId) {
    if (!membersListWrapper) return;

    // Usa o seletor de atributo de dados para encontrar e remover
    const memberElement = membersListWrapper.querySelector(`[data-user-id="${userId}"]`);

    if (memberElement) {
        memberElement.remove();
        console.log(`[SIDEBAR] Membro ${userId} removido do DOM.`);
    } else {
        console.warn(`[SIDEBAR] Tentativa de remover membro ${userId}, mas o elemento não foi encontrado.`);
    }
}


// ======================================================================
// LÓGICA DE INICIALIZAÇÃO (CHAMADA NO DOMContentLoaded)
// ======================================================================
function initChat() {
    console.log("Chat JS - Inicializando Chat.");

    // 1. Define os elementos DOM
    chatLogWrapper = document.querySelector('#chat-log ul.chat-messages-wrapper');
    chatLog = document.querySelector('#chat-log');
    messageInput = document.querySelector('#chat-message-input');
    messageSubmit = document.querySelector('#chat-message-submit');
    membersListWrapper = document.querySelector('.chat-members-list-wrapper');

    // Inicializa elementos da sidebar e do toggle
    sidebarElement = document.querySelector('#members-sidebar');
    sidebarToggleButton = document.querySelector('#sidebar-toggle-button');
    mainContent = document.querySelector('.chat-main-content'); // O conteúdo principal

    // 2. Garante que os elementos cruciais existam
    if (!chatLogWrapper || !chatLog || !messageInput || !messageSubmit || !membersListWrapper || !sidebarElement || !sidebarToggleButton || !mainContent) {
        console.error("ERRO: Elementos DOM essenciais não encontrados.");
        if (messageInput) messageInput.placeholder = "ERRO: Elementos do Chat Incompletos.";
        return;
    }

    // 3. LÓGICA DE INICIALIZAÇÃO DO WEBSOCKET
    try {
        const canalIdElement = document.getElementById('canal-id');
        const userIdElement = document.getElementById('user-id');

        if (!canalIdElement || !userIdElement) {
            throw new Error("Elementos 'canal-id' ou 'user-id' não encontrados no template HTML.");
        }

        // Leitura e Conversão Segura
        canalId = parseInt(canalIdElement.textContent.trim());
        currentUserId = parseInt(userIdElement.textContent.trim());

        if (isNaN(canalId)) {
            throw new Error("canalId é inválido. Valor lido: '" + canalIdElement.textContent.trim() + "'");
        }

        if (isNaN(currentUserId)) {
             throw new Error("currentUserId é inválido. Valor lido: '" + userIdElement.textContent.trim() + "'");
        }


        // Constrói a URL do WebSocket
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const wsUrl = protocol + '://' + window.location.host +
            '/ws/chat/' + canalId + '/';

        console.log("Tentando conectar WebSocket em:", wsUrl);

        chatSocket = new WebSocket(wsUrl);

        // 4. Atribuição dos Handlers do WS
        chatSocket.onopen = onWsOpen;
        chatSocket.onmessage = onWsMessage;
        chatSocket.onclose = onWsClose;
        chatSocket.onerror = onWsError;

    } catch (error) {
        console.error("WS INIT ERROR:", error.message);

        // Cria um objeto dummy/mock
        chatSocket = {
            readyState: WebSocket.CLOSED,
            send: (msg) => { console.error("Não foi possível enviar: WS não inicializado ou fechado."); }
        };

        // Desabilita o campo de input e mostra a mensagem de erro
        messageInput.placeholder = "ERRO: Inicialização do Chat Falhou. Consulte o Console (F12).";
        messageInput.disabled = true;
        messageSubmit.disabled = true;
    }

    // 5. Binds de Eventos de Input
    messageInput.oninput = toggleSubmitButton;

    messageInput.onkeyup = function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!messageSubmit.disabled) {
                sendMessage();
            }
        }
        toggleSubmitButton();
    };

    messageSubmit.onclick = sendMessage;

    // 6. BIND DE EVENTO DA SIDEBAR (Mantido no initChat)
    sidebarToggleButton.onclick = toggleSidebar;
    sidebarToggleButton.setAttribute('aria-expanded', 'false');

    // 7. BIND DE EVENTO DE REDIMENSIONAMENTO (responsividade)
    window.addEventListener('resize', handleResize);


    // Scroll inicial (para carregar o histórico)
    scrollToBottom();
}

// Garante que o script só inicialize após o DOM estar pronto
window.addEventListener('DOMContentLoaded', initChat);