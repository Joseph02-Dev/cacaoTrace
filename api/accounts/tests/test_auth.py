from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Company, User, Village

LOGIN_URL = "/api/auth/login"
REFRESH_URL = "/api/auth/refresh"


class LoginTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Cacao", standard_bag_weight_kg="65.00")
        self.village = Village.objects.create(
            company=self.company, name="Diécké", prefecture="Nzérékoré",
            latitude="7.700000", longitude="-8.680000",
        )
        self.user = User.objects.create_user(
            code="COL001", name="Fatoumata Camara", password="UnMotDePasse8", company=self.company,
        )
        self.client = APIClient()

    def test_login_ok_returns_tokens_and_bootstrap(self):
        response = self.client.post(
            LOGIN_URL, {"identifier": "col001", "password": "UnMotDePasse8"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["code"], "col001")
        self.assertEqual(response.data["user"]["role"], "collector")
        self.assertEqual(response.data["company"]["standard_bag_weight_kg"], "65.00")
        self.assertEqual(len(response.data["villages"]), 1)
        self.assertEqual(response.data["villages"][0]["name"], "Diécké")

    def test_login_is_case_insensitive_on_code(self):
        response = self.client.post(
            LOGIN_URL, {"identifier": "Col001", "password": "UnMotDePasse8"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_login_wrong_password_is_generic_401(self):
        response = self.client.post(
            LOGIN_URL, {"identifier": "col001", "password": "faux-mdp"}, format="json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Identifiant ou mot de passe incorrect.")

    def test_login_unknown_identifier_is_generic_401(self):
        response = self.client.post(
            LOGIN_URL, {"identifier": "inconnu", "password": "peu-importe"}, format="json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Identifiant ou mot de passe incorrect.")

    def test_login_missing_fields_is_400(self):
        response = self.client.post(LOGIN_URL, {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            LOGIN_URL, {"identifier": "col001", "password": "UnMotDePasse8"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    @override_settings(LOGIN_MAX_FAILED_ATTEMPTS=5, LOGIN_LOCK_MINUTES=15)
    def test_account_locks_after_max_failed_attempts(self):
        for _ in range(5):
            self.client.post(
                LOGIN_URL, {"identifier": "col001", "password": "faux"}, format="json"
            )
        response = self.client.post(
            LOGIN_URL, {"identifier": "col001", "password": "UnMotDePasse8"}, format="json"
        )
        self.assertEqual(response.status_code, 429)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked())

    def test_successful_login_resets_failed_attempts(self):
        self.client.post(LOGIN_URL, {"identifier": "col001", "password": "faux"}, format="json")
        self.client.post(
            LOGIN_URL, {"identifier": "col001", "password": "UnMotDePasse8"}, format="json"
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 0)


class RefreshTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme Cacao")
        self.user = User.objects.create_user(
            code="COL002", name="Ibrahim Diallo", password="UnMotDePasse8", company=self.company,
        )
        self.client = APIClient()
        login = self.client.post(
            LOGIN_URL, {"identifier": "col002", "password": "UnMotDePasse8"}, format="json"
        )
        self.refresh_token = login.data["refresh"]

    def test_refresh_returns_new_access_token(self):
        response = self.client.post(REFRESH_URL, {"refresh": self.refresh_token}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_refresh_refused_for_disabled_user(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(REFRESH_URL, {"refresh": self.refresh_token}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_refresh_rejects_garbage_token(self):
        response = self.client.post(REFRESH_URL, {"refresh": "not-a-token"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_refresh_requires_body(self):
        response = self.client.post(REFRESH_URL, {}, format="json")
        self.assertEqual(response.status_code, 400)


class ModelConstraintTests(TestCase):
    def test_user_code_is_normalized_lowercase(self):
        company = Company.objects.create(name="Acme Cacao")
        user = User.objects.create_user(
            code="COL003", name="Test", password="UnMotDePasse8", company=company
        )
        self.assertEqual(user.code, "col003")

    def test_village_name_unique_per_company(self):
        company = Company.objects.create(name="Acme Cacao")
        Village.objects.create(company=company, name="Diécké")
        with self.assertRaises(Exception):
            Village.objects.create(company=company, name="Diécké")
