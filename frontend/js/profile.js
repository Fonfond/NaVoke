// frontend/static/js/profile.js

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('📋 DOM загружен, инициализация профиля...');
    
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/';
        return;
    }
    
    // Настройка переключения вкладок
    setupTabs();
    
    // Загрузка данных
    loadProfile();
    loadOrders();
    loadFavorites();
    loadBonus();
});

// ===== НАСТРОЙКА ВКЛАДОК =====
function setupTabs() {
    const menuItems = document.querySelectorAll('.profile-menu li');
    const tabContents = document.querySelectorAll('.tab-content');
    
    console.log('📋 Найдено пунктов меню:', menuItems.length);
    console.log('📋 Найдено вкладок:', tabContents.length);
    
    // Показываем первую вкладку по умолчанию (Профиль)
    if (tabContents.length > 0) {
        tabContents.forEach(tc => tc.classList.remove('active'));
        document.getElementById('tab-profile')?.classList.add('active');
    }
    
    menuItems.forEach(item => {
        item.addEventListener('click', function(e) {
            const tab = this.dataset.tab;
            console.log('🔄 Переключение на вкладку:', tab);
            
            menuItems.forEach(el => el.classList.remove('active'));
            this.classList.add('active');
            
            tabContents.forEach(el => el.classList.remove('active'));
            
            const targetTab = document.getElementById(`tab-${tab}`);
            if (targetTab) {
                targetTab.classList.add('active');
                console.log('✅ Показана вкладка:', tab);
                
                // Перезагружаем данные при переключении
                if (tab === 'favorites') {
                    loadFavorites();
                } else if (tab === 'orders') {
                    loadOrders();
                } else if (tab === 'bonus') {
                    loadBonus();
                }
            } else {
                console.error('❌ Вкладка не найдена:', tab);
            }
        });
    });
}

// ===== ЗАГРУЗКА ПРОФИЛЯ =====
async function loadProfile() {
    try {
        const user = await getProfile();
        console.log('👤 Профиль загружен:', user);
        
        const avatarLetter = document.getElementById('avatarLetter');
        if (avatarLetter) {
            const name = user.full_name || user.username || 'П';
            avatarLetter.textContent = name.charAt(0).toUpperCase();
        }
        
        document.getElementById('profileName').textContent = user.full_name || user.username;
        document.getElementById('pUsername').textContent = user.username;
        document.getElementById('pFullName').textContent = user.full_name || '-';
        document.getElementById('pEmail').textContent = user.email || '-';
        document.getElementById('pPhone').textContent = user.phone || '-';
        document.getElementById('pDate').textContent = user.date_joined ? new Date(user.date_joined).toLocaleDateString('ru-RU') : '-';
        document.getElementById('pBonus').textContent = user.bonus_points || 0;
        document.getElementById('bonusAmount').textContent = user.bonus_points || 0;
        
        const roleMap = {
            'client': 'Клиент',
            'manager': 'Менеджер',
            'courier': 'Курьер',
            'admin': 'Администратор'
        };
        document.getElementById('profileRole').textContent = roleMap[user.role] || 'Клиент';
        
        document.getElementById('eUsername').value = user.username;
        document.getElementById('eFullName').value = user.full_name || '';
        document.getElementById('eEmail').value = user.email || '';
        document.getElementById('ePhone').value = user.phone || '';
        
        window.currentUserId = user.id;
        
    } catch (error) {
        console.error('❌ Ошибка загрузки профиля:', error);
        if (error.message.includes('credentials') || error.message.includes('401')) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/';
        }
    }
}

// ===== РЕДАКТИРОВАНИЕ ПРОФИЛЯ =====
function toggleEditProfile() {
    const info = document.getElementById('profileInfo');
    const edit = document.getElementById('profileEdit');
    if (info.classList.contains('d-none')) {
        info.classList.remove('d-none');
        edit.classList.add('d-none');
    } else {
        info.classList.add('d-none');
        edit.classList.remove('d-none');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const editForm = document.getElementById('editProfileForm');
    if (editForm) {
        editForm.addEventListener('submit', handleEditProfile);
    }
});

