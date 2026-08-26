// frontend/static/js/product.js

function getProductId() {
    const path = window.location.pathname;
    const parts = path.split('/');
    const id = parts[parts.length - 2];
    console.log('📦 ID товара из URL:', id);
    return id;
}

document.addEventListener('DOMContentLoaded', function() {
    const productId = getProductId();
    console.log('📦 Загружаем товар с ID:', productId);
    
    if (productId && !isNaN(productId) && productId > 0) {
        loadProduct(productId);
        loadSimilarProducts(productId);
    } else {
        console.error('❌ Неверный ID товара:', productId);
        document.getElementById('productContainer').innerHTML = `
            <div class="col-12 text-center py-5">
                <p class="text-danger">Неверный ID товара</p>
                <a href="/catalog/" class="btn btn-primary">Вернуться в каталог</a>
            </div>
        `;
    }
    
    updateAuthUI();
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchProducts();
            }
        });
    }
});

function updateAuthUI() {
    const token = localStorage.getItem('access_token');
    const authText = document.getElementById('authText');
    const authBtn = document.getElementById('authBtn');
    
    if (token) {
        getProfile().then(user => {
            if (authText) authText.textContent = user.full_name || user.username || 'Профиль';
            if (authBtn) {
                authBtn.classList.remove('btn-outline-primary');
                authBtn.classList.add('btn-primary');
                authBtn.removeAttribute('data-bs-toggle');
                authBtn.removeAttribute('data-bs-target');
                authBtn.onclick = function(e) {
                    e.preventDefault();
                    window.location.href = '/profile/';
                };
            }
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
    authBtn.classList.remove('btn-primary');
    authBtn.classList.add('btn-outline-primary');
    authBtn.setAttribute('data-bs-toggle', 'modal');
    authBtn.setAttribute('data-bs-target', '#authModal');
    authBtn.onclick = null;
}

async function loadProduct(id) {
    const container = document.getElementById('productContainer');
    
    try {
        const product = await getProduct(id);
        console.log('✅ Получен товар:', product);
        
        if (!product || product.detail) {
            throw new Error('Товар не найден');
        }
        
        let isFavorite = false;
        try {
            const favCheck = await checkFavorite(id);
            isFavorite = favCheck.is_favorite || false;
        } catch (e) {
            console.log('Проверка избранного пропущена');
        }
        
        document.getElementById('breadcrumbName').textContent = product.name;
        document.title = `${product.name} — НаVoke`;
        
        const avgRating = product.average_rating || 0;
        const fullStars = '★'.repeat(Math.floor(avgRating));
        const halfStar = (avgRating % 1 >= 0.5) ? '★' : '';
        const emptyStars = '☆'.repeat(5 - Math.ceil(avgRating));
        
        const variants = product.variants || [];
        const sortedVariants = [...variants].sort((a, b) => a.price - b.price);
        const firstVariant = sortedVariants[0] || { price: 0, weight: 0, id: null };
        
        // ✅ Если есть вариации — показываем селект
        const hasVariants = product.has_variants === true;
        
        container.innerHTML = `
            <div class="col-lg-6">
                <div class="product-image-wrapper">
                    <img src="${product.image_url || '/static/images/no-image.png'}" 
                         alt="${product.name}" 
                         class="product-image"
                         onerror="this.src='/static/images/no-image.png'">
                </div>
            </div>
            <div class="col-lg-6">
                <div class="product-details">
                    <h1 class="product-title">${product.name}</h1>
                    
                    <div class="product-meta">
                        <span class="badge bg-primary">${product.category_name || 'Категория'}</span>
                        ${product.is_hit ? '<span class="badge bg-success">🔥 Хит</span>' : ''}
                        ${product.is_new ? '<span class="badge bg-info">✨ Новинка</span>' : ''}
                    </div>

                    <div class="product-rating mt-2 mb-3">
                        <span class="rating-stars" style="color: #FF6B35; font-size: 20px;">
                            ${fullStars}${halfStar}${emptyStars}
                        </span>
                        <span class="ms-2 fw-bold">${avgRating > 0 ? avgRating : '—'}</span>
                        <span class="ms-2 text-muted">(${product.reviews?.length || 0} отзывов)</span>
                    </div>
                    
                    <div class="product-description">
                        <h5>Состав</h5>
                        <p>${product.ingredients || 'Информация о составе отсутствует'}</p>
                        <h5>Описание</h5>
                        <p>${product.description || 'Описание отсутствует'}</p>
                    </div>
                    
                    <!-- ✅ ВЫБОР ВАРИАНТА ТОЛЬКО ЕСЛИ ОНИ ЕСТЬ -->
                    ${hasVariants && sortedVariants.length > 0 ? `
                        <div class="variant-selector mb-3">
                            <label class="form-label fw-bold">Выберите размер:</label>
                            <select class="form-select" id="productVariant">
                                ${sortedVariants.map(v => `
                                    <option value="${v.id}" data-price="${v.price}" data-weight="${v.weight}">
                                        ${v.name || 'Стандарт'} — ${v.price} ₽ (${v.weight} г)
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                        <div class="product-price-block">
                            <div class="product-price" id="productPriceDisplay">${firstVariant.price} ₽</div>
                            ${firstVariant.old_price ? `<span class="product-old-price">${firstVariant.old_price} ₽</span>` : ''}
                        </div>
                    ` : `
                        <div class="product-price-block">
                            <div class="product-price">${product.min_price || 0} ₽</div>
                        </div>
                    `}
                    
                    <div class="product-actions">
                        <div class="quantity-selector">
                            <button class="btn-quantity" onclick="changeQuantity(-1)">−</button>
                            <span class="quantity-value" id="productQuantity">1</span>
                            <button class="btn-quantity" onclick="changeQuantity(1)">+</button>
                        </div>
                        
                        <button class="btn-add-to-cart" onclick="addProductToCart()">
                            <i class="fas fa-shopping-cart"></i> В корзину
                        </button>
                        
                        <div class="favorite-actions">
                            <button class="btn-favorite ${isFavorite ? 'active' : ''}" 
                                    onclick="toggleFavoriteProduct(${product.id})" 
                                    id="favoriteBtn">
                                <i class="fas fa-heart" style="${isFavorite ? 'color: #FF0000;' : ''}"></i>
                            </button>
                            ${isFavorite ? `
                                <button class="btn-favorite-remove" onclick="removeFromFavorites(${product.id})" 
                                        title="Удалить из избранного">
                                    <i class="fas fa-times"></i>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                    
                    <div class="product-info-links">
                        <div class="info-item">
                            <i class="fas fa-truck"></i>
                            <span>Бесплатная доставка от 800 ₽</span>
                        </div>
                        <div class="info-item">
                            <i class="fas fa-star"></i>
                            <span>${avgRating > 0 ? avgRating : '—'} / 5</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // ✅ Обработчик изменения варианта
        const variantSelect = document.getElementById('productVariant');
        if (variantSelect) {
            variantSelect.addEventListener('change', function() {
                const selected = this.options[this.selectedIndex];
                document.getElementById('productPriceDisplay').textContent = selected.dataset.price + ' ₽';
                window.currentVariantId = this.value;
                window.currentPrice = selected.dataset.price;
            });
            window.currentVariantId = variantSelect.value;
            window.currentPrice = firstVariant.price;
        } else {
            window.currentVariantId = null;
        }
        
        window.currentProduct = product;
        window.isFavorite = isFavorite;

        renderReviews(product.reviews || []);
        renderReviewForm(product.id);

    } catch (error) {
        console.error('❌ Ошибка загрузки товара:', error);
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <p class="text-danger">❌ Товар не найден</p>
                <a href="/catalog/" class="btn btn-primary">Вернуться в каталог</a>
            </div>
        `;
    }
}

function renderReviews(reviews) {
    const container = document.getElementById('reviewsContainer');
    if (!container) {
        const productContainer = document.getElementById('productContainer');
        if (productContainer) {
            const reviewsSection = document.createElement('div');
            reviewsSection.id = 'reviewsContainer';
            reviewsSection.className = 'mt-5';
            productContainer.parentElement.appendChild(reviewsSection);
        }
        return renderReviews(reviews);
    }

    if (!reviews || reviews.length === 0) {
        container.innerHTML = `
            <h3 class="section-title">Отзывы</h3>
            <p class="text-muted">У этого товара пока нет отзывов. Будьте первым!</p>
        `;
        return;
    }

    container.innerHTML = `
        <h3 class="section-title">Отзывы (${reviews.length})</h3>
        <div class="reviews-list">
            ${reviews.map(review => `
                <div class="review-item border-bottom py-3">
                    <div class="d-flex justify-content-between">
                        <div>
                            <strong>${review.user_name || 'Пользователь'}</strong>
                            <span class="ms-2 text-warning" style="font-size: 16px;">
                                ${'★'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)}
                            </span>
                        </div>
                        <span class="text-muted small">${new Date(review.created_at).toLocaleDateString('ru-RU')}</span>
                    </div>
                    <p class="mt-1 mb-0">${review.text || 'Без текста'}</p>
                </div>
            `).join('')}
        </div>
    `;
}

function renderReviewForm(productId) {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const container = document.getElementById('reviewFormContainer');
    if (!container) {
        const reviewsContainer = document.getElementById('reviewsContainer');
        if (reviewsContainer) {
            const formDiv = document.createElement('div');
            formDiv.id = 'reviewFormContainer';
            formDiv.className = 'mt-4 p-3 border rounded bg-light';
            reviewsContainer.parentElement.appendChild(formDiv);
        }
        return renderReviewForm(productId);
    }

    container.innerHTML = `
        <h5>Оставить отзыв</h5>
        <form id="reviewForm">
            <div class="mb-3">
                <label class="form-label">Оценка</label>
                <div class="rating-input">
                    <div class="stars-container">
                        ${[5, 4, 3, 2, 1].map(i => `
                            <input type="radio" name="rating" id="star${i}" value="${i}" required>
                            <label for="star${i}" class="star-label" title="${i} звезд">★</label>
                        `).join('')}
                    </div>
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label">Текст отзыва (необязательно)</label>
                <textarea class="form-control" id="reviewText" rows="2" placeholder="Поделитесь впечатлениями..."></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Отправить</button>
            <div id="reviewError" class="alert alert-danger d-none mt-2"></div>
            <div id="reviewSuccess" class="alert alert-success d-none mt-2"></div>
        </form>
    `;

    document.getElementById('reviewForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const rating = document.querySelector('input[name="rating"]:checked')?.value;
        const text = document.getElementById('reviewText').value.trim();
        const errorEl = document.getElementById('reviewError');
        const successEl = document.getElementById('reviewSuccess');

        errorEl.classList.add('d-none');
        successEl.classList.add('d-none');

        if (!rating) {
            errorEl.textContent = '⚠️ Поставьте оценку';
            errorEl.classList.remove('d-none');
            return;
        }

        try {
            const response = await fetch(`/api/v1/products/${productId}/reviews/create/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    rating: parseInt(rating),
                    text: text
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                if (errData.detail && errData.detail.includes('already')) {
                    throw new Error('Вы уже оставили отзыв на этот товар.');
                }
                throw new Error(errData.detail || errData.error || 'Ошибка при отправке');
            }

            successEl.textContent = '✅ Спасибо! Ваш отзыв опубликован.';
            successEl.classList.remove('d-none');
            document.getElementById('reviewText').value = '';
            document.querySelectorAll('input[name="rating"]').forEach(r => r.checked = false);

            setTimeout(() => {
                loadProduct(productId);
            }, 1000);

        } catch (error) {
            console.error('❌ Ошибка отправки отзыва:', error);
            errorEl.textContent = '❌ ' + error.message;
            errorEl.classList.remove('d-none');
        }
    });
}

function addReviewStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .stars-container {
            display: flex;
            flex-direction: row-reverse;
            justify-content: flex-start;
            gap: 4px;
            font-size: 30px;
        }
        .stars-container input {
            display: none;
        }
        .stars-container .star-label {
            cursor: pointer;
            color: #ddd;
            transition: color 0.2s;
        }
        .stars-container .star-label:hover,
        .stars-container .star-label:hover ~ .star-label,
        .stars-container input:checked ~ .star-label {
            color: #FF6B35;
        }
        .review-item {
            padding: 12px 0;
        }
        .rating-stars {
            color: #FF6B35;
        }
    `;
    document.head.appendChild(style);
}
addReviewStyles();

async function removeFromFavorites(productId) {
    try {
        const result = await toggleFavorite(productId);
        console.log('🗑️ Удаление из избранного:', result);
        
        const btn = document.getElementById('favoriteBtn');
        const icon = btn?.querySelector('i');
        if (icon) icon.style.color = '';
        btn?.classList.remove('active');
        window.isFavorite = false;
        
        const removeBtn = document.querySelector('.btn-favorite-remove');
        if (removeBtn) removeBtn.style.display = 'none';
        
        showNotification('💔 Удалено из избранного');
        updateFavoriteBadge();
        
    } catch (error) {
        console.error('❌ Ошибка удаления из избранного:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

function updateFavoriteBadge() {
    const badge = document.getElementById('favoritesCount');
    if (badge) {
        getFavorites().then(favorites => {
            badge.textContent = favorites.length || 0;
        }).catch(() => {
            badge.textContent = '0';
        });
    }
}

async function toggleFavoriteProduct(productId) {
    const btn = document.getElementById('favoriteBtn');
    const icon = btn?.querySelector('i');
    const actions = document.querySelector('.favorite-actions');
    
    try {
        const result = await toggleFavorite(productId);
        console.log('Избранное:', result);
        
        if (result.status === 'added') {
            if (icon) icon.style.color = '#FF0000';
            btn?.classList.add('active');
            window.isFavorite = true;
            
            if (actions && !actions.querySelector('.btn-favorite-remove')) {
                const removeBtn = document.createElement('button');
                removeBtn.className = 'btn-favorite-remove';
                removeBtn.innerHTML = '<i class="fas fa-times"></i>';
                removeBtn.title = 'Удалить из избранного';
                removeBtn.onclick = () => removeFromFavorites(productId);
                actions.appendChild(removeBtn);
            }
            
            showNotification('❤️ Добавлено в избранное');
        } else {
            if (icon) icon.style.color = '';
            btn?.classList.remove('active');
            window.isFavorite = false;
            
            const removeBtn = actions?.querySelector('.btn-favorite-remove');
            if (removeBtn) removeBtn.style.display = 'none';
            
            showNotification('💔 Удалено из избранного');
        }
        
        updateFavoriteBadge();
        
    } catch (error) {
        console.error('Ошибка избранного:', error);
        if (error.message.includes('authentication') || error.message.includes('credentials')) {
            showNotification('⚠️ Пожалуйста, войдите в систему', 'warning');
            const modal = new bootstrap.Modal(document.getElementById('authModal'));
            modal.show();
        } else {
            showNotification('❌ Ошибка: ' + error.message, 'danger');
        }
    }
}

async function loadSimilarProducts(productId) {
    const container = document.getElementById('similarProducts');
    
    try {
        const products = await getProducts();
        
        if (!Array.isArray(products)) {
            console.error('Товары не являются массивом');
            return;
        }
        
        const currentProduct = products.find(p => p.id == productId);
        if (!currentProduct) {
            container.innerHTML = `<p class="text-muted">Похожие товары не найдены</p>`;
            return;
        }
        
        const similar = products
            .filter(p => p.category === currentProduct.category && p.id != productId)
            .slice(0, 4);
        
        if (similar.length === 0) {
            container.innerHTML = `<p class="text-muted">Похожие товары не найдены</p>`;
            return;
        }
        
        container.innerHTML = similar.map(product => `
            <div class="col-lg-3 col-md-6">
                <div class="product-card" onclick="window.location.href='/product/${product.id}/'">
                    <img src="${product.image_url || '/static/images/no-image.png'}" alt="${product.name}">
                    <div class="product-info">
                        <div class="product-name">${product.name}</div>
                        <div class="product-desc">${product.weight || 0} г</div>
                        <div class="product-price">${product.price} ₽</div>
                        <button class="btn-add-cart" onclick="event.stopPropagation(); addToCart(${product.id})">
                            В корзину
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Ошибка загрузки похожих товаров:', error);
    }
}

let quantity = 1;

function changeQuantity(delta) {
    quantity += delta;
    if (quantity < 1) quantity = 1;
    if (quantity > 99) quantity = 99;
    const el = document.getElementById('productQuantity');
    if (el) el.textContent = quantity;
}

async function addProductToCart() {
    if (!window.currentProduct) {
        showNotification('❌ Товар не загружен', 'danger');
        return;
    }
    
    const token = localStorage.getItem('access_token');
    const data = {
        product_id: window.currentProduct.id,
        quantity: quantity
    };
    
    // ✅ Если есть вариации и выбран вариант — передаём variant_id
    if (window.currentProduct.has_variants && window.currentVariantId) {
        data.variant_id = parseInt(window.currentVariantId);
    }
    
    try {
        let result;
        if (token) {
            result = await apiRequest('/orders/cart/add/', 'POST', data, true);
        } else {
            result = await addToGuestCart(data.product_id, data.quantity, data.variant_id || null);
        }
        
        if (result && result.items) {
            window.cartData = result;
        }
        updateCartBadgeFromCache();
        showNotification(`✅ ${window.currentProduct.name} добавлен в корзину!`);
        quantity = 1;
        document.getElementById('productQuantity').textContent = quantity;
    } catch (error) {
        console.error('❌ Ошибка добавления в корзину:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

function searchProducts() {
    const query = document.getElementById('searchInput')?.value.trim();
    if (query) {
        window.location.href = `/catalog/?search=${encodeURIComponent(query)}`;
    }
}

window.changeQuantity = changeQuantity;
window.addProductToCart = addProductToCart;
window.toggleFavoriteProduct = toggleFavoriteProduct;
window.removeFromFavorites = removeFromFavorites;
window.searchProducts = searchProducts;
window.loadProduct = loadProduct;
window.loadSimilarProducts = loadSimilarProducts;

console.log('✅ product.js загружен!');