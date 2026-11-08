document.addEventListener('DOMContentLoaded', function () {
    const checkoutForm = document.getElementById('checkout-form');

    if (checkoutForm) {
        checkoutForm.addEventListener('submit', function (event) {
            if (!window.confirm('Finalizar pedido no valor apresentado?')) event.preventDefault();
        });
    }

    const formatCurrency = function (value) {
        return `${Number(value).toFixed(2)} Kz`;
    };

    const setFeedback = function (message) {
        const feedback = document.getElementById('cart-update-feedback');
        if (feedback) feedback.textContent = message;
    };

    const updateSummary = function (data) {
        const productsCount = document.querySelector('[data-cart-products-count]');
        const subtotal = document.querySelector('[data-cart-subtotal]');
        const shipping = document.querySelector('[data-cart-shipping]');
        const total = document.querySelector('[data-cart-total]');
        const cartCount = document.getElementById('cart-count');
        const lineCount = document.querySelector('[data-cart-line-count]');

        if (productsCount) productsCount.textContent = data.line_count;
        if (subtotal) subtotal.textContent = formatCurrency(data.subtotal);
        if (shipping) {
            const hasShipping = Number(data.frete) > 0;
            shipping.textContent = hasShipping ? formatCurrency(data.frete) : 'Grátis';
            shipping.classList.toggle('text-success', !hasShipping);
        }
        if (total) total.textContent = formatCurrency(data.total);
        if (cartCount) cartCount.textContent = data.total_itens;
        if (lineCount) {
            lineCount.textContent = `${data.line_count} produto${data.line_count === 1 ? '' : 's'}`;
        }
    };

    document.querySelectorAll('.cart-quantity-form').forEach(function (form) {
        form.addEventListener('submit', async function (event) {
            event.preventDefault();

            const button = form.querySelector('button[type="submit"]');
            const row = form.closest('[data-cart-item]');
            if (!button || button.disabled) return;

            const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]')?.value;
            button.disabled = true;
            if (row) {
                row.setAttribute('aria-busy', 'true');
                row.classList.add('is-updating');
            }

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken,
                    },
                    credentials: 'same-origin',
                });

                if (!response.ok) throw new Error('Não foi possível atualizar o carrinho.');
                const data = await response.json();
                updateSummary(data);
                const idempotencyKey = checkoutForm?.querySelector('[name="idempotency_key"]');
                if (idempotencyKey && data.idempotency_key) {
                    idempotencyKey.value = data.idempotency_key;
                }

                if (data.removed) {
                    if (row) row.remove();
                    const itemsCard = document.querySelector('[data-cart-items-card]');
                    const emptyState = document.querySelector('[data-cart-empty-state]');
                    if (!document.querySelector('[data-cart-item]')) {
                        if (itemsCard) itemsCard.classList.add('d-none');
                        if (emptyState) emptyState.classList.remove('d-none');
                        if (checkoutForm) checkoutForm.classList.add('d-none');
                    }
                } else if (row) {
                    const quantity = row.querySelector('[data-cart-quantity]');
                    const itemSubtotal = row.querySelector('[data-cart-item-subtotal]');
                    if (quantity) quantity.textContent = data.quantidade;
                    if (itemSubtotal) itemSubtotal.textContent = formatCurrency(data.item_subtotal);
                }

                setFeedback('Carrinho atualizado.');
            } catch (error) {
                setFeedback(error.message || 'Não foi possível atualizar o carrinho.');
            } finally {
                button.disabled = false;
                if (row) {
                    row.removeAttribute('aria-busy');
                    row.classList.remove('is-updating');
                }
            }
        });
    });
});
