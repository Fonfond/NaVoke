// frontend/static/js/admin.js

document.addEventListener('DOMContentLoaded', function () {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    checkAdminAccess();

    const addImageInput = document.getElementById('addProductImage');
    if (addImageInput) {
        addImageInput.addEventListener('change', function (e) {
            const preview = document.getElementById('addProductPreview');
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (event) {
                    preview.src = event.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            } else {
                preview.style.display = 'none';
            }
        });
    }
});

async function checkAdminAccess() {
    try {
        const user = await getProfile();
        console.log('👤 Пользователь:', user);

        if (user.role !== 'admin') {
            document.getElementById('adminContent').classList.add('hidden');
            document.getElementById('accessDenied').classList.add('visible');
            showNotification('⛔ Доступ запрещён! Только для администраторов.', 'danger');
            return;
        }

        document.getElementById('adminContent').classList.remove('hidden');
        document.getElementById('accessDenied').classList.remove('visible');

        loadDashboard();
        loadOrders();
        loadProducts();
        loadUsers();
        loadSettings();
        startOrderNotifications();

        document.querySelectorAll('.nav-link[data-tab]').forEach(el => {
            el.addEventListener('click', function (e) {
                e.preventDefault();
                const tab = this.dataset.tab;
                document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
                this.classList.add('active');
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                document.getElementById(`tab-${tab}`).classList.add('active');

                if (tab === 'orders') loadOrders();
                if (tab === 'products') loadProducts();
                if (tab === 'users') loadUsers();
            });
        });

    } catch (error) {
        console.error('❌ Ошибка проверки прав:', error);
        document.getElementById('adminContent').classList.add('hidden');
        document.getElementById('accessDenied').classList.add('visible');
        showNotification('⚠️ Ошибка проверки прав доступа', 'danger');
    }
}

let allUsers = [];
let allProducts = [];
let currentProductPage = 1;
const productsPageSize = 10;
let currentUserPage = 1;
const usersPageSize = 10;

async function loadUsers() {
    const tbody = document.getElementById('usersList');
    if (!tbody) return;

    try {
        const response = await fetch('/api/v1/users/list/', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        if (!response.ok) {
            throw new Error('Ошибка загрузки пользователей');
        }

        const users = await response.json();
        allUsers = Array.isArray(users) ? users : (users.results || []);
        console.log('👥 Пользователи загружены:', allUsers);

        document.getElementById('statUsers').textContent = allUsers.length;

        renderUsersTable(allUsers);

    } catch (error) {
        console.error('❌ Ошибка загрузки пользователей:', error);
        renderUsersMock();
    }
}

function renderUsersMock() {
    const tbody = document.getElementById('usersList');
    if (!tbody) return;

    const mockUsers = [{
            id: 1,
            username: 'admin',
            full_name: 'Администратор',
            email: 'admin@navoke.ru',
            phone: '+7 (999) 111-11-11',
            orders_count: 15,
            role: 'admin',
            is_active: true
        },
        {
            id: 2,
            username: 'manager',
            full_name: 'Менеджер',
            email: 'manager@navoke.ru',
            phone: '+7 (999) 222-22-22',
            orders_count: 8,
            role: 'manager',
            is_active: true
        },
        {
            id: 3,
            username: 'client1',
            full_name: 'Иван Иванов',
            email: 'ivan@mail.ru',
            phone: '+7 (999) 333-33-33',
            orders_count: 3,
            role: 'client',
            is_active: true
        },
        {
            id: 4,
            username: 'client2',
            full_name: 'Петр Петров',
            email: 'petr@mail.ru',
            phone: '+7 (999) 444-44-44',
            orders_count: 1,
            role: 'client',
            is_active: false
        },
    ];

    allUsers = mockUsers;
    renderUsersTable(allUsers);
    document.getElementById('statUsers').textContent = allUsers.length;
}

function renderUsersTable(users) {
    const tbody = document.getElementById('usersList');
    if (!tbody) return;

    if (!users || users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">Нет пользователей</td></tr>`;
        return;
    }

    const start = (currentUserPage - 1) * usersPageSize;
    const end = start + usersPageSize;
    const pageUsers = users.slice(start, end);

    tbody.innerHTML = pageUsers.map(user => `
        <tr id="user-row-${user.id}">
            <td>${user.id}</td>
            <td>
                <div class="d-flex align-items-center">
                    <div class="avatar-circle-sm me-2" style="width:32px;height:32px;border-radius:50%;background:#FF6B35;color:white;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:14px;">
                        ${(user.full_name || user.username || 'U').charAt(0).toUpperCase()}
                    </div>
                    <span>${user.full_name || user.username}</span>
                </div>
            </td>
            <td>${user.email || '—'}</td>
            <td>${user.phone || '—'}</td>
            <td>${user.orders_count || 0}</td>
            <td>
                <span class="badge bg-${user.role === 'admin' ? 'danger' : user.role === 'manager' ? 'warning' : 'secondary'}">
                    ${user.role === 'admin' ? 'Админ' : user.role === 'manager' ? 'Менеджер' : 'Клиент'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary me-1" onclick="editUserRole(${user.id})" title="Изменить роль">
                    <i class="fas fa-user-cog"></i>
                </button>
                <button class="btn btn-sm btn-outline-${user.is_active ? 'danger' : 'success'} me-1" onclick="toggleUserStatus(${user.id})" title="${user.is_active ? 'Заблокировать' : 'Разблокировать'}">
                    <i class="fas fa-${user.is_active ? 'ban' : 'check-circle'}"></i>
                </button>
                <button class="btn btn-sm btn-outline-info" onclick="viewUserOrders(${user.id})" title="Заказы пользователя">
                    <i class="fas fa-list"></i>
                </button>
            </td>
        </tr>
    `).join('');

    renderUsersPagination(users.length);
}

function renderUsersPagination(total) {
    const container = document.getElementById('usersPagination');
    if (!container) return;

    const totalPages = Math.ceil(total / usersPageSize);
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = `
        <li class="page-item ${currentUserPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changeUsersPage(${currentUserPage - 1})">Назад</a>
        </li>
    `;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || Math.abs(i - currentUserPage) <= 1) {
            html += `
                <li class="page-item ${i === currentUserPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="changeUsersPage(${i})">${i}</a>
                </li>
            `;
        } else if (i === currentUserPage - 2 || i === currentUserPage + 2) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }

    html += `
        <li class="page-item ${currentUserPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changeUsersPage(${currentUserPage + 1})">Вперед</a>
        </li>
    `;

    container.innerHTML = html;
}

function changeUsersPage(page) {
    if (page < 1) return;
    const totalPages = Math.ceil(allUsers.length / usersPageSize);
    if (page > totalPages) return;
    currentUserPage = page;
    renderUsersTable(allUsers);
}

function filterUsers() {
    const searchInput = document.getElementById('userSearch');
    const search = searchInput ? searchInput.value.toLowerCase() : '';

    const roleSelect = document.getElementById('userRoleFilter');
    const roleFilter = roleSelect ? roleSelect.value : '';

    let filtered = allUsers;

    if (search) {
        filtered = filtered.filter(u =>
            (u.username && u.username.toLowerCase().includes(search)) ||
            (u.full_name && u.full_name.toLowerCase().includes(search)) ||
            (u.email && u.email.toLowerCase().includes(search)) ||
            (u.phone && u.phone.includes(search))
        );
    }

    if (roleFilter) {
        filtered = filtered.filter(u => u.role === roleFilter);
    }

    currentUserPage = 1;
    renderUsersTable(filtered);
}

