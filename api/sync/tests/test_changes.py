import uuid

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Company, User, Village
from purchases.models import Purchase

CHANGES_URL = "/api/sync/changes"


def make_purchase(company, collector, village, **overrides):
    defaults = dict(
        id=uuid.uuid4(),
        company=company,
        collector=collector,
        village=village,
        number=f"ACH-2026-{overrides.pop('seq', 1):04d}",
        seller_name="Vendeur test",
        bags=5,
        weight_kg="325.00",
        weight_method=Purchase.WEIGHT_WEIGHED,
        price_per_bag=150000,
        amount=5 * 150000,
        purchased_at=timezone.now(),
    )
    defaults.update(overrides)
    return Purchase.objects.create(**defaults)


class ChangesTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Cacao", standard_bag_weight_kg="65.00")
        self.village = Village.objects.create(company=self.company, name="Diécké")
        self.inactive_village = Village.objects.create(
            company=self.company, name="Ancien village", status=Village.STATUS_INACTIVE
        )
        self.collector = User.objects.create_user(
            code="col001", name="Fatoumata", password="UnMotDePasse8", company=self.company,
        )
        self.other_collector = User.objects.create_user(
            code="col002", name="Ibrahim", password="UnMotDePasse8", company=self.company,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.collector)

    def test_empty_history_returns_no_purchases_but_villages_and_company(self):
        response = self.client.get(CHANGES_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["purchases"], [])
        self.assertFalse(response.data["has_more"])
        self.assertEqual(len(response.data["villages"]), 2)  # actif + inactif inclus

    def test_villages_include_inactive_with_is_active_flag(self):
        response = self.client.get(CHANGES_URL)
        by_name = {v["name"]: v for v in response.data["villages"]}
        self.assertTrue(by_name["Diécké"]["is_active"])
        self.assertFalse(by_name["Ancien village"]["is_active"])

    def test_first_pull_without_cursor_returns_all_own_purchases(self):
        make_purchase(self.company, self.collector, self.village, seq=1)
        make_purchase(self.company, self.collector, self.village, seq=2)
        make_purchase(self.company, self.other_collector, self.village, seq=3)  # pas le sien

        response = self.client.get(CHANGES_URL)
        self.assertEqual(len(response.data["purchases"]), 2)
        self.assertFalse(response.data["has_more"])

    def test_purchases_include_history(self):
        make_purchase(self.company, self.collector, self.village, seq=1)
        response = self.client.get(CHANGES_URL)
        self.assertIn("history", response.data["purchases"][0])

    def test_pagination_with_limit_and_cursor(self):
        for i in range(5):
            make_purchase(self.company, self.collector, self.village, seq=i + 1)

        page1 = self.client.get(CHANGES_URL, {"limit": 2})
        self.assertEqual(len(page1.data["purchases"]), 2)
        self.assertTrue(page1.data["has_more"])
        cursor1 = page1.data["cursor"]

        page2 = self.client.get(CHANGES_URL, {"limit": 2, "cursor": cursor1})
        self.assertEqual(len(page2.data["purchases"]), 2)
        self.assertTrue(page2.data["has_more"])
        cursor2 = page2.data["cursor"]

        page3 = self.client.get(CHANGES_URL, {"limit": 2, "cursor": cursor2})
        self.assertEqual(len(page3.data["purchases"]), 1)
        self.assertFalse(page3.data["has_more"])

        ids_seen = {
            p["id"] for page in (page1, page2, page3) for p in page.data["purchases"]
        }
        self.assertEqual(len(ids_seen), 5)  # aucun doublon ni oubli sur une série complete

    def test_final_cursor_is_reusable_for_a_later_session(self):
        make_purchase(self.company, self.collector, self.village, seq=1)
        first = self.client.get(CHANGES_URL)
        self.assertFalse(first.data["has_more"])
        cursor = first.data["cursor"]

        second = self.client.get(CHANGES_URL, {"cursor": cursor})
        self.assertEqual(second.status_code, 200)
        # Le chevauchement (marge de securite) peut renvoyer le meme achat : pas une erreur.
        self.assertFalse(second.data["has_more"])

    def test_new_purchase_appears_after_previous_final_cursor(self):
        make_purchase(self.company, self.collector, self.village, seq=1)
        first = self.client.get(CHANGES_URL)
        cursor = first.data["cursor"]

        make_purchase(self.company, self.collector, self.village, seq=2)
        second = self.client.get(CHANGES_URL, {"cursor": cursor})
        numbers = {p["number"] for p in second.data["purchases"]}
        self.assertIn("ACH-2026-0002", numbers)

    def test_collector_never_sees_another_collectors_purchase(self):
        make_purchase(self.company, self.other_collector, self.village, seq=1)
        response = self.client.get(CHANGES_URL)
        self.assertEqual(response.data["purchases"], [])

    def test_invalid_cursor_is_400(self):
        response = self.client.get(CHANGES_URL, {"cursor": "!!!pas-un-curseur!!!"})
        self.assertEqual(response.status_code, 400)

    def test_limit_out_of_range_is_400(self):
        response = self.client.get(CHANGES_URL, {"limit": 0})
        self.assertEqual(response.status_code, 400)
        response2 = self.client.get(CHANGES_URL, {"limit": 501})
        self.assertEqual(response2.status_code, 400)

    def test_requires_authentication(self):
        anon = APIClient()
        response = anon.get(CHANGES_URL)
        self.assertEqual(response.status_code, 401)
