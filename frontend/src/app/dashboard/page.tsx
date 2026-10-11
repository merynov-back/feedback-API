"use client";
import { useEffect, useState } from 'react';
import { authService } from '@/services/api';
import { useRouter } from 'next/navigation';

export default function DashboardPage() {
    const [user, setUser] = useState<any>(null);
    const router = useRouter();

    // useEffect сработает ровно ОДИН раз, когда страница загрузится
    useEffect(() => {
        const fetchProfile = async () => {
            try {
                // Пытаемся получить данные пользователя. 
                // Если у нас в браузере нет токена (или он протух) - бекенд выдаст ошибку!
                const userData = await authService.getMe();
                setUser(userData);
            } catch (error) {
                // Если ошибка - выгоняем пользователя на страницу логина
                router.push('/login');
            }
        };
        fetchProfile();
    }, [router]);

    const handleLogout = () => {
        authService.logout(); // Удаляем токен
        router.push('/login');
    };

    // Пока данные грузятся, показываем пустоту
    if (!user) return <div>Загрузка...</div>;

    return (
        <div className="min-h-screen p-8 bg-gray-50">
            <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-md p-8">
                <h1 className="text-3xl font-bold mb-8">Привет, {user.name}!</h1>

                <p className="mb-2"><strong>Ваш ID:</strong> {user.id}</p>
                <p className="mb-2"><strong>Ваш Email:</strong> {user.email}</p>
                <p className="mb-6 text-green-600 font-bold">Статус: {user.is_active ? 'Активен' : 'Не активен'}</p>

                <button onClick={handleLogout} className="text-white bg-red-500 px-4 py-2 rounded-lg">Выйти</button>
            </div>
        </div>
    );
}