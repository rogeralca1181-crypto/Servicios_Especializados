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
import os # Importar 'os' para leer variables de entorno

# ==============================
# CONFIGURACIONES
# ==============================
# Nombre de tu hoja de cálculo en Google Sheets
NOMBRE_HOJA = "Servicios_Especializados" 

# --- IMPORTANTE: CONFIGURACIÓN DE WHATSAPP ---
# Se recomienda configurar estas credenciales como "Environment Variables" en Render.
ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "TU_ACCESS_TOKEN_AQUI")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_ID", "TU_PHONE_ID_AQUI")
API_VERSION = "v19.0" # Usar una versión reciente de la API

# --- ¡NUEVO! DEBES CONFIGURAR ESTO ---
# 1. Ve a tu cuenta de Meta for Developers > WhatsApp > Message Templates.
# 2. Crea una plantilla. Por ejemplo, con el nombre "recordatorio_entrega".
# 3. En el cuerpo (Body) de la plantilla, escribe tu mensaje usando una variable:
#    "Hola {{1}}, recuerda entregar o corregir tu reporte mensual de actividades. ¡Gracias!"
# 4. Una vez aprobada, pon el nombre exacto de la plantilla aquí abajo.
NOMBRE_PLANTILLA_WHATSAPP = "recordatorio_entrega" # Reemplaza con el nombre de tu plantilla


# ==============================
# 1. Conexión a Google Sheets y Carga de Datos
# ==============================
def cargar_datos():
    """
    Se conecta a Google Sheets, carga los datos y los limpia, 
    asegurando que solo se procesen los estados de entrega válidos.
    """
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Asegúrate de que tu archivo 'credentials.json' esté en el repositorio
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)

        sheet = client.open(NOMBRE_HOJA).sheet1
        
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return pd.DataFrame(columns=["Nombre", "Estado_Entrega", "Teléfono"])
            
        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers)

        estados_validos = ["Entregado", "No Entregado", "Correccion"]
        if "Estado_Entrega" in df.columns:
            df = df[df["Estado_Entrega"].isin(estados_validos)].copy()
            if "Teléfono" in df.columns:
                 df["Teléfono"] = df["Teléfono"].astype(str).str.strip()
        else:
            print("Error: La columna 'Estado_Entrega' no se encontró en la hoja.")
            return pd.DataFrame(columns=["Nombre", "Estado_Entrega", "Teléfono"])

        return df

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Error: No se encontró la hoja de cálculo con el nombre '{NOMBRE_HOJA}'.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Ocurrió un error inesperado al cargar los datos: {e}")
        return pd.DataFrame()

# ==============================
# 2. Procesamiento de Datos para Gráficos
# ==============================
def obtener_resumen(df):
    """
    Genera un resumen para el gráfico de pastel y una lista de pendientes.
    """
    if df.empty or "Estado_Entrega" not in df.columns:
        return pd.DataFrame(columns=["Estado", "Cantidad"]), pd.DataFrame()

    resumen = df["Estado_Entrega"].value_counts().reset_index()
    resumen.columns = ["Estado", "Cantidad"]
    # El filtro ya era correcto: solo toma en cuenta "No entregado" y "Corrección".
    pendientes = df[df["Estado_Entrega"].isin(["No entregado", "Corrección"])]
    return resumen, pendientes

# ==============================
# 3. Envío de Recordatorios con WhatsApp Cloud API (VERSIÓN ACTUALIZADA)
# ==============================
def enviar_recordatorio(pendientes):
    """
    Envía un mensaje de recordatorio usando una PLANTILLA DE MENSAJE pre-aprobada.
    Retorna el número de mensajes enviados y una lista de errores.
    """
    if pendientes.empty:
        return 0, []

    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    enviados_count = 0
    errores = []
    for _, fila in pendientes.iterrows():
        if not all(k in fila and fila[k] for k in ["Nombre", "Teléfono"]):
            errores.append(f"Fila ignorada por falta de datos: {fila.to_dict()}")
            continue

        # --- CAMBIO IMPORTANTE: Payload para usar plantillas ---
        data = {
            "messaging_product": "whatsapp",
            "to": str(fila["Teléfono"]),
            "type": "template",
            "template": {
                "name": NOMBRE_PLANTILLA_WHATSAPP,
                "language": { "code": "es_MX" }, # O el código de tu idioma, ej: "es"
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": str(fila["Nombre"])
                            }
                        ]
                    }
                ]
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            enviados_count += 1
        except requests.exceptions.RequestException as e:
            error_msg = f"Error enviando a {fila['Nombre']} ({fila['Teléfono']}): {e}"
            if e.response is not None:
                error_msg += f" | Detalle: {e.response.text}"
            print(error_msg)
            errores.append(error_msg)

    print(f"Proceso finalizado. Mensajes enviados: {enviados_count}. Errores: {len(errores)}.")
    return enviados_count, errores

