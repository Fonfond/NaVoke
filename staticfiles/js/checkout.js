// frontend/static/js/checkout.js

document.addEventListener('DOMContentLoaded', function () {
    loadOrderSummary();

    const form = document.getElementById('checkoutForm');
    if (form) {
        form.addEventListener('submit', handleCheckout);
    }
});

// ===== ПЕРЕКЛЮЧЕНИЕ МЕЖДУ ДОСТАВКОЙ И САМОВЫВОЗОМ =====
function toggleDeliveryType() {
    const deliveryType = document.querySelector('input[name="deliveryType"]:checked')?.value;  // ✅ убрал пробел
    const deliveryBlock = document.getElementById('deliveryAddressBlock');
    const pickupBlock = document.getElementById('pickupBlock');
    const addressInput = document.getElementById('checkoutAddress');
    const deliveryDate = document.getElementById('checkoutDeliveryDate');
    const deliveryTime = document.getElementById('checkoutDeliveryTime');

    if (deliveryType === 'pickup') {
        deliveryBlock.classList.add('hidden');
        deliveryBlock.classList.remove('active');
        pickupBlock.classList.add('active');
        pickupBlock.classList.remove('hidden');
        addressInput.removeAttribute('required');
        addressInput.value = 'Самовывоз';
        if (deliveryDate) deliveryDate.value = '';
        if (deliveryTime) deliveryTime.value = '';
        updateDeliveryCost(0);
    } else {
        deliveryBlock.classList.remove('hidden');
        deliveryBlock.classList.add('active');
        pickupBlock.classList.remove('active');
        pickupBlock.classList.add('hidden');
        addressInput.setAttribute('required', 'required');
        addressInput.value = '';
        updateDeliveryCost(150);
    }
}

// ===== ОБНОВЛЕНИЕ СТОИМОСТИ ДОСТАВКИ =====
function updateDeliveryCost(cost) {
    const deliveryEl = document.getElementById('checkoutDelivery');
    const totalEl = document.getElementById('checkoutTotal');
    const subtotalEl = document.getElementById('checkoutSubtotal');

    if (deliveryEl && subtotalEl && totalEl) {
        const subtotal = parseFloat(subtotalEl.textContent) || 0;
        const total = subtotal + cost;
        deliveryEl.textContent = cost === 0 ? '0 ₽' : '150 ₽';
        totalEl.textContent = total.toFixed(2) + ' ₽';
    }
}

// ===== ЗАГРУЗКА ИТОГО =====
async function loadOrderSummary() {
    const container = document.getElementById('orderItems');
    const subtotalEl = document.getElementById('checkoutSubtotal');
    const deliveryEl = document.getElementById('checkoutDelivery');
    const totalEl = document.getElementById('checkoutTotal');

    try {
        const token = localStorage.getItem('access_token');
        let cart;

        if (token) {
            cart = await getCart();
        } else {
            cart = await getGuestCart();
        }

        if (!cart || !cart.items || cart.items.length === 0) {
            window.location.href = '/cart/';
            return;
        }

        const subtotal = parseFloat(cart.total) || 0;
        const deliveryCost = subtotal >= 800 ? 0 : 150;
        const total = subtotal + deliveryCost;

        container.innerHTML = cart.items.map(item => `
            <div class="order-item-summary">
                <span class="item-name">${item.product_name}</span>
                <span class="item-qty">×${item.quantity}</span>
                <span class="item-price">${(item.product_price * item.quantity).toFixed(2)} ₽</span>
            </div>
        `).join('');

        subtotalEl.textContent = `${subtotal.toFixed(2)} ₽`;
        deliveryEl.textContent = deliveryCost === 0 ? '0 ₽' : '150 ₽';
        totalEl.textContent = `${total.toFixed(2)} ₽`;

    } catch (error) {
        console.error('Ошибка загрузки заказа:', error);
        container.innerHTML = `<p class="text-danger">Ошибка загрузки заказа</p>`;
    }
}

