[README.md](https://github.com/user-attachments/files/21724944/README.md)
Dashboard de Entregas con WhatsApp Cloud API y Google Sheets

Este proyecto genera un dashboard en tiempo real con datos de Google Sheets y envía recordatorios por WhatsApp automáticamente y manualmente usando la API oficial de Meta (WhatsApp Cloud API).

## Pasos para usar

### 1. Configurar Meta WhatsApp Cloud API
- Ve a [https://developers.facebook.com/](https://developers.facebook.com/).
- Crea una app tipo **Negocio**.
- Activa el producto **WhatsApp**.
- Copia tu **ACCESS_TOKEN** y **PHONE_NUMBER_ID**.

### 2. Clona este repositorio
```bash
git clone <tu-repo>
cd dashboard-servicios

### 7. Revisa los logs en Render
- Ve a tu servicio → pestaña **Logs**
- Revisa los mensajes de **Build Logs** (instalación) o **Runtime Logs** (errores en la app)
- Si se queda en `Preparing metadata (pyproject.toml)` mucho tiempo, vuelve a hacer un **Manual Deploy** en pestaña **Deploys**