function editUserRole(userId) {
    const user = allUsers.find(u => u.id === userId);
    if (!user) {
        showNotification('❌ Пользователь не найден', 'danger');
        return;
    }

    const modalHtml = `
        <div class="modal fade" id="roleModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Изменить роль пользователя</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p><strong>Пользователь:</strong> ${user.full_name || user.username}</p>
                        <div class="mb-3">
                            <label class="form-label">Роль</label>
                            <select class="form-select" id="newRole">
                                <option value="client" ${user.role === 'client' ? 'selected' : ''}>Клиент</option>
                                <option value="manager" ${user.role === 'manager' ? 'selected' : ''}>Менеджер</option>
                                <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Администратор</option>
                            </select>
                        </div>
                        <input type="hidden" id="roleUserId" value="${user.id}">
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button class="btn btn-primary" onclick="saveUserRole()">Сохранить</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    const oldModal = document.getElementById('roleModal');
    if (oldModal) oldModal.remove();

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    new bootstrap.Modal(document.getElementById('roleModal')).show();
}

async function saveUserRole() {
    const userId = document.getElementById('roleUserId').value;
    const newRole = document.getElementById('newRole').value;

    try {
        const response = await fetch(`/api/v1/users/${userId}/update-role/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                role: newRole
            })
        });

        if (!response.ok) {
            throw new Error('Ошибка обновления роли');
        }

        const result = await response.json();
        console.log('✅ Роль обновлена:', result);

        showNotification('✅ Роль пользователя обновлена!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('roleModal')).hide();
        loadUsers();

    } catch (error) {
        console.error('❌ Ошибка обновления роли:', error);
        showNotification('❌ Ошибка обновления роли: ' + error.message, 'danger');
    }
}

async function toggleUserStatus(userId) {
    const user = allUsers.find(u => u.id === userId);
    if (!user) return;

    const action = user.is_active ? 'заблокировать' : 'разблокировать';
    if (!confirm(`Вы уверены, что хотите ${action} пользователя ${user.full_name || user.username}?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/users/${userId}/toggle-status/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                is_active: !user.is_active
            })
        });

        if (!response.ok) {
            throw new Error('Ошибка изменения статуса');
        }

        const result = await response.json();
        console.log('✅ Статус обновлён:', result);

        showNotification(`✅ Пользователь ${user.is_active ? 'заблокирован' : 'разблокирован'}!`, 'success');
        loadUsers();

    } catch (error) {
        console.error('❌ Ошибка изменения статуса:', error);
        showNotification('❌ Ошибка изменения статуса: ' + error.message, 'danger');
    }
}

function viewUserOrders(userId) {
    const user = allUsers.find(u => u.id === userId);
    if (!user) return;
    window.location.href = `/profile/?user=${userId}`;
}

async function loadDashboard() {
    try {
        const orders = await getOrders();
        const today = new Date().toISOString().split('T')[0];

        const todayOrders = orders.filter(o => o.order_date && o.order_date.startsWith(today));
        const revenue = todayOrders.reduce((sum, o) => sum + parseFloat(o.total_amount), 0);
        const pending = orders.filter(o => o.status === 'new').length;

        document.getElementById('statOrders').textContent = todayOrders.length;
        document.getElementById('statRevenue').textContent = `${revenue.toFixed(0)} ₽`;
        document.getElementById('statPending').textContent = pending;

        document.getElementById('newOrdersBadge').textContent = pending;

        renderRecentOrders(orders.slice(0, 5));
        renderChart(orders);

    } catch (error) {
        console.error('Ошибка загрузки дашборда:', error);
    }
}

async function loadOrders() {
    try {
        const orders = await getOrders();
        const tbody = document.querySelector('#ordersList');
        if (!tbody) return;

        if (!orders || orders.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" class="text-center py-4">Нет заказов</td></tr>`;
            return;
        }

        tbody.innerHTML = orders.map(order => `
            <tr>
                <td><strong>#${order.order_number}</strong></td>
                <td>${order.full_name || order.user_name || '—'}</td>
                <td>${order.phone || '—'}</td>
                <td>${order.total_amount} ₽</td>
                <td><span class="badge bg-${getStatusColor(order.status)}">${getStatusText(order.status)}</span></td>
                <td>
                    <select class="form-select form-select-sm" 
                            onchange="updatePaymentStatus(${order.id}, this.value)" 
                            style="width: 150px;">
                        <option value="pending" ${order.payment_status === 'pending' ? 'selected' : ''}>⏳ Ожидает</option>
                        <option value="paid" ${order.payment_status === 'paid' ? 'selected' : ''}>✅ Оплачен</option>
                        <option value="failed" ${order.payment_status === 'failed' ? 'selected' : ''}>❌ Ошибка</option>
                        <option value="refunded" ${order.payment_status === 'refunded' ? 'selected' : ''}>🔄 Возврат</option>
                    </select>
                </td>
                <td>${order.payment_method_display || order.payment_method || '—'}</td>
                <td>${new Date(order.created_at || order.order_date).toLocaleDateString('ru-RU')}</td>
                <td>${order.persons_count || '—'} чел. / ${order.cutlery_count || '—'} приб.</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="openStatusModal(${order.id}, '${order.status}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-info" onclick="viewOrderDetail(${order.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Ошибка загрузки заказов:', error);
    }
}

async function updatePaymentStatus(orderId, newStatus) {
    try {
        const response = await fetch(`/api/v1/orders/${orderId}/update-payment-status/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({ payment_status: newStatus })
        });
        
        if (!response.ok) {
            throw new Error('Ошибка обновления статуса оплаты');
        }
        
        showNotification('✅ Статус оплаты обновлён!', 'success');
        loadOrders();
        
    } catch (error) {
        console.error('❌ Ошибка обновления статуса оплаты:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

async function loadProducts() {
    const tbody = document.getElementById('productsList');
    if (!tbody) return;

    try {
        const products = await getProducts();
        console.log('📦 Загруженные товары:', products);

        if (!products || products.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">Нет товаров</td></tr>`;
            return;
        }

        allProducts = Array.isArray(products) ? products : (products.results || []);
        console.log('📦 Всего товаров:', allProducts.length);
        renderProductsTable(allProducts);

    } catch (error) {
        console.error('❌ Ошибка загрузки товаров:', error);
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">Ошибка загрузки товаров</td></tr>`;
    }
}

// Добавьте функцию renderProductsTable():
function renderProductsTable(products) {
    const tbody = document.getElementById('productsList');
    if (!tbody) return;

    if (!products || products.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">Нет товаров</td></tr>`;
        return;
    }

    const start = (currentProductPage - 1) * productsPageSize;
    const end = start + productsPageSize;
    const pageProducts = products.slice(start, end);

    // Обновляем счётчик товаров
    const totalProductsEl = document.querySelector('#productsCount');
    if (totalProductsEl) {
        totalProductsEl.textContent = `${products.length} товаров`;
    }

    tbody.innerHTML = pageProducts.map(product => `
        <tr id="product-row-${product.id}">
            <td>
                <img src="${product.image || product.image_url || '/static/images/no-image.png'}" 
                     alt="${product.name}" 
                     style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;"
                     onclick="openUploadModal(${product.id})"
                     title="Нажмите для смены фото"
                     class="product-thumb">
            </td>
            <td><strong>${product.id}</strong></td>
            <td>${product.name}</td>
            <td>${product.category_name || '—'}</td>
            <td>${product.has_variants ? (product.min_price || '—') : (product.price || '—')} ₽</td>
            <td>${product.variants?.length || 0} шт.</td>
            <td>
                <button class="btn btn-sm btn-outline-primary me-1" onclick="openEditVariantModal(${product.id})" title="Управлять вариациями">
                    <i class="fas fa-layer-group"></i> Вариации
                </button>
                <button class="btn btn-sm btn-outline-warning me-1" onclick="editProduct(${product.id})" title="Редактировать">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteProduct(${product.id})" title="Удалить">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');

    renderProductsPagination(products.length);
}

// Добавьте функцию пагинации:
function renderProductsPagination(total) {
    const container = document.getElementById('productsPagination');
    if (!container) return;

    const totalPages = Math.ceil(total / productsPageSize);
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = `
        <li class="page-item ${currentProductPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changeProductsPage(${currentProductPage - 1})">Назад</a>
        </li>
    `;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || Math.abs(i - currentProductPage) <= 1) {
            html += `
                <li class="page-item ${i === currentProductPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="changeProductsPage(${i})">${i}</a>
                </li>
            `;
        } else if (i === currentProductPage - 2 || i === currentProductPage + 2) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }

    html += `
        <li class="page-item ${currentProductPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changeProductsPage(${currentProductPage + 1})">Вперед</a>
        </li>
    `;

    container.innerHTML = html;
}

// Добавьте функцию переключения страниц:
function changeProductsPage(page) {
    if (page < 1) return;
    const totalPages = Math.ceil(allProducts.length / productsPageSize);
    if (page > totalPages) return;
    currentProductPage = page;
    renderProductsTable(allProducts);
}

function openUploadModal(productId) {
    document.getElementById('uploadProductId').value = productId;
    document.getElementById('uploadPreview').style.display = 'none';
    document.getElementById('uploadFileInput').value = '';
    document.getElementById('uploadError').classList.add('d-none');
    document.getElementById('uploadSuccess').classList.add('d-none');

    new bootstrap.Modal(document.getElementById('uploadImageModal')).show();
}

document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('uploadFileInput');
    if (fileInput) {
        fileInput.addEventListener('change', function (e) {
            const preview = document.getElementById('uploadPreview');
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (event) {
                    preview.src = event.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
});

async function uploadProductImage() {
    const productId = document.getElementById('uploadProductId').value;
    const fileInput = document.getElementById('uploadFileInput');
    const errorEl = document.getElementById('uploadError');
    const successEl = document.getElementById('uploadSuccess');

    errorEl.classList.add('d-none');
    successEl.classList.add('d-none');

    if (!fileInput.files || fileInput.files.length === 0) {
        errorEl.textContent = '⚠️ Выберите файл для загрузки';
        errorEl.classList.remove('d-none');
        return;
    }

    const file = fileInput.files[0];

    if (file.size > 5 * 1024 * 1024) {
        errorEl.textContent = '⚠️ Размер файла не должен превышать 5 МБ';
        errorEl.classList.remove('d-none');
        return;
    }

    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    if (!allowedTypes.includes(file.type)) {
        errorEl.textContent = '⚠️ Поддерживаются только: JPEG, PNG, WebP, GIF';
        errorEl.classList.remove('d-none');
        return;
    }

    const formData = new FormData();
    formData.append('image', file);

    try {
        const response = await fetch(`/api/v1/products/${productId}/upload-image/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: formData
        });

        const result = await response.json();
        console.log('📸 Результат загрузки:', result);

        if (!response.ok) {
            throw new Error(result.error || 'Ошибка загрузки');
        }

        successEl.textContent = '✅ Фото успешно загружено!';
        successEl.classList.remove('d-none');

        setTimeout(() => {
            bootstrap.Modal.getInstance(document.getElementById('uploadImageModal')).hide();
            loadProducts();
            showNotification('✅ Фото товара обновлено!', 'success');
        }, 1000);

    } catch (error) {
        console.error('❌ Ошибка загрузки фото:', error);
        errorEl.textContent = '❌ ' + error.message;
        errorEl.classList.remove('d-none');
    }
}

