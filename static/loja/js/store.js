document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.btn-ajax-cart').forEach(function (button) {
        button.addEventListener('click', function (event) {
            event.preventDefault();
            const csrfToken = document.querySelector('#cart-csrf-form [name=csrfmiddlewaretoken]')?.value;
            fetch(button.dataset.url, {
                method: 'POST',
                headers: {'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken, 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
                body: new URLSearchParams({csrfmiddlewaretoken: csrfToken})
            }).then(function (response) {
                if (!response.ok) throw new Error('Não foi possível atualizar o carrinho.');
                return response.json();
            }).then(function (data) {
                const toast = document.getElementById('toast-ia');
                const countBadge = document.getElementById('cart-count');
                const toastMsg = document.getElementById('toast-message');
                if (toastMsg) toastMsg.textContent = data.message || 'Adicionado com sucesso!';
                if (countBadge && data.total_itens !== undefined) countBadge.textContent = data.total_itens;
                if (toast) { toast.classList.add('show'); window.setTimeout(() => toast.classList.remove('show'), 2500); }
            }).catch(function () { window.location.reload(); });
        });
    });
});
