"use client";
import { useState } from 'react';
import { authService } from '@/services/api';
import { useRouter, useSearchParams } from 'next/navigation';

export default function VerifyEmailForm() {
    const searchParams = useSearchParams(); // Достаем параметры из ссылки (тот самый ?email=...)
    const [email, setEmail] = useState(searchParams.get('email') || '');
    const [code, setCode] = useState('');
    const router = useRouter();

    const handleVerify = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await authService.verifyEmail({ email, code });
            alert("Почта подтверждена! Теперь можно войти.");
            router.push('/login');
        } catch (err) {
            alert('Неверный код!');
        }
    };

    return (
        <form onSubmit={handleVerify} className="flex flex-col gap-4 max-w-sm w-full mx-auto p-6 bg-white shadow-md rounded-xl">
            <h2 className="text-2xl font-bold text-center">Код подтверждения</h2>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="p-3 border rounded-lg" required />
            <input type="text" placeholder="6-значный код" value={code} onChange={(e) => setCode(e.target.value)} className="p-3 border rounded-lg text-center" maxLength={6} required />
            <button type="submit" className="bg-blue-600 text-white p-3 rounded-lg">Подтвердить</button>
        </form>
    );
}