async function deleteProductImage() {
    if (!confirm('Вы уверены, что хотите удалить фото товара?')) {
        return;
    }

    const productId = document.getElementById('uploadProductId').value;
    const errorEl = document.getElementById('uploadError');
    const successEl = document.getElementById('uploadSuccess');

    errorEl.classList.add('d-none');
    successEl.classList.add('d-none');

    try {
        const response = await fetch(`/api/v1/products/${productId}/delete-image/`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        const result = await response.json();
        console.log('🗑️ Результат удаления:', result);

        if (!response.ok) {
            throw new Error(result.error || 'Ошибка удаления');
        }

        successEl.textContent = '✅ Фото удалено!';
        successEl.classList.remove('d-none');

        setTimeout(() => {
            bootstrap.Modal.getInstance(document.getElementById('uploadImageModal')).hide();
            loadProducts();
            showNotification('🗑️ Фото удалено', 'success');
        }, 1000);

    } catch (error) {
        console.error('❌ Ошибка удаления фото:', error);
        errorEl.textContent = '❌ ' + error.message;
        errorEl.classList.remove('d-none');
    }
}

function editProduct(productId) {
    showEditProductModal(productId);
}

async function showEditProductModal(productId) {
    let productData = null;
    try {
        const response = await fetch(`/api/v1/products/${productId}/`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        if (!response.ok) throw new Error('Ошибка загрузки товара');
        productData = await response.json();
    } catch (error) {
        console.error('❌ Ошибка загрузки товара:', error);
        showNotification('❌ Ошибка загрузки данных товара', 'danger');
        return;
    }

    let categories = [];
    try {
        categories = await getCategories();
        console.log('📦 Загруженные категории для редактирования:', categories);
    } catch (error) {
        console.error('❌ Ошибка загрузки категорий:', error);
        categories = [];
    }

    const categoryOptions = categories.map(cat =>
        `<option value="${cat.id}" ${productData.category === cat.id ? 'selected' : ''}>${cat.name}</option>`
    ).join('');

    // ✅ Определяем, есть ли у товара вариации
    const hasVariants = productData.has_variants === true || (productData.variants && productData.variants.length > 0);

    // ✅ Если вариаций нет — берём цену и вес из productData, иначе скрываем поля
    const priceValue = !hasVariants && productData.price ? productData.price : '';
    const weightValue = !hasVariants && productData.weight ? productData.weight : '';

    const modalHtml = `
        <div class="modal fade" id="editProductModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-edit text-warning"></i> Редактировать товар #${productId}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editProductForm">
                            <input type="hidden" id="editProductId" value="${productData.id}">
                            
                            <div class="mb-3">
                                <label class="form-label">Название *</label>
                                <input type="text" class="form-control" id="editProductName" value="${productData.name}" required>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Категория</label>
                                <select class="form-select" id="editProductCategory">
                                    ${categories.length > 0 ? categoryOptions : '<option value="">Нет категорий</option>'}
                                </select>
                            </div>
                            
                            <!-- ✅ БЛОК ЦЕНЫ И ВЕСА (только если нет вариаций) -->
                            <div id="editProductPriceWeightBlock" style="${hasVariants ? 'display: none;' : ''}">
                                <div class="mb-3">
                                    <label class="form-label">Цена (₽)</label>
                                    <input type="number" class="form-control" id="editProductPrice" value="${priceValue}" step="0.01" ${!hasVariants ? 'required' : ''}>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Вес (г)</label>
                                    <input type="number" class="form-control" id="editProductWeight" value="${weightValue}">
                                </div>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Состав</label>
                                <textarea class="form-control" id="editProductIngredients" rows="2">${productData.ingredients || ''}</textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Описание</label>
                                <textarea class="form-control" id="editProductDescription" rows="2">${productData.description || ''}</textarea>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="editProductHit" ${productData.is_hit ? 'checked' : ''}>
                                <label class="form-check-label" for="editProductHit">Хит</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="editProductNew" ${productData.is_new ? 'checked' : ''}>
                                <label class="form-check-label" for="editProductNew">Новинка</label>
                            </div>
                            <div id="editProductError" class="alert alert-danger d-none mt-3"></div>
                            <div id="editProductSuccess" class="alert alert-success d-none mt-3"></div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button class="btn btn-primary" onclick="submitEditProduct()">Сохранить изменения</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    const oldModal = document.getElementById('editProductModal');
    if (oldModal) oldModal.remove();

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    new bootstrap.Modal(document.getElementById('editProductModal')).show();
}

async function submitEditProduct() {
    const productId = document.getElementById('editProductId').value;
    const name = document.getElementById('editProductName').value.trim();
    const category = document.getElementById('editProductCategory').value;
    const ingredients = document.getElementById('editProductIngredients').value;
    const description = document.getElementById('editProductDescription').value;
    const is_hit = document.getElementById('editProductHit').checked;
    const is_new = document.getElementById('editProductNew').checked;

    // ✅ УПРОЩЁННАЯ ПРОВЕРКА: видим ли блок с ценой и весом
    const priceWeightBlock = document.getElementById('editProductPriceWeightBlock');
    const isVisible = priceWeightBlock && priceWeightBlock.style.display !== 'none';

    // ✅ ЧИТАЕМ ЦЕНУ И ВЕС (только если блок виден)
    let price = null;
    let weight = 0;
    if (isVisible) {
        const priceInput = document.getElementById('editProductPrice');
        const weightInput = document.getElementById('editProductWeight');
        price = priceInput ? parseFloat(priceInput.value) || null : null;
        weight = weightInput ? parseInt(weightInput.value) || 0 : 0;
    }

    const errorEl = document.getElementById('editProductError');
    const successEl = document.getElementById('editProductSuccess');

    errorEl.classList.add('d-none');
    successEl.classList.add('d-none');

    if (!name || !category) {
        errorEl.textContent = '⚠️ Заполните название и категорию';
        errorEl.classList.remove('d-none');
        return;
    }

    try {
        const response = await fetch(`/api/v1/products/${productId}/update/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                name: name,
                category: category,
                ingredients: ingredients || '',
                description: description || '',
                is_hit: is_hit,
                is_new: is_new,
                price: price, // ✅ Если null — в базе станет NULL
                weight: weight // ✅ Если 0 — в базе станет 0
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || result.detail || 'Ошибка редактирования товара');
        }

        successEl.textContent = '✅ Товар успешно обновлён!';
        successEl.classList.remove('d-none');

        setTimeout(() => {
            bootstrap.Modal.getInstance(document.getElementById('editProductModal')).hide();
            loadProducts();
            showNotification('✅ Товар обновлён!', 'success');
        }, 1500);

    } catch (error) {
        console.error('❌ Ошибка редактирования товара:', error);
        errorEl.textContent = '❌ ' + error.message;
        errorEl.classList.remove('d-none');
    }
}

