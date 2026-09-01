// frontend/static/js/auth.js

document.addEventListener('DOMContentLoaded', function() {
    updateAuthUI();
    
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }

    // ✅ ПЕРЕКЛЮЧЕНИЕ ФОРМ (ГЛАВНАЯ ЛОГИКА)
    const showRegister = document.getElementById('showRegister');
    const showLogin = document.getElementById('showLogin');
    const modalTitle = document.getElementById('authModalTitle');

    if (showRegister) {
        showRegister.addEventListener('click', function() {
            loginForm.style.display = 'none';
            registerForm.style.display = 'block';
            if (modalTitle) modalTitle.textContent = 'Регистрация';
            document.getElementById('authError').classList.add('d-none');
            document.getElementById('authSuccess').classList.add('d-none');
        });
    }

    if (showLogin) {
        showLogin.addEventListener('click', function() {
            registerForm.style.display = 'none';
            loginForm.style.display = 'block';
            if (modalTitle) modalTitle.textContent = 'Вход';
            document.getElementById('authError').classList.add('d-none');
            document.getElementById('authSuccess').classList.add('d-none');
        });
    }

    // ✅ ПРИ ЗАГРУЗКЕ ВСЕГДА ПОКАЗЫВАЕМ ФОРМУ ВХОДА
    if (loginForm) loginForm.style.display = 'block';
    if (registerForm) registerForm.style.display = 'none';

    // ✅ Если ссылки для переключения не найдены — создаём их автоматически
    if (!showRegister && loginForm) {
        const loginToggle = document.createElement('p');
        loginToggle.className = 'text-center mt-3 small';
        loginToggle.innerHTML = 'Нет аккаунта? <span class="toggle-link" id="showRegister" style="color: #FF6B35; cursor: pointer;">Зарегистрироваться</span>';
        loginForm.appendChild(loginToggle);
        document.getElementById('showRegister').addEventListener('click', function() {
            loginForm.style.display = 'none';
            registerForm.style.display = 'block';
            if (modalTitle) modalTitle.textContent = 'Регистрация';
        });
    }

    if (!showLogin && registerForm) {
        const registerToggle = document.createElement('p');
        registerToggle.className = 'text-center mt-3 small';
        registerToggle.innerHTML = 'Уже есть аккаунт? <span class="toggle-link" id="showLogin" style="color: #FF6B35; cursor: pointer;">Войти</span>';
        registerForm.appendChild(registerToggle);
        document.getElementById('showLogin').addEventListener('click', function() {
            registerForm.style.display = 'none';
            loginForm.style.display = 'block';
            if (modalTitle) modalTitle.textContent = 'Вход';
        });
    }
});

// ===== ОБНОВЛЕНИЕ UI ПОСЛЕ ВХОДА =====
function updateAuthUI() {
    const token = localStorage.getItem('access_token');
    const authText = document.getElementById('authText');
    const authBtn = document.getElementById('authBtn');
    
    // ✅ Удаляем старую кнопку "Админ", если есть
    const oldAdminLink = document.querySelector('.admin-link');
    if (oldAdminLink) oldAdminLink.remove();
    
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
                authBtn.onclick = function(e) {
                    e.preventDefault();
                    // ✅ Если админ — в админку, иначе в профиль
                    if (user.role === 'admin') {
                        window.location.href = '/admin-panel/';
                    } else {
                        window.location.href = '/profile/';
                    }
                };
            }
            
            // ✅ Если пользователь админ — показываем ссылку на админку
            if (user.role === 'admin') {
                const adminLink = document.createElement('a');
                adminLink.href = '/admin-panel/';
                adminLink.className = 'btn btn-outline-danger ms-2 admin-link';
                adminLink.innerHTML = '<i class="fas fa-shield-alt"></i> Админ';
                adminLink.style.fontSize = '14px';
                adminLink.style.padding = '6px 12px';
                
                const headerActions = document.querySelector('.header-actions');
                if (headerActions && !document.querySelector('.admin-link')) {
                    headerActions.appendChild(adminLink);
                }
            }
            
            // ✅ Сохраняем пользователя глобально
            window.currentUser = user;
            
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

