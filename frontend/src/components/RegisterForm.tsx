"use client";
import { useState } from 'react';
import { authService } from '@/services/api';
import { useRouter } from 'next/navigation';

export default function RegisterForm() {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [success, setSuccess] = useState(false);
    const router = useRouter();

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await authService.register({ name, email, password });
            setSuccess(true);
            // Ждем 2 секунды и перекидываем юзера вводить код. Передаем email прямо в ссылке!
            setTimeout(() => router.push(`/verify?email=${email}`), 2000);
        } catch (err) {
            alert("Ошибка регистрации!");
        }
    };

    if (success) return <div className="text-green-500 p-4">Регистрация успешна! Идем на верификацию...</div>;

    return (
        <form onSubmit={handleRegister} className="flex flex-col gap-4 max-w-sm w-full mx-auto p-6 bg-white shadow-md rounded-xl">
            <h2 className="text-2xl font-bold text-center">Регистрация</h2>
            <input type="text" placeholder="Имя" value={name} onChange={(e) => setName(e.target.value)} className="p-3 border rounded-lg" required />
            <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className="p-3 border rounded-lg" required />
            <input type="password" placeholder="Пароль" value={password} onChange={(e) => setPassword(e.target.value)} className="p-3 border rounded-lg" required />
            <button type="submit" className="bg-blue-600 text-white p-3 rounded-lg">Создать аккаунт</button>
        </form>
    );
}