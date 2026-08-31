// frontend/static/js/main.js

document.addEventListener('DOMContentLoaded', function () {
    console.log('🚀 DOM загружен');

    updateAuthUI();

    if (document.getElementById('categoriesContainer')) {
        loadCategories();
    }
    if (document.getElementById('productsContainer')) {
        loadPopularProducts();
    }

    loadCartForBadge();
    loadAndApplySettings();

    if (document.getElementById('searchInput')) {
        initLiveSearch();
    }
});

// ===== ЗАГРУЗКА КОРЗИНЫ ДЛЯ СЧЁТЧИКА =====
async function loadCartForBadge() {
    try {
        const token = localStorage.getItem('access_token');
        let cart;

        if (token) {
            cart = await getCart();
        } else {
            try {
                cart = await getGuestCart();
            } catch (e) {
                console.warn('⚠️ Не удалось загрузить гостевую корзину');
                return;
            }
        }

        window.cartData = cart;
        updateCartBadgeFromCache();
        console.log('🛒 Корзина загружена для счётчика:', cart);
    } catch (error) {
        console.error('❌ Ошибка загрузки корзины:', error);
    }
}

// ===== ОБНОВЛЕНИЕ СЧЁТЧИКА ИЗ КЭША =====
function updateCartBadgeFromCache() {
    const badge = document.getElementById('cartCount');
    if (!badge) return;

    if (window.cartData && window.cartData.total_quantity !== undefined) {
        badge.textContent = window.cartData.total_quantity;
    } else if (window.cartData && window.cartData.items) {
        const total = window.cartData.items.reduce((sum, item) => sum + item.quantity, 0);
        badge.textContent = total;
        window.cartData.total_quantity = total;
    } else {
        badge.textContent = '0';
    }
}

// ===== ДОБАВЛЕНИЕ В КОРЗИНУ =====
async function addToCartHandler(productId) {
    console.log(`🛒 addToCartHandler(${productId}) вызвана`);

    try {
        const token = localStorage.getItem('access_token');
        let result;

        if (token) {
            console.log('👤 Авторизованный пользователь');
            result = await apiRequest('/orders/cart/add/', 'POST', {
                product_id: productId,
                quantity: 1
            }, true);
        } else {
            console.log('👤 Гостевой пользователь');
            result = await addToGuestCart(productId, 1);
        }

        console.log('✅ Товар добавлен, результат:', result);

        if (result && result.items) {
            window.cartData = result;
        }

        updateCartBadgeFromCache();
        showNotification('✅ Товар добавлен в корзину!');

    } catch (error) {
        console.error('❌ Ошибка добавления в корзину:', error);

        if (error.message.includes('authentication') || error.message.includes('credentials') || error.message.includes('401')) {
            showNotification('⚠️ Пожалуйста, войдите в систему', 'warning');
            const modalElement = document.getElementById('authModal');
            if (modalElement) {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            }
        } else {
            showNotification('❌ Ошибка: ' + error.message, 'danger');
        }
    }
}

// ===== ОБНОВЛЕНИЕ UI АВТОРИЗАЦИИ =====
function updateAuthUI() {
    const token = localStorage.getItem('access_token');
    const authText = document.getElementById('authText');
    const authBtn = document.getElementById('authBtn');

    console.log('🔐 Обновление UI авторизации, токен:', token ? 'есть' : 'нет');

    if (token) {
        getProfile().then(user => {
            if (authText) {
                authText.textContent = user.full_name || user.username || 'Профиль';
            }
            if (authBtn) {
                authBtn.classList.remove('btn-outline-primary');
                authBtn.classList.add('btn-primary');
                authBtn.removeAttribute('data-bs-toggle');
                authBtn.removeAttribute('data-bs-target');
                authBtn.onclick = function (e) {
                    e.preventDefault();
                    window.location.href = '/profile/';
                };
            }
            console.log('👤 Пользователь:', user.username);
        }).catch(() => {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            if (authText) authText.textContent = 'Вход';
            resetAuthButton();
        });
    } else {
        if (authText) authText.textContent = 'Вход';
        resetAuthButton();
    }
}

