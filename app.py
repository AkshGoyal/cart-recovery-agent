from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


def now():
    return datetime.now(IST).isoformat(timespec="seconds")


CARTS = {
    "CRT88417": {
        "customer": {
            "customer_id": "CUS10231",
            "first_name": "Ramesh",
            "pincode": "141001",
            "dnd_registered": False,
            "marketing_consent": True,
        },
        "cart": {
            "cart_id": "CRT88417",
            "abandon_stage": "prescription_upload",
            "purchase_type": "chronic",
            "prescription_status": "missing",
            "payment_status": "not_attempted",
            "delivery_eta_days": 2,
            "express_available": True,
            "items": [
                {
                    "sku": "SKU4412",
                    "name": "Metformin 500 mg",
                    "qty": 2,
                    "price_inr": 145,
                    "rx_required": True,
                    "drug_schedule": "H",
                    "sensitive_category": False,
                    "generic_alternative": "Glycomet 500 mg",
                    "generic_saving_inr": 62,
                },
                {
                    "sku": "SKU4490",
                    "name": "Telmisartan 40 mg",
                    "qty": 1,
                    "price_inr": 220,
                    "rx_required": True,
                    "drug_schedule": "H",
                    "sensitive_category": False,
                    "generic_alternative": "Telma 40",
                    "generic_saving_inr": 48,
                },
            ],
        },
        "eligibility": {"callable": True, "suppression_reason": None},
    },
    "CRT88418": {
        "customer": {
            "customer_id": "CUS10232",
            "first_name": "Priya",
            "pincode": "160017",
            "dnd_registered": False,
            "marketing_consent": True,
        },
        "cart": {
            "cart_id": "CRT88418",
            "abandon_stage": "payment",
            "purchase_type": "chronic",
            "prescription_status": "valid",
            "payment_status": "failed",
            "delivery_eta_days": 1,
            "express_available": True,
            "items": [
                {
                    "sku": "SKU4412",
                    "name": "Metformin 500 mg",
                    "qty": 2,
                    "price_inr": 145,
                    "rx_required": True,
                    "drug_schedule": "H",
                    "sensitive_category": False,
                    "generic_alternative": "Glycomet 500 mg",
                    "generic_saving_inr": 62,
                },
                {
                    "sku": "SKU9902",
                    "name": "Vitamin D3 sachets",
                    "qty": 1,
                    "price_inr": 340,
                    "rx_required": False,
                    "drug_schedule": None,
                    "sensitive_category": False,
                    "generic_alternative": None,
                    "generic_saving_inr": 0,
                },
            ],
        },
        "eligibility": {"callable": True, "suppression_reason": None},
    },
    "CRT88419": {
        "customer": {
            "customer_id": "CUS10233",
            "first_name": "Anil",
            "pincode": "141002",
            "dnd_registered": True,
            "marketing_consent": False,
        },
        "cart": {
            "cart_id": "CRT88419",
            "abandon_stage": "cart_review",
            "purchase_type": "acute",
            "prescription_status": "not_required",
            "payment_status": "not_attempted",
            "delivery_eta_days": 3,
            "express_available": False,
            "items": [
                {
                    "sku": "SKU7781",
                    "name": "Accu-Chek test strips",
                    "qty": 1,
                    "price_inr": 1200,
                    "rx_required": False,
                    "drug_schedule": None,
                    "sensitive_category": False,
                    "generic_alternative": None,
                    "generic_saving_inr": 0,
                },
                {
                    "sku": "SKU7712",
                    "name": "Multivitamin tablets",
                    "qty": 1,
                    "price_inr": 450,
                    "rx_required": False,
                    "drug_schedule": None,
                    "sensitive_category": False,
                    "generic_alternative": None,
                    "generic_saving_inr": 0,
                },
            ],
        },
        "eligibility": {"callable": False, "suppression_reason": "dnd_registered"},
    },
}

CUSTOMER_TO_CART = {
    "CUS10231": "CRT88417",
    "CUS10232": "CRT88418",
    "CUS10233": "CRT88419",
}

DEFAULT_CART = "CRT88417"

REQUEST_LOG = []


def record(endpoint, payload, response):
    REQUEST_LOG.insert(
        0, {"at": now(), "endpoint": endpoint, "request": payload, "response": response}
    )
    del REQUEST_LOG[50:]
    return response


def line_total(item):
    return item["price_inr"] * item["qty"]


def summarise(entry):
    items = entry["cart"]["items"]
    rx_items = [i for i in items if i["rx_required"]]
    otc_items = [i for i in items if not i["rx_required"]]
    primary = rx_items[0] if rx_items else max(items, key=line_total)
    return {
        "primary_item": primary["name"],
        "item_count": sum(i["qty"] for i in items),
        "cart_value_inr": sum(line_total(i) for i in items),
        "rx_required": bool(rx_items),
        "rx_item_names": [i["name"] for i in rx_items],
        "otc_subtotal_inr": sum(line_total(i) for i in otc_items),
        "contains_sensitive_category": any(i["sensitive_category"] for i in items),
    }


def resolve(identifier):
    if not identifier:
        return DEFAULT_CART
    return CUSTOMER_TO_CART.get(identifier, identifier)


