import uuid

from django.db import models

from accounts.models import Company, User, Village


class Purchase(models.Model):
    """UUID généré sur le téléphone (§8.2 cahier) : deux collecteurs peuvent créer
    des achats sans conflit, même hors ligne."""

    STATUS_ACTIVE = "active"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [(STATUS_ACTIVE, "Actif"), (STATUS_CANCELLED, "Annulé")]

    WEIGHT_WEIGHED = "weighed"
    WEIGHT_ESTIMATED = "estimated"
    WEIGHT_METHOD_CHOICES = [(WEIGHT_WEIGHED, "Pesé"), (WEIGHT_ESTIMATED, "Estimé")]

    QUALITY_GOOD = "good"
    QUALITY_MEDIUM = "medium"
    QUALITY_LOW = "low"
    QUALITY_CHOICES = [
        (QUALITY_GOOD, "Bonne"), (QUALITY_MEDIUM, "Moyenne"), (QUALITY_LOW, "Faible"),
    ]

    id = models.UUIDField(primary_key=True, editable=False)  # fourni par le téléphone
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="purchases")
    collector = models.ForeignKey(User, on_delete=models.PROTECT, related_name="purchases")
    village = models.ForeignKey(Village, on_delete=models.PROTECT, related_name="purchases")

    number = models.CharField(max_length=20, null=True, blank=True, unique=True)

    seller_name = models.CharField(max_length=255)
    seller_phone = models.CharField(max_length=20, blank=True)

    bags = models.PositiveIntegerField()
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    weight_method = models.CharField(max_length=10, choices=WEIGHT_METHOD_CHOICES)
    standard_bag_weight_kg = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    price_per_bag = models.PositiveIntegerField(help_text="GNF, entier")
    amount = models.PositiveIntegerField(help_text="GNF, calculé par le serveur")

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_accuracy_m = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    gps_exemption_reason = models.CharField(max_length=255, blank=True)

    quality = models.CharField(max_length=10, choices=QUALITY_CHOICES, blank=True)
    moisture_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comment = models.TextField(blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    cancel_reason = models.CharField(max_length=255, blank=True)
    needs_review = models.BooleanField(default=False)
    # Concurrence optimiste (A3) : incrémentée à chaque update/cancel appliqué.
    version = models.PositiveIntegerField(default=1)

    # P5 : horloge du téléphone potentiellement fausse hors ligne, signalée sans bloquer.
    clock_skew_flagged = models.BooleanField(default=False)

    purchased_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "purchases"
        indexes = [
            models.Index(fields=["company", "purchased_at"]),
            models.Index(fields=["company", "village"]),
            models.Index(fields=["collector", "updated_at"]),
        ]

    def __str__(self):
        return self.number or str(self.id)


class PurchaseHistory(models.Model):
    """Historique en ajout seul (US-402/403, A3) : jamais modifié ni supprimé."""

    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_CANCEL = "cancel"
    ACTION_CONFLICT = "conflict"
    ACTION_CHOICES = [
        (ACTION_CREATE, "Création"), (ACTION_UPDATE, "Modification"),
        (ACTION_CANCEL, "Annulation"), (ACTION_CONFLICT, "Conflit"),
    ]

    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reason = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "purchase_history"
        ordering = ["at"]
        verbose_name_plural = "purchase history"


class PurchaseSequence(models.Model):
    """Compteur ACH-AAAA-NNNN par entreprise et par année, ligne verrouillée."""

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="purchase_sequences"
    )
    year = models.PositiveIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "purchase_sequences"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "year"], name="unique_sequence_per_company_year"
            )
        ]

    @classmethod
    def next_number(cls, company, year) -> int:
        """Doit être appelé à l'intérieur d'une transaction (verrouillage de ligne)."""
        obj, _ = cls.objects.get_or_create(company=company, year=year)
        obj = cls.objects.select_for_update().get(pk=obj.pk)
        obj.last_number += 1
        obj.save(update_fields=["last_number"])
        return obj.last_number


class SyncOperation(models.Model):
    """Rejeu idempotent : un op_id déjà traité renvoie le même résultat sans rien dupliquer."""

    STATUS_APPLIED = "applied"
    STATUS_CONFLICT = "conflict"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_APPLIED, "Appliquée"), (STATUS_CONFLICT, "Conflit"),
        (STATUS_REJECTED, "Rejetée"),
    ]

    op_id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sync_operations")
    type = models.CharField(max_length=32)
    entity_id = models.UUIDField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    code = models.CharField(max_length=32, blank=True)
    result = models.JSONField(help_text="Snapshot renvoyé au premier traitement, rejoué tel quel.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sync_operations"