function resetAuthButton() {
    const authBtn = document.getElementById('authBtn');
    if (!authBtn) return;
    authBtn.classList.add('btn-outline-primary');
    authBtn.classList.remove('btn-primary');
    authBtn.setAttribute('data-bs-toggle', 'modal');
    authBtn.setAttribute('data-bs-target', '#authModal');
    authBtn.onclick = null;
}

// ===== LIVE SEARCH =====
function initLiveSearch() {
    const searchInput = document.getElementById('searchInput');
    const dropdown = document.getElementById('searchDropdown');
    let debounceTimer;

    if (!searchInput || !dropdown) return;

    searchInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        const query = this.value.trim();

        if (query.length < 2) {
            dropdown.classList.remove('active');
            return;
        }

        debounceTimer = setTimeout(() => {
            liveSearch(query);
        }, 300);
    });

    document.addEventListener('click', function (e) {
        if (!e.target.closest('.search-wrapper')) {
            dropdown.classList.remove('active');
        }
    });

    searchInput.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            dropdown.classList.remove('active');
            this.blur();
        }
    });
}

// ===== ЗАПРОС К API =====
async function liveSearch(query) {
    const dropdown = document.getElementById('searchDropdown');
    if (!dropdown) return;

    dropdown.innerHTML = `
        <div class="dropdown-loading">
            <div class="spinner"></div> Загрузка...
        </div>
    `;
    dropdown.classList.add('active');

    try {
        const response = await fetch(`/api/v1/products/live-search/?q=${encodeURIComponent(query)}`);
        const products = await response.json();

        if (products.length === 0) {
            dropdown.innerHTML = `<div class="dropdown-empty">Ничего не найдено</div>`;
            return;
        }

        // В функции liveSearch(), внутри .then(products => ...)
        dropdown.innerHTML = products.map(product => `
    <a href="/product/${product.id}/" class="search-dropdown-item">
        <img src="${product.image_url || '/static/images/no-image.png'}" alt="${product.name}">
        <div class="item-info">
            <div class="item-name">${highlightMatch(product.name, query)}</div>
            <div class="item-category">${product.category_name || ''}</div>
        </div>
        <div class="item-price">${product.price ? product.price + ' ₽' : '—'}</div>
    </a>
`).join('');

    } catch (error) {
        console.error('Ошибка live search:', error);
        dropdown.innerHTML = `<div class="dropdown-empty">Ошибка загрузки</div>`;
    }
}

