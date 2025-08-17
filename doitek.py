import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import base64

st.set_page_config(page_title="Doitek Digital Store", page_icon="💻")

st.title("💻 Doitek Digital Store")

# -------------------------
# Load Google Drive Credentials
# -------------------------
creds_info = json.loads(st.secrets["gdrive"]["service_account_json"])
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)

service = build("drive", "v3", credentials=credentials)

# -------------------------
# PayPal credentials
# -------------------------
PAYPAL_CLIENT_ID = st.secrets["paypal"]["client_id"]
PAYPAL_SECRET = st.secrets["paypal"]["secret"]
PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"  # Change to live URL for production

def get_paypal_access_token():
    auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    data = {"grant_type": "client_credentials"}
    r = requests.post(f"{PAYPAL_BASE_URL}/v1/oauth2/token", headers=headers, data=data, auth=auth)
    r.raise_for_status()
    return r.json()["access_token"]

def create_order(product_name, price):
    token = get_paypal_access_token()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    data = {
        "intent": "CAPTURE",
        "purchase_units": [{"amount": {"currency_code": "USD", "value": str(price)}, "description": product_name}]
    }
    r = requests.post(f"{PAYPAL_BASE_URL}/v2/checkout/orders", json=data, headers=headers)
    r.raise_for_status()
    return r.json()

def capture_order(order_id):
    token = get_paypal_access_token()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    r = requests.post(f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture", headers=headers)
    r.raise_for_status()
    return r.json()

# -------------------------
# Products
# -------------------------
products = {
    "XML Key Generator Tool v4.0": {"price": 5.0, "drive_file_id": "1SRI05oRIFGW6eKbpNiNVuuaLHSvKM4l1"},
    "Bulk XML File Generator v1.0": {"price": 7.0, "drive_file_id": "1fnySG8P15lhAkJNkOM27PcbB1j5Ut5oa"},
}

st.subheader("Choose a product:")
selected_product = st.selectbox("", list(products.keys()))

price = products[selected_product]["price"]
file_id = products[selected_product]["drive_file_id"]

if st.button(f"💳 Pay ${price} via PayPal"):
    try:
        order = create_order(selected_product, price)
        order_id = order["id"]
        st.session_state["order_id"] = order_id
        st.success(f"✅ PayPal order created! Order ID: {order_id}")
        capture = capture_order(order_id)
        if capture["status"] == "COMPLETED":
            st.success(f"🎉 Payment successful! Download {selected_product} below:")

            # Generate secure single-use Google Drive link
            request = service.files().get(fileId=file_id, fields="webContentLink, name").execute()
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            st.markdown(f"[⬇ Download {selected_product}]({download_url})")
        else:
            st.error("Payment could not be completed.")
    except requests.HTTPError as e:
        st.error(f"HTTP Error: {e}")
    except Exception as e:
        st.error(f"Error: {e}")
