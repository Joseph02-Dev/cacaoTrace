from datetime import timedelta

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Company, User, Village
from purchases.models import Purchase, PurchaseSequence, SyncOperation

SYNC_URL = "/api/sync"


def op(op_type, entity_id, payload, base_version=None, op_id=None, reason=None):
    import uuid

    entry = {
        "op_id": str(op_id or uuid.uuid4()),
        "type": op_type,
        "entity_id": str(entity_id),
        "payload": payload,
    }
    if base_version is not None:
        entry["base_version"] = base_version
    if reason is not None:
        entry["reason"] = reason
    return entry


def base_payload(village_id, **overrides):
    data = {
        "village_id": str(village_id),
        "seller_name": "Mamadou Bah",
        "bags": 10,
        "weight_kg": "650.00",
        "weight_method": "weighed",
        "price_per_bag": 150000,
        "latitude": "7.700000",
        "longitude": "-8.680000",
        "gps_accuracy_m": "8.0",
        "purchased_at": timezone.now().isoformat(),
    }
    data.update(overrides)
    return data


class SyncTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Cacao", standard_bag_weight_kg="65.00")
        self.other_company = Company.objects.create(name="Autre Entreprise")
        self.village = Village.objects.create(company=self.company, name="Diécké")
        self.other_village = Village.objects.create(company=self.other_company, name="Ailleurs")
        self.collector = User.objects.create_user(
            code="col001", name="Fatoumata", password="UnMotDePasse8", company=self.company,
        )
        self.other_collector = User.objects.create_user(
            code="col002", name="Ibrahim", password="UnMotDePasse8", company=self.company,
        )
        self.supervisor = User.objects.create_user(
            code="sup001", name="Superviseur", password="UnMotDePasse8", company=self.company,
            role=User.ROLE_SUPERVISOR,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.collector)


