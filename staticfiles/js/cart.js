// frontend/static/js/cart.js

let isLoading = false;

document.addEventListener('DOMContentLoaded', function() {
    loadCart();
});

// ===== ЗАГРУЗКА КОРЗИНЫ =====
async function loadCart() {
    if (isLoading) {
        console.log('⏳ Загрузка корзины уже выполняется, пропускаем');
        return;
    }
    
    const container = document.getElementById('cartContainer');
    if (!container) {
        console.warn('⚠️ Контейнер cartContainer не найден');
        return;
    }
    
    isLoading = true;
    
    try {
        const token = localStorage.getItem('access_token');
        let cart;
        
        if (token) {
            cart = await getCart();
        } else {
            cart = await getGuestCart();
        }
        
        console.log('🛒 Корзина загружена:', cart);
        
        window.cartData = cart;
        updateCartBadgeOnly(cart);
        
        if (!cart || !cart.items || cart.items.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="fas fa-shopping-cart fa-3x text-muted"></i>
                    <p class="mt-3">Корзина пуста</p>
                    <a href="/catalog/" class="btn btn-primary">Перейти в каталог</a>
                </div>
            `;
            isLoading = false;
            return;
        }
        
        const subtotal = parseFloat(cart.total) || 0;
        const deliveryCost = subtotal >= 800 ? 0 : 150;
        const total = subtotal + deliveryCost;
        
        container.innerHTML = `
            <div class="col-lg-8">
                <div class="cart-items">
                    ${cart.items.map(item => `
                        <div class="cart-item" id="cart-item-${item.id}">
                            <img src="${item.product_image || 'https://via.placeholder.com/80x80/FFF0E6/FF6B35?text=НаVoke'}" 
                                 alt="${item.product_name}" 
                                 onerror="this.src='https://via.placeholder.com/80x80/FFF0E6/FF6B35?text=НаVoke'">
                            <div class="cart-item-info">
                                <div class="cart-item-name">${item.product_name}</div>
                                <div class="cart-item-price">${item.product_price} ₽</div>
                            </div>
                            <div class="cart-item-actions">
                                <button class="btn-quantity" onclick="updateQuantity(${item.id}, -1)">
                                    <i class="fas fa-minus"></i>
                                </button>
                                <span class="cart-item-quantity" id="qty-${item.id}">${item.quantity}</span>
                                <button class="btn-quantity" onclick="updateQuantity(${item.id}, 1)">
                                    <i class="fas fa-plus"></i>
                                </button>
                            </div>
                            <div class="cart-item-total">${(item.product_price * item.quantity).toFixed(2)} ₽</div>
                            <button class="btn-remove" onclick="removeFromCart(${item.id})">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    `).join('')}
                </div>
                <a href="/catalog/" class="btn btn-outline-primary mt-3">
                    <i class="fas fa-arrow-left"></i> Продолжить покупки
                </a>
            </div>
            <div class="col-lg-4">
                <div class="cart-summary">
                    <h4>Итого</h4>
                    <div class="summary-row">
                        <span>Товары</span>
                        <span id="subtotal">${subtotal.toFixed(2)} ₽</span>
                    </div>
                    <div class="summary-row">
                        <span>Доставка</span>
                        <span id="deliveryCost">${deliveryCost === 0 ? '0 ₽' : '150 ₽'}</span>
                    </div>
                    <div class="summary-divider"></div>
                    <div class="summary-total">
                        <span>К оплате</span>
                        <span id="totalAmount">${total.toFixed(2)} ₽</span>
                    </div>
                    <button class="btn btn-primary w-100 mt-3" onclick="checkout()">
                        Оформить заказ
                    </button>
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('❌ Ошибка загрузки корзины:', error);
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <p class="text-danger">Ошибка загрузки корзины: ${error.message}</p>
                <button class="btn btn-secondary" onclick="loadCart()">🔄 Повторить</button>
            </div>
        `;
    }
    
    isLoading = false;
}

// ===== ОБНОВЛЕНИЕ СЧЁТЧИКА =====
function updateCartBadgeOnly(cart) {
    const badge = document.getElementById('cartCount');
    if (!badge) return;
    
    if (cart && cart.items) {
        const total = cart.items.reduce((sum, item) => sum + item.quantity, 0);
        badge.textContent = total;
        if (window.cartData) {
            window.cartData.total_quantity = total;
        }
    } else {
        badge.textContent = '0';
    }
}

function updateCartBadgeFromCache() {
    const badge = document.getElementById('cartCount');
    if (!badge) return;
    
    if (window.cartData && window.cartData.items) {
        const total = window.cartData.items.reduce((sum, item) => sum + item.quantity, 0);
        badge.textContent = total;
        window.cartData.total_quantity = total;
    } else {
        badge.textContent = '0';
    }
}

// ===== ОБНОВЛЕНИЕ КОЛИЧЕСТВА =====
async function updateQuantity(itemId, delta) {
    const quantityEl = document.getElementById(`qty-${itemId}`);
    if (!quantityEl) return;
    
    let newQuantity = parseInt(quantityEl.textContent) + delta;
    if (newQuantity < 1) newQuantity = 1;
    if (newQuantity > 99) newQuantity = 99;
    
    try {
        const token = localStorage.getItem('access_token');
        if (token) {
            await updateCartItem(itemId, newQuantity);
        } else {
            await updateGuestCartItem(itemId, newQuantity);
        }
        await loadCart();
    } catch (error) {
        console.error('❌ Ошибка обновления:', error);
        showNotification('❌ Ошибка обновления корзины', 'danger');
    }
}

// ===== УДАЛЕНИЕ ТОВАРА =====
async function removeFromCart(itemId) {
    console.log(`🗑️ Попытка удалить товар с ID: ${itemId}`);
    
    if (!confirm('Удалить товар из корзины?')) {
        console.log('❌ Удаление отменено пользователем');
        return;
    }
    
    try {
        const token = localStorage.getItem('access_token');
        console.log('🔑 Токен:', token ? 'есть' : 'нет');
        
        let url, response;
        
        if (token) {
            // ✅ АВТОРИЗОВАННЫЙ ПОЛЬЗОВАТЕЛЬ
            url = `/api/v1/orders/cart/remove/${itemId}/`;
            console.log('📤 DELETE запрос к (авторизованный):', url);
            
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            };
            
            response = await fetch(url, {
                method: 'DELETE',
                headers: headers,
            });
        } else {
            // ✅ НЕАВТОРИЗОВАННЫЙ ПОЛЬЗОВАТЕЛЬ (ГОСТЕВАЯ КОРЗИНА)
            url = `/api/v1/orders/guest-cart/${itemId}/`;
            console.log('📤 DELETE запрос к (гостевая):', url);
            
            response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
        }
        
        console.log('📥 Статус ответа:', response.status);
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error('❌ Ошибка от сервера:', errorData);
            throw new Error(errorData.detail || errorData.error || 'Ошибка удаления');
        }
        
        const result = await response.json();
        console.log('✅ Результат удаления:', result);
        
        // ✅ ОБНОВЛЯЕМ ЛОКАЛЬНЫЙ КЭШ
        if (window.cartData && window.cartData.items) {
            window.cartData.items = window.cartData.items.filter(item => item.id !== itemId);
            window.cartData.items_count = window.cartData.items.length;
            window.cartData.total_quantity = window.cartData.items.reduce((sum, item) => sum + item.quantity, 0);
            console.log('✅ Локальный кэш обновлён, товаров осталось:', window.cartData.items_count);
        }
        
        // ✅ ПЕРЕЗАГРУЖАЕМ КОРЗИНУ
        await loadCart();
        showNotification('🗑️ Товар удалён из корзины');
        
    } catch (error) {
        console.error('❌ Ошибка удаления:', error);
        showNotification('❌ Ошибка удаления: ' + error.message, 'danger');
    }
}

// ===== ОФОРМЛЕНИЕ ЗАКАЗА =====
function checkout() {
    window.location.href = '/checkout/';
}

// ===== ЭКСПОРТ =====
window.loadCart = loadCart;
window.updateQuantity = updateQuantity;
window.removeFromCart = removeFromCart;
window.checkout = checkout;
window.updateCartBadgeFromCache = updateCartBadgeFromCache;

console.log('✅ cart.js загружен!');