// ===== ПОДСВЕТКА СОВПАДЕНИЙ =====
function highlightMatch(text, query) {
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

// ===== ЗАГРУЗКА КАТЕГОРИЙ (ИСПРАВЛЕННАЯ) =====
async function loadCategories() {
    const container = document.getElementById('categoriesContainer');
    if (!container) return;

    try {
        const categories = await getCategories();

        if (!Array.isArray(categories)) {
            console.error('Категории не являются массивом:', categories);
            return;
        }

        const icons = {
            'Суши': 'fa-fish',
            'Роллы': 'fa-roll',
            'Пицца': 'fa-pizza-slice',
            'Вок': 'fa-utensils',
            'Десерты': 'fa-cake-candles',
            'Напитки': 'fa-wine-bottle'
        };

        container.innerHTML = categories.map(cat => `
            <div class="category-card" onclick="window.location.href='/catalog/?category=${cat.slug}'">
                ${cat.image_url 
                    ? `<img src="${cat.image_url}" alt="${cat.name}" style="width:50px;height:50px;object-fit:contain;border-radius:8px;display:block;margin:0 auto;">`
                    : `<i class="fas ${icons[cat.name] || 'fa-circle'}" style="font-size:28px;color:#FF6B35;display:block;margin:0 auto;"></i>`
                }
                <span style="display:block;margin-top:8px;font-weight:600;">${cat.name}</span>
            </div>
        `).join('');

    } catch (error) {
        console.error('Ошибка загрузки категорий:', error);
    }
}

// ===== ЗАГРУЗКА ПОПУЛЯРНЫХ ТОВАРОВ =====
async function loadPopularProducts() {
    const container = document.getElementById('productsContainer');
    if (!container) return;

    try {
        const products = await getProducts();

        if (!Array.isArray(products)) {
            console.error('Товары не являются массивом:', products);
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <p>Товары временно недоступны</p>
                </div>
            `;
            return;
        }

        if (products.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <p>Товары временно недоступны</p>
                </div>
            `;
            return;
        }

        // Сортируем: сначала товары с is_hit=true, затем по рейтингу
        const sorted = [...products].sort((a, b) => {
            if (a.is_hit && !b.is_hit) return -1;
            if (!a.is_hit && b.is_hit) return 1;
            return (b.average_rating || 0) - (a.average_rating || 0);
        });

        // Берём первые 10
        const popular = sorted.slice(0, 10);

        container.innerHTML = popular.map(product => `
            <div class="col-lg-3 col-md-6">
                <div class="product-card" onclick="window.location.href='/product/${product.id}/'">
                    <img src="${product.image_url || '/static/images/no-image.png'}" alt="${product.name}">
                    <div class="product-info">
                        <div class="product-name">${product.name}</div>
                        <div class="product-desc">
                            ${product.weight || 0} г · ${product.ingredients || ''}
                            ${product.is_hit ? ' 🔥 Хит' : ''}
                            ${product.average_rating ? ` ⭐ ${product.average_rating}` : ''}
                        </div>
                        <div class="product-price">
                            ${product.price || 0} ₽
                        </div>
                        <button class="btn-add-cart" onclick="event.stopPropagation(); window.addToCartHandler(${product.id})">
                            В корзину
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Ошибка загрузки товаров:', error);
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <p class="text-danger">Ошибка загрузки товаров</p>
            </div>
        `;
    }
}

// ===== ЗАГРУЗКА И ПРИМЕНЕНИЕ НАСТРОЕК (БАННЕР, БОНУСЫ) =====
async function loadAndApplySettings() {
    try {
        const response = await fetch('/api/v1/core/settings/public/');
        const settings = await response.json();

        // ===== ЗАГРУЗКА МЕНЮ БИЗНЕС-ЛАНЧА =====
        const lunchMenuResponse = await fetch('/api/v1/products/lunch-menu/');
        const lunchMenu = await lunchMenuResponse.json();

        console.log('🍽️ Меню бизнес-ланча:', lunchMenu);

        // ✅ ПРОВЕРКА: элемент lunchSection существует
        const lunchSection = document.getElementById('lunchSection');
        if (lunchSection) {
            if (lunchMenu.items && lunchMenu.items.length > 0) {
                lunchSection.style.display = 'block';
                lunchSection.classList.add('active');
            } else {
                lunchSection.style.display = 'none';
            }
        }

        // ✅ ПРОВЕРКА: элемент lunchTitle существует
        const lunchTitle = document.getElementById('lunchTitle');
        if (lunchTitle) {
            lunchTitle.textContent = lunchMenu.title || 'Бизнес-ланч';
        }

        // ✅ ПРОВЕРКА: элемент lunchItems существует
        const lunchItems = document.getElementById('lunchItems');
        if (lunchItems) {
            if (lunchMenu.items && lunchMenu.items.length > 0) {
                lunchItems.innerHTML = lunchMenu.items.map((item) => `
                    <div class="lunch-item" onclick="addToCartAndGoToCheckout(${item.product_id})">
                        <div class="lunch-item-name">${item.name}</div>
                        <div class="lunch-item-price">${item.price} ₽</div>
                        <button class="btn-add-cart">В корзину</button>
                    </div>
                `).join('');
            } else {
                lunchItems.innerHTML = '<p>Меню пока пусто</p>';
            }
        } else {
            console.warn('⚠️ Элемент lunchItems не найден на странице');
        }

        // ✅ Остальные настройки (баннер и т.д.)
        const banner = document.querySelector('.banner');
        if (banner) {
            banner.style.display = settings.banner_enabled ? 'block' : 'none';
        }

        

    } catch (error) {
        console.error('❌ Ошибка загрузки настроек:', error);
    }
}

async function addToCartAndGoToCheckout(productId) {
    // ✅ ПРОВЕРКА: если product_id не найден — не добавляем в корзину
    if (!productId) {
        showNotification('⚠️ Товар не найден. Пожалуйста, обновите меню бизнес-ланча.', 'warning');
        return;
    }

    console.log('🛒 Добавляем товар в корзину, product_id:', productId);

    const token = localStorage.getItem('access_token');

    try {
        if (token) {
            await apiRequest('/orders/cart/add/', 'POST', {
                product_id: productId,
                quantity: 1
            }, true);
            console.log('✅ Товар добавлен в корзину!');
        } else {
            await addToGuestCart(productId, 1);
            console.log('✅ Товар добавлен в гостевую корзину!');
        }

        showNotification('✅ Товар добавлен в корзину!');
        window.location.href = '/checkout/';

    } catch (error) {
        console.error('❌ Ошибка добавления в корзину:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}


async function addToCartAndGoToCheckout(productId) {
    // ✅ ПРОВЕРКА: если product_id не найден — не добавляем в корзину
    if (!productId) {
        showNotification('⚠️ Товар не найден. Пожалуйста, обновите меню бизнес-ланча.', 'warning');
        return;
    }

    console.log('🛒 Добавляем товар в корзину, product_id:', productId);

    const token = localStorage.getItem('access_token');

    try {
        if (token) {
            await apiRequest('/orders/cart/add/', 'POST', {
                product_id: productId,
                quantity: 1
            }, true);
            console.log('✅ Товар добавлен в корзину!');
        } else {
            await addToGuestCart(productId, 1);
            console.log('✅ Товар добавлен в гостевую корзину!');
        }

        showNotification('✅ Товар добавлен в корзину!');
        window.location.href = '/checkout/';

    } catch (error) {
        console.error('❌ Ошибка добавления в корзину:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

// ===== УВЕДОМЛЕНИЯ =====
function showNotification(message, type = 'success') {
    const colors = {
        success: '#27AE60',
        warning: '#F39C12',
        danger: '#E74C3C',
        info: '#3498DB'
    };

    const oldNotifications = document.querySelectorAll('.alert.position-fixed');
    oldNotifications.forEach(el => el.remove());

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.style.maxWidth = '400px';
    alertDiv.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    alertDiv.style.borderLeft = `4px solid ${colors[type] || '#27AE60'}`;
    alertDiv.textContent = message;
    alertDiv.style.transition = 'opacity 0.3s ease';
    document.body.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.style.opacity = '0';
        setTimeout(() => alertDiv.remove(), 300);
    }, 1500);
}

// ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
function searchProducts() {
    const input = document.getElementById('searchInput');
    if (!input) return;
    const query = input.value.trim();
    if (query) {
        window.location.href = `/catalog/?search=${encodeURIComponent(query)}`;
    }
}

// ===== ЭКСПОРТ =====
window.updateAuthUI = updateAuthUI;
window.resetAuthButton = resetAuthButton;
window.initLiveSearch = initLiveSearch;
window.liveSearch = liveSearch;
window.highlightMatch = highlightMatch;
window.loadCategories = loadCategories;
window.loadPopularProducts = loadPopularProducts;
window.showNotification = showNotification;
window.searchProducts = searchProducts;
window.addToCartHandler = addToCartHandler; // ✅ ЯВНЫЙ ЭКСПОРТ
window.addToCart = addToCartHandler; // ✅ АЛИАС
window.updateCartBadgeFromCache = updateCartBadgeFromCache;
window.loadCartForBadge = loadCartForBadge;
window.loadAndApplySettings = loadAndApplySettings;

console.log('✅ main.js загружен!');