async function deleteProduct(productId) {
    if (!confirm(`Вы уверены, что хотите удалить товар #${productId}?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/products/${productId}/delete/`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        if (response.status === 204) {
            showNotification(`✅ Товар #${productId} удалён!`, 'success');
            loadProducts();
            return;
        }

        if (!response.ok) {
            let errorMessage = `Ошибка ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorData.detail || errorMessage;
            } catch (e) {}
            throw new Error(errorMessage);
        }

        const result = await response.json();
        console.log('✅ Товар удалён:', result);

        showNotification(`✅ Товар #${productId} удалён!`, 'success');
        loadProducts();

    } catch (error) {
        console.error('❌ Ошибка удаления товара:', error);
        showNotification('❌ Ошибка удаления товара: ' + error.message, 'danger');
    }
}

async function showAddProductModal() {
    let categories = [];
    try {
        categories = await getCategories();
        console.log('📦 Загруженные категории:', categories);
    } catch (error) {
        console.error('❌ Ошибка загрузки категорий:', error);
        categories = [];
    }

    const categoryOptions = categories.map(cat =>
        `<option value="${cat.id}">${cat.name}</option>`
    ).join('');

    const modalHtml = `
        <div class="modal fade" id="addProductModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-box text-primary"></i> Добавить товар</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addProductForm">
                            <div class="mb-3">
                                <label class="form-label">Название *</label>
                                <input type="text" class="form-control" id="addProductName" required>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Фото товара</label>
                                <input type="file" class="form-control" id="addProductImage" accept="image/*">
                                <div class="mt-2 text-center">
                                    <img id="addProductPreview" src="" alt="Предпросмотр" 
                                         style="max-width: 100%; max-height: 150px; border-radius: 8px; display: none;">
                                </div>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Категория</label>
                                <select class="form-select" id="addProductCategory">
                                    ${categories.length > 0 ? categoryOptions : '<option value="">Нет категорий</option>'}
                                </select>
                            </div>
                            <div class="mb-3" id="addProductPriceBlock">
    <label class="form-label">Цена *</label>
    <input type="number" class="form-control" id="addProductPrice" placeholder="500" required>
</div>
<div class="mb-3" id="addProductWeightBlock">
    <label class="form-label">Вес (г)</label>
    <input type="number" class="form-control" id="addProductWeight" placeholder="300">
</div>
                            <div class="mb-3">
                                <label class="form-label">Состав</label>
                                <textarea class="form-control" id="addProductIngredients" rows="2"></textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Описание</label>
                                <textarea class="form-control" id="addProductDescription" rows="2"></textarea>
                            </div>
                            
                            <!-- ✅ ЧЕКБОКС ДЛЯ ВАРИАЦИЙ -->
                            <div class="mb-3 form-check">
                                <input class="form-check-input" type="checkbox" id="addProductHasVariants">
                                <label class="form-check-label" for="addProductHasVariants">У товара есть вариации (размеры/цены)</label>
                            </div>
                            
                            <div id="addProductError" class="alert alert-danger d-none mt-3"></div>
                            <div id="addProductSuccess" class="alert alert-success d-none mt-3"></div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button class="btn btn-primary" onclick="submitAddProduct()">Сохранить</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    // Внутри showAddProductModal(), после создания чекбокса
    const hasVariantsCheckbox = document.getElementById('addProductHasVariants');
    if (hasVariantsCheckbox) {
        hasVariantsCheckbox.addEventListener('change', function () {
            const priceBlock = document.getElementById('addProductPriceBlock');
            const weightBlock = document.getElementById('addProductWeightBlock');
            const priceInput = document.getElementById('addProductPrice');
            const weightInput = document.getElementById('addProductWeight');

            if (this.checked) {
                // Если есть вариации — скрываем цену и вес
                priceBlock.style.display = 'none';
                weightBlock.style.display = 'none';
                priceInput.removeAttribute('required');
            } else {
                // Если нет вариаций — показываем цену и вес
                priceBlock.style.display = 'block';
                weightBlock.style.display = 'block';
                priceInput.setAttribute('required', 'required');
            }
        });
        // По умолчанию скрываем, если чекбокс отмечен
        if (hasVariantsCheckbox.checked) {
            document.getElementById('addProductPriceBlock').style.display = 'none';
            document.getElementById('addProductWeightBlock').style.display = 'none';
            document.getElementById('addProductPrice').removeAttribute('required');
        }
    }
    const oldModal = document.getElementById('addProductModal');
    if (oldModal) oldModal.remove();

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    new bootstrap.Modal(document.getElementById('addProductModal')).show();
}

async function submitAddProduct() {
    const name = document.getElementById('addProductName').value.trim();
    const category = document.getElementById('addProductCategory').value;
    const ingredients = document.getElementById('addProductIngredients').value;
    const description = document.getElementById('addProductDescription').value;
    const imageFile = document.getElementById('addProductImage').files[0];
    const hasVariants = document.getElementById('addProductHasVariants').checked;
    const price = document.getElementById('addProductPrice').value;
    const weight = document.getElementById('addProductWeight').value;

    const errorEl = document.getElementById('addProductError');
    const successEl = document.getElementById('addProductSuccess');

    errorEl.classList.add('d-none');
    successEl.classList.add('d-none');

    if (!name || !category) {
        errorEl.textContent = '⚠️ Заполните название и категорию';
        errorEl.classList.remove('d-none');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('category', category);
        formData.append('ingredients', ingredients || '');
        formData.append('description', description || '');
        formData.append('has_variants', hasVariants);

        // ✅ ЦЕНА И ВЕС ДОБАВЛЯЮТСЯ ТОЛЬКО ЕСЛИ НЕТ ВАРИАЦИЙ
        if (!hasVariants) {
            formData.append('price', price);
            formData.append('weight', weight || 0);
        }

        if (imageFile) {
            formData.append('image', imageFile);
        }

        // ... остальной код ...

        const response = await fetch('/api/v1/products/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: formData
        });

        const result = await response.json();
        console.log('📦 Результат создания товара:', result);

        if (!response.ok) {
            throw new Error(result.error || result.detail || 'Ошибка создания товара');
        }

        successEl.textContent = '✅ Товар успешно создан!';
        successEl.classList.remove('d-none');

        setTimeout(() => {
            bootstrap.Modal.getInstance(document.getElementById('addProductModal')).hide();
            loadProducts();
            showNotification('✅ Товар создан!', 'success');
        }, 1500);

    } catch (error) {
        console.error('❌ Ошибка создания товара:', error);
        errorEl.textContent = '❌ ' + error.message;
        errorEl.classList.remove('d-none');
    }
}

async function openEditVariantModal(productId) {
    let productData = null;
    try {
        const response = await fetch(`/api/v1/products/${productId}/`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        if (!response.ok) throw new Error('Ошибка загрузки вариаций');
        productData = await response.json();
    } catch (error) {
        console.error('❌ Ошибка загрузки вариаций:', error);
        showNotification('❌ Ошибка загрузки данных', 'danger');
        return;
    }

    const variants = productData.variants || [];
    const variantRows = variants.map(v => `
        <tr id="variant-row-${v.id}">
            <td>${v.id}</td>
            <td>${v.name || '—'}</td>
            <td>${v.price} ₽</td>
            <td>${v.weight || 0} г</td>
            <td>${v.is_available ? '✅' : '❌'}</td>
            <td>
                <button class="btn btn-sm btn-outline-warning me-1" onclick="editVariant(${v.id}, ${productId})" title="Редактировать">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteVariant(${v.id}, ${productId})" title="Удалить">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');

    const modalHtml = `
        <div class="modal fade" id="editVariantModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-layer-group text-info"></i> Управление вариациями товара #${productId}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="d-flex justify-content-between mb-3">
                            <h6>Товар: <strong>${productData.name}</strong></h6>
                            <button class="btn btn-success btn-sm" onclick="showAddVariantModal(${productId})">
                                <i class="fas fa-plus"></i> Добавить вариацию
                            </button>
                        </div>

                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Название (размер)</th>
                                        <th>Цена</th>
                                        <th>Вес</th>
                                        <th>Доступен</th>
                                        <th>Действия</th>
                                    </tr>
                                </thead>
                                <tbody id="variantsTableBody">
                                    ${variantRows || '<tr><td colspan="6" class="text-center">Нет вариаций</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                        
                        <div id="variantError" class="alert alert-danger d-none mt-2"></div>
                        <div id="variantSuccess" class="alert alert-success d-none mt-2"></div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    const oldModal = document.getElementById('editVariantModal');
    if (oldModal) oldModal.remove();

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    new bootstrap.Modal(document.getElementById('editVariantModal')).show();
}

function showAddVariantModal(productId) {
    const modalHtml = `
        <div class="modal fade" id="addVariantModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-plus-circle text-success"></i> Добавить вариацию</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addVariantForm">
                            <input type="hidden" id="addVariantProductId" value="${productId}">
                            <div class="mb-3">
                                <label class="form-label">Название (размер) *</label>
                                <input type="text" class="form-control" id="addVariantName" placeholder="Например: 30 см, 40 см, большой" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Цена *</label>
                                <input type="number" class="form-control" id="addVariantPrice" placeholder="500" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Вес (г)</label>
                                <input type="number" class="form-control" id="addVariantWeight" placeholder="300">
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="addVariantAvailable" checked>
                                <label class="form-check-label" for="addVariantAvailable">Доступен</label>
                            </div>
                            <div id="addVariantError" class="alert alert-danger d-none mt-2"></div>
                            <div id="addVariantSuccess" class="alert alert-success d-none mt-2"></div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button class="btn btn-primary" onclick="submitAddVariant()">Сохранить</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    const oldModal = document.getElementById('addVariantModal');
    if (oldModal) oldModal.remove();

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    new bootstrap.Modal(document.getElementById('addVariantModal')).show();
}

async function submitAddVariant() {
    const productId = document.getElementById('addVariantProductId').value;
    const name = document.getElementById('addVariantName').value.trim();
    const price = document.getElementById('addVariantPrice').value;
    const weight = document.getElementById('addVariantWeight').value;
    const is_available = document.getElementById('addVariantAvailable').checked;

    const errorEl = document.getElementById('addVariantError');
    const successEl = document.getElementById('addVariantSuccess');

    errorEl.classList.add('d-none');
    successEl.classList.add('d-none');

    if (!name || !price) {
        errorEl.textContent = '⚠️ Заполните название и цену';
        errorEl.classList.remove('d-none');
        return;
    }

    try {
        const response = await fetch(`/api/v1/products/${productId}/variants/create/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                name: name,
                price: parseFloat(price),
                weight: parseInt(weight) || 0,
                is_available: is_available
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || errorData.detail || 'Ошибка добавления вариации');
        }

        const result = await response.json();
        console.log('✅ Вариация добавлена:', result);

        successEl.textContent = '✅ Вариация успешно добавлена!';
        successEl.classList.remove('d-none');

        setTimeout(() => {
            bootstrap.Modal.getInstance(document.getElementById('addVariantModal')).hide();
            const variantModal = bootstrap.Modal.getInstance(document.getElementById('editVariantModal'));
            if (variantModal) variantModal.hide();
            setTimeout(() => {
                openEditVariantModal(productId);
                loadProducts();
                showNotification('✅ Вариация добавлена!', 'success');
            }, 300);
        }, 1500);

    } catch (error) {
        console.error('❌ Ошибка добавления вариации:', error);
        errorEl.textContent = '❌ ' + error.message;
        errorEl.classList.remove('d-none');
    }
}

async function editVariant(variantId, productId) {
    let variantData = null;
    try {
        const response = await fetch(`/api/v1/products/${productId}/`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        if (!response.ok) throw new Error('Ошибка загрузки данных');
        const product = await response.json();
        const variant = product.variants.find(v => v.id === variantId);
        if (!variant) throw new Error('Вариация не найдена');
        variantData = variant;
    } catch (error) {
        console.error('❌ Ошибка загрузки вариации:', error);
        showNotification('❌ Ошибка загрузки данных', 'danger');
        return;
    }

    const modalHtml = `
        <div class="modal fade" id="editSingleVariantModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-edit text-warning"></i> Редактировать вариацию</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editSingleVariantForm">
                            <input type="hidden" id="editSingleVariantId" value="${variantData.id}">
                            <input type="hidden" id="editSingleProductId" value="${productId}">
                            <div class="mb-3">
                                <label class="form-label">Название (размер)</label>
                                <input type="text" class="form-control" id="editSingleVariantName" value="${variantData.name || ''}">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Цена</label>
                                <input type="number" class="form-control" id="editSingleVariantPrice" value="${variantData.price}">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Вес (г)</label>
                                <input type="number" class="form-control" id="editSingleVariantWeight" value="${variantData.weight || 0}">
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="editSingleVariantAvailable" ${variantData.is_available ? 'checked' : ''}>
                                <label class="form-check-label" for="editSingleVariantAvailable">Доступен</label>
                            </div>
                            <div id="editSingleVariantError" class="alert alert-danger d-none mt-2"></div>
                            <div id="editSingleVariantSuccess" class="alert alert-success d-none mt-2"></div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button class="btn btn-primary" onclick="submitEditSingleVariant()">Сохранить</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    const oldModal = document.getElementById('editSingleVariantModal');
    if (oldModal) oldModal.remove();

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    new bootstrap.Modal(document.getElementById('editSingleVariantModal')).show();
}

async function submitEditSingleVariant() {
    const variantId = document.getElementById('editSingleVariantId').value;
    const productId = document.getElementById('editSingleProductId').value;
    const name = document.getElementById('editSingleVariantName').value.trim();
    const price = document.getElementById('editSingleVariantPrice').value;
    const weight = document.getElementById('editSingleVariantWeight').value;
    const is_available = document.getElementById('editSingleVariantAvailable').checked;

    const errorEl = document.getElementById('editSingleVariantError');
    const successEl = document.getElementById('editSingleVariantSuccess');

    errorEl.classList.add('d-none');
    successEl.classList.add('d-none');

    if (!price) {
        errorEl.textContent = '⚠️ Укажите цену';
        errorEl.classList.remove('d-none');
        return;
    }

    try {
        // Сначала удаляем старую вариацию
        const deleteResponse = await fetch(`/api/v1/products/${productId}/variants/delete/${variantId}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        if (!deleteResponse.ok) {
            throw new Error('Ошибка удаления старой вариации');
        }

        // Затем создаём новую с обновлёнными данными
        const createResponse = await fetch(`/api/v1/products/${productId}/variants/create/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                name: name || 'Стандарт',
                price: parseFloat(price),
                weight: parseInt(weight) || 0,
                is_available: is_available
            })
        });

        if (!createResponse.ok) {
            const errorData = await createResponse.json();
            throw new Error(errorData.error || errorData.detail || 'Ошибка обновления вариации');
        }

        const result = await createResponse.json();
        console.log('✅ Вариация обновлена:', result);

        successEl.textContent = '✅ Вариация успешно обновлена!';
        successEl.classList.remove('d-none');

        setTimeout(() => {
            bootstrap.Modal.getInstance(document.getElementById('editSingleVariantModal')).hide();
            const variantModal = bootstrap.Modal.getInstance(document.getElementById('editVariantModal'));
            if (variantModal) variantModal.hide();
            setTimeout(() => {
                openEditVariantModal(productId);
                loadProducts();
                showNotification('✅ Вариация обновлена!', 'success');
            }, 300);
        }, 1500);

    } catch (error) {
        console.error('❌ Ошибка редактирования вариации:', error);
        errorEl.textContent = '❌ ' + error.message;
        errorEl.classList.remove('d-none');
    }
}

async function deleteVariant(variantId, productId) {
    if (!confirm('Вы уверены, что хотите удалить эту вариацию?')) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/products/${productId}/variants/delete/${variantId}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || errorData.detail || 'Ошибка удаления вариации');
        }

        showNotification('✅ Вариация удалена!', 'success');

        const variantModal = bootstrap.Modal.getInstance(document.getElementById('editVariantModal'));
        if (variantModal) variantModal.hide();
        setTimeout(() => {
            openEditVariantModal(productId);
            loadProducts();
        }, 300);

    } catch (error) {
        console.error('❌ Ошибка удаления вариации:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

function saveSettings() {
    const notifTelegram = document.getElementById('notifTelegram').checked;
    const notifEmail = document.getElementById('notifEmail').checked;
    const paymentMode = document.getElementById('paymentMode').value;

    console.log('✅ Настройки сохранены:', {
        notifTelegram,
        notifEmail,
        paymentMode
    });
    showNotification('✅ Настройки сохранены!', 'success');
}

function showAddUserModal() {
    const modalHtml = `
        <div class="modal fade" id="addUserModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-user-plus text-primary"></i> Добавить пользователя</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addUserForm">
                            <div class="mb-3">
                                <label class="form-label">Имя пользователя *</label>
                                <input type="text" class="form-control" id="addUsername" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Email *</label>
                                <input type="email" class="form-control" id="addEmail" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Телефон</label>
                                <input type="tel" class="form-control" id="addPhone">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Полное имя</label>
                                <input type="text" class="form-control" id="addFullName">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Пароль *</label>
                                <input type="password" class="form-control" id="addPassword" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Подтверждение пароля *</label>
                                <input type="password" class="form-control" id="addPassword2" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Роль</label>
                                <select class="form-select" id="addUserRole">
                                    <option value="client">Клиент</option>
                                    <option value="manager">Менеджер</option>
                                    <option value="admin">Администратор</option>
                                </select>
                            </div>
                            <div id="addUserError" class="alert alert-danger d-none"></div>
                            <div id="addUserSuccess" class="alert alert-success d-none"></div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button class="btn btn-primary" onclick="submitAddUser()">Создать</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    const oldModal = document.getElementById('addUserModal');
    if (oldModal) oldModal.remove();

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    new bootstrap.Modal(document.getElementById('addUserModal')).show();
}

async function submitAddUser() {
    const username = document.getElementById('addUsername').value.trim();
    const email = document.getElementById('addEmail').value.trim();
    const phone = document.getElementById('addPhone').value.trim();
    const full_name = document.getElementById('addFullName').value.trim();
    const password = document.getElementById('addPassword').value;
    const password2 = document.getElementById('addPassword2').value;
    const role = document.getElementById('addUserRole').value;

    const errorEl = document.getElementById('addUserError');
    const successEl = document.getElementById('addUserSuccess');

    errorEl.classList.add('d-none');
    successEl.classList.add('d-none');

    if (!username || !email || !password || !password2) {
        errorEl.textContent = '⚠️ Заполните все обязательные поля';
        errorEl.classList.remove('d-none');
        return;
    }

    if (password.length < 8) {
        errorEl.textContent = '⚠️ Пароль должен содержать минимум 8 символов';
        errorEl.classList.remove('d-none');
        return;
    }

    if (password !== password2) {
        errorEl.textContent = '⚠️ Пароли не совпадают';
        errorEl.classList.remove('d-none');
        return;
    }

    try {
        const response = await fetch('/api/v1/users/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                username,
                email,
                phone,
                full_name,
                password,
                password2,
                role
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || result.error || 'Ошибка создания пользователя');
        }

        successEl.textContent = '✅ Пользователь успешно создан!';
        successEl.classList.remove('d-none');

        setTimeout(() => {
            bootstrap.Modal.getInstance(document.getElementById('addUserModal')).hide();
            loadUsers();
            showNotification('✅ Пользователь создан!', 'success');
        }, 1500);

    } catch (error) {
        console.error('❌ Ошибка создания пользователя:', error);
        errorEl.textContent = '❌ ' + error.message;
        errorEl.classList.remove('d-none');
    }
}

function renderRecentOrders(orders) {
    const container = document.getElementById('recentOrdersList');
    if (!container) return;

    if (!orders || orders.length === 0) {
        container.innerHTML = `<p class="text-muted text-center py-3">Нет заказов</p>`;
        return;
    }

    container.innerHTML = orders.map(order => `
        <div class="order-item d-flex justify-content-between align-items-center py-2 border-bottom">
            <div>
                <strong>#${order.order_number}</strong>
                <span class="text-muted ms-2">${order.user_name || order.user}</span>
            </div>
            <div>
                <span class="badge bg-${getStatusColor(order.status)} me-2">${getStatusText(order.status)}</span>
                <span class="fw-bold">${order.total_amount} ₽</span>
            </div>
        </div>
    `).join('');
}

let chartInstance = null;

function renderChart(orders) {
    const ctx = document.getElementById('salesChart');
    if (!ctx) return;

    const days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    const today = new Date();
    const weekData = [];

    for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split('T')[0];
        const dayOrders = orders.filter(o => o.order_date && o.order_date.startsWith(dateStr));
        const total = dayOrders.reduce((sum, o) => sum + parseFloat(o.total_amount), 0);
        weekData.push(total);
    }

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: days,
            datasets: [{
                label: 'Выручка (₽)',
                data: weekData,
                backgroundColor: '#FF6B35',
                borderRadius: 8,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: value => value + ' ₽'
                    }
                }
            }
        }
    });
}

function getStatusText(status) {
    const map = {
        'new': 'Новый',
        'confirmed': 'Подтверждён',
        'cooking': 'Готовится',
        'ready': 'Готов',
        'delivering': 'В доставке',
        'delivered': 'Доставлен',
        'cancelled': 'Отменён'
    };
    return map[status] || status;
}

function getStatusColor(status) {
    const map = {
        'new': 'primary',
        'confirmed': 'info',
        'cooking': 'warning',
        'ready': 'success',
        'delivering': 'primary',
        'delivered': 'success',
        'cancelled': 'danger'
    };
    return map[status] || 'secondary';
}

function openStatusModal(orderId, currentStatus) {
    document.getElementById('editOrderId').value = orderId;
    document.getElementById('editOrderStatus').value = currentStatus;
    new bootstrap.Modal(document.getElementById('statusModal')).show();
}

async function updateOrderStatus() {
    const orderId = document.getElementById('editOrderId').value;
    const status = document.getElementById('editOrderStatus').value;

    if (!orderId || !status) {
        showNotification('⚠️ Выберите статус', 'warning');
        return;
    }

    try {
        const response = await fetch(`/api/v1/orders/${orderId}/update-status/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                status: status
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || errorData.detail || 'Ошибка обновления статуса');
        }

        showNotification('✅ Статус заказа обновлён!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('statusModal')).hide();
        loadOrders();
        loadDashboard();

    } catch (error) {
        console.error('❌ Ошибка обновления статуса:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}



function viewOrderDetail(orderId) {
    window.location.href = `/order/${orderId}/`;
}

function refreshData() {
    loadDashboard();
    loadOrders();
    loadUsers();
    showNotification('🔄 Данные обновлены', 'info');
}

function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/';
    }
}

function addLunchItem(name = '', price = '') {
    const container = document.getElementById('lunchItemsContainer');
    const itemDiv = document.createElement('div');
    itemDiv.className = 'lunch-item-form row g-2 mb-2';
    itemDiv.innerHTML = `
        <div class="col-md-4">
            <input type="text" class="form-control" placeholder="Название блюда" value="${name}">
        </div>
        <div class="col-md-2">
            <input type="number" class="form-control" placeholder="Цена" value="${price}">
        </div>
        <div class="col-md-3">
            <input type="hidden" class="form-control lunch-product-id" value="">
            <span class="text-muted small">ID будет найден автоматически</span>
        </div>
        <div class="col-md-3">
            <button class="btn btn-danger btn-sm" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-trash"></i> Удалить
            </button>
        </div>
    `;
    container.appendChild(itemDiv);
}

function loadLunchItems(items) {
    const container = document.getElementById('lunchItemsContainer');
    container.innerHTML = '';
    
    if (items && items.length > 0) {
        // ✅ Убираем product_id, чтобы не передавать его в addLunchItem
        items.forEach(item => addLunchItem(item.name, item.price));
    } else {
        addLunchItem(); // Добавляем пустое поле, если меню пустое
    }
}

function getLunchItems() {
    const items = [];
    const itemForms = document.querySelectorAll('.lunch-item-form');
    
    itemForms.forEach(form => {
        const inputs = form.querySelectorAll('input');
        const name = inputs[0].value.trim();
        const price = inputs[1].value.trim();
        
        if (name && price) {
            items.push({
                name: name,
                price: parseFloat(price),
                product_id: null // ✅ Не передаём product_id
            });
        }
    });
    
    return items;
}

// ✅ ПРАВИЛЬНАЯ ВЕРСИЯ
async function saveLunchMenu() {
    const items = [];
    const itemForms = document.querySelectorAll('.lunch-item-form');
    
    itemForms.forEach(form => {
        const inputs = form.querySelectorAll('input');
        const name = inputs[0].value.trim();
        const price = inputs[1].value.trim();
        
        if (name && price) {
            items.push({
                name: name,
                price: parseFloat(price),
                // ✅ НЕ ПЕРЕДАЁМ product_id — СЕРВЕР НАЙДЁТ ЕГО САМ
                product_id: null
            });
        }
    });
    
    const data = {
        title: document.getElementById('lunchTitle').value.trim(),
        items: items
    };
    
    try {
        const response = await fetch('/api/v1/products/lunch-menu/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error('Ошибка сохранения меню');
        }
        
        showNotification('✅ Меню бизнес-ланча сохранено!', 'success');
        
    } catch (error) {
        console.error('❌ Ошибка сохранения меню:', error);
        showNotification('❌ Ошибка: ' + error.message, 'danger');
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/v1/core/settings/', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        if (!response.ok) {
            throw new Error('Ошибка загрузки настроек');
        }

        const settings = await response.json();
        console.log('⚙️ Настройки загружены:', settings);

        // ===== ЗАГРУЗКА МЕНЮ БИЗНЕС-ЛАНЧА =====
        const lunchMenu = await fetch('/api/v1/products/lunch-menu/', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        }).then(r => r.json());

        // ✅ Проверяем, что элемент существует
        const lunchTitle = document.getElementById('lunchTitle');
        if (lunchTitle) {
            lunchTitle.value = lunchMenu.title || 'Бизнес-ланч';
        }

        // ✅ Проверяем, что контейнер существует
        const lunchItemsContainer = document.getElementById('lunchItemsContainer');
        if (lunchItemsContainer) {
            loadLunchItems(lunchMenu.items || []);
        }

        // ✅ ИСПРАВЛЕНИЕ: Проверяем каждый элемент перед доступом
        const bannerEnabled = document.getElementById('bannerEnabled');
        if (bannerEnabled) bannerEnabled.checked = settings.banner_enabled;
        
        const bannerTitle = document.getElementById('bannerTitle');
        if (bannerTitle) bannerTitle.value = settings.banner_title || '';
        
        const bannerSubtitle = document.getElementById('bannerSubtitle');
        if (bannerSubtitle) bannerSubtitle.value = settings.banner_subtitle || '';
        
        const bannerButtonText = document.getElementById('bannerButtonText');
        if (bannerButtonText) bannerButtonText.value = settings.banner_button_text || '';
        
        const bannerImageUrl = document.getElementById('bannerImageUrl');
        if (bannerImageUrl) bannerImageUrl.value = settings.banner_image_url || '';
        
        const bannerLink = document.getElementById('bannerLink');
        if (bannerLink) bannerLink.value = settings.banner_link || '';

        const deliveryFreeThreshold = document.getElementById('deliveryFreeThreshold');
        if (deliveryFreeThreshold) deliveryFreeThreshold.value = settings.delivery_free_threshold || 800;
        
        const deliveryBaseCost = document.getElementById('deliveryBaseCost');
        if (deliveryBaseCost) deliveryBaseCost.value = settings.delivery_base_cost || 150;

        const bonusEnabled = document.getElementById('bonusEnabled');
        if (bonusEnabled) bonusEnabled.checked = settings.bonus_enabled;
        
        const bonusRate = document.getElementById('bonusRate');
        if (bonusRate) bonusRate.value = settings.bonus_rate || 5;
        
        const bonusMinOrder = document.getElementById('bonusMinOrder');
        if (bonusMinOrder) bonusMinOrder.value = settings.bonus_min_order || 300;
        
        const bonusMaxPercent = document.getElementById('bonusMaxPercent');
        if (bonusMaxPercent) bonusMaxPercent.value = settings.bonus_max_percent || 30;

        const notificationsEnabled = document.getElementById('notificationsEnabled');
        if (notificationsEnabled) notificationsEnabled.checked = settings.notifications_enabled;
        
        const notificationEmail = document.getElementById('notificationEmail');
        if (notificationEmail) notificationEmail.value = settings.notification_email || '';
        
        const notificationOrderSubject = document.getElementById('notificationOrderSubject');
        if (notificationOrderSubject) notificationOrderSubject.value = settings.notification_order_subject || '';

        const siteName = document.getElementById('siteName');
        if (siteName) siteName.value = settings.site_name || '';
        
        const contactPhone = document.getElementById('contactPhone');
        if (contactPhone) contactPhone.value = settings.contact_phone || '';
        
        const contactEmail = document.getElementById('contactEmail');
        if (contactEmail) contactEmail.value = settings.contact_email || '';
        
        const contactAddress = document.getElementById('contactAddress');
        if (contactAddress) contactAddress.value = settings.contact_address || '';
        
        const workingHours = document.getElementById('workingHours');
        if (workingHours) workingHours.value = settings.working_hours || '';

    } catch (error) {
        console.error('❌ Ошибка загрузки настроек:', error);
        showNotification('❌ Ошибка загрузки настроек', 'danger');
    }
}

