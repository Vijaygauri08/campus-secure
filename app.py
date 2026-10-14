import cv2
import numpy as np
import pandas as pd
import streamlit as st
from src import database as db
from src.anpr import detect_and_read, is_valid
from src.rules import decide

st.set_page_config(page_title="Campus Secure", page_icon="🚗", layout="wide")
db.init()
st.title("🚗 Campus Secure – Automated Vehicle Monitoring")
page = st.sidebar.radio("Menu", ["Scan Vehicle", "Register Vehicle", "Logs & Alerts"])

if page == "Scan Vehicle":
    gate = st.selectbox("Gate", ["Main Gate", "Hostel Gate", "Back Gate"])
    up = st.file_uploader("Upload vehicle image", type=["jpg", "jpeg", "png"])
    if up:
        img = cv2.imdecode(np.frombuffer(up.read(), np.uint8), cv2.IMREAD_COLOR)
        res = detect_and_read(img)
        st.image(cv2.cvtColor(res["annotated"], cv2.COLOR_BGR2RGB), use_container_width=True)
        if res["box"] is None:
            st.warning("No plate localised - enter the number manually.")
        plate = st.text_input("Detected plate (edit if wrong)", res["plate"]).strip().upper()
        if st.button("Confirm & log"):
            decision, msg = decide(plate, is_valid(plate))
            event = db.next_event(plate) if plate else "ENTRY"
            db.log_event(plate, event, gate, decision)
            {"ALLOW": st.success, "REVIEW": st.warning, "DENY": st.error, "ALERT": st.error}[decision](
                f"{decision} ({event}): {msg}")

elif page == "Register Vehicle":
    with st.form("reg"):
        plate = st.text_input("Plate number").strip().upper()
        owner = st.text_input("Owner name")
        cat = st.selectbox("Category", db.CATEGORIES)
        if st.form_submit_button("Save"):
            if is_valid(plate):
                db.add_vehicle(plate, owner, cat)
                st.success("Saved.")
            else:
                st.error("Invalid plate format (expected e.g. MH31AB1234).")
    st.dataframe(pd.DataFrame(db.all_vehicles(), columns=["Plate", "Owner", "Category"]))

else:
    hours = st.slider("Visitor overstay limit (hours)", 1, 12, 4)
    for plate, ts in db.overstaying_visitors(hours):
        st.error(f"⏰ Visitor {plate} inside since {ts}")
    logs = pd.DataFrame(db.recent_logs(), columns=["Time", "Plate", "Event", "Gate", "Decision"])
    st.dataframe(logs, use_container_width=True)
    st.download_button("Export CSV", logs.to_csv(index=False), "campus_logs.csv")