// ✅ Маска телефона
function formatPhone(input) {
    let value = input.value.replace(/\D/g, '');
    if (value.startsWith('8')) {
        value = '7' + value.slice(1);
    }
    if (!value.startsWith('7')) {
        value = '7' + value;
    }
    
    let formatted = '+7';
    if (value.length > 1) formatted += ' (' + value.slice(1, 4);
    if (value.length >= 4) formatted += ') ' + value.slice(4, 7);
    if (value.length >= 7) formatted += '-' + value.slice(7, 9);
    if (value.length >= 9) formatted += '-' + value.slice(9, 11);
    
    input.value = formatted;
}

// ✅ Инициализация маски телефона
document.addEventListener('DOMContentLoaded', function() {
    const loginPhoneInput = document.getElementById('loginPhone');
    if (loginPhoneInput) {
        loginPhoneInput.addEventListener('input', function() {
            formatPhone(this);
        });
    }
    
    const regPhoneInput = document.getElementById('regPhone');
    if (regPhoneInput) {
        regPhoneInput.addEventListener('input', function() {
            formatPhone(this);
        });
    }
});

// ===== ВХОД =====
async function handleLogin(e) {
    e.preventDefault();
    
    const phone = document.getElementById('loginPhone').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    const errorEl = document.getElementById('authError');
    const successEl = document.getElementById('authSuccess');
    const btn = document.getElementById('loginBtn');
    const btnText = document.getElementById('loginBtnText');
    const spinner = document.getElementById('loginSpinner');
    
    errorEl.classList.add('d-none');
    successEl.classList.add('d-none');
    
    if (!phone || !password) {
        showAuthError('Заполните все поля');
        return;
    }
    
    // ✅ Валидация телефона
    const phoneRegex = /^\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$/;
    if (!phoneRegex.test(phone)) {
        showAuthError('⚠️ Введите телефон в формате +7 (999) 123-45-67');
        return;
    }
    
    btn.disabled = true;
    btnText.textContent = 'Вход...';
    spinner.classList.remove('d-none');
    
    try {
        // ✅ Вместо username передаём phone
        const result = await login({ username: phone, password });
        console.log('✅ Вход выполнен:', result);
        
        // ✅ ПЕРЕНОСИМ ГОСТЕВУЮ КОРЗИНУ
        if (typeof mergeCart === 'function') {
            console.log('🔄 Перенос гостевой корзины...');
            await mergeCart();
        }
        
        showAuthSuccess('✅ Вход выполнен успешно!');
        
        updateAuthUI();
        
        // ✅ ПОЛУЧАЕМ ПРОФИЛЬ ДЛЯ ПРОВЕРКИ РОЛИ
        try {
            const user = await getProfile();
            console.log('👤 Пользователь:', user);
            window.currentUser = user;
            
            // ✅ ОБНОВЛЯЕМ ДАННЫЕ КОРЗИНЫ
            const newCart = await getCart();
            window.cartData = newCart;
            console.log('🛒 Данные корзины обновлены:', newCart);
            
            // ✅ ОБНОВЛЯЕМ СЧЁТЧИК
            if (typeof updateCartBadgeFromCache === 'function') {
                updateCartBadgeFromCache();
            }
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('authModal'));
            if (modal) modal.hide();
            
            // ✅ ПРОВЕРЯЕМ РОЛЬ И ПЕРЕНАПРАВЛЯЕМ
            if (user.role === 'admin') {
                console.log('👑 Администратор! Перенаправляем в админ-панель');
                showNotification('👑 Добро пожаловать в админ-панель!', 'success');
                setTimeout(() => {
                    window.location.href = '/admin-panel/';
                }, 500);
            } else {
                setTimeout(() => {
                    window.location.href = '/profile/';
                }, 500);
            }
            
        } catch (e) {
            console.warn('⚠️ Не удалось получить профиль после входа');
            setTimeout(() => {
                window.location.href = '/profile/';
            }, 500);
        }
        
    } catch (error) {
        console.error('❌ Ошибка входа:', error);
        showAuthError(error.message || 'Неверный телефон или пароль');
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Войти';
        spinner.classList.add('d-none');
    }
}

