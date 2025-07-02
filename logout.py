import streamlit as st

def show_logout():
    st.subheader("🚪 Logout")

    st.write(f"Anda login sebagai **{st.session_state.get('username', 'Tidak diketahui')}**.")

    if st.button("Konfirmasi Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.page = "login"  # Redirect ke login page
        st.success("Logout berhasil! Mengalihkan ke halaman login...")
        st.rerun()
