import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class Company(models.Model):
    """Entreprise cliente. Toute donnée métier référence une Company (⚠9 / A5)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    standard_bag_weight_kg = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        help_text="Poids standard par défaut ; modifiable par le collecteur côté mobile (design v2).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "companies"
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class Village(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_PENDING = "pending"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Actif"),
        (STATUS_PENDING, "En attente de validation"),
        (STATUS_INACTIVE, "Inactif"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="villages")
    name = models.CharField(max_length=255)
    prefecture = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    # Fusion (P3, US-205) : pointeur conservé pour que les achats qui référencent
    # l'ancien village restent valides.
    merged_into = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="merged_from",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "villages"
        constraints = [
            # Unicité seulement parmi les villages actifs : des propositions en
            # attente (US-205 / P3) peuvent porter un nom déjà proposé ailleurs,
            # l'admin les fusionne ensuite (merged_into). "active" == STATUS_ACTIVE
            # (valeur littérale nécessaire : Meta ne voit pas l'espace de noms de Village).
            models.UniqueConstraint(
                fields=["company", "name"],
                condition=models.Q(status="active"),
                name="unique_active_village_name_per_company",
            )
        ]

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    """`code` utilisateur unique, insensible à la casse (décision dev)."""

    use_in_migrations = True

    def _create(self, code, name, password, **extra_fields):
        if not code:
            raise ValueError("Le code utilisateur est obligatoire.")
        user = self.model(code=code.strip().lower(), name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, code, name, password=None, **extra_fields):
        extra_fields.setdefault("role", User.ROLE_COLLECTOR)
        return self._create(code, name, password, **extra_fields)

    def create_superuser(self, code, name, password=None, **extra_fields):
        extra_fields.setdefault("role", User.ROLE_ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create(code, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_COLLECTOR = "collector"
    ROLE_SUPERVISOR = "supervisor"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [
        (ROLE_COLLECTOR, "Collecteur"),
        (ROLE_SUPERVISOR, "Superviseur"),
        (ROLE_ADMIN, "Administrateur"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="users")
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default=ROLE_COLLECTOR)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Verrouillage de connexion, en base (architecture §5, §10.2).
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "code"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        db_table = "users"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().lower()
        super().save(*args, **kwargs)

    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > timezone.now())

    def register_failed_attempt(self) -> None:
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
            self.locked_until = timezone.now() + timezone.timedelta(
                minutes=settings.LOGIN_LOCK_MINUTES
            )
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def reset_failed_attempts(self) -> None:
        if self.failed_login_attempts or self.locked_until:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save(update_fields=["failed_login_attempts", "locked_until"])

    def __str__(self):
        return f"{self.name} ({self.code})"
