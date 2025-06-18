import streamlit as st
import requests

st.title("Simple Data Agent System (LLM + Pandas)")

st.header("Upload your CSV and get columns")
uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
session_id = st.session_state.get("session_id")
columns = None

if uploaded_file and not session_id:
    files = {"file": uploaded_file}
    resp = requests.post("http://localhost:9000/upload", files=files)
    if resp.status_code == 200:
        upload_result = resp.json()
        session_id = upload_result.get("session_id")
        columns = upload_result.get("columns")
        if session_id:
            st.session_state["session_id"] = session_id
        if columns:
            st.subheader("Columns")
            st.write(columns)
    else:
        st.error(f"Upload error: {resp.text}")

if session_id:
    columns = columns or st.session_state.get("columns")
    if columns:
        st.subheader("Columns")
        st.write(columns)
    user_query = st.text_input("Your question:")
    if user_query:
        if st.button("Ask"):
            data = {"session_id": session_id, "query": user_query}
            resp = requests.post("http://localhost:9000/ask", data=data)
            if resp.status_code == 200:
                result = resp.json()
                st.subheader("Answer")
                st.write(result.get("answer", "No answer returned."))
                st.subheader("Pandas Code")
                st.code(result.get("pandas_code", ""), language="python")
                if result.get("sandbox_output"):
                    st.subheader("Sandbox Output")
                    st.text(result["sandbox_output"])
            else:
                st.error(f"Error: {resp.text}")
