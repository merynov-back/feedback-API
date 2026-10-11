import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8 text-center">
      <h1 className="text-4xl font-bold mb-4">Наш крутой Frontend</h1>
      <div className="flex gap-4 mt-8">
        <Link href="/login" className="bg-black text-white px-6 py-2 rounded-lg">Войти</Link>
        <Link href="/register" className="border border-black px-6 py-2 rounded-lg">Регистрация</Link>
      </div>
    </div>
  );
}