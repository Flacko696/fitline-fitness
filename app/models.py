from datetime import date
 
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import F, Q
 
MEMBERSHIP_STATUS = [("active", "Действует"), ("frozen", "Заморожен"), ("expired", "Истёк")]
 
 
class Client(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_profile")
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Клиент", "Клиенты", ["full_name"]
 
    def __str__(self):
        return self.full_name
 
 
class MembershipType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField()
    visits_limit = models.PositiveIntegerField(null=True, blank=True)  # пусто = безлимит
    max_freeze_days = models.PositiveIntegerField(default=0)
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Тип абонемента", "Типы абонементов", ["price"]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="membershiptype_price_gte_0"),
            models.CheckConstraint(condition=Q(duration_days__gte=1), name="membershiptype_duration_gte_1"),
        ]
 
    def __str__(self):
        return f"{self.name} — {self.price} руб."
 
 
class Membership(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="memberships")
    membership_type = models.ForeignKey(MembershipType, on_delete=models.PROTECT, related_name="memberships")
    purchase_date = models.DateField(default=date.today)
    end_date = models.DateField()
    remaining_visits = models.PositiveIntegerField(null=True, blank=True)  # пусто = безлимит
    status = models.CharField(max_length=10, choices=MEMBERSHIP_STATUS, default="active")
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Абонемент", "Абонементы", ["-purchase_date"]
        constraints = [models.CheckConstraint(condition=Q(end_date__gte=F("purchase_date")),
                                              name="membership_end_after_purchase")]
 
    def __str__(self):
        return f"{self.client} · {self.membership_type.name}"
 
 
class Freeze(models.Model):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="freezes")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, default="planned",
                              choices=[("planned", "Запланирована"), ("active", "Действует"), ("finished", "Завершена")])
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Заморозка", "Заморозки", ["-start_date"]
        constraints = [models.CheckConstraint(condition=Q(end_date__gte=F("start_date")),
                                              name="freeze_end_after_start")]
 
    def __str__(self):
        return f"Заморозка {self.start_date} — {self.end_date}"
 
 
class Trainer(models.Model):
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, unique=True)
    specialization = models.CharField(max_length=100)
    experience_years = models.PositiveSmallIntegerField(default=1)
    photo = models.CharField(max_length=255, null=True, blank=True)
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Тренер", "Тренеры", ["full_name"]
 
    def __str__(self):
        return f"{self.full_name} ({self.specialization})"
 
 
class Workout(models.Model):
    name = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=50)
    level = models.CharField(max_length=10, default="beginner",
                             choices=[("beginner", "Начальный"), ("medium", "Средний"), ("hard", "Продвинутый")])
    duration_min = models.PositiveSmallIntegerField(validators=[MinValueValidator(15), MaxValueValidator(180)])
    description = models.TextField(blank=True)
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Занятие", "Занятия", ["name"]
 
    def __str__(self):
        return self.name
 
 
class Schedule(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.PROTECT, related_name="schedules")
    trainer = models.ForeignKey(Trainer, on_delete=models.PROTECT, related_name="schedules")
    date = models.DateField()
    start_time = models.TimeField()
    hall = models.CharField(max_length=50)
    max_places = models.PositiveSmallIntegerField(default=15)
    clients = models.ManyToManyField(Client, through="Booking", related_name="booked_classes")
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Расписание", "Расписание", ["date", "start_time"]
        constraints = [
            models.CheckConstraint(condition=Q(max_places__gte=1), name="schedule_places_gte_1"),
            models.UniqueConstraint(fields=["hall", "date", "start_time"], name="schedule_unique_hall_slot"),
        ]
 
    @property
    def free_places(self):
        return self.max_places - self.bookings.filter(status="confirmed").count()
 
    def __str__(self):
        return f"{self.workout.name}, {self.date} {self.start_time:%H:%M}"
 
 
class Booking(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="bookings")
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="bookings")
    membership = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name="bookings")
    booked_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, default="confirmed",
                              choices=[("confirmed", "Подтверждена"), ("cancelled", "Отменена")])
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Запись на занятие", "Записи на занятия", ["-booked_at"]
        constraints = [models.UniqueConstraint(fields=["client", "schedule"], name="booking_unique_client_schedule")]
 
    def __str__(self):
        return f"{self.client} → {self.schedule}"
 
    @classmethod
    def book(cls, client, schedule, membership):
        """Запись с проверкой: абонемент действует и не заморожен, есть место; остаток уменьшается."""
        with transaction.atomic():
            s = Schedule.objects.select_for_update().get(pk=schedule.pk)
            m = Membership.objects.select_for_update().get(pk=membership.pk, client=client)
            if m.status != "active" or m.end_date < s.date or m.remaining_visits == 0:
                raise ValueError("Абонемент не действует, заморожен или закончились занятия")
            if s.free_places <= 0:
                raise ValueError("Свободных мест нет")
            booking = cls.objects.create(client=client, schedule=s, membership=m)
            if m.remaining_visits is not None:
                Membership.objects.filter(pk=m.pk).update(remaining_visits=F("remaining_visits") - 1)
            return booking
 
    def cancel(self):
        """Отмена записи возвращает занятие на абонемент."""
        with transaction.atomic():
            if self.status == "confirmed":
                self.status = "cancelled"
                self.save(update_fields=["status"])
                Membership.objects.filter(pk=self.membership_id, remaining_visits__isnull=False) \
                    .update(remaining_visits=F("remaining_visits") + 1)
 
 
class Attendance(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="attendance")
    marked_by = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, related_name="marked_attendances")
    marked_at = models.DateTimeField()
    status = models.CharField(max_length=10, default="came", choices=[("came", "Пришёл"), ("missed", "Не пришёл")])
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Посещение", "Посещения", ["-marked_at"]
 
    def __str__(self):
        return f"{self.booking.client}: {self.get_status_display()}"
 
 
class Payment(models.Model):
    membership = models.OneToOneField(Membership, on_delete=models.PROTECT, related_name="payment")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    method = models.CharField(max_length=10,
                              choices=[("card", "Банковская карта"), ("sbp", "СБП"), ("cash", "Наличные на ресепшене")])
    paid_at = models.DateTimeField()
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Оплата", "Оплаты", ["-paid_at"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_gt_0")]
 
    def __str__(self):
        return f"Оплата {self.amount} руб. ({self.get_method_display()})"
 
 
class Review(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="reviews")
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        verbose_name, verbose_name_plural, ordering = "Отзыв", "Отзывы", ["-created_at"]
        constraints = [models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="review_rating_1_5")]
 
    def __str__(self):
        return f"{self.client}: {self.rating}/5"

