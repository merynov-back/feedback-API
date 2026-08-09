import redis
from src.config import settings

class RedisService:
    _OTP_KEY = "otp:email:{email}"
    _COOLDOWN_KEY = "otp:cooldown:{email}"

    def __init__(self, redis_url: str = settings.REDIS_URL) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)
    
    
    def set_otp(self, email: str, otp_code: str) -> None:
        """
        Сохранить OTP-код с TTL из config
        redis автоматически удалит ключ через OTP_TTL_SECONDS секунд
        """
        key = self._OTP_KEY.format(email=email)
        self._client.setex(key, settings.OTP_TTL_SECONDS, otp_code)
    
    def get_otp(self, email: str) -> str | None:
        """
        Получить OTP-код для email
        Возвращает None если ключ не существует (истек TTL или не был создан)
        """
        key = self._OTP_KEY.format(email=email)
        return self._client.get(key)
    
    def delete_otp(self, email: str) -> None:
        """
        Удалить OTP-код после успешной верификации
        Предотвращает повторние и использование кода
        """
        key = self._OTP_KEY.format(email=email)
        self._client.delete(key)
    
    def get_otp_ttl(self, email: str) -> int:
        """
        Вернуть оставшиеся время кода в секундах
        -2 - ключ не существует
        -1 - ключ существует но без TTL
        """
        key = self._OTP_KEY.format(email=email)
        return self._client.ttl(key)

    def can_resend(self, email: str) -> bool:
        """
        Проверить, можно ли повторно отправить код
        Использует cooldown между отправками
        """
        key = self._COOLDOWN_KEY.format(email=email)
        return self._client.get(key) is None

    def set_resend_cooldown(self, email: str) -> None:
        """
        Установить кулдаун после отправки кода
        В течении OTP_RESEND_COOLDOWN_SECONDS секунд
        будет запрещено повторное отправка кода       
        """
        key = self._COOLDOWN_KEY.format(email=email)
        self._client.setex(key, settings.OTP_RESEND_COOLDOWN_SECONDS, "1")
    
    def get_cooldown_ttl(self, email: str) -> int:
        """
        Вернуть оставшееся время кулдауна в секундах
        """
        key = self._COOLDOWN_KEY.format(email=email)
        ttl = self._client.ttl(key) 
        return max(ttl, 0)
    
    
    