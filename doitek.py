import streamlit as st
import json
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime

# ----------------------
# Load secrets
# ----------------------
paypal_client_id = st.secrets["paypal"]["client_id"]
paypal_secret = st.secrets["paypal"]["secret"]
gdrive_json = json.loads(st.secrets["gdrive"]["service_account_json"])

# ----------------------
# Google Drive setup
# ----------------------
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
credentials = service_account.Credentials.from_service_account_info(
    gdrive_json, scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=credentials)

# ----------------------
# PayPal setup
# ----------------------
environment = SandboxEnvironment(client_id=paypal_client_id, client_secret=paypal_secret)
paypal_client = PayPalHttpClient(environment)

# ----------------------
# Products
# ----------------------
products = {
    "XML Key Generator Tool v4.0": {
        "price": "5.00",
        "currency": "USD",
        "file_id": "1SRI05oRIFGW6eKbpNiNVuuaLHSvKM4l1"  # Replace with your file ID
    }
}

st.title("💻 Doitek Digital Store")

# Product selection
selected_product = st.selectbox("Choose a product:", list(products.keys()))
product = products[selected_product]

# ----------------------
# PayPal Order Creation
# ----------------------
if st.button(f"Pay ${product['price']} via PayPal Sandbox"):
    # 1️⃣ Create Order
    request = OrdersCreateRequest()
    request.prefer("return=representation")
    request.request_body({
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": product["currency"], "value": product["price"]}
        }]
    })
    try:
        response = paypal_client.execute(request)
        order_id = response.result.id
        st.success(f"✅ PayPal order created! Order ID: {order_id}")

        # 2️⃣ Show approval link
        for link in response.result.links:
            if link.rel == "approve":
                st.markdown(f"[Click here to approve payment]({link.href})")
                st.session_state["paypal_order_id"] = order_id
    except Exception as e:
        st.error(f"Error creating order: {e}")

# ----------------------
# Capture payment after approval
# ----------------------
if "paypal_order_id" in st.session_state:
    if st.button("Capture Payment"):
        capture_request = OrdersCaptureRequest(st.session_state["paypal_order_id"])
        capture_request.request_body({})
        try:
            capture_response = paypal_client.execute(capture_request)
            if capture_response.result.status == "COMPLETED":
                st.success("🎉 Payment completed! Generating secure download link...")

                # ----------------------
                # Generate Google Drive file link
                # ----------------------
                file_id = product["file_id"]
                expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
                download_link = f"https://drive.google.com/uc?id={file_id}&export=download"
                st.markdown(f"[⬇ Download {selected_product}]({download_link})")
            else:
                st.warning(f"Payment status: {capture_response.result.status}")
        except Exception as e:
            st.error(f"Error capturing payment: {e}")

