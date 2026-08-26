// frontend/static/js/api.js
(function () {
    'use strict';

    const API_BASE = 'http://127.0.0.1:8000/api/v1';

    function getToken() {
        return localStorage.getItem('access_token');
    }

    function setToken(token) {
        localStorage.setItem('access_token', token);
    }

    function removeToken() {
        localStorage.removeItem('access_token');
    }

    function logout() {
        removeToken();
        localStorage.removeItem('refresh_token');
        window.location.href = '/';
    }

    async function apiRequest(endpoint, method = 'GET', data = null, auth = false) {
        const url = `${API_BASE}${endpoint}`;

        const headers = {
            'Content-Type': 'application/json',
        };

        if (auth) {
            const token = getToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }

        const options = {
            method,
            headers,
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            let response = await fetch(url, options);

            // ✅ Если токен истёк (401) и запрос требовал авторизации — пробуем обновить
            if (response.status === 401 && auth) {
                const refreshToken = localStorage.getItem('refresh_token');
                if (refreshToken) {
                    try {
                        const refreshResponse = await fetch(`${API_BASE}/users/refresh/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ refresh: refreshToken })
                        });

                        if (refreshResponse.ok) {
                            const refreshData = await refreshResponse.json();
                            localStorage.setItem('access_token', refreshData.access);

                            // ✅ Повторяем исходный запрос с новым токеном
                            headers['Authorization'] = `Bearer ${refreshData.access}`;
                            response = await fetch(url, options);
                        } else {
                            // Если обновить не удалось — выходим
                            removeToken();
                            localStorage.removeItem('refresh_token');
                            window.location.href = '/';
                            throw new Error('Сессия истекла. Пожалуйста, войдите заново.');
                        }
                    } catch (refreshError) {
                        console.error('❌ Ошибка обновления токена:', refreshError);
                        removeToken();
                        localStorage.removeItem('refresh_token');
                        window.location.href = '/';
                        throw new Error('Сессия истекла. Пожалуйста, войдите заново.');
                    }
                } else {
                    // Нет refresh_token — выходим
                    removeToken();
                    window.location.href = '/';
                    throw new Error('Сессия истекла. Пожалуйста, войдите заново.');
                }
            }

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || result.error || 'Ошибка запроса');
            }

            return result;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // ===== ТОВАРЫ =====
    async function getProducts(params = {}) {
        try {
            const allParams = { ...params, page_size: 10000 };
            const query = new URLSearchParams(params).toString();
            const endpoint = `/products/${query ? '?' + query : ''}`;
            const result = await apiRequest(endpoint);
            return result.results || result || [];
        } catch (error) {
            console.error('Ошибка загрузки товаров:', error);
            return [];
        }
    }

    async function getProduct(id) {
        return apiRequest(`/products/${id}/`);
    }

    async function getCategories() {
        try {
            const result = await apiRequest('/products/categories/');
            return result.results || result || [];
        } catch (error) {
            console.error('Ошибка загрузки категорий:', error);
            return [];
        }
    }

    // ===== АВТОРИЗАЦИЯ =====
    async function register(data) {
        return apiRequest('/users/register/', 'POST', data);
    }

    async function login(data) {
        const result = await apiRequest('/users/login/', 'POST', data);
        if (result.access) {
            setToken(result.access);
            if (result.refresh) {
                localStorage.setItem('refresh_token', result.refresh);
            }
        }
        return result;
    }

    async function getProfile() {
        return apiRequest('/users/profile/', 'GET', null, true);
    }

    // ===== КОРЗИНА (авторизованная) =====
    async function getCart() {
        return apiRequest('/orders/cart/', 'GET', null, true);
    }

    async function updateCartItem(item_id, quantity) {
        return apiRequest(`/orders/cart/update/${item_id}/`, 'PUT', {
            quantity
        }, true);
    }

    async function removeFromCart(item_id) {
        try {
            const result = await apiRequest(`/orders/cart/remove/${item_id}/`, 'DELETE', null, true);
            console.log('✅ Товар удалён из авторизованной корзины:', result);
            return result;
        } catch (error) {
            console.error('❌ Ошибка удаления из авторизованной корзины:', error);
            throw error;
        }
    }

    async function clearCart() {
        return apiRequest('/orders/cart/clear/', 'DELETE', null, true);
    }

    // ===== ГОСТЕВАЯ КОРЗИНА =====
    async function getGuestCart() {
        const response = await fetch('/api/v1/orders/guest-cart/');
        if (!response.ok) {
            throw new Error('Ошибка загрузки гостевой корзины');
        }
        return response.json();
    }

    async function addToGuestCart(product_id, quantity = 1, variant_id = null) {
        const response = await fetch('/api/v1/orders/guest-cart/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ product_id, quantity, variant_id }),
        });
        if (!response.ok) {
            throw new Error('Ошибка добавления в гостевую корзину');
        }
        return response.json();
    }

    async function updateGuestCartItem(item_id, quantity) {
        const response = await fetch(`/api/v1/orders/guest-cart/${item_id}/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ quantity }),
        });
        if (!response.ok) {
            throw new Error('Ошибка обновления гостевой корзины');
        }
        return response.json();
    }

    async function removeFromGuestCart(item_id) {
        const response = await fetch(`/api/v1/orders/guest-cart/${item_id}/`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            throw new Error('Ошибка удаления из гостевой корзины');
        }
        return response.json();
    }

    // ===== ОБЪЕДИНЕНИЕ КОРЗИН =====
    async function mergeCart() {
        try {
            console.log('🔄 Начинаем перенос гостевой корзины...');
            
            let guestCart;
            try {
                guestCart = await getGuestCart();
            } catch (e) {
                console.log('ℹ️ Гостевая корзина пуста или недоступна');
                return;
            }
            
            console.log('📦 Гостевая корзина:', guestCart);
            
            if (guestCart && guestCart.items && guestCart.items.length > 0) {
                for (const item of guestCart.items) {
                    try {
                        // ✅ ИСПОЛЬЗУЕМ apiRequest НАПРЯМУЮ ДЛЯ ДОБАВЛЕНИЯ
                        await apiRequest('/orders/cart/add/', 'POST', {
                            product_id: item.product,
                            variant_id: item.variant_id,
                            quantity: item.quantity
                        }, true);
                        console.log(`✅ Перенесён товар: ${item.product_name || item.product} x${item.quantity}`);
                    } catch (e) {
                        console.error(`❌ Ошибка переноса товара ${item.product}:`, e);
                    }
                }
                console.log('✅ Гостевая корзина перенесена в аккаунт');
            } else {
                console.log('ℹ️ Гостевая корзина пуста, перенос не требуется');
            }
            
            try {
                const newCart = await getCart();
                window.cartData = newCart;
                if (typeof updateCartBadgeFromCache === 'function') {
                    updateCartBadgeFromCache();
                }
                console.log('🛒 Данные корзины обновлены после переноса:', newCart);
            } catch (e) {
                console.warn('⚠️ Не удалось обновить данные корзины после переноса');
            }
            
        } catch (error) {
            console.error('❌ Ошибка переноса корзины:', error);
        }
    }

    // ===== ЗАКАЗЫ =====
    async function createOrder(data) {
        return apiRequest('/orders/', 'POST', data, true);
    }

    async function getOrders() {
        const result = await apiRequest('/orders/list/', 'GET', null, true);
        return result.results || result || [];
    }

    async function getOrder(id) {
        return apiRequest(`/orders/${id}/`, 'GET', null, true);
    }

    // ===== ИЗБРАННОЕ =====
    async function toggleFavorite(productId) {
        const token = getToken();
        if (!token) {
            throw new Error('Пожалуйста, войдите в систему');
        }
        return apiRequest(`/products/${productId}/favorite/`, 'POST', null, true);
    }

    async function getFavorites() {
        const token = getToken();
        if (!token) {
            console.warn('⚠️ Нет токена, возвращаем пустой массив');
            return [];
        }
        
        try {
            const result = await apiRequest('/products/favorites/', 'GET', null, true);
            console.log('📥 Избранное получено:', result);
            return result.results || result || [];
        } catch (error) {
            if (error.message.includes('401') || error.message.includes('credentials')) {
                console.warn('⚠️ Токен невалидный, удаляем');
                removeToken();
                localStorage.removeItem('refresh_token');
                return [];
            }
            throw error;
        }
    }

    async function checkFavorite(productId) {
        const token = getToken();
        if (!token) {
            return { is_favorite: false };
        }
        return apiRequest(`/products/${productId}/favorite/check/`, 'GET', null, true);
    }

    // ===== ЭКСПОРТ =====
    window.getToken = getToken;
    window.setToken = setToken;
    window.removeToken = removeToken;
    window.logout = logout;
    window.apiRequest = apiRequest;
    window.getProducts = getProducts;
    window.getProduct = getProduct;
    window.getCategories = getCategories;
    window.register = register;
    window.login = login;
    window.getProfile = getProfile;
    
    // ✅ КОРЗИНА
    window.getCart = getCart;
    window.updateCartItem = updateCartItem;
    window.removeFromCart = removeFromCart;
    window.clearCart = clearCart;
    window.getGuestCart = getGuestCart;
    window.addToGuestCart = addToGuestCart;
    window.updateGuestCartItem = updateGuestCartItem;
    window.removeFromGuestCart = removeFromGuestCart;
    window.mergeCart = mergeCart;
    
    // ✅ ЗАКАЗЫ
    window.createOrder = createOrder;
    window.getOrders = getOrders;
    window.getOrder = getOrder;
    
    // ✅ ИЗБРАННОЕ
    window.toggleFavorite = toggleFavorite;
    window.getFavorites = getFavorites;
    window.checkFavorite = checkFavorite;

    console.log('✅ api.js загружен!');
})();