async function saveAllSettings() {
    const errorEl = document.getElementById('settingsError');
    const successEl = document.getElementById('settingsSuccess');

    errorEl.classList.add('d-none');
    successEl.classList.add('d-none');

    // ✅ ИСПРАВЛЕННЫЙ БЛОК ДАННЫХ - все поля проверены
    const data = {
        banner_enabled: document.getElementById('bannerEnabled')?.checked || false,
        banner_title: document.getElementById('bannerTitle')?.value.trim() || '',
        banner_subtitle: document.getElementById('bannerSubtitle')?.value.trim() || '',
        banner_button_text: document.getElementById('bannerButtonText')?.value.trim() || '',
        banner_image_url: document.getElementById('bannerImageUrl')?.value.trim() || '',
        banner_link: document.getElementById('bannerLink')?.value.trim() || '',
        
        delivery_free_threshold: parseInt(document.getElementById('deliveryFreeThreshold')?.value) || 800,
        delivery_base_cost: parseInt(document.getElementById('deliveryBaseCost')?.value) || 150,
        
        bonus_enabled: document.getElementById('bonusEnabled')?.checked || false,
        bonus_rate: document.getElementById('bonusRate')?.value || '5.00',  // ✅ СТРОКА!
        bonus_min_order: parseInt(document.getElementById('bonusMinOrder')?.value) || 300,
        bonus_max_percent: parseInt(document.getElementById('bonusMaxPercent')?.value) || 30,
        
        notifications_enabled: document.getElementById('notificationsEnabled')?.checked || false,
        notification_email: document.getElementById('notificationEmail')?.value.trim() || '',
        notification_order_subject: document.getElementById('notificationOrderSubject')?.value.trim() || '',
        
        site_name: document.getElementById('siteName')?.value.trim() || '',
        contact_phone: document.getElementById('contactPhone')?.value.trim() || '',
        contact_email: document.getElementById('contactEmail')?.value.trim() || '',
        contact_address: document.getElementById('contactAddress')?.value.trim() || '',
        working_hours: document.getElementById('workingHours')?.value.trim() || '',
    };

    try {
        const response = await fetch('/api/v1/core/settings/', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            // ✅ ВЫВОДИМ ТЕКСТ ОШИБКИ ОТ DJANGO
            console.error('❌ Ошибка от Django:', result);
            throw new Error(result.error || result.detail || JSON.stringify(result) || 'Ошибка сохранения настроек');
        }

        console.log('✅ Настройки сохранены:', result);

        successEl.textContent = '✅ Все настройки успешно сохранены!';
        successEl.classList.remove('d-none');

        showNotification('✅ Настройки сохранены!', 'success');

        if (document.querySelector('[data-tab="dashboard"]')) {
            loadDashboard();
        }

    } catch (error) {
        console.error('❌ Ошибка сохранения настроек:', error);
        errorEl.textContent = '❌ ' + error.message;
        errorEl.classList.remove('d-none');
        showNotification('❌ Ошибка сохранения настроек', 'danger');
    }
}

