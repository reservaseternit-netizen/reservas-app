from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import streamlit as st
import io

SCOPES = ["https://www.googleapis.com/auth/drive"]

creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES,
)

drive_service = build("drive", "v3", credentials=creds)

CARPETA_RAIZ = "1vqU3XAyaqiv_2r8CbAEmD_9_OrADKCMW"


def subir_pdf(nombre_archivo, contenido):

    archivo = io.BytesIO(contenido)

    metadata = {
        "name": nombre_archivo,
        "parents": [CARPETA_RAIZ]
    }

    media = MediaIoBaseUpload(
        archivo,
        mimetype="application/pdf"
    )

    resultado = drive_service.files().create(
        body=metadata,
        media_body=media,
        fields="id,name"
    ).execute()

    return resultado