class CreateTests(SyncTestCase):
    def test_create_computes_amount_and_number(self):
        pid = "11111111-1111-1111-1111-111111111111"
        response = self.client.post(
            SYNC_URL, {"operations": [op("purchase.create", pid, base_payload(self.village.id))]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        result = response.data["results"][0]
        self.assertEqual(result["status"], "applied")
        purchase = result["purchase"]
        self.assertEqual(purchase["amount"], 10 * 150000)
        self.assertTrue(purchase["number"].startswith(f"ACH-{timezone.now().year}-"))
        self.assertEqual(purchase["version"], 1)
        self.assertEqual(len(purchase["history"]), 1)
        self.assertEqual(purchase["history"][0]["action"], "create")

    def test_sequential_numbers_have_no_gap(self):
        for i in range(3):
            pid = f"2222222-2222-2222-2222-22222222222{i}".replace("2222222-", "22222222-")
            self.client.post(
                SYNC_URL, {"operations": [op("purchase.create", pid, base_payload(self.village.id))]},
                format="json",
            )
        numbers = list(Purchase.objects.order_by("created_at").values_list("number", flat=True))
        suffixes = sorted(int(n.split("-")[-1]) for n in numbers)
        self.assertEqual(suffixes, [suffixes[0], suffixes[0] + 1, suffixes[0] + 2])

    def test_missing_required_field_is_rejected_invalid(self):
        pid = "33333333-3333-3333-3333-333333333333"
        payload = base_payload(self.village.id)
        payload["bags"] = 0
        response = self.client.post(
            SYNC_URL, {"operations": [op("purchase.create", pid, payload)]}, format="json"
        )
        result = response.data["results"][0]
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["code"], "invalid")
        self.assertIn("bags", result["errors"])

    def test_missing_gps_requires_exemption_reason(self):
        pid = "44444444-4444-4444-4444-444444444444"
        payload = base_payload(self.village.id)
        del payload["latitude"]
        del payload["longitude"]
        response = self.client.post(
            SYNC_URL, {"operations": [op("purchase.create", pid, payload)]}, format="json"
        )
        result = response.data["results"][0]
        self.assertEqual(result["code"], "invalid")
        self.assertIn("gps_exemption_reason", result["errors"])

        payload["gps_exemption_reason"] = "GPS indisponible dans le village"
        response2 = self.client.post(
            SYNC_URL, {"operations": [op("purchase.create", pid, payload)]}, format="json"
        )
        self.assertEqual(response2.data["results"][0]["status"], "applied")

    def test_estimated_weight_must_match_bags_times_standard(self):
        pid = "55555555-5555-5555-5555-555555555555"
        payload = base_payload(
            self.village.id, weight_method="estimated", standard_bag_weight_kg="65.00",
            weight_kg="999.00",
        )
        response = self.client.post(
            SYNC_URL, {"operations": [op("purchase.create", pid, payload)]}, format="json"
        )
        result = response.data["results"][0]
        self.assertEqual(result["code"], "invalid")
        self.assertIn("weight_kg", result["errors"])

        payload["weight_kg"] = "650.00"
        response2 = self.client.post(
            SYNC_URL, {"operations": [op("purchase.create", pid, payload)]}, format="json"
        )
        self.assertEqual(response2.data["results"][0]["status"], "applied")

    def test_village_from_other_company_is_rejected(self):
        pid = "66666666-6666-6666-6666-666666666666"
        payload = base_payload(self.other_village.id)
        response = self.client.post(
            SYNC_URL, {"operations": [op("purchase.create", pid, payload)]}, format="json"
        )
        result = response.data["results"][0]
        self.assertEqual(result["code"], "invalid")
        self.assertIn("village_id", result["errors"])

    def test_replaying_same_op_id_does_not_duplicate(self):
        pid = "77777777-7777-7777-7777-777777777777"
        op_id = "88888888-8888-8888-8888-888888888888"
        body = {"operations": [op("purchase.create", pid, base_payload(self.village.id), op_id=op_id)]}
        first = self.client.post(SYNC_URL, body, format="json").data["results"][0]
        second = self.client.post(SYNC_URL, body, format="json").data["results"][0]
        self.assertEqual(first, second)
        self.assertEqual(Purchase.objects.filter(id=pid).count(), 1)
        self.assertEqual(SyncOperation.objects.filter(op_id=op_id).count(), 1)

    def test_same_op_id_different_entity_is_op_id_conflict(self):
        op_id = "99999999-9999-9999-9999-999999999999"
        pid1 = "10101010-1010-1010-1010-101010101010"
        pid2 = "20202020-2020-2020-2020-202020202020"
        self.client.post(
            SYNC_URL,
            {"operations": [op("purchase.create", pid1, base_payload(self.village.id), op_id=op_id)]},
            format="json",
        )
        response = self.client.post(
            SYNC_URL,
            {"operations": [op("purchase.create", pid2, base_payload(self.village.id), op_id=op_id)]},
            format="json",
        )
        self.assertEqual(response.data["results"][0]["code"], "op_id_conflict")

    def test_duplicate_entity_id_with_new_op_id_is_already_exists(self):
        pid = "30303030-3030-3030-3030-303030303030"
        self.client.post(
            SYNC_URL, {"operations": [op("purchase.create", pid, base_payload(self.village.id))]},
            format="json",
        )
        response = self.client.post(
            SYNC_URL, {"operations": [op("purchase.create", pid, base_payload(self.village.id))]},
            format="json",
        )
        self.assertEqual(response.data["results"][0]["code"], "already_exists")

    def test_invalid_envelope_returns_400(self):
        response = self.client.post(SYNC_URL, {"operations": []}, format="json")
        self.assertEqual(response.status_code, 400)

        response2 = self.client.post(
            SYNC_URL, {"operations": [{"type": "purchase.create"}]}, format="json"
        )
        self.assertEqual(response2.status_code, 400)


class UpdateCancelTests(SyncTestCase):
    def _create(self):
        pid = "40404040-4040-4040-4040-404040404040"
        self.client.post(
            SYNC_URL, {"operations": [op("purchase.create", pid, base_payload(self.village.id))]},
            format="json",
        )
        return pid

    def test_update_applies_and_bumps_version(self):
        pid = self._create()
        payload = base_payload(self.village.id, bags=12)
        response = self.client.post(
            SYNC_URL,
            {"operations": [op("purchase.update", pid, payload, base_version=1)]},
            format="json",
        )
        result = response.data["results"][0]
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["purchase"]["bags"], 12)
        self.assertEqual(result["purchase"]["amount"], 12 * 150000)
        self.assertEqual(result["purchase"]["version"], 2)

    def test_update_with_stale_version_is_conflict_and_keeps_server_state(self):
        pid = self._create()
        payload = base_payload(self.village.id, bags=99)
        response = self.client.post(
            SYNC_URL,
            {"operations": [op("purchase.update", pid, payload, base_version=0)]},
            format="json",
        )
        result = response.data["results"][0]
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["purchase"]["bags"], 10)  # valeur serveur inchangée
        self.assertTrue(result["purchase"]["needs_review"])

    def test_collector_cannot_update_another_collectors_purchase(self):
        pid = self._create()
        other_client = APIClient()
        other_client.force_authenticate(self.other_collector)
        response = other_client.post(
            SYNC_URL,
            {"operations": [op("purchase.update", pid, base_payload(self.village.id), base_version=1)]},
            format="json",
        )
        self.assertEqual(response.data["results"][0]["code"], "not_found")

    def test_supervisor_update_requires_reason(self):
        pid = self._create()
        sup_client = APIClient()
        sup_client.force_authenticate(self.supervisor)
        response = sup_client.post(
            SYNC_URL,
            {"operations": [op("purchase.update", pid, base_payload(self.village.id), base_version=1)]},
            format="json",
        )
        self.assertEqual(response.data["results"][0]["code"], "invalid")

        response2 = sup_client.post(
            SYNC_URL,
            {
                "operations": [
                    op(
                        "purchase.update", pid, base_payload(self.village.id, bags=15),
                        base_version=1, reason="Correction erreur de saisie",
                    )
                ]
            },
            format="json",
        )
        self.assertEqual(response2.data["results"][0]["status"], "applied")

    def test_cancel_requires_reason(self):
        pid = self._create()
        response = self.client.post(
            SYNC_URL, {"operations": [op("purchase.cancel", pid, {}, base_version=1)]}, format="json"
        )
        self.assertEqual(response.data["results"][0]["code"], "invalid")

    def test_cancel_applies_and_excludes_from_active(self):
        pid = self._create()
        response = self.client.post(
            SYNC_URL,
            {"operations": [op("purchase.cancel", pid, {"reason": "sacs humides"}, base_version=1)]},
            format="json",
        )
        result = response.data["results"][0]
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["purchase"]["status"], "cancelled")
        self.assertEqual(result["purchase"]["cancel_reason"], "sacs humides")

    def test_cannot_cancel_twice(self):
        pid = self._create()
        self.client.post(
            SYNC_URL,
            {"operations": [op("purchase.cancel", pid, {"reason": "erreur"}, base_version=1)]},
            format="json",
        )
        response = self.client.post(
            SYNC_URL,
            {"operations": [op("purchase.cancel", pid, {"reason": "erreur"}, base_version=2)]},
            format="json",
        )
        self.assertEqual(response.data["results"][0]["code"], "already_cancelled")

    def test_update_unknown_purchase_is_not_found(self):
        response = self.client.post(
            SYNC_URL,
            {
                "operations": [
                    op(
                        "purchase.update", "50505050-5050-5050-5050-505050505050",
                        base_payload(self.village.id), base_version=1,
                    )
                ]
            },
            format="json",
        )
        self.assertEqual(response.data["results"][0]["code"], "not_found")