async function applySettingsToFrontend() {
    try {
        const response = await fetch('/api/v1/core/settings/public/');
        const settings = await response.json();

        console.log('📢 Применяем настройки на главную:', settings);

        const banner = document.querySelector('.banner');
        const bannerTitle = document.querySelector('.banner-title');
        const bannerSubtitle = document.querySelector('.banner-subtitle');
        const bannerBtn = document.querySelector('.btn-order');
        const bannerImg = document.querySelector('.banner-img');

        if (banner) {
            banner.style.display = settings.banner_enabled ? 'block' : 'none';
        }
        if (bannerTitle) {
            bannerTitle.textContent = settings.banner_title || 'Скидка 20% на первый заказ';
        }
        if (bannerSubtitle) {
            bannerSubtitle.textContent = settings.banner_subtitle || 'При заказе от 800 ₽ — доставка бесплатно';
        }
        if (bannerBtn) {
            bannerBtn.textContent = settings.banner_button_text || 'Заказать';
            if (settings.banner_link) {
                bannerBtn.href = settings.banner_link;
            }
        }
        if (bannerImg && settings.banner_image_url) {
            bannerImg.src = settings.banner_image_url;
        }

    } catch (error) {
        console.error('❌ Ошибка применения настроек:', error);
    }
}

let lastOrderCount = 0;
let notificationCheckInterval = null;