# ==============================
# 4. Tarea Automática Diaria (Opcional)
# ==============================
def tarea_programada():
    print("Ejecutando tarea diaria de recordatorios...")
    df = cargar_datos()
    _, pendientes = obtener_resumen(df)
    enviados, errores = enviar_recordatorio(pendientes)
    print(f"Tarea diaria ejecutada. Mensajes enviados: {enviados}. Errores: {len(errores)}")

def iniciar_programacion():
    schedule.every().day.at("09:00").do(tarea_programada)
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=iniciar_programacion, daemon=True).start()

# ==============================
# 5. Dashboard con Dash
# ==============================
app = Dash(__name__)
server = app.server
app.title = "Dashboard de Entregas"

app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'padding': '20px'}, children=[
    html.H1("Dashboard de Seguimiento de Entregas", style={"textAlign": "center", "color": "#333"}),
    html.Div(id="live-update-text", style={"textAlign": "center", "marginBottom": "20px"}),
    dcc.Graph(id="grafico-pie"),
    dcc.Graph(id="grafico-bar"),
    html.Div(style={"textAlign": "center", "marginTop": "30px"}, children=[
        html.Button("Enviar Recordatorios Manualmente", id="btn-recordatorios", n_clicks=0, 
                    style={
                        'backgroundColor': '#007bff', 'color': 'white', 'border': 'none',
                        'padding': '10px 20px', 'fontSize': '16px', 'borderRadius': '5px', 'cursor': 'pointer'
                    }),
    ]),
    html.Div(id="output-mensaje", style={"marginTop": "20px", "textAlign": "center", "fontWeight": "bold"}),
    dcc.Interval(id="intervalo-actualizacion", interval=60*1000, n_intervals=0)
])

# Callback para actualizar gráficos y texto en vivo
@app.callback(
    [Output("grafico-pie", "figure"),
     Output("grafico-bar", "figure"),
     Output("live-update-text", "children")],
    [Input("intervalo-actualizacion", "n_intervals")]
)
def actualizar_graficos(n):
    df = cargar_datos()
    resumen, pendientes = obtener_resumen(df)

    if df.empty:
        mensaje = "No se pudieron cargar los datos o la hoja está vacía."
        fig_pie_vacia = px.pie(title="Estado de Entrega de Reportes")
        fig_bar_vacia = px.bar(title="Pendientes de Entrega/Corrección")
        return fig_pie_vacia, fig_bar_vacia, mensaje

    fig_pie = px.pie(resumen, names="Estado", values="Cantidad", title="Estado de Entrega de Reportes",
                     color_discrete_map={'Entregado':'#28a745', 'No entregado':'#dc3545', 'Corrección':'#ffc107'})
    
    fig_bar = px.bar(pendientes, x="Nombre", y="Estado_Entrega", color="Estado_Entrega",
                     title="Personas con Entregas Pendientes o en Corrección",
                     labels={"Nombre": "Nombre de la Persona", "Estado_Entrega": "Estado"})
    
    mensaje_actualizacion = f"Datos actualizados por última vez a las {time.strftime('%H:%M:%S')}"
    return fig_pie, fig_bar, mensaje_actualizacion

# Callback para el botón de envío manual de WhatsApp
@app.callback(
    Output("output-mensaje", "children"),
    Input("btn-recordatorios", "n_clicks"),
    prevent_initial_call=True
)
def enviar_mensajes_manual(n_clicks):
    df = cargar_datos()
    _, pendientes = obtener_resumen(df)
    
    if pendientes.empty:
        return html.P("¡Excelente! No hay recordatorios pendientes por enviar.", style={'color': 'green'})

    enviados, errores = enviar_recordatorio(pendientes)
    
    mensaje_exito = f"Se intentó enviar recordatorios a {enviados} persona(s)."
    
    if not errores:
        return html.P(mensaje_exito, style={'color': 'green'})
    else:
        elementos_error = [html.P(f"Se completó el proceso con {len(errores)} error(es):", style={'color': 'orange'})]
        for error in errores:
            elementos_error.append(html.P(error, style={'color': 'red', 'fontSize': '12px'}))
        return html.Div([html.P(mensaje_exito)] + elementos_error)

# ==============================
# Ejecutar la aplicación
# ==============================
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=False)
