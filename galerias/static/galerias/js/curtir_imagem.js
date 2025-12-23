document.addEventListener('DOMContentLoaded', function() {
    const likeButtons = document.querySelectorAll('.like-button');
    const totalLikesDisplay = document.getElementById('total-likes');

    // O CSRF Token é lido do DOM, assumindo que está em um input hidden no base.html
    const CSRF_TOKEN = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

    // Função auxiliar para converter o total de curtidas
    function parseTotalLikes() {
        return parseInt(totalLikesDisplay.textContent) || 0;
    }

    likeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const imagePk = this.dataset.imagePk;
            const url = this.dataset.url;
            const likesCountElement = document.getElementById(`likes-count-${imagePk}`);

            // Estado inicial para a atualização do total
            let currentTotalLikes = parseTotalLikes();

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({})
            })
            .then(response => {
                if (response.status === 403) {
                    alert("Acesso Negado: Você não tem permissão para curtir esta galeria.");
                    return Promise.reject('Forbidden');
                }
                if (!response.ok) {
                    throw new Error('Erro na requisição.');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // 1. Atualiza o botão (estado)
                    const buttonTextSpan = button.querySelector('span');
                    if (data.curtiu) {
                        button.classList.add('is-liked');
                        buttonTextSpan.textContent = 'Descurtir';
                        currentTotalLikes += 1; // Aumenta o total
                    } else {
                        button.classList.remove('is-liked');
                        buttonTextSpan.textContent = 'Curtir';
                        currentTotalLikes -= 1; // Diminui o total
                    }

                    // 2. Atualiza o contador individual da imagem
                    if (likesCountElement) {
                        likesCountElement.textContent = data.new_count;
                    }

                    // 3. Atualiza o contador TOTAL da galeria
                    totalLikesDisplay.textContent = currentTotalLikes;

                } else {
                    alert(data.message || 'Erro ao processar a curtida.');
                }
            })
            .catch(error => {
                if (error !== 'Forbidden') {
                     console.error('Falha na interação:', error);
                     alert('Não foi possível realizar a operação de curtida. Tente novamente.');
                }
            });
        });
    });
});