class BatchOrderingTests(SyncTestCase):
    def test_create_then_update_in_same_batch_applies_in_order(self):
        pid = "60606060-6060-6060-6060-606060606060"
        response = self.client.post(
            SYNC_URL,
            {
                "operations": [
                    op("purchase.create", pid, base_payload(self.village.id)),
                    op("purchase.update", pid, base_payload(self.village.id, bags=20), base_version=1),
                ]
            },
            format="json",
        )
        results = response.data["results"]
        self.assertEqual(results[0]["status"], "applied")
        self.assertEqual(results[1]["status"], "applied")
        self.assertEqual(results[1]["purchase"]["bags"], 20)

    def test_one_rejected_operation_does_not_block_the_others(self):
        pid_bad = "70707070-7070-7070-7070-707070707070"
        pid_ok = "80808080-8080-8080-8080-808080808080"
        bad_payload = base_payload(self.village.id)
        bad_payload["bags"] = -1
        response = self.client.post(
            SYNC_URL,
            {
                "operations": [
                    op("purchase.create", pid_bad, bad_payload),
                    op("purchase.create", pid_ok, base_payload(self.village.id)),
                ]
            },
            format="json",
        )
        results = response.data["results"]
        self.assertEqual(results[0]["status"], "rejected")
        self.assertEqual(results[1]["status"], "applied")
        self.assertTrue(Purchase.objects.filter(id=pid_ok).exists())
        self.assertFalse(Purchase.objects.filter(id=pid_bad).exists())


class SequenceConcurrencyTests(TransactionTestCase):
    def test_next_number_has_no_gap_under_repeated_calls(self):
        company = Company.objects.create(name="Acme")
        year = timezone.now().year
        numbers = [PurchaseSequence.next_number(company, year) for _ in range(10)]
        self.assertEqual(numbers, list(range(1, 11)))
