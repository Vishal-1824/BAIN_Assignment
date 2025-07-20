import base64
from io import BytesIO

import streamlit as st
import requests
import json

###############################################################################
# Streamlit UI
###############################################################################
st.set_page_config(page_title="BAIN Assignment", layout="wide")

###############################################################################
# SIDEBAR
###############################################################################
QueueView = "Message Queue Controls"
MetricView = "Vendor Metrics"
QueryInterpreter = "Query Interpreter"
VisualizerView = "Metrics Visualizer"
# Sidebar navigation
view = st.sidebar.radio(
    "Select the view",
    (QueueView, MetricView, QueryInterpreter, VisualizerView),

)

st.title("Event-Driven Data Processor for Vendor Orders")

Producer_url = "http://ba_producer:8001"
Consumer_url = "http://ba_consumer:8002"
GenAIUrl =  "http://ba_gen_ai:8003"

# Main view content
if view == QueueView:
    st.header("Message Queue Controls")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            cols = st.columns([8, 2])
            with cols[0]:
                st.subheader("Kafka Producer Controls")
            with cols[1]:
                if st.session_state.get("auth_token"):
                    st.button("Logged In", key="logged_in_btn", disabled=True, type="primary")
                else:
                    if st.button("Login", key="show_login_btn"):
                        st.session_state["show_login_form"] = True

            if st.session_state.get("show_login_form", False):
                with st.form("login_form"):
                    login_url = f"{Producer_url}/token"
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Login")
                    if submitted:
                        try:
                            resp = requests.post(login_url, data={"username": username, "password": password})
                            if resp.ok:
                                token = resp.json().get("access_token")
                                if token:
                                    st.session_state["auth_token"] = token
                                    st.success("Login successful. Token stored.")
                                    st.session_state["show_login_form"] = False
                                else:
                                    st.error("Token not found in response.")
                            else:
                                st.error(f"Login failed: {resp.text}")
                        except Exception as e:
                            st.error(f"Login error: {e}")

            # Example: Use token in API requests
            headers = {}
            if "auth_token" in st.session_state:
                headers["Authorization"] = f"Bearer {st.session_state['auth_token']}"

            if st.button(key="topics1", label="List Topics"):
                try:
                    resp = requests.get(f"{Producer_url}/get_topic_list", headers=headers)
                    if resp.ok:
                        topics = resp.json().get("topics", [])
                        st.write("Topics:", [t for t in topics if not t.startswith("_")])
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect: {e}")

            # Add Topic
            st.subheader("Add Topic")
            topic_name = st.text_input("Topic Name")
            # num_partitions = st.number_input("Partitions", min_value=1, max_value=100, value=1)
            # replication_factor = st.number_input("Replication Factor", min_value=1, max_value=3, value=1)
            if st.button("Add Topic"):
                try:
                    params = {
                        "topic_name": topic_name,
                        # "num_partitions": num_partitions,
                        # "replication_factor": replication_factor
                    }
                    resp = requests.post(f"{Producer_url}/create_topic", params=params, headers=headers)
                    if resp.ok:
                        st.success(resp.text)
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect to Producer: {str(e)}")

            # Send Data
            st.subheader("Send Data")
            send_topic = st.text_input("Send to Topic",)
            ord_data = {
                "vendor_id": "V001",
                "order_id": "ORD123",
                "items": [
                    { "sku": "SKU1", "qty": 2, "unit_price": 120 },
                    { "sku": "SKU2", "qty": 1, "unit_price": 50 }
                ],
                "timestamp": "2025-07-04T14:00:00Z"
            }
            data_json = st.text_area("Data (JSON)", value=json.dumps(ord_data, indent=2), height=200)
            if st.button("Send Data"):
                import json
                try:
                    data = json.loads(data_json)
                    params = {"topic": send_topic}
                    resp = requests.post(f"{Producer_url}/send_data", params=params, json={"data": data, "topic": send_topic}, headers=headers)
                    if resp.ok:
                        st.success(resp.text)
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")

            # Start Data Stream
            if st.button("Start Data Stream"):
                try:
                    resp = requests.post(f"{Producer_url}/start_data_stream", headers=headers)
                    if resp.ok:
                        st.success(resp.text)
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect to Producer: {str(e)}")

            # Stop Data Stream
            if st.button("Stop Data Stream"):
                try:
                    resp = requests.post(f"{Producer_url}/stop_data_stream", headers=headers)
                    if resp.ok:
                        st.success(resp.text)
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect to Producer: {str(e)}")

    with col2:
        with st.container(border=True):
            cols = st.columns([8, 2])
            with cols[0]:
                st.subheader("Kafka Consumer Controls")
            with cols[1]:
                if st.session_state.get("auth_token2"):
                    st.button("Logged In", key="logged_in_btn2", disabled=True, type="primary")
                else:
                    if st.button("Login", key="show_login_btn2"):
                        st.session_state["show_login_form2"] = True

            if st.session_state.get("show_login_form2", False):
                with st.form("login_form2"):
                    login_url = f"{Consumer_url}/token"
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Login")
                    if submitted:
                        try:
                            resp = requests.post(login_url, data={"username": username, "password": password})
                            if resp.ok:
                                token = resp.json().get("access_token")
                                if token:
                                    st.session_state["auth_token2"] = token
                                    st.success("Login successful. Token stored.")
                                    st.session_state["show_login_form2"] = False
                                else:
                                    st.error("Token not found in response.")
                            else:
                                st.error(f"Login failed: {resp.text}")
                        except Exception as e:
                            st.error(f"Login error: {e}")

            # Example: Use token in API requests
            headers = {}
            if "auth_token2" in st.session_state:
                headers["Authorization"] = f"Bearer {st.session_state['auth_token2']}"

            # List Topics
            if st.button(key="topics2", label="List Topics"):
                try:
                    resp = requests.get(f"{Consumer_url}/get_topic_list", headers=headers)
                    if resp.ok:
                        topics = resp.json().get("topics", [])
                        st.write("Topics:", [t for t in topics if not t.startswith("_")])
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect: {e}")

            # Subscribe to Topic
            subscribe_topic = st.text_input("Subscribe to Topic")
            if st.button("Subscribe"):
                try:
                    resp = requests.post(f"{Consumer_url}/subscribe_topic", params={"topic": subscribe_topic}, headers=headers)
                    if resp.ok:
                        st.success(resp.text)
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect: {e}")

            # Get Data
            if st.button("Get Data"):
                try:
                    resp = requests.get(f"{Consumer_url}/get_data", headers=headers)
                    if resp.ok:
                        st.json(resp.json())
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect: {e}")

            # Save Stream Data to DB
            save_topic = st.text_input("Save Stream Data for Topic")
            if st.button("Save Stream Data to DB"):
                try:
                    resp = requests.post(f"{Consumer_url}/save_stream_data_to_db", params={"topic": save_topic}, headers=headers)
                    if resp.ok:
                        st.success(resp.json().get("message", resp.text))
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect: {e}")

            # Stop Data Stream
            if st.button("Stop Saving to DB Data Stream"):
                try:
                    resp = requests.post(f"{Consumer_url}/stop_data_stream", headers=headers)
                    if resp.ok:
                        st.success(resp.text)
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect: {e}")

