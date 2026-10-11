import { Suspense } from 'react';
import VerifyEmailForm from '@/components/VerifyEmailForm';

export default function VerifyPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <Suspense>
                <VerifyEmailForm />
            </Suspense>
        </div>
    );
}
