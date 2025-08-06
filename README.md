
### 1. Clona este repositorio
```bash
git clone <tu-repo>
cd dashboard-servicios
```

### 2. Agrega tus credenciales
- Descarga el archivo `credentials.json` desde Google Cloud (API de Google Sheets).
- Colócalo en la raíz del proyecto (NO lo subas a GitHub).

### 3. Configura Twilio
- Registra una cuenta en Twilio y habilita WhatsApp Sandbox.
- Sustituye en `app.py` las variables:
  - `account_sid`
  - `auth_token`
  - `from_whatsapp_number`

### 4. Instala dependencias (local)
```bash
pip install -r requirements.txt
python app.py
```

### 5. Despliega en Render
- Crea un servicio web en Render.
- Usa `requirements.txt` para dependencias y `Procfile` para arranque.
- Sube `credentials.json` como **Secret File**.

### 6. Accede a tu dashboard
Render generará una URL tipo `https://tu-app.onrender.com`.

### 7. Revisa los logs en Render
- Ve a tu servicio → pestaña **Logs**
- Revisa los mensajes de **Build Logs** (instalación) o **Runtime Logs** (errores en la app)
- Si se queda en `Preparing metadata (pyproject.toml)` mucho tiempo, vuelve a hacer un **Manual Deploy** en pestaña **Deploys**
