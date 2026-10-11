"use client"; // Говорит Next.js, что этот код должен выполняться в браузере пользователя (так как тут есть кнопки и ввод текста)
import { useState } from 'react';
import { authService } from '@/services/api';
import { useRouter } from 'next/navigation';

export default function LoginForm() {
    // useState - это "память" компонента. Здесь мы храним то, что ввел юзер
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const router = useRouter(); // Для перенаправления на другие страницы

    // Эта функция сработает при нажатии на кнопку "Войти"
    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault(); // Запрещаем браузеру перезагружать страницу
        try {
            await authService.login({ email, password });
            router.push('/dashboard'); // При успехе - отправляем в личный кабинет
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Ошибка авторизации');
        }
    };

    return (
        <form onSubmit={handleLogin} className="flex flex-col gap-4 max-w-sm w-full mx-auto p-6 bg-white shadow-md rounded-xl">
            <h2 className="text-2xl font-bold text-center">Вход</h2>
            {error && <div className="text-red-500 text-sm text-center">{error}</div>}

            {/* При вводе текста, мы обновляем "память" (setEmail) */}
            <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className="p-3 border rounded-lg" required />
            <input type="password" placeholder="Пароль" value={password} onChange={(e) => setPassword(e.target.value)} className="p-3 border rounded-lg" required />

            <button type="submit" className="bg-blue-600 text-white p-3 rounded-lg">Войти</button>
        </form>
    );
}