"""
IQMATH Telegram bot: marketing va admin uchun avtomatik xabarlar.

  marketing — yangi ro'yxatdan o'tgan o'quvchilar haqida xabar (Celery, har daqiqa)
  admin     — har kuni baza va fayllar backupi, 45 MB lik bo'laklarga bo'lib (Celery, 03:00)

Sozlamalar: telegram_bot/.telegram-env
Qo'lda ishga tushirish: python -m telegram_bot test | marketing | backup
"""
