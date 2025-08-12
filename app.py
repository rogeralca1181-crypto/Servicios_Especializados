import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import threading
import schedule
import time

# ==============================
# CONFIGURACIONES
# ==============================
NOMBRE_HOJA = "Servicios_Especializados"  # Nombre de tu Google Sheet

# WhatsApp Cloud API (Meta)
ACCESS_TOKEN = "aaf9786688b3bfffaf936cf5b7afe3cc"
PHONE_NUMBER_ID = "1225507482591128"

# ==============================
# 1. Conexión a Google Sheets
# ==============================
def cargar_datos():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open(NOMBRE_HOJA).sheet1
    data = sheet.get_all_records()

    return pd.DataFrame(data)

# ==============================
# 2. Procesamiento
# ==============================
def obtener_resumen(df):
    resumen = df["Estado_Entrega"].value_counts().reset_index()
    resumen.columns = ["Estado", "Cantidad"]
    pendientes = df[df["Estado_Entrega"].isin(["No Entregado", "Corrección"])]
    return resumen, pendientes

# ==============================
# 3. Envío de recordatorios con WhatsApp Cloud API
# ==============================
def enviar_recordatorio(pendientes):
    if pendientes.empty:
        print("No hay pendientes para enviar mensajes.")
        return 0

    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    enviados = 0
    for _, fila in pendientes.iterrows():
        data = {
            "messaging_product": "whatsapp",
            "to": str(fila["Teléfono"]),
            "type": "text",
            "text": {
                "body": f"Hola {fila['Nombre']}, recuerda entregar o corregir tu reporte mensual de actividades."
            }
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            enviados += 1
        else:
            print(f"Error enviando a {fila['Teléfono']}: {response.text}")

    print(f"Mensajes enviados a {enviados} personas.")
    return enviados

# ==============================
# 4. Tarea automática diaria
# ==============================
def tarea_programada():
    df = cargar_datos()
    _, pendientes = obtener_resumen(df)
    enviados = enviar_recordatorio(pendientes)
    print(f"Tarea diaria ejecutada. Mensajes enviados: {enviados}")

def iniciar_programacion():
    # Ejecutar cada día a las 9:00 AM
    schedule.every().day.at("09:00").do(tarea_programada)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Lanzar en hilo separado para no bloquear el dashboard
threading.Thread(target=iniciar_programacion, daemon=True).start()

# ==============================
# 5. Dashboard con Dash
# ==============================
app = Dash(__name__)
app.title = "Dashboard Entregas"

app.layout = html.Div([
    html.H1("Dashboard de Entregas", style={"textAlign": "center"}),

    dcc.Graph(id="grafico-pie"),
    dcc.Graph(id="grafico-bar"),

    html.Button("Enviar Recordatorios por WhatsApp", id="btn-recordatorios", n_clicks=0),
    html.Div(id="output-mensaje", style={"marginTop": "20px", "fontWeight": "bold"}),

    # Auto-refresh cada 60 segundos
    dcc.Interval(id="intervalo-actualizacion", interval=60*1000, n_intervals=0)
])

# Callback para actualizar gráficos automáticamente
@app.callback(
    [Output("grafico-pie", "figure"),
     Output("grafico-bar", "figure")],
    [Input("intervalo-actualizacion", "n_intervals")]
)
def actualizar_graficos(n):
    df = cargar_datos()
    resumen, pendientes = obtener_resumen(df)

    fig_pie = px.pie(resumen, names="Estado", values="Cantidad", title="Estado de Entrega de Reportes")
    fig_bar = px.bar(
        pendientes,
        x="Nombre",
        y="Estado_Entrega",
        color="Estado_Entrega",
        title="Pendientes de Entrega/Corrección"
    )
    return fig_pie, fig_bar

# Callback para botón de envío manual
@app.callback(
    Output("output-mensaje", "children"),
    Input("btn-recordatorios", "n_clicks"),
    prevent_initial_call=True
)
def enviar_mensajes_manual(n_clicks):
    df = cargar_datos()
    _, pendientes = obtener_resumen(df)
    enviados = enviar_recordatorio(pendientes)
    return f"Mensajes enviados manualmente a {enviados} personas."

# ==============================
# Ejecutar
# ==============================
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
"""
