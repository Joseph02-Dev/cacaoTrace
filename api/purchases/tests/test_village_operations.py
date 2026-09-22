from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Company, User, Village
from accounts.services import merge_village
from common.errors import OperationError
from purchases.models import Purchase
from purchases.tests.test_sync import base_payload, op

SYNC_URL = "/api/v1/sync"


class VillageProposeTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Cacao")
        self.village = Village.objects.create(company=self.company, name="Diécké")
        self.collector = User.objects.create_user(
            code="col001", name="Fatoumata", password="UnMotDePasse8", company=self.company,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.collector)

    def test_propose_creates_pending_village(self):
        vid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        response = self.client.post(
            SYNC_URL,
            {"operations": [op("village.propose", vid, {"name": "Koyama", "prefecture": "Lola"})]},
            format="json",
        )
        result = response.data["results"][0]
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["village"]["status"], Village.STATUS_PENDING)
        village = Village.objects.get(id=vid)
        self.assertEqual(village.status, Village.STATUS_PENDING)
        self.assertEqual(village.company_id, self.company.id)

    def test_propose_missing_name_is_rejected(self):
        vid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        response = self.client.post(
            SYNC_URL, {"operations": [op("village.propose", vid, {})]}, format="json"
        )
        result = response.data["results"][0]
        self.assertEqual(result["code"], "invalid")
        self.assertIn("name", result["errors"])

    def test_propose_reused_entity_id_is_already_exists(self):
        vid = "cccccccc-cccc-cccc-cccc-cccccccccccc"
        self.client.post(
            SYNC_URL, {"operations": [op("village.propose", vid, {"name": "Koyama"})]}, format="json"
        )
        response = self.client.post(
            SYNC_URL, {"operations": [op("village.propose", vid, {"name": "Koyama bis"})]},
            format="json",
        )
        self.assertEqual(response.data["results"][0]["code"], "already_exists")

    def test_two_collectors_can_propose_the_same_name(self):
        """La contrainte d'unicité ne s'applique qu'aux villages actifs (P3)."""
        vid1 = "dddddddd-dddd-dddd-dddd-dddddddddddd"
        vid2 = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
        r1 = self.client.post(
            SYNC_URL, {"operations": [op("village.propose", vid1, {"name": "Nouveau Village"})]},
            format="json",
        )
        r2 = self.client.post(
            SYNC_URL, {"operations": [op("village.propose", vid2, {"name": "Nouveau Village"})]},
            format="json",
        )
        self.assertEqual(r1.data["results"][0]["status"], "applied")
        self.assertEqual(r2.data["results"][0]["status"], "applied")

    def test_proposed_village_usable_immediately_for_a_purchase(self):
        vid = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        pid = "12121212-1212-1212-1212-121212121212"
        response = self.client.post(
            SYNC_URL,
            {
                "operations": [
                    op("village.propose", vid, {"name": "Koyama"}),
                    op("purchase.create", pid, base_payload(vid)),
                ]
            },
            format="json",
        )
        results = response.data["results"]
        self.assertEqual(results[0]["status"], "applied")
        self.assertEqual(results[1]["status"], "applied")


class MergeVillageServiceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Cacao")
        self.other_company = Company.objects.create(name="Autre")
        self.pending = Village.objects.create(
            company=self.company, name="Koyama (proposé)", status=Village.STATUS_PENDING
        )
        self.target = Village.objects.create(company=self.company, name="Koyama")
        self.collector = User.objects.create_user(
            code="col001", name="Fatoumata", password="UnMotDePasse8", company=self.company,
        )
        self.admin = User.objects.create_user(
            code="adm001", name="Admin", password="UnMotDePasse8", company=self.company,
            role=User.ROLE_ADMIN,
        )
        self.purchase = Purchase.objects.create(
            id="21212121-2121-2121-2121-212121212121",
            company=self.company, collector=self.collector, village=self.pending,
            number="ACH-2026-0001", seller_name="X", bags=1, weight_kg="65.00",
            weight_method=Purchase.WEIGHT_WEIGHED, price_per_bag=100000, amount=100000,
            gps_exemption_reason="test", purchased_at=timezone.now(),
        )

    def test_merge_repoints_purchases_and_bumps_updated_at(self):
        old_updated_at = self.purchase.updated_at
        moved = merge_village(source=self.pending, target=self.target, actor=self.admin)
        self.assertEqual(moved, 1)
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.village_id, self.target.id)
        self.assertGreater(self.purchase.updated_at, old_updated_at)

        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Village.STATUS_INACTIVE)
        self.assertEqual(self.pending.merged_into_id, self.target.id)

    def test_merge_into_self_is_rejected(self):
        with self.assertRaises(OperationError) as ctx:
            merge_village(source=self.pending, target=self.pending, actor=self.admin)
        self.assertEqual(ctx.exception.code, "invalid")

    def test_merge_across_companies_is_rejected(self):
        other_village = Village.objects.create(company=self.other_company, name="Ailleurs")
        with self.assertRaises(OperationError):
            merge_village(source=self.pending, target=other_village, actor=self.admin)

    def test_merged_purchase_reappears_in_downstream_sync(self):
        client = APIClient()
        client.force_authenticate(self.collector)
        first = client.get("/api/v1/sync/changes")
        cursor = first.data["cursor"]

        merge_village(source=self.pending, target=self.target, actor=self.admin)

        second = client.get("/api/v1/sync/changes", {"cursor": cursor})
        ids = {p["id"] for p in second.data["purchases"]}
        self.assertIn(str(self.purchase.id), ids)
