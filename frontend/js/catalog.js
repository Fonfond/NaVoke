// frontend/static/js/catalog.js

let currentProducts = [];
let currentPage = 1;
const pageSize = 9;
let allCategories = [];
let isFiltersLoaded = false;

document.addEventListener('DOMContentLoaded', function() {
    // Читаем параметры из URL
    const urlParams = new URLSearchParams(window.location.search);
    const categorySlug = urlParams.get('category');
    const searchQuery = urlParams.get('search');
    
    // Загружаем категории для хлебных крошек
    loadCategoriesForBreadcrumbs();
    
    // Обновляем хлебные крошки
    updateBreadcrumbs(categorySlug, searchQuery);
    
    if (searchQuery) {
        const searchInput = document.querySelector('.search-wrapper input');
        if (searchInput) {
            searchInput.value = searchQuery;
            console.log('🔍 Установлен поисковый запрос:', searchQuery);
        }
    }
    
    // ✅ СНАЧАЛА ЗАГРУЖАЕМ ФИЛЬТРЫ
    loadCategoryFilters().then(() => {
        isFiltersLoaded = true;
        loadCatalog();
    });
    
    // Сортировка
    const sortSelect = document.getElementById('sortOrder');
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            currentPage = 1;
            loadCatalog();
        });
    }
    
    // Поиск по нажатию Enter
    const searchInput = document.querySelector('.search-wrapper input');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                applySearch();
            }
        });
    }
    
    // ✅ ОБРАБОТЧИКИ ДЛЯ ФИЛЬТРАЦИИ ПО ЦЕНЕ
    const priceMin = document.getElementById('priceMin');
    const priceMax = document.getElementById('priceMax');
    if (priceMin && priceMax) {
        priceMin.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') applyFilters();
        });
        priceMax.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') applyFilters();
        });
    }
    
    // Обработчик изменения URL
    window.addEventListener('popstate', function() {
        const newParams = new URLSearchParams(window.location.search);
        const newCategory = newParams.get('category');
        const newSearch = newParams.get('search');
        updateBreadcrumbs(newCategory, newSearch);
        loadCatalog();
    });
});

// ===== ЗАГРУЗКА КАТЕГОРИЙ ДЛЯ ХЛЕБНЫХ КРОШЕК =====
async function loadCategoriesForBreadcrumbs() {
    try {
        allCategories = await getCategories();
        console.log('📋 Категории загружены для хлебных крошек:', allCategories);
    } catch (error) {
        console.error('Ошибка загрузки категорий:', error);
    }
}

// ===== ХЛЕБНЫЕ КРОШКИ =====
function updateBreadcrumbs(categorySlug, searchQuery) {
    const breadcrumbContainer = document.querySelector('.breadcrumb');
    if (!breadcrumbContainer) return;
    
    const lastItem = breadcrumbContainer.querySelector('.active');
    if (!lastItem) return;
    
    let displayName = 'Каталог';
    
    if (searchQuery) {
        displayName = `Поиск: "${searchQuery}"`;
    } else if (categorySlug) {
        const found = allCategories.find(c => c.slug === categorySlug);
        if (found) {
            displayName = found.name;
        } else {
            displayName = categorySlug;
        }
    }
    
    lastItem.textContent = displayName;
    console.log('🍞 Хлебные крошки обновлены:', displayName);
}

// ===== ПРИМЕНЕНИЕ ПОИСКА =====
function applySearch() {
    const searchInput = document.querySelector('.search-wrapper input');
    const query = searchInput?.value.trim();
    console.log('🔍 Поиск:', query);
    
    if (query) {
        window.location.href = `/catalog/?search=${encodeURIComponent(query)}`;
    } else {
        window.location.href = `/catalog/`;
    }
}

