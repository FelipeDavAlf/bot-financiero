# 🤖 Bot Financiero Personal

Bot asistente financiero inteligente integrado con **Telegram**, impulsado por **Google Gemini**, respaldado por **PostgreSQL / SQLite** y sincronizado opcionalmente con **Google Sheets**.

Permite el registro, categorización y conciliación automática de gastos, ingresos y traspasos financieros a través de mensajes de texto natural, notas de voz y estados de cuenta en PDF, Excel o CSV.

---

## 📖 Documentación para el Usuario

Para conocer a detalle todos los comandos, ejemplos de uso por texto, notas de voz y cómo cargar estados de cuenta masivos, consulta nuestro:

👉 **[Manual de Usuario Completo (MANUAL_DE_USUARIO.md)](./MANUAL_DE_USUARIO.md)**

---

## 🚀 Características Principales

- ✍️ **Reconocimiento de Texto Natural**: Escribe tus gastos cotidianos sin formatos rígidos.
- 🎙️ **Notas de Voz**: Envía audios por Telegram; Gemini interpreta el audio de forma nativa.
- 📄 **Cargas Masivas (PDF / Excel / CSV)**: Procesa estados de cuenta bancarios (BBVA, Nu, Mercado Pago, etc.) con barra de progreso en vivo.
- 🛡️ **Prevención Anti-Duplicados**: Algoritmo de huella digital (*fingerprint*) para evitar transacciones repetidas.
- 🗄️ **Persistencia Multi-Usuario**: Base de datos relacional con SQLAlchemy para gestión de perfiles, cuentas bancarias y transacciones.
- 📊 **Sincronización con Google Sheets**: Conciliación en tiempo real con tu hoja de cálculo.
