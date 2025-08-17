import streamlit as st
import json
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment, LiveEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersCaptureRequest
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# ----------------------
# Load secrets
# ----------------------
paypal_client_id = st.secrets["paypal"]["client_id"]
paypal_secret = st.secrets["paypal"]["secret"]
paypal_mode = st.secrets["paypal"].get("mode", "sandbox")  # "sandbox" or "live"
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
if paypal_mode.lower() == "live":
    environment = LiveEnvironment(client_id=paypal_client_id, client_secret=paypal_secret)
else:
    environment = SandboxEnvironment(client_id=paypal_client_id, client_secret=paypal_secret)
paypal_client = PayPalHttpClient(environment)

# ----------------------
# Products
# ----------------------
PRODUCTS = {
    "XML Key Generator Tool v4.0": {
        "file_id": "1SRI05oRIFGW6eKbpNiNVuuaLHSvKM4l1",  # Shared with service account
        "price": "20.00",
        "currency": "USD"
    },
    "Bulk XML File Generator Tool v1.0": {
        "file_id": "1abcDEFghIJKlmnOPqrsTUvWxYZ123456",  # Replace with your actual file ID
        "price": "100.00",
        "currency": "USD"
    },
    "HDD GUI Tool": {
        "file_id": "1zyXWVutSRqponMLkjIHGFEDCBA987654",  # Replace with your actual file ID
        "price": "50.00",
        "currency": "USD"
    },
    "Hikvision Video Downloader": {
        "file_id": "1a2b3c4d5e6f7g8h9i0jklmnopqrstuv",  # Replace with your actual file ID
        "price": "100.00",
        "currency": "USD"
    }
}

st.title("💻 Doitek Digital Store")

# Product selection
selected_product = st.selectbox("Choose a product:", list(PRODUCTS.keys()))
product = PRODUCTS[selected_product]

# ----------------------
# PayPal Order Creation
# ----------------------
if st.button(f"Pay ${product['price']} via PayPal"):
    request = OrdersCreateRequest()
    request.prefer("return=representation")
    request.request_body({
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "USD", "value": str(product["price"])}
        }]
    })
    try:
        response = paypal_client.execute(request)
        order_id = response.result.id
        st.success(f"✅ PayPal order created! Order ID: {order_id}")

        # Show approval link
        for link in response.result.links:
            if link.rel == "approve":
                st.markdown(f"[Click here to approve payment]({link.href})")
                st.session_state["paypal_order_id"] = order_id
    except Exception as e:
        st.error(f"Error creating order: {e}")

# ----------------------
# Capture Payment & Download
# ----------------------
if "paypal_order_id" in st.session_state:
    if st.button("Capture Payment and Get Download"):
        capture_request = OrdersCaptureRequest(st.session_state["paypal_order_id"])
        capture_request.request_body({})
        try:
            capture_response = paypal_client.execute(capture_request)
            if capture_response.result.status == "COMPLETED":
                st.success("🎉 Payment completed! Preparing secure download...")

                # Google Drive download
                file_id = product["file_id"]
                request = drive_service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)

                done = False
                while not done:
                    status, done = downloader.next_chunk()

                fh.seek(0)
                st.download_button(
                    label=f"⬇ Download {selected_product}",
                    data=fh,
                    file_name=f"{selected_product}.zip",  # adjust extension
                    mime="application/octet-stream"
                )

                # Clear order to prevent reuse
                del st.session_state["paypal_order_id"]
            else:
                st.warning(f"Payment status: {capture_response.result.status}")
        except Exception as e:
            st.error(f"Error capturing payment: {e}")