async function handleEditProfile(e) {
    e.preventDefault();
    
    const data = {
        full_name: document.getElementById('eFullName').value.trim(),
        email: document.getElementById('eEmail').value.trim(),
        phone: document.getElementById('ePhone').value.trim(),
    };
    
    // ✅ ОТПРАВЛЯЕМ ЗАПРОС НА СЕРВЕР
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/v1/users/profile/', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            // ✅ ВЫВОДИМ ОШИБКУ СЕРИАЛИЗАТОРА
            console.error('Ошибка валидации:', result);
            throw new Error(result.detail || JSON.stringify(result) || 'Ошибка обновления профиля');
        }
        
        console.log('✅ Профиль обновлён:', result);
        showNotification('✅ Профиль обновлён!', 'success');
        toggleEditProfile();
        loadProfile();
        
    } catch (error) {
        console.error('❌ Ошибка обновления профиля:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

// ===== ЗАГРУЗКА ЗАКАЗОВ (с кнопкой оплаты) =====
async function loadOrders() {
    const container = document.getElementById('ordersList');
    if (!container) {
        console.warn('⚠️ Контейнер ordersList не найден');
        return;
    }
    
    try {
        let orders = await getOrders();
        console.log('📦 Заказы загружены:', orders);
        
        if (!Array.isArray(orders)) {
            if (orders && orders.results) {
                orders = orders.results;
            } else {
                orders = [];
            }
        }
        
        if (!orders || orders.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-box-open fa-3x text-muted"></i>
                    <p class="mt-3">У вас пока нет заказов</p>
                    <a href="/catalog/" class="btn btn-primary">Перейти в каталог</a>
                </div>
            `;
            return;
        }
        
        container.innerHTML = orders.map(order => `
            <div class="order-card">
                <div class="order-header">
                    <div class="order-number">Заказ #${order.order_number || order.id}</div>
                    <span class="order-status status-${order.status || 'new'}">${getStatusText(order.status)}</span>
                </div>
                <div class="order-body">
                    <div class="order-date">${order.order_date ? new Date(order.order_date).toLocaleDateString('ru-RU') : 'Дата неизвестна'}</div>
                    <div class="order-total">${order.total_amount || order.total || 0} ₽</div>
                </div>
                <div class="order-items">
                    ${order.items && Array.isArray(order.items) ? order.items.map(item => `
                        <span class="order-item">${item.quantity || 1}x ${item.product_name || item.product || 'Товар'}</span>
                    `).join('') : ''}
                </div>
                <div class="d-flex gap-2 mt-2">
                    <button class="btn btn-sm btn-outline-primary" onclick="viewOrder(${order.id})">
                        Подробнее
                    </button>
                    ${order.status === 'new' && order.payment_status !== 'paid' ? `
                        <button class="btn btn-sm btn-success" onclick="payOrder(${order.id})">
                            <i class="fas fa-credit-card"></i> Оплатить
                        </button>
                    ` : ''}
                    ${order.status === 'new' || order.status === 'confirmed' ? `
                        <button class="btn btn-sm btn-danger" onclick="cancelOrder(${order.id})">
                            <i class="fas fa-times"></i> Отменить
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('❌ Ошибка загрузки заказов:', error);
        container.innerHTML = `
            <div class="text-center py-4">
                <p class="text-danger">Ошибка загрузки заказов: ${error.message}</p>
                <button class="btn btn-secondary btn-sm mt-2" onclick="loadOrders()">🔄 Повторить</button>
            </div>
        `;
    }
}

// ===== ФУНКЦИЯ ОПЛАТЫ ИЗ ПРОФИЛЯ =====
async function payOrder(orderId) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        showNotification('⚠️ Пожалуйста, войдите в систему', 'warning');
        return;
    }

    try {
        // ✅ СНАЧАЛА ПОЛУЧАЕМ ДАННЫЕ ЗАКАЗА, ЧТОБЫ УЗНАТЬ СПОСОБ ОПЛАТЫ
        const order = await getOrder(orderId);
        const paymentMethod = order.payment_method || 'cash'; // Если не указано, считаем наличными

        // ✅ ЕСЛИ ОПЛАТА НАЛИЧНЫМИ — ПРОСТО ПОКАЗЫВАЕМ УВЕДОМЛЕНИЕ
        if (paymentMethod === 'cash') {
            showNotification('✅ Оплата при получении!', 'success');
            return;
        }

        // ✅ ЕСЛИ ОНЛАЙН — СОЗДАЁМ ПЛАТЁЖ
        const response = await fetch('/api/v1/payments/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ order_id: orderId })
        });

        if (!response.ok) {
            const errorData = await response.json();
            // ✅ Если ошибка ЮKassa — просто показываем уведомление
            if (errorData.code === 'invalid_credentials') {
                showNotification('⚠️ Онлайн-оплата временно недоступна. Оплата при получении.', 'warning');
                return;
            }
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

// ===== ФУНКЦИЯ ОТМЕНЫ ЗАКАЗА =====
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
        loadOrders();
        
    } catch (error) {
        console.error('❌ Ошибка отмены заказа:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

function getStatusText(status) {
    const map = {
        'new': 'Новый',
        'confirmed': 'Подтверждён',
        'cooking': 'Готовится',
        'ready': 'Готов',
        'delivering': 'В доставке',
        'delivered': 'Доставлен ✅',
        'cancelled': 'Отменён ❌'
    };
    return map[status] || status;
}

function viewOrder(orderId) {
    window.location.href = `/order/${orderId}/`;
}

// ===== ЗАГРУЗКА ИЗБРАННОГО =====
async function loadFavorites() {
    console.log('⭐ loadFavorites() вызвана!');
    const container = document.getElementById('favoritesList');
    console.log('🔍 Контейнер favoritesList:', container);
    
    if (!container) {
        console.error('❌ Контейнер favoritesList не найден!');
        return;
    }
    
    try {
        const favorites = await getFavorites();
        console.log('⭐ Избранное получено:', favorites);
        
        if (!favorites || favorites.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-4">
                    <i class="fas fa-heart fa-3x text-muted"></i>
                    <p class="mt-3">У вас пока нет избранных товаров</p>
                    <a href="/catalog/" class="btn btn-primary">Перейти в каталог</a>
                </div>
            `;
            return;
        }
        
        container.innerHTML = favorites.map(fav => {
            const productId = fav.product || fav.product_id || fav.id;
            const productName = fav.product_name || fav.name || 'Товар';
            const productPrice = fav.product_price || fav.price || 0;
            
            let productImage = fav.product_image || fav.image_url || '';
            if (!productImage) {
                productImage = 'https://via.placeholder.com/300x200/FFF0E6/FF6B35?text=НаVoke';
            } else if (!productImage.startsWith('http') && !productImage.startsWith('/')) {
                productImage = `/media/${productImage}`;
            }
            
            return `
                <div class="col-lg-3 col-md-6">
                    <div class="product-card" onclick="window.location.href='/product/${productId}/'">
                        <img src="${productImage}" alt="${productName}" onerror="this.src='https://via.placeholder.com/300x200/FFF0E6/FF6B35?text=НаVoke'">
                        <div class="product-info">
                            <div class="product-name">${productName}</div>
                            <div class="product-price">${productPrice} ₽</div>
                            <div class="favorite-actions">
                                <button class="btn-add-cart" onclick="event.stopPropagation(); addToCart(${productId})">
                                    В корзину
                                </button>
                                <button class="btn-favorite-remove" onclick="event.stopPropagation(); removeFavoriteItem(${productId})" 
                                        title="Удалить из избранного">
                                    <i class="fas fa-trash-alt"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('❌ Ошибка загрузки избранного:', error);
        container.innerHTML = `
            <div class="col-12 text-center py-4">
                <p class="text-danger">Ошибка загрузки избранного: ${error.message}</p>
                <button class="btn btn-secondary btn-sm mt-2" onclick="loadFavorites()">🔄 Повторить</button>
            </div>
        `;
    }
}

// ===== УДАЛЕНИЕ ИЗ ИЗБРАННОГО В ПРОФИЛЕ =====
async function removeFavoriteItem(productId) {
    try {
        const result = await toggleFavorite(productId);
        console.log('🗑️ Удаление из избранного:', result);
        
        showNotification('💔 Удалено из избранного');
        
        // Обновляем список избранного
        loadFavorites();
        
    } catch (error) {
        console.error('❌ Ошибка удаления из избранного:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

// ===== ЗАГРУЗКА БОНУСОВ =====
async function loadBonus() {
    try {
        const user = await getProfile();
        const amount = document.getElementById('bonusAmount');
        if (amount) {
            amount.textContent = user.bonus_points || 0;
        }
        
        const history = document.getElementById('bonusHistory');
        if (history) {
            history.innerHTML = `
                <li class="text-muted">История начислений пока пуста</li>
            `;
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки бонусов:', error);
    }
}

// ===== ВЫХОД =====
function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        removeToken();
        localStorage.removeItem('refresh_token');
        window.location.href = '/';
    }
}

// ===== ПОИСК =====
function searchProducts() {
    const query = document.getElementById('searchInput')?.value.trim();
    if (query) {
        window.location.href = `/catalog/?search=${encodeURIComponent(query)}`;
    }
}

// ===== ДОБАВЛЕНИЕ СТИЛЕЙ ДЛЯ ЗАКАЗОВ =====
function addOrderStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .order-card {
            background: white;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border-left: 4px solid #ddd;
        }
        .order-card .order-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .order-card .order-number {
            font-weight: 700;
            font-size: 16px;
        }
        .order-card .order-status {
            font-size: 13px;
            font-weight: 600;
            padding: 4px 12px;
            border-radius: 20px;
        }
        .order-card .order-status.status-delivered { background: #D4EDDA; color: #155724; }
        .order-card .order-status.status-new { background: #CCE5FF; color: #004085; }
        .order-card .order-status.status-cooking { background: #FFF3CD; color: #856404; }
        .order-card .order-status.status-cancelled { background: #F8D7DA; color: #721C24; }
        .order-card .order-body {
            display: flex;
            justify-content: space-between;
            color: var(--gray);
            font-size: 14px;
        }
        .order-card .order-items {
            margin: 8px 0;
            font-size: 13px;
            color: var(--gray);
        }
        .order-card .order-item {
            display: inline-block;
            margin-right: 8px;
            background: var(--light-gray);
            padding: 2px 10px;
            border-radius: 12px;
        }
        .order-card .order-total {
            font-weight: 700;
            color: var(--primary);
        }
        .order-card .order-detail-btn {
            margin-top: 8px;
        }
    `;
    document.head.appendChild(style);
}
addOrderStyles();

// ===== ДОБАВЛЯЕМ ФУНКЦИИ В ГЛОБАЛЬНУЮ ОБЛАСТЬ =====
window.toggleEditProfile = toggleEditProfile;
window.logout = logout;
window.searchProducts = searchProducts;
window.viewOrder = viewOrder;
window.loadFavorites = loadFavorites;
window.loadBonus = loadBonus;
window.loadOrders = loadOrders;
window.loadProfile = loadProfile;
window.payOrder = payOrder;
window.cancelOrder = cancelOrder;

console.log('✅ profile.js загружен!');