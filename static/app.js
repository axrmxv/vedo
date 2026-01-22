// API базовый URL
const API_BASE = '/api/v1';

// Состояние приложения
let currentUser = null;
let currentPage = 1;
let currentUsersPage = 1;

// Утилиты
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(pageId).classList.add('active');
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.classList.add('active');
    setTimeout(() => element.classList.remove('active'), 5000);
}

function showStatus(elementId, message, isError = false) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `status-message ${isError ? 'error' : 'success'}`;
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

// API запросы
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(API_BASE + url, {
            ...options,
            credentials: 'include',
            headers: {
                ...options.headers,
            }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Ошибка сервера' }));
            throw new Error(error.detail || 'Ошибка запроса');
        }
        
        return response.json();
    } catch (error) {
        // Если это наша ошибка, пробрасываем дальше
        if (error.message) {
            throw error;
        }
        // Иначе создаём новую с понятным сообщением
        throw new Error('Ошибка соединения с сервером');
    }
}

// Авторизация
async function login(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    try {
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: formData
        });
        
        currentUser = data.user;
        document.getElementById('userName').textContent = currentUser.username;
        
        if (currentUser.role === 'admin') {
            document.getElementById('adminBtn').style.display = 'block';
        }
        
        showPage('mainPage');
        await loadFiles(1);
    } catch (error) {
        showError('loginError', error.message);
    }
}

async function logout() {
    try {
        await apiRequest('/auth/logout', { method: 'POST' });
        currentUser = null;
        showPage('loginPage');
        document.getElementById('loginForm').reset();
    } catch (error) {
        console.error('Ошибка выхода:', error);
    }
}

async function checkAuth() {
    try {
        const data = await apiRequest('/auth/me');
        currentUser = data;
        document.getElementById('userName').textContent = currentUser.username;
        
        if (currentUser.role === 'admin') {
            document.getElementById('adminBtn').style.display = 'block';
        }
        
        showPage('mainPage');
        await loadFiles(1);
    } catch (error) {
        showPage('loginPage');
    }
}

// Загрузка файлов
async function uploadFile(e) {
    e.preventDefault();
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        showStatus('uploadStatus', 'Выберите файл', true);
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showStatus('uploadStatus', 'Обработка файла...');
        const data = await apiRequest('/files/upload', {
            method: 'POST',
            body: formData
        });
        
        showStatus('uploadStatus', 'Файл успешно обработан!');
        
        // Скачивание файла
        await downloadFile(data.file.id);
        
        // Обновление списка
        await loadFiles(currentPage);
        
        // Сброс формы
        fileInput.value = '';
        document.getElementById('fileName').textContent = 'Выберите файл (.txt или .xlsx)';
    } catch (error) {
        showStatus('uploadStatus', error.message, true);
    }
}

async function loadFiles(page = 1) {
    currentPage = page;
    const container = document.getElementById('filesList');
    container.innerHTML = '<p class="loading">Загрузка...</p>';
    
    try {
        const data = await apiRequest(`/files/list?page=${page}&page_size=5`);
        
        if (data.files.length === 0) {
            container.innerHTML = '<p class="loading">Нет файлов</p>';
            return;
        }
        
        container.innerHTML = data.files.map(file => `
            <div class="file-item">
                <div class="file-info">
                    <div class="file-name">${file.original_filename}</div>
                    <div class="file-meta">
                        ${new Date(file.created_at).toLocaleString('ru-RU')} • 
                        ${(file.file_size / 1024).toFixed(1)} КБ
                    </div>
                </div>
                <div class="file-actions">
                    <button class="btn btn-edit" onclick="downloadFile(${file.id})">Скачать</button>
                    <button class="btn btn-danger" onclick="deleteFile(${file.id})">Удалить</button>
                </div>
            </div>
        `).join('');
        
        renderPagination('pagination', data.page, data.page_size, data.total, loadFiles);
    } catch (error) {
        container.innerHTML = `<p class="loading" style="color: var(--error);">Ошибка: ${error.message}</p>`;
    }
}

async function downloadFile(fileId) {
    try {
        window.location.href = `${API_BASE}/files/download/${fileId}`;
    } catch (error) {
        alert('Ошибка скачивания: ' + error.message);
    }
}

async function deleteFile(fileId) {
    if (!confirm('Вы уверены, что хотите удалить этот файл?')) {
        return;
    }
    
    try {
        await apiRequest(`/files/${fileId}`, { method: 'DELETE' });
        await loadFiles(currentPage);
    } catch (error) {
        alert('Ошибка удаления: ' + error.message);
    }
}

