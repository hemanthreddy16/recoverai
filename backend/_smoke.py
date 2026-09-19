from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)
H = {"Authorization": "Bearer " + c.post("/api/v1/auth/login", json={"email": "demo@resurge.dev", "password": "resurge123"}).json()["access_token"]}
for s in ["simple_payment_failure", "recoverable_payment_failure", "repeated_payment_failure", "high_value_payment", "checkout_abandonment", "subscription_failure", "failed_recovery", "successful_recovery"]:
    r = c.post("/api/v1/demo/run", json={"scenario": s}, headers=H).json()
    print(f"{s:28s} prob={r['recovery_probability']:.2f} policy={r['policy_decision']:8s} action={r['approved_action']} status={r['recovery_status']}")