elif view == MetricView:
    st.header("Vendor Metrics")
    st.write("Get the metrics for a particular vendor.")


    # Button to fetch and display available vendors
    if st.button("Get Available Vendors"):
        try:
            resp = requests.get(f"{Consumer_url}/get_vendors")
            if resp.ok:
                vendors = resp.json().get("vendors", [])
                st.markdown("**Available Vendors:**")
                st.write(", ".join(vendors) if vendors else "No vendors found.")
            else:
                st.error(f"Error fetching vendors: {resp.text}")
        except Exception as e:
            st.error(f"Failed to fetch vendors: {e}")

    vendor_id = st.text_input("Enter Vendor ID")
    if st.button("Get Metrics"):
        if not vendor_id.strip():
            st.error("Vendor ID cannot be empty.")
        else:
            try:
                api_url = f"{Consumer_url}/metrics"  # Replace with actual host/port
                resp = requests.post(api_url, params={"vendor_id": vendor_id})
                if resp.status_code == 200:
                    metrics = resp.json()
                    st.subheader("Metrics")
                    st.json(metrics)
                elif resp.status_code == 404:
                    st.error("Vendor not found.")
                else:
                    st.error(f"Error: {resp.text}")
            except Exception as e:
                st.error(f"Failed to fetch metrics: {e}")
elif view == QueryInterpreter:
    st.header("Query Interpreter")
    st.write("Ask a question about your data or system.")

    user_query = st.text_input("Enter your query")
    if st.button("Submit Query"):
        if not user_query.strip():
            st.error("Query cannot be empty.")
        else:
            try:
                resp = requests.post(f"{GenAIUrl}/query", json={"question": user_query})
                if resp.ok:
                    data = resp.json()
                    st.markdown(f"**Question:** {data.get('question')}")
                    st.markdown(f"**Answer:** {data.get('answer')}")
                else:
                    st.error(f"API error: {resp.text}")
            except Exception as e:
                st.error(f"Request failed: {e}")
elif view == VisualizerView:
    st.header("Metrics Visualizer")
    vendor_id = st.text_input("Vendor ID for Visualisation")
    if st.button("Visualize"):
        try:
            resp = requests.post(f"{GenAIUrl}/visualise", params={"vendor_id": vendor_id})
            if resp.ok:
                data = resp.json()
                img_base64 = data.get("visualisation_base64")
                if img_base64:
                    img_bytes = base64.b64decode(img_base64)
                    st.image(BytesIO(img_bytes), caption=f"Visualisation for Vendor {vendor_id}")
                else:
                    st.error("No image data received from API.")
            else:
                st.error(f"API error: {resp.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")