// Администрирование
async function createUser(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    const userData = {
        username: formData.get('username'),
        role: formData.get('role')
    };
    
    try {
        const data = await apiRequest('/admin/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        
        // Показ модального окна с данными
        document.getElementById('modalUsername').textContent = data.username;
        document.getElementById('modalPassword').textContent = data.password;
        document.getElementById('userModal').classList.add('active');
        
        // Сброс формы
        e.target.reset();
        
        // Обновление списка
        await loadUsers(currentUsersPage);
    } catch (error) {
        // Правильная обработка ошибки
        const errorMessage = error.message || 'Ошибка создания пользователя';
        showStatus('createUserStatus', errorMessage, true);
    }
}

async function loadUsers(page = 1) {
    currentUsersPage = page;
    const container = document.getElementById('usersList');
    container.innerHTML = '<p class="loading">Загрузка...</p>';
    
    try {
        const data = await apiRequest(`/admin/users?page=${page}&page_size=10`);
        
        if (data.users.length === 0) {
            container.innerHTML = '<p class="loading">Нет пользователей</p>';
            return;
        }
        
        container.innerHTML = data.users.map(user => `
            <div class="user-item">
                <div class="user-info">
                    <div class="user-name-text">${user.username}</div>
                    <div class="user-meta">
                        Роль: ${user.role === 'admin' ? 'Администратор' : 'Пользователь'} • 
                        ${new Date(user.created_at).toLocaleString('ru-RU')}
                    </div>
                </div>
                <div class="user-actions">
                    <button class="btn btn-edit" onclick="openEditModal(${user.id}, '${user.username}', '${user.role}')">Изменить</button>
                    <button class="btn btn-danger" onclick="deleteUser(${user.id})">Удалить</button>
                </div>
            </div>
        `).join('');
        
        renderPagination('usersPagination', data.page, data.page_size, data.total, loadUsers);
    } catch (error) {
        container.innerHTML = `<p class="loading" style="color: var(--error);">Ошибка: ${error.message}</p>`;
    }
}

function openEditModal(userId, username, role) {
    document.getElementById('editUserId').value = userId;
    document.getElementById('editUsername').value = username;
    document.getElementById('editUserRole').value = role;
    document.getElementById('editPassword').value = '';
    document.getElementById('editModal').classList.add('active');
}

async function editUser(e) {
    e.preventDefault();
    const userId = document.getElementById('editUserId').value;
    const formData = new FormData(e.target);
    
    const userData = {
        username: formData.get('username'),
        role: formData.get('role')
    };
    
    const password = formData.get('password');
    if (password) {
        userData.password = password;
    }
    
    try {
        await apiRequest(`/admin/users/${userId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        
        document.getElementById('editModal').classList.remove('active');
        await loadUsers(currentUsersPage);
        alert('Пользователь успешно обновлён');
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

async function deleteUser(userId) {
    if (!confirm('Вы уверены, что хотите удалить этого пользователя?')) {
        return;
    }
    
    try {
        await apiRequest(`/admin/users/${userId}`, { method: 'DELETE' });
        await loadUsers(currentUsersPage);
    } catch (error) {
        alert('Ошибка удаления: ' + error.message);
    }
}

// Пагинация
function renderPagination(containerId, page, pageSize, total, loadFunction) {
    const totalPages = Math.ceil(total / pageSize);
    const container = document.getElementById(containerId);
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    container.innerHTML = `
        <button ${page === 1 ? 'disabled' : ''} onclick="${loadFunction.name}(${page - 1})">Назад</button>
        <span class="pagination-info">Страница ${page} из ${totalPages}</span>
        <button ${page === totalPages ? 'disabled' : ''} onclick="${loadFunction.name}(${page + 1})">Вперёд</button>
    `;
}

// Обработчики событий
document.addEventListener('DOMContentLoaded', () => {
    // Авторизация
    document.getElementById('loginForm').addEventListener('submit', login);
    document.getElementById('logoutBtn').addEventListener('click', logout);
    document.getElementById('adminLogoutBtn').addEventListener('click', logout);
    
    // Загрузка файлов
    document.getElementById('uploadForm').addEventListener('submit', uploadFile);
    document.getElementById('fileInput').addEventListener('change', (e) => {
        const fileName = e.target.files[0]?.name || 'Выберите файл (.txt или .xlsx)';
        document.getElementById('fileName').textContent = fileName;
    });
    
    // Администрирование
    document.getElementById('adminBtn').addEventListener('click', () => {
        showPage('adminPage');
        loadUsers(1);
    });
    document.getElementById('backToMainBtn').addEventListener('click', () => {
        showPage('mainPage');
        loadFiles(currentPage);
    });
    document.getElementById('createUserForm').addEventListener('submit', createUser);
    document.getElementById('editUserForm').addEventListener('submit', editUser);
    
    // Модальные окна
    document.getElementById('closeModalBtn').addEventListener('click', () => {
        document.getElementById('userModal').classList.remove('active');
    });
    document.getElementById('closeEditModalBtn').addEventListener('click', () => {
        document.getElementById('editModal').classList.remove('active');
    });
    
    // Проверка авторизации при загрузке
    checkAuth();
});
