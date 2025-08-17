import streamlit as st
import requests
import json
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build

# -----------------------
# CONFIGURATION
# -----------------------

PRODUCTS = {
    "XML Key Generator Tool v4.0": {"file_id": "1SRI05oRIFGW6eKbpNiNVuuaLHSvKM4l1", "price": 5.0},
    "Bulk XML File Generator Tool v1.0": {"file_id": "1fnySG8P15lhAkJNkOM27PcbB1j5Ut5oa", "price": 3.0},
    "HDD GUI Tool": {"file_id": "1ADyxtRVz4q4O-sAMFa-Q8w4tbvra-L10", "price": 4.0},
    "Hikvision Video Downloader": {"file_id": "1gsFrb5Fz5DozAsR2V65aoLfCCTL6bIbN", "price": 6.0}
}

# -----------------------
# PAYPAL CONFIG FROM STREAMLIT SECRETS
# -----------------------

BASE_URL = "https://api-m.sandbox.paypal.com" if st.secrets.get("paypal_sandbox", True) else "https://api-m.paypal.com"
PAYPAL_CLIENT_ID = st.secrets["paypal"]["client_id"]
PAYPAL_SECRET = st.secrets["paypal"]["secret"]

# -----------------------
# GOOGLE DRIVE API SETUP FROM STREAMLIT SECRETS
# -----------------------

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
creds_info = json.loads(st.secrets["gdrive"]["service_account_json"])
credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# -----------------------
# FUNCTIONS
# -----------------------

def generate_secure_link(file_id, expire_seconds=300):
    """Generate a temporary link to a Google Drive file."""
    # Google Drive API does not directly support expiring links,
    # but we can use the webContentLink and control access via sharing
    request = drive_service.files().get(fileId=file_id, fields='webContentLink')
    file = request.execute()
    return file.get('webContentLink')

# PAYPAL Functions
def get_access_token(client_id, secret):
    url = f"{BASE_URL}/v1/oauth2/token"
    resp = requests.post(url, auth=(client_id, secret), data={"grant_type": "client_credentials"})
    resp.raise_for_status()
    return resp.json().get("access_token")

def create_order(amount, currency, access_token, product_name):
    url = f"{BASE_URL}/v2/checkout/orders"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = {
        "intent": "CAPTURE",
        "purchase_units": [{"amount": {"currency_code": currency, "value": str(amount)}, "description": product_name}]
    }
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()

def get_order(order_id, access_token):
    url = f"{BASE_URL}/v2/checkout/orders/{order_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def capture_order(order_id, access_token):
    url = f"{BASE_URL}/v2/checkout/orders/{order_id}/capture"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

# -----------------------
# STREAMLIT UI
# -----------------------

st.title("💻 Doitek Digital Store")

mode = st.radio("Select Mode:", ["Sandbox (Test)", "Live (Real Payments)"])
BASE_URL = "https://api-m.sandbox.paypal.com" if mode.startswith("Sandbox") else "https://api-m.paypal.com"

# Select product
product_name = st.selectbox("Choose a product:", list(PRODUCTS.keys()))
price = PRODUCTS[product_name]["price"]
st.write(f"💰 Price: **${price} USD**")

# Step 1: Create order
if st.button("Buy with PayPal"):
    try:
        access_token = get_access_token(PAYPAL_CLIENT_ID, PAYPAL_SECRET)
        order = create_order(price, "USD", access_token, product_name)

        if "id" in order:
            order_id = order["id"]
            st.session_state["order_id"] = order_id
            st.session_state["access_token"] = access_token
            st.session_state["product_name"] = product_name

            # Find approval link
            for link in order["links"]:
                if link["rel"] == "approve":
                    approval_url = link["href"]
                    st.markdown(f"[👉 Click here to Pay on PayPal]({approval_url})")
            st.info("✅ After payment approval, click 'Confirm Payment' below.")
        else:
            st.error("❌ Failed to create PayPal order. Check credentials.")
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ HTTP Error: {e}")

# Step 2: Confirm payment
if "order_id" in st.session_state:
    if st.button("Confirm Payment"):
        order_id = st.session_state["order_id"]
        access_token = st.session_state["access_token"]
        product_name = st.session_state["product_name"]

        try:
            order_info = get_order(order_id, access_token)
            status = order_info.get("status", "")

            if status == "APPROVED":
                result = capture_order(order_id, access_token)
                if result.get("status") == "COMPLETED":
                    file_id = PRODUCTS[product_name]["file_id"]
                    download_link = generate_secure_link(file_id)
                    st.success(f"🎉 Payment successful! Download **{product_name}** here:")
                    st.markdown(f"[⬇ Download {product_name}]({download_link})")
                else:
                    st.warning("⚠ Payment capture failed.")
            elif status == "CREATED":
                st.warning("⚠ Order not approved yet. Please complete PayPal approval first.")
            elif status == "COMPLETED":
                st.success("✅ Payment already captured.")
                file_id = PRODUCTS[product_name]["file_id"]
                download_link = generate_secure_link(file_id)
                st.markdown(f"[⬇ Download {product_name}]({download_link})")
            else:
                st.error(f"⚠ Cannot capture payment. Current order status: {status}")

        except requests.exceptions.HTTPError as e:
            st.error(f"❌ HTTP Error: {e}")
