"""Bolalarning shaxsiy ma'lumotlarini ommaviy ro'yxatlarda (reyting, battle) himoyalash."""


def public_name(full_name):
    """Ommaga ko'rinadigan ism: birinchi so'z to'liq, ikkinchisining bosh harfi.

    "Azizbek Olimov Rustamovich" -> "Azizbek O."; bitta so'z bo'lsa o'zgarmaydi.
    """
    parts = (full_name or "").split()
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[1][0].upper()}."


def can_see_private_data(user):
    """O'qituvchi/admin to'liq ism va telefonni ko'radi, o'quvchi va ota-ona — yo'q."""
    return bool(user and (user.is_staff or getattr(user, "role", None) in ("teacher", "admin", "superadmin")))
