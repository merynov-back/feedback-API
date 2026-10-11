import axios from 'axios';

// 1. Указываем адрес нашего Python бекенда
const API_URL = 'http://localhost:8000';

// 2. Создаем "экземпляр" axios
export const api = axios.create({
    baseURL: API_URL,
    headers: { 'Content-Type': 'application/json' },
});

// 3. Магия авторизации (Интерцептор)
// Этот блок кода срабатывает ПЕРЕД каждым запросом на сервер.
// Он достает из памяти браузера (localStorage) секретный токен и приклеивает его к запросу.
api.interceptors.request.use((config) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// 4. Описываем все возможные действия
export const authService = {
    async register(data: any) {
        const response = await api.post('/auth/register', data);
        return response.data;
    },
    async login(data: { email: string, password: string }) {
        // Бекенд ждет OAuth2-форму (username + password), а не JSON
        const form = new URLSearchParams({ username: data.email, password: data.password });
        const response = await api.post('/auth/token', form, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
        // Если бекенд отдал токен, сохраняем его в память браузера!
        if (response.data.access_token) {
            localStorage.setItem('access_token', response.data.access_token);
        }
        return response.data;
    },
    async verifyEmail(data: { email: string, code: string }) {
        const response = await api.post('/auth/verify-email', data);
        return response.data;
    },
    async getMe() {
        const response = await api.get('/auth/me');
        return response.data; // Этот запрос пройдет только если есть валидный токен!
    },
    logout() {
        localStorage.removeItem('access_token');
    }
};