// ===== РЕГИСТРАЦИЯ =====
async function handleRegister(e) {
    e.preventDefault();
    
    const phone = document.getElementById('regPhone').value.trim();
    const full_name = document.getElementById('regFullName').value.trim();
    const password = document.getElementById('regPassword').value;
    const password2 = document.getElementById('regPassword2').value;
    const errorEl = document.getElementById('authError');
    const successEl = document.getElementById('authSuccess');
    const btn = document.getElementById('registerBtn');
    const btnText = document.getElementById('registerBtnText');
    const spinner = document.getElementById('registerSpinner');
    
    errorEl.classList.add('d-none');
    successEl.classList.add('d-none');
    
    if (!phone || !password || !password2) {
        showAuthError('⚠️ Заполните все обязательные поля');
        return;
    }
    
    if (password.length < 8) {
        showAuthError('⚠️ Пароль должен содержать минимум 8 символов');
        return;
    }
    
    if (password !== password2) {
        showAuthError('⚠️ Пароли не совпадают');
        return;
    }
    
    // ✅ Валидация телефона
    const phoneRegex = /^\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$/;
    if (!phoneRegex.test(phone)) {
        showAuthError('⚠️ Введите телефон в формате +7 (999) 123-45-67');
        return;
    }
    
    btn.disabled = true;
    btnText.textContent = 'Регистрация...';
    spinner.classList.remove('d-none');
    
    try {
        const result = await register({
            phone,
            full_name,
            password,
            password2
        });
        console.log('✅ Регистрация выполнена:', result);
        
        showAuthSuccess('✅ Регистрация выполнена успешно! Теперь войдите в систему.');
        
        document.getElementById('regPhone').value = '';
        document.getElementById('regFullName').value = '';
        document.getElementById('regPassword').value = '';
        document.getElementById('regPassword2').value = '';
        
        setTimeout(() => {
            const showLogin = document.getElementById('showLogin');
            if (showLogin) showLogin.click();
        }, 2000);
        
    } catch (error) {
        console.error('❌ Ошибка регистрации:', error);
        showAuthError(error.message || 'Ошибка регистрации. Попробуйте другой телефон.');
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Зарегистрироваться';
        spinner.classList.add('d-none');
    }
}

function showAuthError(message) {
    const errorEl = document.getElementById('authError');
    errorEl.textContent = message;
    errorEl.classList.remove('d-none');
    document.getElementById('authSuccess').classList.add('d-none');
}

function showAuthSuccess(message) {
    const successEl = document.getElementById('authSuccess');
    successEl.textContent = message;
    successEl.classList.remove('d-none');
    document.getElementById('authError').classList.add('d-none');
}

function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        removeToken();
        localStorage.removeItem('refresh_token');
        updateAuthUI();
        
        // ✅ ОБНОВЛЯЕМ СЧЁТЧИК ИЗ КЭША (БЕЗ API)
        if (typeof updateCartBadgeFromCache === 'function') {
            updateCartBadgeFromCache();
        } else {
            const badge = document.getElementById('cartCount');
            if (badge) {
                badge.textContent = window.cartData?.items_count || '0';
            }
        }
        window.location.href = '/';
    }
}

// ===== ЭКСПОРТ =====
window.updateAuthUI = updateAuthUI;
window.resetAuthButton = resetAuthButton;
window.handleLogin = handleLogin;
window.handleRegister = handleRegister;
window.logout = logout;
window.showAuthError = showAuthError;
window.showAuthSuccess = showAuthSuccess;

console.log('✅ auth.js загружен!');
