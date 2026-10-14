# 📘 Manual de Usuario: Bot Financiero Personal

¡Bienvenido al **Manual de Usuario** de tu **Bot Financiero Personal**! 🤖💳

Este asistente inteligente opera a través de **Telegram**, impulsado por los modelos de lenguaje de **Google Gemini** y respaldado por una **base de datos relacional** y sincronización opcional con **Google Sheets**. Su objetivo es registrar, clasificar y conciliar tus gastos, ingresos y traspasos de manera automática y sin fricción.

---

## 📑 Tabla de Contenidos

1. [Primeros Pasos](#-1-primeros-pasos)
2. [Comandos Disponibles](#-2-comandos-disponibles)
3. [Formas de Interactuar](#-3-formas-de-interactuar)
   - [3.1 Mensajes de Texto Natural](#31-mensajes-de-texto-natural)
   - [3.2 Notas de Voz (Audios)](#32-notas-de-voz-audios)
   - [3.3 Estados de Cuenta y Carga Masiva (PDF, Excel, CSV)](#33-estados-de-cuenta-y-carga-masiva-pdf-excel-csv)
4. [Cuentas y Métodos de Pago Soportados](#-4-cuentas-y-métodos-de-pago-soportados)
5. [Categorías Financieras](#-5-categorías-financieras)
6. [Manejo de Fechas Inteligentes](#-6-manejo-de-fechas-inteligentes)
7. [Sistema Anti-Duplicados (Deduplicación)](#-7-sistema-anti-duplicados-deduplicación)
8. [Estructura de Respuestas del Bot](#-8-estructura-de-respuestas-del-bot)
9. [Preguntas Frecuentes y Consejos Prácticos](#-9-preguntas-frecuentes-y-consejos-prácticos)

---

## 🚀 1. Primeros Pasos

1. Abre tu aplicación de **Telegram** (en tu celular, tablet o computadora).
2. Busca tu bot por su nombre de usuario e inicia el chat.
3. Presiona el botón **Iniciar** o envía el comando `/start`.
4. El bot registrará automáticamente tu perfil de usuario en la base de datos y configurará tus cuentas por defecto.

---

## ⌨️ 2. Comandos Disponibles

El bot cuenta con comandos rápidos para consultar su funcionamiento y reglas:

| Comando | Descripción |
| :--- | :--- |
| `/start` | Registra al usuario y muestra el mensaje de bienvenida con el resumen operativo. |
| `/exportar` | Genera y envía tu reporte financiero en formato Excel (.xlsx) con balances y detalle. |
| `/help` | Despliega una guía rápida con ejemplos recomendados de ingresos, gastos y traspasos. |
| `/cuentas` | Muestra la lista de tus cuentas y métodos de pago habilitados. |
| `/categorias` | Despliega el catálogo oficial de categorías para clasificar movimientos. |

> 💡 **Tip:** También puedes escribir palabras como *"hola"*, *"buenas tardes"*, *"ayuda"* o *"info"*, y el bot responderá de forma instantánea sin consumir créditos de IA.

---

## 💬 3. Formas de Interactuar

Puedes registrar tus movimientos financieros de **3 maneras distintas**:

### 3.1 Mensajes de Texto Natural

Simplemente redacta tu movimiento como si hablaras con un amigo o asistente personal. La IA detectará automáticamente:
- **Tipo de movimiento:** Gasto, Ingreso o Traspaso.
- **Monto numérico.**
- **Cuenta de origen y/o destino.**
- **Categoría y subcategoría.**
- **Concepto o comercio.**
- **Fecha del movimiento.**

#### 🟢 Ejemplos de Gastos:
- *"Gasté $150 en unos tacos con efectivo"*
- *"Pagué 420 de despensa en Walmart con débito BBVA"*
- *"Compré un videojuego de 1,200 en tarjeta de crédito Nu"*
- *"Uber de 85 pesos pagado con Rappi Card"*
- *"Pagué el recibo de luz de $650 con débito"*

#### 🔵 Ejemplos de Ingresos:
- *"Me depositaron $15,000 de mi nómina en BBVA"*
- *"Recibí 500 pesos en efectivo de un dinero que me debían"*
- *"Me pagaron 3,200 de un freelance en Mercado Pago"*
- *"Cobré 450 pesos de rendimientos en Cetes"*

#### 🟣 Ejemplos de Traspasos y Pagos de Tarjetas:
- *"Pasé 2,000 pesos de mi débito BBVA a Mercado Pago"*
- *"Pagué $3,500 a mi tarjeta de crédito Nu desde mi cuenta BBVA"*
- *"Transferí 500 de efectivo a débito Stori"*

---

### 3.2 Notas de Voz (Audios)

¿Vas caminando o tienes prisa? Envía una **nota de voz**:

1. Mantén presionado el micrófono de Telegram.
2. Habla con naturalidad mencionando el **monto**, el **concepto** y opcionalmente el **método de pago**.
   - *Ejemplo de audio:* *"Hola bot, acabo de pagar 230 pesos de gasolina con mi tarjeta de débito BBVA ayer por la noche"*.
3. El bot actualizará el estado en tiempo real:
   - `🎙️ Escuchando nota de voz...`
   - `🤖 Analizando audio...` (Gemini procesa el audio directamente).
   - `📊 Guardando transacción...`
4. Recibirás la confirmación detallada con el registro creado.

---

### 3.3 Estados de Cuenta y Carga Masiva (PDF, Excel, CSV)

Si deseas registrar todo un mes o período sin capturar transacción por transacción, puedes enviarle tu estado de cuenta bancario:

1. **Formatos soportados:**
   - 📄 Archivos **PDF** (estados de cuenta digitales de BBVA, Mercado Pago, Nu, etc.).
   - 📊 Hojas de cálculo **Excel** (`.xlsx`, `.xls`).
   - 📑 Archivos delimitados **CSV** (formato coma o punto y coma).
2. **Cómo enviarlo:**
   - Arrastra el archivo al chat o usa el icono de clip/adjunto 📎 y selecciona **Archivo / Documento**.
3. **Flujo de procesamiento en vivo:**
   - `📥 Descargando documento: Recibiendo archivo...`
   - `🔍 Extrayendo datos: Leyendo tablas y formato del archivo...`
   - `🤖 Analizando con IA: Detectando y clasificando transacciones con Gemini...`
   - `📊 Guardando registros: Sincronizando con base de datos y Google Sheets...`
4. **Reporte final:**
   Al finalizar, el bot te enviará un balance exacto:
   - ➕ Transacciones nuevas guardadas.
   - ⏭️ Transacciones ignoradas por ser duplicadas.
   - ⚠️ Registros descartados por datos incompletos.

---

## 💳 4. Cuentas y Métodos de Pago Soportados

El sistema cuenta con un catálogo de cuentas preconfiguradas que se asignan a tu usuario:

| Cuenta Oficial | Palabras Clave Recomendadas | Tipo |
| :--- | :--- | :--- |
| **Efectivo** | `efectivo`, `cash`, `monedas`, `billetes` | Efectivo |
| **Tarjeta Débito BBVA** | `débito BBVA`, `BBVA débito`, `nómina BBVA` | Débito |
| **Tarjeta Crédito BBVA** | `crédito BBVA`, `BBVA crédito`, `tarjeta azul BBVA` | Crédito |
| **Tarjeta Débito Nu** | `cuenta Nu`, `débito Nu`, `cajita Nu` | Débito |
| **Tarjeta Crédito Nu** | `crédito Nu`, `tarjeta morada`, `Nu crédito` | Crédito |
| **Tarjeta Débito Stori** | `débito Stori`, `cuenta Stori` | Débito |
| **Tarjeta Crédito Stori** | `crédito Stori`, `Stori crédito` | Crédito |
| **Tarjeta Crédito Rappi** | `Rappi`, `RappiCard`, `crédito Rappi` | Crédito |
| **Cuenta Mercado Pago** | `Mercado Pago`, `mercadopago`, `MP` | Débito |

> 📌 **¿Qué pasa si no menciono la cuenta?**  
> La IA intentará inferirla lógicamente según el tipo de gasto o la dejará como general para que no pierdas el registro del gasto.

---

## 🏷️ 5. Categorías Financieras

Tus transacciones se organizan automáticamente en 12 categorías principales:

| Categoría | Ejemplos Comunes de Gastos o Ingresos |
| :--- | :--- |
| 🍔 **Alimentación** | Despensa, supermercado, restaurantes, fondas, comida rápida, cafeterías, OXXO. |
| 🚗 **Transporte** | Gasolina, Uber, Didi, transporte público, casetas, estacionamiento, afinación de auto. |
| 🏠 **Vivienda y Servicios** | Renta, electricidad (CFE), agua, internet, gas natural o cilindro, mantenimiento de casa. |
| 📺 **Suscripciones** | Netflix, Spotify, Amazon Prime, YouTube Premium, ChatGPT, iCloud, gimnasio. |
| 🎮 **Ocio y Entretenimiento** | Cine, conciertos, videojuegos, salidas con amigos, bares, libros, viajes. |
| 💊 **Salud y Cuidado** | Medicamentos, farmacia, consultas médicas, dentista, análisis clínicos, skincare. |
| 🐾 **Mascotas** | Alimento para perro/gato, veterinario, vacunas, juguetes, estética canina. |
| 📈 **Ahorro e Inversión** | Apartados de ahorro, Cetes, compra de fondos de inversión, ahorro para metas. |
| 💼 **Salario** | Sueldo, nómina quincenal, aguinaldo, bonos laborales, primas vacacionales. |
| 💰 **Rendimientos** | Intereses generados en cuentas de inversión, dividendos, ganancias de saldo. |
| 🔁 **Traspaso** | Movimientos propios entre tus cuentas o pagos al saldo de tu tarjeta de crédito. |
| 📦 **Otros** | Compras varias, imprevistos o gastos no clasificados en las opciones anteriores. |

---

## 📅 6. Manejo de Fechas Inteligentes

No te preocupes por recordar el formato exacto de fecha. Puedes expresarlo con lenguaje humano:

- **"Hoy":** Usa la fecha actual automáticamente.
- **"Ayer":** Resta 1 día a la fecha actual (ej. *"Ayer gasté 80 pesos en farmacia"*).
- **"Antier" o "Anteayer":** Resta 2 días a la fecha actual.
- **Fechas explícitas:** Puedes decir *"el 5 de octubre"*, *"el lunes pasado"*, o formatos estándar como `12/10/2026`.

---

## 🛡️ 7. Sistema Anti-Duplicados (Deduplicación)

Para evitar registros repetidos por fallas de conexión, reintentos de Telegram o cargas duplicadas de estados de cuenta:

1. **Huella Digital Única (Fingerprint):**  
   Cada movimiento genera un identificador único determinista combinando:
   - Fecha
   - Monto normalizado
   - Tipo de movimiento
   - Cuenta de origen y destino
   - Descripción normalizada
2. **Validación en Base de Datos y Sheets:**  
   Antes de insertar un movimiento, se valida si esa huella ya existe.
3. **Respuesta en caso de duplicado:**  
   El bot te avisará:
   > ⚠️ **Transacción duplicada ignorada**  
   > *Ya habías registrado algo idéntico: [Detalle del movimiento]*

---

## 📋 8. Estructura de Respuestas del Bot

Cuando una transacción se guarda exitosamente, el bot te enviará una tarjeta informativa como esta:

```text
✅ Transacción guardada exitosamente

🔹 Tipo: Gasto
💰 Monto: $150.0
🏷️ Categoría: Alimentación
📌 Subcategoría: Taquería
📝 Descripción: Tacos con efectivo
🏦 Origen: Efectivo
🎯 Destino: N/A
📅 Fecha: 2026-10-14
```

Si el bot no detecta intención de dinero en tu mensaje (por ejemplo, preguntas generales, textos al azar o notas de voz vacías):
```text
🤔 No identifiqué ninguna transacción financiera en tu mensaje.
Para registrar un gasto, ingreso o traspaso, asegúrate de mencionar al menos el monto y el concepto.
```

---

## ❓ 9. Preguntas Frecuentes y Consejos Prácticos

### ¿Qué hago si el bot clasificó mal una categoría?
El modelo de Gemini tiene una tasa muy alta de precisión. Si un comercio es poco conocido (por ejemplo, una tienda local llamada *"Don Pepe"*), añade una palabra de contexto: *"Gasté 120 en ferretería Don Pepe con efectivo"*.

### ¿Puedo registrar transacciones de días anteriores?
Sí. Solo menciona la fecha en tu mensaje o audio: *"El 10 de octubre pagué 850 de seguro con tarjeta de crédito BBVA"*.

### ¿Mis datos se pierden si se reinicia el servidor?
No. Todas las transacciones se almacenan de forma permanente en la **base de datos relacional** y, si tienes configurado Google Sheets, se respaldan en tu hoja de cálculo en la nube.

### ¿Cómo subo un estado de cuenta protegido por contraseña?
Antes de enviarlo a Telegram, retira la contraseña del PDF para que el lector del bot pueda extraer el texto y las tablas de movimientos.
