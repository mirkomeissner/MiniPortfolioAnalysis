import resend
import streamlit as st

def send_duplicate_info_mail(email):
    """
    Sends a notification email via Resend API if a user tries 
    to register with an existing email address.
    """
    try:
        resend.api_key = st.secrets["RESEND_API_KEY"]
        
        params = {
            "from": "MiniPortfolioAnalysis <onboarding@resend.dev>", # Start-Adresse von Resend
            "to": email,
            "subject": "Important: Registration Attempt",
            "html": f"""
                <h3>Hello!</h3>
                <p>An attempt was made to register a new account with this email address (<strong>{email}</strong>).</p>
                <p>Since you already have an account with us, no new account was created.</p>
                <p>If this was you, you can simply log in as usual. If not, you can safely ignore this email.</p>
                <p>Best regards,<br>Your MiniPortfolioAnalysis Team</p>
            """
        }
        
        resend.Emails.send(params)
    except Exception as e:
        # We log this to the console, but don't stop the app
        print(f"Error sending Resend email: {e}")

  
