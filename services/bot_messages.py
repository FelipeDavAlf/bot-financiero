import re

WELCOME_MESSAGE = """👋 **¡Hola! Bienvenido a tu Asistente Financiero Personal.**

Soy tu bot inteligente para el control de gastos e ingresos. Registro, clasifico y resguardo tus finanzas en una base de datos segura y te permito descargar tu reporte estructurado en **Excel** en cualquier momento.

---
### 🛠️ ¿Cómo puedes registrar movimientos?
Puedes enviarme tu información de 3 formas:

1. ✍️ **Texto normal:**
   • `"Gasté $150 en comida con efectivo"`
   • `"Pagué $680 de luz con débito BBVA"`
   • `"Transferí $1,500 de BBVA a Mercado Pago"`
   • `"Me pagaron $12,500 de sueldo en BBVA"`

2. 🎙️ **Nota de voz:**
   Envía un audio diciendo tu movimiento de forma natural.

3. 📄 **Estados de Cuenta (Carga Masiva):**
   Envía tu estado de cuenta en **PDF**, **Excel (.xlsx)** o **CSV** (ej. Mercado Pago, BBVA, etc.) y guardaré todas las transacciones automáticamente sin duplicados.

---
### 💳 Cuentas y Métodos de Pago Disponibles:
• 💵 **Efectivo**
• 🏦 **BBVA:** Tarjeta Débito BBVA | Tarjeta Crédito BBVA
• 💜 **Nu:** Tarjeta Débito Nu | Tarjeta Crédito Nu
• 🟢 **Stori:** Tarjeta Débito Stori | Tarjeta Crédito Stori
• 🧡 **Rappi:** Tarjeta Crédito Rappi
• 💙 **Mercado Pago:** Cuenta Mercado Pago

---
### 🏷️ Categorías Disponibles:
Alimentación, Transporte, Vivienda y Servicios, Suscripciones, Ocio y Entretenimiento, Salud y Cuidado, Mascotas, Ahorro e Inversión, Salario, Rendimientos, Traspaso, Otros.

---
💡 *Comandos útiles:*
• `/cuentas` - Ver tus cuentas y métodos de pago
• `/agregar_cuenta` - Agregar nueva cuenta o banco (ej: `/agregar_cuenta Santander`)
• `/eliminar_cuenta` - Desactivar una cuenta (ej: `/eliminar_cuenta Stori`)
• `/exportar` - Descargar tu reporte financiero en Excel (.xlsx)
• `/categorias` - Ver categorías de gastos e ingresos
• `/ayuda` - Ver guía de ayuda y ejemplos
• `/inicio` - Ver mensaje de bienvenida
"""

HELP_MESSAGE = """📖 **Guía de Uso del Bot Financiero**

Para registrar cualquier transacción, sólo escríbela o dila en una nota de voz incluyendo el **monto** y el **concepto**.

### 💡 Ejemplos recomendados:
• **Gastos:**
  - `"Gasté 85 pesos en Uber con débito BBVA"`
  - `"Pagué 420 de despensa en efectivo"`
  - `"Compré un videojuego de 1200 en tarjeta crédito Nu"`

• **Ingresos:**
  - `"Recibí 15,000 de sueldo en BBVA"`
  - `"Me pagaron 500 en efectivo de una tanda"`

• **Traspasos:**
  - `"Pasé 2,000 de débito BBVA a Mercado Pago"`
  - `"Pagué 1,600 a mi tarjeta de crédito BBVA desde débito"`

• **Estados de cuenta:**
  - Arrastra o sube cualquier archivo PDF, Excel (.xlsx) o CSV.

---
📌 Comandos rápidos:
• `/cuentas` - Ver y administrar tus cuentas
• `/agregar_cuenta <nombre>` - Registrar nuevo banco o tarjeta
• `/eliminar_cuenta <nombre>` - Desactivar una cuenta
• `/exportar` - Descargar tu plantilla y reporte en Excel (.xlsx)
• `/categorias` - Ver categorías permitidas
• `/ayuda` - Ver esta guía de ayuda
• `/inicio` - Ver mensaje de inicio
"""

