/**
 * Arquivo: mensagens/js/chat.js
 * Adaptado para Tailwind v4 e lógica reativa
 */

let chatSocket = null;
let canalId = null;
let currentUserId = null;

// DOM Elements
let chatLog = null;
let chatMessagesList = null;
let messageInput = null;
let messageSubmit = null;
let sidebar = null;
let sidebarToggle = null;

/**
 * Scroll automático para o fim das mensagens
 */
function scrollToBottom() {
    if (chatLog) {
        chatLog.scrollTo({
            top: chatLog.scrollHeight,
            behavior: 'smooth'
        });
    }
}

/**
 * Criação do elemento de mensagem com classes Tailwind v4
 */
function createMessageElement(data) {
    const isMe = String(data.user_id) === String(currentUserId);

    const li = document.createElement('li');
    li.className = `flex ${isMe ? 'justify-end' : 'justify-start'}`;

    const innerHtml = `
        <div class="max-w-[80%] sm:max-w-[60%] rounded-2xl p-4 shadow-sm relative group
            ${isMe ? 'bg-primary text-white rounded-br-none' : 'bg-white border border-border-custom text-text-main rounded-bl-none'}">

            <span class="block text-[10px] font-bold uppercase tracking-wider mb-1 opacity-70">
                ${isMe ? 'Você' : (data.autor_nome || 'Usuário')}
            </span>

            <p class="text-sm leading-relaxed">${data.message || data.conteudo}</p>

            <span class="block text-[9px] text-right mt-2 opacity-60 italic">
                ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
        </div>
    `;

    li.innerHTML = innerHtml;
    return li;
}

/**
 * Lógica do WebSocket
 */
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    // Nota: O backend deve estar configurado para aceitar o ID ou Slug
    const wsUrl = `${protocol}://${window.location.host}/ws/chat/${canalId}/`;

    chatSocket = new WebSocket(wsUrl);

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === 'chat_message' || data.message) {
            const emptyMsg = document.querySelector('.flex.flex-col.items-center.justify-center');
            if (emptyMsg) emptyMsg.remove();

            const msgElement = createMessageElement(data);
            chatMessagesList.appendChild(msgElement);
            scrollToBottom();
        }
    };

    chatSocket.onclose = function(e) {
        console.error('Chat socket fechado inesperadamente');
        if (messageInput) {
            messageInput.disabled = true;
            messageInput.placeholder = "Conexão perdida. Recarregue a página.";
        }
    };
}

/**
 * Envio de Mensagem
 */
function sendMessage() {
    const message = messageInput.value.trim();
    if (message && chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({
            'message': message
        }));
        messageInput.value = '';
        messageSubmit.disabled = true;
    }
}

/**
 * Inicialização
 */
document.addEventListener('DOMContentLoaded', () => {
    // Captura de dados dos scripts do template
    const canalIdElem = document.getElementById('canal-id');
    const userIdElem = document.getElementById('user-id');

    if (!canalIdElem || !userIdElem) return;

    canalId = canalIdElem.textContent.trim();
    currentUserId = userIdElem.textContent.trim();

    // Elementos da UI
    chatLog = document.getElementById('chat-log');
    chatMessagesList = chatLog.querySelector('ul');
    messageInput = document.getElementById('chat-message-input');
    messageSubmit = document.getElementById('chat-message-submit');
    sidebar = document.getElementById('members-sidebar');
    sidebarToggle = document.getElementById('sidebar-toggle-button');

    // Toggle Sidebar Mobile
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('translate-x-full');
        });
    }

    // Eventos de Input
    if (messageInput) {
        messageInput.addEventListener('input', () => {
            messageSubmit.disabled = messageInput.value.trim() === '';
        });

        messageInput.addEventListener('keyup', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    if (messageSubmit) {
        messageSubmit.addEventListener('click', sendMessage);
    }

    connectWebSocket();
    scrollToBottom();
});