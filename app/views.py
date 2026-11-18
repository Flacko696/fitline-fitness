from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import FeedbackForm, FreezeForm, ReviewForm
from .models import Booking, Client, Freeze, Membership, MembershipType, Payment, Review, Schedule, Trainer, Workout

def index(request):
    return render(request, "index.html", {
        "memberships": MembershipType.objects.all()[:4],
        "nearest_schedules": Schedule.objects.select_related("workout", "trainer").all()[:5],
    })

def memberships_list(request):
    return render(request, "memberships.html", {"memberships": MembershipType.objects.all()})

@login_required
def buy_membership(request, pk):
    m_type = get_object_or_404(MembershipType, pk=pk)
    client, _ = Client.objects.get_or_create(user=request.user, defaults={"full_name": request.user.username, "phone": "+79000000000"})
    if request.method == "POST":
        membership = Membership.objects.create(
            client=client, membership_type=m_type, purchase_date=date.today(),
            end_date=date.today() + timedelta(days=m_type.duration_days),
            remaining_visits=m_type.visits_limit, status="active"
        )
        Payment.objects.create(membership=membership, amount=m_type.price, method="card", paid_at=timezone.now())
        messages.success(request, "Абонемент успешно оформлен!")
        return redirect("account")
    return redirect("memberships")

def schedule_list(request):
    qs = Schedule.objects.select_related("workout", "trainer").all()
    if request.GET.get("workout"): qs = qs.filter(workout_id=request.GET.get("workout"))
    if request.GET.get("trainer"): qs = qs.filter(trainer_id=request.GET.get("trainer"))
    page_obj = Paginator(qs, 15).get_page(request.GET.get("page"))
    return render(request, "schedule.html", {"page_obj": page_obj, "workouts": Workout.objects.all(), "trainers": Trainer.objects.all()})

def schedule_detail(request, pk):
    schedule = get_object_or_404(Schedule.objects.select_related("workout", "trainer"), pk=pk)
    active_m = request.user.client_profile.memberships.filter(status="active") if request.user.is_authenticated and hasattr(request.user, "client_profile") else []
    return render(request, "schedule_detail.html", {"schedule": schedule, "active_memberships": active_m})

@login_required
def book_workout(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    if request.method == "POST":
        client = getattr(request.user, "client_profile", None)
        membership = get_object_or_404(Membership, pk=request.POST.get("membership_id"), client=client)
        try:
            Booking.book(client=client, schedule=schedule, membership=membership)
            messages.success(request, "Запись успешна!")
            return redirect("account")
        except Exception as e:
            messages.error(request, f"Ошибка: {e}")
    return redirect("schedule_detail", pk=pk)

def trainers_list(request):
    return render(request, "trainers.html", {"trainers": Trainer.objects.all()})

def reviews_page(request):
    if request.method == "POST" and request.user.is_authenticated:
        form = ReviewForm(request.POST)
        if form.is_valid():
            client, _ = Client.objects.get_or_create(user=request.user, defaults={"full_name": request.user.username, "phone": "+79000000000"})
            r = form.save(commit=False)
            r.client = client
            r.is_published = True
            r.save()
            messages.success(request, "Отзыв опубликован!")
            return redirect("reviews")
    return render(request, "reviews.html", {"reviews": Review.objects.filter(is_published=True), "form": ReviewForm()})

def contacts_page(request):
    if request.method == "POST" and FeedbackForm(request.POST).is_valid():
        messages.success(request, "Сообщение отправлено!")
        return redirect("contacts")
    return render(request, "contacts.html", {"form": FeedbackForm()})

def search_page(request):
    q = request.GET.get("q", "").strip()
    return render(request, "search.html", {
        "query": q,
        "workouts": Workout.objects.filter(name__icontains=q) if q else [],
        "trainers": Trainer.objects.filter(full_name__icontains=q) if q else []
    })

@login_required
def account_page(request):
    client, _ = Client.objects.get_or_create(user=request.user, defaults={"full_name": request.user.username, "phone": "+79000000000"})
    return render(request, "account.html", {
        "client": client,
        "memberships": client.memberships.all(),
        "bookings": client.bookings.select_related("schedule__workout").all(),
        "freeze_form": FreezeForm()
    })

@login_required
def freeze_membership(request, pk):
    client = get_object_or_404(Client, user=request.user)
    m = get_object_or_404(Membership, pk=pk, client=client)
    form = FreezeForm(request.POST)
    if form.is_valid():
        start, end = form.cleaned_data["start_date"], form.cleaned_data["end_date"]
        days = (end - start).days + 1
        Freeze.objects.create(membership=m, start_date=start, end_date=end, status="active")
        m.status = "frozen"
        m.end_date += timedelta(days=days)
        m.save()
        messages.success(request, "Абонемент заморожен.")
    return redirect("account")

@login_required
def cancel_booking(request, pk):
    get_object_or_404(Booking, pk=pk, client=getattr(request.user, "client_profile", None)).cancel()
    messages.success(request, "Запись отменена.")
    return redirect("account")