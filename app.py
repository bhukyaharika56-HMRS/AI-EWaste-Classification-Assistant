
import streamlit as st
import ollama
import pandas as pd
import sqlite3
from datetime import datetime
from PIL import Image
from io import BytesIO

# =========================
# PAGE CONFIGURATION
# =========================
st.set_page_config(
    page_title="AI E-Waste Assistant",
    page_icon="♻️",
    layout="wide"
)

DB_NAME = "ewaste.db"

st.title("♻️ AI E-Waste Classification & Recycling Assistant")
st.write(
    "Identify electronic waste, learn recycling practices, "
    "and ask questions using a local AI chatbot."
)

# =========================
# SESSION STATE
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "latest_image_result" not in st.session_state:
    st.session_state.latest_image_result = None

# =========================
# SQLITE DATABASE
# =========================
def initialize_database():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_time TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                result TEXT NOT NULL
            )
        """)


def save_record(source, category, result):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO history
            (date_time, source, category, result)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            source,
            category,
            result
        ))


def get_history():
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("""
            SELECT
                date_time AS 'Date and Time',
                source AS 'Source',
                category AS 'Category',
                result AS 'Result'
            FROM history
            ORDER BY id DESC
        """, conn)

    return df


def clear_database_history():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM history")


initialize_database()

# =========================
# RECYCLING GUIDANCE
# =========================
recycling_guidance = {
    "Mobile Phone": (
        "Take the phone to an authorized e-waste collection centre "
        "or manufacturer take-back programme. Erase personal data first."
    ),
    "Battery": (
        "Keep batteries away from heat. Do not burn, crush, or put "
        "them in household waste. Use an authorized battery collection point."
    ),
    "Laptop / Computer": (
        "Back up and erase personal data, then give the device to an "
        "authorized e-waste recycler."
    ),
    "Charger / Cable": (
        "Collect cables and chargers separately and take them to an "
        "authorized electronics recycling centre."
    ),
    "Television / Monitor": (
        "Arrange collection through an authorized e-waste recycler. "
        "Do not dismantle the screen yourself."
    ),
    "Other Electronic Waste": (
        "Keep electronic waste separate from regular rubbish and take "
        "it to an authorized e-waste collection centre."
    )
}

# =========================
# CATEGORY DETECTION
# =========================
def detect_category(description):
    text = description.lower()

    if any(word in text for word in [
        "television", "monitor", "computer screen"
    ]):
        return "Television / Monitor"

    if any(word in text for word in [
        "battery", "batteries"
    ]):
        return "Battery"

    if any(word in text for word in [
        "mobile phone", "smartphone", "cell phone", "iphone"
    ]):
        return "Mobile Phone"

    if any(word in text for word in [
        "laptop", "notebook computer", "desktop computer", "pc tower"
    ]):
        return "Laptop / Computer"

    if any(word in text for word in [
        "charger", "charging cable", "usb cable", "power cable",
        "charging adapter", "power adapter"
    ]):
        return "Charger / Cable"

    return "Unclassified AI result"


# =========================
# PROJECT DASHBOARD
# =========================
st.divider()
st.header("📊 Project Dashboard")

history_df = get_history()

total = len(history_df)

if total > 0:
    image_count = int(
        (history_df["Source"] == "Image Analysis").sum()
    )
    manual_count = int(
        (history_df["Source"] == "Manual Selection").sum()
    )
else:
    image_count = 0
    manual_count = 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Records", total)
col2.metric("Images Analyzed", image_count)
col3.metric("Manual Selections", manual_count)

st.subheader("📈 Category Statistics")

if not history_df.empty:
    category_counts = history_df["Category"].value_counts()
    st.bar_chart(category_counts)
else:
    st.info("Analyze an image or save a category to populate the dashboard.")

# =========================
# IMAGE ANALYSIS
# =========================
st.divider()
st.header("📷 1. Identify E-Waste from an Image")

uploaded_file = st.file_uploader(
    "Upload an electronic-waste image",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    image_bytes = uploaded_file.getvalue()
    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    st.image(image, caption="Uploaded Image", width=350)

    if st.button("🔍 Analyze Image", key="analyze_image"):
        with st.spinner("Ollama is analyzing the image..."):
            try:
                response = ollama.chat(
                    model="moondream",
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "Carefully identify the main object in the image. "
                                "Describe its visible features. Decide whether it is "
                                "electronic waste, ordinary waste, or uncertain. "
                                "If it is electronic waste, identify the likely category "
                                "such as mobile phone, battery, laptop, charger, cable, "
                                "or television. Explain your decision briefly and give "
                                "safe recycling guidance. Never guess when the image "
                                "is unclear."
                            ),
                            "images": [image_bytes]
                        }
                    ]
                )

                analysis_result = response["message"]["content"]
                detected_category = detect_category(analysis_result)

                st.session_state.latest_image_result = analysis_result

                st.subheader("Image Analysis Result")
                st.write(analysis_result)
                st.write(f"**Suggested category:** {detected_category}")

                save_record(
                    source="Image Analysis",
                    category=detected_category,
                    result=analysis_result
                )

                st.success("Image analysis completed and saved permanently.")

            except Exception as e:
                st.error(
                    "Image analysis failed. Check that Ollama is running "
                    "and the Moondream model is installed."
                )
                st.caption(str(e))

if st.session_state.latest_image_result:
    st.subheader("Latest Image Analysis")
    st.write(st.session_state.latest_image_result)

# =========================
# MANUAL CATEGORY SELECTION
# =========================
st.divider()
st.header("♻️ 2. Recycling Guidance")

category = st.selectbox(
    "Select an electronic-waste category",
    list(recycling_guidance.keys())
)

st.subheader("Recommended Recycling Method")
st.write(recycling_guidance[category])

if st.button("Save Category to History", key="save_category"):
    save_record(
        source="Manual Selection",
        category=category,
        result=recycling_guidance[category]
    )
    st.success("Category saved permanently!")

# =========================
# OLLAMA CHATBOT
# =========================
st.divider()
st.header("🤖 3. E-Waste AI Chatbot")
st.caption("Ask questions about electronic waste and recycling.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

with st.form("chat_form", clear_on_submit=True):
    user_question = st.text_input(
        "Your question",
        placeholder="How should I recycle an old mobile phone?"
    )
    send_message = st.form_submit_button("Send")

if send_message and user_question.strip():
    st.session_state.messages.append({
        "role": "user",
        "content": user_question.strip()
    })

    with st.spinner("Thinking..."):
        try:
            response = ollama.chat(
                model="gemma3:1b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful e-waste recycling assistant. "
                            "Give simple, practical and safe recycling advice. "
                            "Recommend authorized recycling centres. "
                            "Do not advise users to dismantle hazardous "
                            "electronics or batteries."
                        )
                    }
                ] + st.session_state.messages
            )

            answer = response["message"]["content"]

        except Exception as e:
            answer = (
                "Sorry, I could not connect to Ollama. Check that Ollama "
                "is running and gemma3:1b is installed."
            )
            st.error(str(e))

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    st.rerun()

# =========================
# CLASSIFICATION HISTORY
# =========================
st.divider()
st.header("📋 4. Classification History")

history_df = get_history()

if not history_df.empty:
    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True
    )

    csv_data = history_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download History as CSV",
        data=csv_data,
        file_name="ewaste_classification_history.csv",
        mime="text/csv"
    )

    if st.button("🗑️ Clear History", key="clear_history"):
        clear_database_history()
        st.rerun()

else:
    st.info("No history saved yet. Analyze an image or save a category.")

# =========================
# FOOTER
# =========================
st.divider()
st.caption(
    "AI-assisted educational project | Verify recycling instructions "
    "with an authorized e-waste collection centre."
)