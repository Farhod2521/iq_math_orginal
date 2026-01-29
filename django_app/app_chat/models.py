from django.db import models
from django.conf import settings
from django_app.app_user.models import  Teacher
User = settings.AUTH_USER_MODEL


# ------------------------------
# 1. CONVERSATION (Chat)
# ------------------------------
class Conversation(models.Model):
    CHAT_TYPE_CHOICES = (
        ("direct", "1-to-1 Chat"),
        ("group", "Guruh Chat"),
    )

    chat_type = models.CharField(
        max_length=10,
        choices=CHAT_TYPE_CHOICES,
        default="direct",
        verbose_name="Chat turi"
    )

    title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Chat nomi"
    )  # faqat guruhda ishlaydi

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Chatlar ro‘yxatini tez chiqarish uchun
    last_message = models.TextField(blank=True, null=True)
    last_message_at = models.DateTimeField(blank=True, null=True)
    is_closed = models.BooleanField(
        default=False,
        verbose_name="Chat yopilganmi?"
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Yopilgan vaqt"
    )

    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_conversations",
        verbose_name="Chatni yopgan foydalanuvchi"
    )
    def __str__(self):
        if self.chat_type == "direct":
            return f"Direct Chat #{self.id}"
        return f"Guruh Chat: {self.title}"

    class Meta:
        verbose_name = "Chat"
        verbose_name_plural = "Chatlar"
        ordering = ['-last_message_at']


class ConversationAssignment(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="assignments"
    )

    from_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transferred_from"
    )

    to_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="transferred_to"
    )

    reason = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Nega o‘tkazildi"
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="chat_assignments"
    )

    def __str__(self):
        return f"Chat {self.conversation_id} → {self.to_teacher}"

# ------------------------------
# 2. PARTICIPANTS (Kim chatda?)
# ------------------------------
class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name="Chat"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_participations',
        verbose_name="Foydalanuvchi"
    )

    last_read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Oxirgi ko‘rgan vaqt"
    )
    unread_count = models.PositiveIntegerField(
        default=0,
        verbose_name="O‘qilmagan xabarlar soni"
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} → Chat {self.conversation_id}"

    class Meta:
        unique_together = ("conversation", "user")
        verbose_name = "Chat ishtirokchisi"
        verbose_name_plural = "Chat ishtirokchilari"


# ------------------------------
# 3. MESSAGE (Xabar)
# ------------------------------
class Message(models.Model):
    MESSAGE_TYPE_CHOICES = (
        ("text", "Text"),
        ("file", "Fayl"),
        ("image", "Rasm"),
        ("system", "Tizim xabari"),
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Chat"
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name="Yuboruvchi"
    )

    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPE_CHOICES,
        default="text",
        verbose_name="Xabar turi"
    )
    url = models.CharField(
        null=True,
        blank=True,
        verbose_name="url"
    )
    text = models.TextField(
        null=True,
        blank=True,
        verbose_name="Matn"
    )
    independent = models.CharField(max_length=10, blank=True, null=True)
    file = models.FileField(
        upload_to="chat/files/",
        null=True,
        blank=True,
        verbose_name="Fayl"
    )

    # Reply mexanizmi
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name="Qaysi xabarga javob"
    )

    is_edited = models.BooleanField(default=False, verbose_name="Tahrirlanganmi?")
    is_deleted = models.BooleanField(default=False, verbose_name="O‘chirildimi?")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.text:
            return f"{self.sender} → {self.text[:30]}"
        return f"{self.sender} fayl yubordi"

    class Meta:
        ordering = ['created_at']
        verbose_name = "Xabar"
        verbose_name_plural = "Xabarlar"


# ------------------------------
# 4. MESSAGE RECEIPT (Seen / Delivered)
# ------------------------------
class MessageReceipt(models.Model):
    STATUS_CHOICES = (
        ('delivered', 'Yetkazilgan'),
        ('read', 'O‘qilgan'),
    )

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='receipts',
        verbose_name="Xabar"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='message_receipts',
        verbose_name="Foydalanuvchi"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        verbose_name="Holat"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user}: {self.message_id} — {self.status}"

    class Meta:
        unique_together = ("message", "user")
        verbose_name = "Xabar holati"
        verbose_name_plural = "Xabar holatlari"


# ------------------------------
# 5. TYPING INDICATOR (ixtiyoriy)
# ------------------------------
class TypingIndicator(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        verbose_name="Chat"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Foydalanuvchi"
    )
    is_typing = models.BooleanField(default=False, verbose_name="Yozmoqda")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("conversation", "user")
        verbose_name = "Yozmoqda holati"
        verbose_name_plural = "Yozmoqda holatlari"

    def __str__(self):
        return f"{self.user} yozmoqda: {self.is_typing}"







class ConversationRating(models.Model):
    conversation = models.OneToOneField(
        Conversation,
        on_delete=models.CASCADE,
        related_name="rating",
        verbose_name="Chat"
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="given_ratings",
        verbose_name="Student"
    )

    mentor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_ratings",
        verbose_name="Mentor"
    )

    stars = models.PositiveSmallIntegerField(
        choices=[(i, f"{i} ⭐") for i in range(1, 6)],
        verbose_name="Baho"
    )

    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh (ixtiyoriy)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.stars}⭐ - Chat {self.conversation_id}"

    class Meta:
        verbose_name = "Chat bahosi"
        verbose_name_plural = "Chat baholari"