// ===== ОФОРМЛЕНИЕ ЗАКАЗА =====
async function handleCheckout(e) {
    e.preventDefault();

    const btn = document.getElementById('submitOrderBtn');
    const btnText = document.getElementById('submitBtnText');
    const spinner = document.getElementById('submitSpinner');

    const deliveryType = document.querySelector('input[name="deliveryType"]:checked')?.value || 'delivery';

    const data = {
        full_name: document.getElementById('checkoutName').value.trim(),
        phone: document.getElementById('checkoutPhone').value.trim(),
        email: document.getElementById('checkoutEmail').value.trim(),
        delivery_type: deliveryType,
        comment: document.getElementById('checkoutComment').value.trim(),
        payment_method: document.querySelector('input[name="paymentMethod"]:checked')?.value || 'online',
        bonus_used: 0,
    };

    if (deliveryType === 'delivery') {
        data.delivery_address = document.getElementById('checkoutAddress').value.trim();
        data.delivery_date = document.getElementById('checkoutDeliveryDate')?.value || null;
        data.delivery_time_from = document.getElementById('checkoutDeliveryTime')?.value || null;
        data.delivery_time_to = null;
        data.pickup_date = null;
        data.pickup_time = null;
    } else {
        data.delivery_address = 'Самовывоз';
        data.delivery_date = null;
        data.delivery_time_from = null;
        data.delivery_time_to = null;
        data.pickup_date = document.getElementById('pickupDate')?.value || null;
        data.pickup_time = document.getElementById('pickupTime')?.value || null;
    }

    if (!data.full_name || !data.phone || !data.email) {
        showNotification('⚠️ Заполните все обязательные поля', 'warning');
        return;
    }

    if (deliveryType === 'delivery' && !data.delivery_address) {
        showNotification('⚠️ Укажите адрес доставки', 'warning');
        return;
    }

    btn.disabled = true;
    btnText.textContent = 'Оформление...';
    spinner.classList.remove('d-none');

    try {
        const token = localStorage.getItem('access_token');
        const url = '/api/v1/orders/';
        const headers = {
            'Content-Type': 'application/json',
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(data),
        });

        const result = await response.json();
        console.log('📦 Результат заказа:', result);

        if (!response.ok) {
            throw new Error(result.detail || result.error || 'Ошибка оформления заказа');
        }

        showNotification('✅ Заказ оформлен! Спасибо!', 'success');

        if (token) {
            await clearCart();
        } else {
            await fetch('/api/v1/orders/guest-cart/', {
                method: 'DELETE'
            });
        }

        if (typeof updateCartBadgeFromCache === 'function') {
            updateCartBadgeFromCache();
        }

        // ✅ Если оплата онлайн - создаём платёж
        if (data.payment_method === 'online') {
            try {
                const paymentResponse = await fetch('/api/v1/payments/create/', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({
                        order_id: result.id
                    })
                });

                if (paymentResponse.ok) {
                    const paymentData = await paymentResponse.json();
                    if (paymentData.confirmation_url) {
                        showNotification('🔄 Перенаправляем на оплату...', 'info');
                        setTimeout(() => {
                            window.location.href = paymentData.confirmation_url;
                        }, 1500);
                        return;
                    }
                }
            } catch (paymentError) {
                console.error('Ошибка создания платежа:', paymentError);
                showNotification('⚠️ Заказ создан, но возникла ошибка оплаты', 'warning');
            }
        }

        // Если не онлайн-оплата или ошибка — переходим на страницу успеха
        const paymentMethod = data.payment_method === 'online' ? 'online' : 'cash';
        setTimeout(() => {
            window.location.href = `/order-success/?order=${result.order_number}&total=${result.total_amount}&delivery=${data.delivery_type}&payment=${paymentMethod}&order_id=${result.id}`;
        }, 2000);

    } catch (error) {
        console.error('❌ Ошибка оформления заказа:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Подтвердить заказ';
        spinner.classList.add('d-none');
    }
}

// ===== ПОИСК =====
function searchProducts() {
    const input = document.getElementById('searchInput');
    if (!input) return;
    const query = input.value.trim();
    if (query) {
        window.location.href = `/catalog/?search=${encodeURIComponent(query)}`;
    }
}

// ===== ЭКСПОРТ =====
window.toggleDeliveryType = toggleDeliveryType;
window.loadOrderSummary = loadOrderSummary;
window.handleCheckout = handleCheckout;
window.searchProducts = searchProducts;

console.log('✅ checkout.js загружен!');