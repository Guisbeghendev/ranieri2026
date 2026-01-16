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
 * Formatação de hora simplificada
 */
function formatTime(dateString) {
    const date = dateString ? new Date(dateString) : new Date();
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Criação do elemento de mensagem com classes Tailwind v4
 */
function createMessageElement(data, isMe) {
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
                ${formatTime(data.timestamp)}
            </span>
        </div>
    `;

    li.innerHTML = innerHtml;
    return li;
}

/**
 * Gerenciamento de Membros na Sidebar
 */
function updateMemberStatus(data, action) {
    if (!sidebar) return;
    const membersList = sidebar.querySelector('.overflow-y-auto');
    if (!membersList) return;

    if (action === 'join') {
        const existing = membersList.querySelector(`[data-user-id="${data.user_id}"]`);
        if (!existing) {
            const isMe = String(data.user_id) === String(currentUserId);
            const memberDiv = document.createElement('div');
            memberDiv.dataset.userId = data.user_id;
            memberDiv.className = `flex items-center gap-3 p-2 rounded-lg transition-colors ${isMe ? 'bg-primary/10 border border-primary/20' : 'hover:bg-gray-50'}`;
            memberDiv.innerHTML = `
                <div class="w-10 h-10 rounded-full bg-verde-petroleo flex items-center justify-center text-white font-bold shrink-0 shadow-sm text-sm">
                    ${(data.display_name || 'U')[0].toUpperCase()}
                </div>
                <div class="flex-grow min-w-0">
                    <span class="block text-sm font-semibold text-text-main truncate">
                        ${data.display_name} ${isMe ? '<span class="text-xs text-primary font-normal">(Você)</span>' : ''}
                    </span>
                    <span class="flex items-center gap-1.5 text-[10px] text-gray-400">
                        <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span> Online
                    </span>
                </div>
            `;
            membersList.appendChild(memberDiv);
        }
    } else if (action === 'leave') {
        const memberElem = membersList.querySelector(`[data-user-id="${data.user_id}"]`);
        if (memberElem) memberElem.remove();
    }
}

/**
 * Lógica do WebSocket
 */
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/ws/chat/${canalId}/`;

    chatSocket = new WebSocket(wsUrl);

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);

        if (data.type === 'chat_message' || data.message) {
            const emptyMsg = chatMessagesList.querySelector('.opacity-40');
            if (emptyMsg) emptyMsg.remove();

            const isMe = String(data.user_id) === String(currentUserId);
            const msgElement = createMessageElement(data, isMe);
            chatMessagesList.appendChild(msgElement);
            scrollToBottom();
        } else if (data.type === 'user_join') {
            updateMemberStatus(data, 'join');
        } else if (data.type === 'user_leave') {
            updateMemberStatus(data, 'leave');
        }
    };

    chatSocket.onclose = () => {
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
            'type': 'chat_message',
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
    const canalIdElem = document.getElementById('canal-id');
    const userIdElem = document.getElementById('user-id');

    if (!canalIdElem || !userIdElem) return;

    canalId = canalIdElem.textContent.trim();
    currentUserId = userIdElem.textContent.trim();

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
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    if (messageSubmit) {
        messageSubmit.addEventListener('click', sendMessage);
    }

    connectWebSocket();
    scrollToBottom();
});