import streamlit as st

st.set_page_config(
    page_title="Test App",
    layout="centered"
)

st.title("✅ App is working")

st.write("""
If you can see this page, then:

- Streamlit deployment is working
- app.py is being loaded correctly
- The problem is in your original code or requirements
""")

st.success("Test successful!")
