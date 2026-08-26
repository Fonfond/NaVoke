// frontend/static/js/order-detail.js

document.addEventListener('DOMContentLoaded', function () {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    // Получаем ID заказа из URL
    const path = window.location.pathname;
    const parts = path.split('/');
    const orderId = parts[parts.length - 2];
    console.log('📦 ID заказа:', orderId);

    if (orderId && !isNaN(orderId)) {
        loadOrderDetail(orderId);
    }
});

async function loadOrderDetail(orderId) {
    const container = document.getElementById('orderDetailContainer');

    try {
        const order = await getOrder(orderId);
        console.log('📦 Детали заказа:', order);

        document.getElementById('orderNumber').textContent = order.order_number || order.id;

        // Форматируем дату
        const orderDate = order.order_date ? new Date(order.order_date).toLocaleDateString('ru-RU') : '—';
        const deliveryDate = order.delivery_date ? new Date(order.delivery_date).toLocaleDateString('ru-RU') : '—';

        const statusMap = {
            'new': 'Новый',
            'confirmed': 'Подтверждён',
            'cooking': 'Готовится',
            'ready': 'Готов',
            'delivering': 'В доставке',
            'delivered': 'Доставлен ✅',
            'cancelled': 'Отменён ❌'
        };

        const statusColorMap = {
            'new': 'primary',
            'confirmed': 'info',
            'cooking': 'warning',
            'ready': 'success',
            'delivering': 'primary',
            'delivered': 'success',
            'cancelled': 'danger'
        };

        const deliveryTypeMap = {
            'delivery': 'Доставка',
            'pickup': 'Самовывоз'
        };

        container.innerHTML = `
    <div class="card">
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <h3>Заказ #${order.order_number || order.id}</h3>
                    <p><strong>Дата заказа:</strong> ${orderDate}</p>
                    <p>
                        <strong>Статус:</strong> 
                        <span class="badge bg-${statusColorMap[order.status] || 'secondary'}">
                            ${statusMap[order.status] || order.status}
                        </span>
                    </p>
                    <p><strong>Способ получения:</strong> ${deliveryTypeMap[order.delivery_type] || order.delivery_type || 'Доставка'}</p>
                    ${order.delivery_type === 'delivery' ? `
                        <p><strong>Адрес доставки:</strong> ${order.delivery_address || '—'}</p>
                        <p><strong>Дата доставки:</strong> ${deliveryDate}</p>
                        <p><strong>Время доставки:</strong> ${order.delivery_time_from || '—'} — ${order.delivery_time_to || '—'}</p>
                    ` : `
                        <p><strong>Адрес самовывоза:</strong> пгт. Селенгинск, ул. Ленина, 10</p>
                        <p><strong>Дата самовывоза:</strong> ${order.pickup_date ? new Date(order.pickup_date).toLocaleDateString('ru-RU') : '—'}</p>
                        <p><strong>Время самовывоза:</strong> ${order.pickup_time || '—'}</p>
                    `}
                    <p><strong>Комментарий:</strong> ${order.comment || '—'}</p>
                    <p><strong>Способ оплаты:</strong> ${order.payment_method === 'online' ? 'Онлайн картой' : 'Наличными'}</p>
                    <p><strong>Статус оплаты:</strong> ${order.payment_status === 'paid' ? '✅ Оплачено' : '⏳ Ожидает оплаты'}</p>
                </div>
                <div class="col-md-6">
                    <h4>Состав заказа</h4>
                    <div class="order-items-list">
                        ${order.items && order.items.length > 0 ? order.items.map(item => `
                            <div class="order-item-row d-flex justify-content-between align-items-center py-2 border-bottom">
                                <div>
                                    <strong>${item.product_name || item.product}</strong>
                                    <span class="text-muted ms-2">× ${item.quantity}</span>
                                </div>
                                <div>
                                    <span class="fw-bold">${item.price_at_order * item.quantity} ₽</span>
                                </div>
                            </div>
                        `).join('') : '<p class="text-muted">Нет товаров в заказе</p>'}
                    </div>
                    
                    <div class="order-total mt-3">
                        <div class="d-flex justify-content-between">
                            <span>Товары:</span>
                            <span>${order.subtotal} ₽</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Доставка:</span>
                            <span>${order.delivery_cost} ₽</span>
                        </div>
                        ${order.bonus_used > 0 ? `
                            <div class="d-flex justify-content-between">
                                <span>Списано бонусов:</span>
                                <span>-${order.bonus_used} ₽</span>
                            </div>
                        ` : ''}
                        ${order.discount > 0 ? `
                            <div class="d-flex justify-content-between">
                                <span>Скидка:</span>
                                <span>-${order.discount} ₽</span>
                            </div>
                        ` : ''}
                        <div class="d-flex justify-content-between fw-bold border-top pt-2 mt-2">
                            <span>Итого:</span>
                            <span class="text-primary">${order.total_amount} ₽</span>
                        </div>
                    </div>
                    
                    <!-- ✅ КНОПКИ В ОДНОЙ СТРОКЕ С ПРАВИЛЬНЫМИ ОТСТУПАМИ -->
                    <div class="d-flex flex-wrap gap-2 mt-4">
                        ${order.status === 'new' && order.payment_status !== 'paid' ? `
                            <button class="btn btn-success" onclick="payOrderFromDetail(${order.id})">
                                <i class="fas fa-credit-card"></i> Оплатить сейчас
                            </button>
                        ` : ''}
                        ${order.status === 'new' || order.status === 'confirmed' ? `
                            <button class="btn btn-danger" onclick="cancelOrder(${order.id})">
                                <i class="fas fa-times"></i> Отменить заказ
                            </button>
                        ` : ''}
                        <a href="/profile/" class="btn btn-outline-primary">
                            <i class="fas fa-arrow-left"></i> Назад к заказам
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
`;

    } catch (error) {
        console.error('❌ Ошибка загрузки заказа:', error);
        container.innerHTML = `
            <div class="text-center py-5">
                <p class="text-danger">❌ Ошибка загрузки заказа</p>
                <a href="/profile/" class="btn btn-primary">Вернуться к заказам</a>
            </div>
        `;
    }
}

// ✅ Добавлена функция оплаты из деталей заказа
async function payOrderFromDetail(orderId) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        showNotification('⚠️ Пожалуйста, войдите в систему', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/v1/payments/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                order_id: orderId
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || errorData.detail || 'Ошибка создания платежа');
        }

        const paymentData = await response.json();
        console.log('✅ Платёж создан:', paymentData);

        if (paymentData.confirmation_url) {
            showNotification('🔄 Перенаправляем на оплату...', 'info');
            setTimeout(() => {
                window.location.href = paymentData.confirmation_url;
            }, 1000);
        } else {
            showNotification('⚠️ Не удалось получить ссылку на оплату', 'warning');
        }

    } catch (error) {
        console.error('❌ Ошибка оплаты:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

async function cancelOrder(orderId) {
    if (!confirm('Вы уверены, что хотите отменить заказ?')) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/orders/${orderId}/cancel/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        if (!response.ok) {
            throw new Error('Ошибка отмены заказа');
        }

        const result = await response.json();
        console.log('✅ Заказ отменён:', result);

        showNotification('✅ Заказ отменён!', 'success');
        loadOrderDetail(orderId);

    } catch (error) {
        console.error('❌ Ошибка отмены заказа:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

// Экспорт функций
window.cancelOrder = cancelOrder;
window.loadOrderDetail = loadOrderDetail;
window.payOrderFromDetail = payOrderFromDetail;

console.log('✅ order-detail.js загружен!');