// ===== ЗАГРУЗКА КАТАЛОГА =====
async function loadCatalog() {
    const container = document.getElementById('productsContainer');
    const countEl = document.getElementById('productsCount');
    
    if (!container) {
        console.warn('⚠️ Контейнер productsContainer не найден');
        return;
    }
    
    if (!isFiltersLoaded) {
        console.log('⏳ Ждём загрузки фильтров...');
        return;
    }
    
    try {
        // Получаем параметры из URL
        const urlParams = new URLSearchParams(window.location.search);
        const urlCategory = urlParams.get('category');
        const urlSearch = urlParams.get('search');
        const priceMinUrl = urlParams.get('price_min');
        const priceMaxUrl = urlParams.get('price_max');
        
        // Получаем выбранную категорию из фильтра или URL
        let category = getCategoryFilter();
        if (!category && urlCategory) {
            category = urlCategory;
            const radio = document.querySelector(`input[name="category"][value="${urlCategory}"]`);
            if (radio) {
                radio.checked = true;
                console.log('🔘 Отмечена радиокнопка из URL:', urlCategory);
            }
        }
        
        const search = getSearchQuery() || urlSearch || '';
        const sort = document.getElementById('sortOrder')?.value || '-created_at';
        
        // ✅ ЧИТАЕМ ЦЕНУ ИЗ URL (если есть) ИЛИ ИЗ ИНПУТОВ
        const priceMin = parseInt(priceMinUrl) || parseInt(document.getElementById('priceMin')?.value) || 0;
        const priceMax = parseInt(priceMaxUrl) || parseInt(document.getElementById('priceMax')?.value) || 99999;
        
        const isNew = document.getElementById('filterNew')?.checked || false;
        const isHit = document.getElementById('filterHit')?.checked || false;
        
        console.log('🔍 Фильтры:', { category, search, sort, priceMin, priceMax, isNew, isHit });
        console.log('🔍 URL параметры:', { urlCategory, urlSearch, priceMinUrl, priceMaxUrl });
        
        // Загружаем товары
        const products = await getProducts();
        
        if (!Array.isArray(products)) {
            console.error('Товары не являются массивом:', products);
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <p class="text-danger">Ошибка формата данных</p>
                </div>
            `;
            return;
        }
        
        console.log(`📦 Всего товаров в БД: ${products.length}`);
        
        // ===== ПРИМЕНЯЕМ ФИЛЬТРЫ =====
        let filteredProducts = products.filter(product => {
            // Фильтр по категории
            if (category && product.category_slug !== category) {
                return false;
            }
            
            // Фильтр по поиску
            if (search) {
                const searchLower = search.toLowerCase();
                const matchName = product.name.toLowerCase().includes(searchLower);
                const matchDesc = product.description && product.description.toLowerCase().includes(searchLower);
                if (!matchName && !matchDesc) {
                    return false;
                }
            }
            
            // Фильтр "Новинки"
            if (isNew && !product.is_new) {
                return false;
            }
            
            // Фильтр "Хиты"
            if (isHit && !product.is_hit) {
                return false;
            }
            
            // ✅ ФИЛЬТР ПО ЦЕНЕ (теперь используем product.price)
            const price = product.price || 0;
            if (price < priceMin || price > priceMax) {
                return false;
            }
            
            return true;
        });
        
        console.log(`📊 Отфильтровано товаров: ${filteredProducts.length}`);
        
        // Сортировка
        filteredProducts.sort((a, b) => {
            if (sort === 'price') return (a.price || 0) - (b.price || 0);
            if (sort === '-price') return (b.price || 0) - (a.price || 0);
            if (sort === 'name') return a.name.localeCompare(b.name);
            return (b.created_at || '').localeCompare(a.created_at || '');
        });
        
        currentProducts = filteredProducts;
        
        // Пагинация
        const totalPages = Math.ceil(filteredProducts.length / pageSize);
        const start = (currentPage - 1) * pageSize;
        const end = start + pageSize;
        const pageProducts = filteredProducts.slice(start, end);
        
        // Отображение
        if (pageProducts.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="fas fa-search fa-3x text-muted"></i>
                    <p class="mt-3">Товары не найдены</p>
                    <a href="/catalog/" class="btn btn-primary" onclick="resetFilters()">Сбросить фильтры</a>
                </div>
            `;
            if (countEl) countEl.textContent = '0 товаров';
        } else {
            container.innerHTML = pageProducts.map(product => `
                <div class="col-lg-4 col-md-6">
                    <div class="product-card" onclick="window.location.href='/product/${product.id}/'">
                        <img src="${product.image_url || '/static/images/no-image.png'}" alt="${product.name}">
                        <div class="product-info">
                            <div class="product-name">${product.name}</div>
                            <div class="product-desc">${product.weight || 0} г · ${product.ingredients || ''}</div>
                            <div class="product-price">${product.price || 0} ₽</div>
                            <button class="btn-add-cart" onclick="event.stopPropagation(); window.addToCart(${product.id})">
                                В корзину
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
            
            if (countEl) countEl.textContent = `${filteredProducts.length} товаров`;
        }
        
        // Пагинация
        renderPagination(totalPages);
        
    } catch (error) {
        console.error('❌ Ошибка загрузки каталога:', error);
        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <p class="text-danger">Ошибка загрузки товаров: ${error.message}</p>
            </div>
        `;
    }
}

// ===== ЗАГРУЗКА ФИЛЬТРОВ КАТЕГОРИЙ =====
async function loadCategoryFilters() {
    return new Promise(async (resolve) => {
        const container = document.getElementById('categoriesFilter');
        if (!container) {
            resolve();
            return;
        }
        
        try {
            const categories = await getCategories();
            
            if (!Array.isArray(categories)) {
                console.error('Категории не являются массивом:', categories);
                resolve();
                return;
            }
            
            console.log('📋 Категории для фильтров:', categories);
            
            allCategories = categories;
            
            const urlParams = new URLSearchParams(window.location.search);
            const selectedCategory = urlParams.get('category');
            
            container.innerHTML = categories.map(cat => `
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="category" 
                           id="cat_${cat.slug}" value="${cat.slug}"
                           ${selectedCategory === cat.slug ? 'checked' : ''}
                           onchange="onCategoryChange('${cat.slug}')">
                    <label class="form-check-label" for="cat_${cat.slug}">
                        ${cat.name}
                    </label>
                </div>
            `).join('');
            
            console.log('📋 Фильтры категорий загружены, выбрано:', selectedCategory || 'нет');
            resolve();
            
        } catch (error) {
            console.error('Ошибка загрузки категорий:', error);
            resolve();
        }
    });
}

// ===== ОБРАБОТЧИК ИЗМЕНЕНИЯ КАТЕГОРИИ =====
function onCategoryChange(slug) {
    console.log('🔄 Изменена категория на:', slug);
    const url = new URL(window.location.href);
    if (slug) {
        url.searchParams.set('category', slug);
    } else {
        url.searchParams.delete('category');
    }
    url.searchParams.delete('search');
    window.history.pushState({}, '', url);
    updateBreadcrumbs(slug, null);
    currentPage = 1;
    loadCatalog();
}

// ===== ПАГИНАЦИЯ =====
function renderPagination(totalPages) {
    const container = document.getElementById('paginationContainer');
    if (!container) return;
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1})">Назад</a>
        </li>
    `;
    
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || Math.abs(i - currentPage) <= 1) {
            html += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
                </li>
            `;
        } else if (i === currentPage - 2 || i === currentPage + 2) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }
    
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1})">Вперед</a>
        </li>
    `;
    
    container.innerHTML = html;
}

function changePage(page) {
    if (page < 1) return;
    const totalPages = Math.ceil(currentProducts.length / pageSize);
    if (page > totalPages) return;
    currentPage = page;
    loadCatalog();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
function getCategoryFilter() {
    const selected = document.querySelector('input[name="category"]:checked');
    return selected ? selected.value : null;
}

function getSearchQuery() {
    const input = document.querySelector('.search-wrapper input');
    return input ? input.value : '';
}

function applyFilters() {
    currentPage = 1;
    const category = getCategoryFilter();
    const priceMin = document.getElementById('priceMin')?.value || 0;
    const priceMax = document.getElementById('priceMax')?.value || 5000;
    
    const url = new URL(window.location.href);
    if (category) {
        url.searchParams.set('category', category);
    } else {
        url.searchParams.delete('category');
    }
    url.searchParams.set('price_min', priceMin);
    url.searchParams.set('price_max', priceMax);
    
    window.history.pushState({}, '', url);
    updateBreadcrumbs(category, null);
    loadCatalog();
}

function resetFilters() {
    document.querySelectorAll('input[name="category"]').forEach(el => el.checked = false);
    const priceMin = document.getElementById('priceMin');
    const priceMax = document.getElementById('priceMax');
    const filterNew = document.getElementById('filterNew');
    const filterHit = document.getElementById('filterHit');
    const searchInput = document.querySelector('.search-wrapper input');
    
    if (priceMin) priceMin.value = 0;
    if (priceMax) priceMax.value = 5000;
    if (filterNew) filterNew.checked = false;
    if (filterHit) filterHit.checked = false;
    if (searchInput) searchInput.value = '';
    
    const url = new URL(window.location.href);
    url.searchParams.delete('category');
    url.searchParams.delete('search');
    url.searchParams.delete('price_min');
    url.searchParams.delete('price_max');
    window.history.pushState({}, '', url);
    
    updateBreadcrumbs(null, null);
    currentPage = 1;
    loadCatalog();
}

// ===== ДЕЛАЕМ ФУНКЦИИ ГЛОБАЛЬНЫМИ ДЛЯ HTML =====
window.applySearch = applySearch;
window.applyFilters = applyFilters;
window.resetFilters = resetFilters;
window.onCategoryChange = onCategoryChange;
window.changePage = changePage;
window.addToCart = window.addToCart || function(productId) {
    // Используем глобальную функцию из main.js
    if (typeof window.addToCartHandler === 'function') {
        window.addToCartHandler(productId);
    } else {
        console.error('❌ addToCartHandler не найдена! Проверьте загрузку main.js');
        showNotification('❌ Ошибка: функция добавления в корзину не загружена', 'danger');
    }
};
// ✅ ЯВНО ЭКСПОРТИРУЕМ addToCartHandler
window.addToCartHandler = window.addToCartHandler || function(productId) {
    console.log('🛒 addToCartHandler вызвана для товара:', productId);
    // Эта функция будет переопределена в main.js
};

console.log('✅ catalog.js загружен!');