function startOrderNotifications() {
    notificationCheckInterval = setInterval(checkNewOrders, 30000);
}

async function checkNewOrders() {
    try {
        const orders = await getOrders();
        const newOrders = orders.filter(o => o.status === 'new');

        if (newOrders.length > lastOrderCount && lastOrderCount > 0) {
            const count = newOrders.length - lastOrderCount;
            showNewOrderModal(count, newOrders.slice(0, 3));
            playNotificationSound();
        }

        lastOrderCount = newOrders.length;
        document.getElementById('newOrdersBadge').textContent = newOrders.length;

    } catch (error) {
        console.error('❌ Ошибка проверки новых заказов:', error);
    }
}

function showNewOrderModal(count, orders) {
    const oldModal = document.getElementById('newOrderModal');
    if (oldModal) oldModal.remove();

    const modalHtml = `
        <div class="modal fade" id="newOrderModal" tabindex="-1" data-bs-backdrop="static">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header" style="background: #FF6B35; color: white;">
                        <h5 class="modal-title">
                            <i class="fas fa-bell"></i> Новый заказ!
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-3">
                            <i class="fas fa-shopping-cart fa-3x text-primary"></i>
                            <h3 class="mt-2">Поступил${count > 1 ? 'о' : ''} ${count} новый${count > 1 ? 'х' : ''} заказ${count > 1 ? 'ов' : ''}!</h3>
                        </div>
                        ${orders.length > 0 ? `
                            <div class="new-orders-list">
                                <h6>Последние заказы:</h6>
                                ${orders.map(order => `
                                    <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                                        <div>
                                            <strong>#${order.order_number || order.id}</strong>
                                            <span class="text-muted ms-2">${order.user_name || order.user || 'Клиент'}</span>
                                        </div>
                                        <div>
                                            <span class="fw-bold">${order.total_amount} ₽</span>
                                            <button class="btn btn-sm btn-outline-primary ms-2" onclick="viewOrderDetail(${order.id})">
                                                <i class="fas fa-eye"></i>
                                            </button>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                        <div class="mt-3 text-center">
                            <button class="btn btn-primary" onclick="closeNewOrderModalAndGoToOrders()">
                                <i class="fas fa-list"></i> Перейти к заказам
                            </button>
                            <button class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times"></i> Закрыть
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    new bootstrap.Modal(document.getElementById('newOrderModal')).show();
}

function closeNewOrderModalAndGoToOrders() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('newOrderModal'));
    if (modal) modal.hide();

    const ordersTab = document.querySelector('.nav-link[data-tab="orders"]');
    if (ordersTab) ordersTab.click();
}

function playNotificationSound() {
    try {
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = 0.5;
        audio.play().catch(() => {});
    } catch (e) {
        console.log('⚠️ Звук уведомления недоступен');
    }
}

let currentViewedUserId = null;

async function viewUserOrders(userId) {
    const user = allUsers.find(u => u.id === userId);
    if (!user) return;
    window.location.href = `/profile/?user=${userId}`;
}

function closeUserOrders() {
    document.getElementById('userOrdersContainer').style.display = 'none';
    currentViewedUserId = null;
}

async function loadUserOrders(userId) {
    const tbody = document.getElementById('userOrdersList');
    if (!tbody) return;

    try {
        const response = await fetch('/api/v1/orders/list/', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        if (!response.ok) {
            throw new Error('Ошибка загрузки заказов');
        }

        let orders = await response.json();
        orders = Array.isArray(orders) ? orders : (orders.results || []);

        const userOrders = orders.filter(o => o.user === userId);
        console.log(`📦 Заказы пользователя ${userId}:`, userOrders);

        if (!userOrders || userOrders.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-4">
                        <p class="text-muted">У пользователя пока нет заказов</p>
                    </td>
                </tr>
            `;
            return;
        }

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

        tbody.innerHTML = userOrders.map(order => `
            <tr>
                <td><strong>#${order.order_number || order.id}</strong></td>
                <td>${order.order_date ? new Date(order.order_date).toLocaleDateString('ru-RU') : '—'}</td>
                <td>${order.total_amount} ₽</td>
                <td>
                    <span class="badge bg-${statusColorMap[order.status] || 'secondary'}">
                        ${statusMap[order.status] || order.status}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewOrderDetail(${order.id})">
                        <i class="fas fa-eye"></i> Подробнее
                    </button>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('❌ Ошибка загрузки заказов пользователя:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4">
                    <p class="text-danger">Ошибка загрузки заказов</p>
                </td>
            </tr>
        `;
    }
}

function viewOrderDetail(orderId) {
    window.location.href = `/order/${orderId}/`;
}

window.loadDashboard = loadDashboard;
window.loadOrders = loadOrders;
window.loadProducts = loadProducts;
window.loadUsers = loadUsers;
window.filterUsers = filterUsers;
window.changeUsersPage = changeUsersPage;
window.editUserRole = editUserRole;
window.saveUserRole = saveUserRole;
window.toggleUserStatus = toggleUserStatus;
window.viewUserOrders = viewUserOrders;
window.openStatusModal = openStatusModal;
window.updateOrderStatus = updateOrderStatus;
window.viewOrderDetail = viewOrderDetail;
window.refreshData = refreshData;
window.showAddProductModal = showAddProductModal;
window.submitAddProduct = submitAddProduct;
window.editProduct = editProduct;
window.deleteProduct = deleteProduct;
window.showAddUserModal = showAddUserModal;
window.submitAddUser = submitAddUser;
window.saveSettings = saveSettings;
window.logout = logout;
window.loadSettings = loadSettings;
window.saveAllSettings = saveAllSettings;
window.applySettingsToFrontend = applySettingsToFrontend;
window.openUploadModal = openUploadModal;
window.uploadProductImage = uploadProductImage;
window.deleteProductImage = deleteProductImage;
window.showEditProductModal = showEditProductModal;
window.submitEditProduct = submitEditProduct;
window.openEditVariantModal = openEditVariantModal;
window.showAddVariantModal = showAddVariantModal;
window.submitAddVariant = submitAddVariant;
window.editVariant = editVariant;
window.submitEditSingleVariant = submitEditSingleVariant;
window.deleteVariant = deleteVariant;
window.changeProductsPage = changeProductsPage;
window.updatePaymentStatus = updatePaymentStatus;
window.addLunchItem = addLunchItem;
window.saveLunchMenu = saveLunchMenu;
window.loadLunchItems = loadLunchItems;

console.log('✅ admin.js загружен!');