ACCOUNTS_MESSAGE = """💳 **Cuentas y Métodos de Pago Configurados**

El sistema clasifica automáticamente tus movimientos en las siguientes cuentas oficiales:

1. 💵 **Efectivo**
2. 🏦 **Tarjeta Débito BBVA**
3. 💳 **Tarjeta Crédito BBVA**
4. 💜 **Tarjeta Débito Nu**
5. 💳 **Tarjeta Crédito Nu**
6. 🟢 **Tarjeta Débito Stori**
7. 💳 **Tarjeta Crédito Stori**
8. 🧡 **Tarjeta Crédito Rappi**
9. 💙 **Cuenta Mercado Pago**

💡 *Si no especificas la cuenta en tu mensaje, la IA intentará inferirla o la registrará como general.*
"""

CATEGORIES_MESSAGE = """🏷️ **Categorías de Finanzas Disponibles**

Tus movimientos se organizan automáticamente en estas categorías:

• 🍔 **Alimentación** (Supermercado, Restaurantes, Cafeterías)
• 🚗 **Transporte** (Gasolina, Uber, Transporte público, Mantenimiento)
• 🏠 **Vivienda y Servicios** (Renta, Luz, Agua, Internet, Gas)
• 📺 **Suscripciones** (Netflix, Spotify, Cloud, Gimnasio)
• 🎮 **Ocio y Entretenimiento** (Salidas, Cine, Videojuegos)
• 💊 **Salud y Cuidado** (Farmacia, Consultas, Cuidado personal)
• 🐾 **Mascotas** (Alimento, Veterinario, Accesorios)
• 📈 **Ahorro e Inversión** (Cetes, Fondos, Apartados)
• 💼 **Salario** (Nómina, Sueldo)
• 💰 **Rendimientos** (Intereses bancarios, Inversiones)
• 🔁 **Traspaso** (Movimientos entre tus propias cuentas)
• 📦 **Otros** (Gastos varios o imprevistos)
"""

NON_TRANSACTION_FALLBACK_MESSAGE = """🤔 **No identifiqué ninguna transacción financiera en tu mensaje.**

Para registrar un gasto, ingreso o traspaso, asegúrate de mencionar al menos el **monto** y el **concepto**. Por ejemplo:

• ☕ `"Gasté $65 en un café con efectivo"`
• 🛒 `"Compré $350 de despensa con débito BBVA"`
• 💼 `"Me depositaron $10,000 de nómina en BBVA"`
• 🔁 `"Pasé $1,000 de BBVA a Mercado Pago"`

🎙️ También puedes enviar una **nota de voz** o subir tu **estado de cuenta** (PDF, Excel o CSV).
Usa `/ayuda` si deseas consultar más información.
"""

GREETING_KEYWORDS = {
    "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
    "que tal", "que onda", "hello", "hi", "hey", "ayuda", "help",
    "inicio", "start", "menu", "info", "informacion", "como funciona",
    "que haces", "quien eres", "opciones", "comandos", "guia"
}


def is_greeting_or_help_intent(message_text: str) -> bool:
    """
    Checks if user text matches common greetings or requests for help/information.
    Allows instant responses without latency or LLM consumption.
    """
    if not message_text:
        return False

    cleaned = message_text.lower().strip()
    # Normalize accents
    for accented, plain in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u")):
        cleaned = cleaned.replace(accented, plain)

    # Normalize punctuation and extra spaces
    cleaned = re.sub(r"[^\w\s]", "", cleaned).strip()

    if cleaned in GREETING_KEYWORDS:
        return True

    words = cleaned.split()
    if words and words[0] in {"hola", "buenas", "ayuda", "help", "info"}:
        return True

    return False