@app.route("/")
def index():
    return jsonify(
        {
            "service": "Mock online pharmacy API",
            "status": "ok",
            "time": now(),
            "endpoints": [
                "GET  /cart/<customer_id or cart_id>",
                "POST /rx/assist",
                "POST /coupon/apply",
                "POST /payment/link",
                "POST /callback/schedule",
                "POST /call/outcome",
                "POST /compliance/adverse-event",
                "GET  /log",
            ],
            "test_carts": {
                "CUS10231": "prescription missing, Rx only, coupon refused",
                "CUS10232": "payment failed, mixed cart, coupon partial",
                "CUS10233": "DND registered, suppressed before dial",
            },
        }
    )


@app.route("/cart", methods=["GET"])
@app.route("/cart/<identifier>", methods=["GET"])
def cart_lookup(identifier=None):
    cart_id = resolve(identifier)
    entry = CARTS.get(cart_id)
    if entry is None:
        out = {"error": "cart_not_found", "requested": identifier}
        return jsonify(record("GET /cart", {"identifier": identifier}, out)), 404
    out = dict(entry)
    out["summary"] = summarise(entry)
    return jsonify(record("GET /cart", {"identifier": identifier}, out))


@app.route("/rx/assist", methods=["POST"])
def rx_assist():
    body = request.get_json(silent=True) or {}
    action = body.get("action", "send_upload_link")
    labels = {
        "send_upload_link": "Prescription upload link sent by SMS, valid for 24 hours",
        "book_teleconsult": "Teleconsultation booked, doctor will call within 30 minutes",
        "pharmacist_callback": "Pharmacist callback scheduled within 2 hours",
    }
    out = {
        "status": "sent",
        "reference_id": "RXA5567",
        "action": action,
        "channel": body.get("channel", "sms"),
        "link_expires_hours": 24,
        "confirmation_summary": labels.get(action, labels["send_upload_link"]),
    }
    return jsonify(record("POST /rx/assist", body, out))


@app.route("/coupon/apply", methods=["POST"])
def coupon_apply():
    body = request.get_json(silent=True) or {}
    cart_id = resolve(body.get("cart_id") or body.get("customer_id"))
    code = body.get("coupon_code", "CARE10")
    entry = CARTS.get(cart_id)

    if entry is None:
        out = {"applied": False, "reason": "cart_not_found"}
        return jsonify(record("POST /coupon/apply", body, out)), 404

    items = entry["cart"]["items"]
    rx_items = [i for i in items if i["rx_required"]]
    eligible = sum(line_total(i) for i in items if not i["rx_required"])
    total = sum(line_total(i) for i in items)

    if eligible == 0:
        alt = rx_items[0]
        out = {
            "applied": False,
            "reason": "rx_items_not_discountable",
            "coupon_code": code,
            "eligible_subtotal_inr": 0,
            "new_total_inr": total,
            "excluded_items": [i["name"] for i in rx_items],
            "alternative_offered": alt["generic_alternative"],
            "alternative_saving_inr": alt["generic_saving_inr"],
            "confirmation_summary": (
                "This coupon cannot be applied because every item in the cart "
                "is a prescription medicine"
            ),
        }
    else:
        discount = round(eligible * 0.10)
        out = {
            "applied": True,
            "reason": "partial" if rx_items else "full",
            "coupon_code": code,
            "discount_inr": discount,
            "eligible_subtotal_inr": eligible,
            "new_total_inr": total - discount,
            "excluded_items": [i["name"] for i in rx_items],
            "confirmation_summary": (
                "Coupon applied, %d rupees off. Prescription items are excluded."
                % discount
                if rx_items
                else "Coupon applied, %d rupees off the order total." % discount
            ),
        }
    return jsonify(record("POST /coupon/apply", body, out))


@app.route("/payment/link", methods=["POST"])
def payment_link():
    body = request.get_json(silent=True) or {}
    out = {
        "status": "sent",
        "payment_link_id": "PAY7781",
        "channel": body.get("channel", "sms"),
        "method_hint": body.get("method_hint", "upi"),
        "expires_in_minutes": 30,
        "confirmation_summary": "Payment link sent by SMS, valid for 30 minutes",
    }
    return jsonify(record("POST /payment/link", body, out))


@app.route("/callback/schedule", methods=["POST"])
def callback_schedule():
    body = request.get_json(silent=True) or {}
    slot = body.get("requested_slot", "tomorrow 6 PM")
    out = {
        "status": "scheduled",
        "callback_id": "CB3390",
        "confirmed_slot": slot,
        "within_calling_hours": True,
        "confirmation_summary": "Callback scheduled for %s" % slot,
    }
    return jsonify(record("POST /callback/schedule", body, out))


@app.route("/call/outcome", methods=["POST"])
def call_outcome():
    body = request.get_json(silent=True) or {}
    out = {
        "status": "recorded",
        "outcome_id": "OUT9912",
        "blocker_code": body.get("blocker_code", "UNKNOWN"),
        "cart_recovered": body.get("cart_recovered", False),
        "recorded_at": now(),
    }
    return jsonify(record("POST /call/outcome", body, out))


@app.route("/compliance/adverse-event", methods=["POST"])
def adverse_event():
    body = request.get_json(silent=True) or {}
    out = {
        "status": "logged",
        "ae_reference": "AE2026-0412",
        "escalated_to": "pharmacovigilance_queue",
        "ack_within_hours": 24,
        "call_terminated_commercially": True,
        "confirmation_summary": "Adverse event logged, pharmacist will call back within 24 hours",
    }
    return jsonify(record("POST /compliance/adverse-event", body, out))


@app.route("/log", methods=["GET"])
def view_log():
    return jsonify({"count": len(REQUEST_LOG), "requests": REQUEST_LOG})


if __name__ == "__main__":
    app.run(debug=True)