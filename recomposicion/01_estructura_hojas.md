# Etapa 1 — Estructura de hojas (Google Sheets)

Sistema de seguimiento de recomposición corporal. Google Sheets como base de datos y Web App de Apps Script como interfaz móvil.

> Estado: **BORRADOR para revisión**. Lo marcado como **PENDIENTE** necesita confirmación antes de escribir código.

---

## 0. Principios de diseño

1. **Hojas de entrada vs hojas calculadas.** Lo que escribes tú (peso, comidas, hábitos…) va en hojas "crudas". Lo que se calcula (promedios, semáforos, tendencias) lo escribe el script en hojas aparte y protegidas. Si algo se descuadra, se recalcula todo desde las hojas crudas sin perder datos.
2. **Una fila = un registro**, con `id` y `timestamp`. No se borran filas; se marcan con `anulado = TRUE` (queda trazabilidad).
3. **Snapshot de macros.** Al registrar una comida se guardan las kcal y macros calculadas en ese momento. Si después corriges el catálogo de alimentos, el historial no cambia.
4. **Metas con historia.** La meta vigente de un día se busca en `METAS_HIST` por fecha. Así el resumen de hace un mes se evalúa contra la meta que tenías ese día, no contra la actual.
5. **Formato:** fechas `yyyy-MM-dd`, zona horaria `America/Santiago`, decimales con punto en el script (Sheets los muestra según la configuración regional).
6. **Registro en < 30 s:** los formularios piden lo mínimo; la fecha viene precargada con hoy y el resto de columnas las rellena el script.

### Mapa de hojas

| # | Hoja | Tipo | Quién escribe | Módulo |
|---|------|------|---------------|--------|
| 1 | `CONFIG` | Parámetros | Usuario (pocas veces) | Todos |
| 2 | `METAS_HIST` | Historial | Script (al aceptar ajustes) | Metas / ajuste |
| 3 | `PESO` | Entrada | Web App | 1 |
| 4 | `MEDIDAS` | Entrada + calc | Web App | 2 |
| 5 | `ALIMENTOS` | Catálogo | Usuario / Web App | 3 |
| 6 | `COMIDAS` | Entrada | Web App | 3 |
| 7 | `EJERCICIOS` | Catálogo | Usuario | 5 |
| 8 | `ENTRENOS` | Entrada | Web App | 5 |
| 9 | `ENTRENO_DET` | Entrada + calc | Web App | 5 |
| 10 | `HABITOS` | Entrada | Web App | 6 |
| 11 | `FOTOS` | Entrada | Web App | 7 |
| 12 | `AJUSTES` | Calc + decisión | Script / usuario | Ajuste automático |
| 13 | `CALC_DIARIO` | Calculada | Script | 1, 4, 8 |
| 14 | `CALC_SEMANAL` | Calculada | Script | 8 |
| 15 | `DASHBOARD` | Visual | Script (gráficos nativos) | 8 |
| 16 | `LOG` | Auditoría | Script | Soporte |

---

## 1. `CONFIG` — parámetros (clave / valor)

Hoja de dos columnas principales. El script la lee completa al inicio de cada llamada.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `clave` | Texto (único) | Nombre del parámetro |
| `valor` | Texto / número / fecha | Valor |
| `unidad` | Texto | Referencia |
| `nota` | Texto | Explicación |

Claves iniciales:

| clave | valor | unidad | nota |
|-------|-------|--------|------|
| `sexo` | M | — | Para fórmula US Navy |
| `altura_cm` | 177 | cm | |
| `fecha_nacimiento` | **PENDIENTE** | fecha | Hoy solo tenemos "40 años"; con la fecha la edad se actualiza sola |
| `peso_inicial_kg` | 85 | kg | |
| `grasa_inicial_pct` | 25 | % | Estimación visual; se reemplaza con la 1ª medición Navy |
| `peso_objetivo_min_kg` | 77 | kg | Fase 1 |
| `peso_objetivo_max_kg` | 79 | kg | Fase 1 |
| `pasos_meta_min` | 8000 | pasos | |
| `pasos_meta_max` | 10000 | pasos | |
| `agua_meta_l` | **PENDIENTE** | L | No definido |
| `sueno_meta_h` | **PENDIENTE** | h | No definido |
| `kcal_piso_advertencia` | 1800 | kcal | Bajo esto se exige confirmación explícita |
| `ajuste_paso_kcal` | 150 | kcal | |
| `ajuste_cada_dias` | 14 | días | |
| `ciclo_7x7_inicio` | **PENDIENTE** | fecha | Primer día de un turno conocido; con esto se calcula Turno/Descanso automático |
| `drive_carpeta_fotos` | **PENDIENTE** | URL | Carpeta de fotos de progreso |
| `fotos_cada_dias` | 28 | días | |
| `medidas_cada_dias` | 14 | días | |
| `zona_horaria` | America/Santiago | — | |
| `inicio_semana` | **PENDIENTE** (propuesta: lunes) | — | Ver pregunta 6 |

Validación: `clave` única (el script avisa si hay duplicados).

---

## 2. `METAS_HIST` — historial de metas

Cada fila es una meta que rige **desde** `fecha_desde` hasta que aparezca otra más nueva.

| Columna | Tipo | Validación | Descripción |
|---------|------|------------|-------------|
| `id_meta` | Texto | Único | `M-0001` |
| `fecha_desde` | Fecha | Obligatoria | Desde cuándo rige |
| `kcal` | Entero | 1200–4000 | |
| `proteina_g` | Entero | 100–300 | |
| `grasa_g` | Entero | 30–150 | |
| `carb_g` | Entero | 50–500 | |
| `origen` | Lista | `Inicial`, `Ajuste aceptado`, `Manual` | |
| `id_ajuste` | Texto | Opcional | Enlaza con `AJUSTES` |
| `confirmo_bajo_piso` | Casilla | — | TRUE si se aceptó bajo 1.800 kcal |
| `motivo` | Texto | — | |
| `timestamp` | Fecha-hora | Auto | |

Fila inicial:

| id_meta | fecha_desde | kcal | proteina_g | grasa_g | carb_g | origen |
|---------|-------------|------|------------|---------|--------|--------|
| M-0001 | **PENDIENTE** (fecha de inicio del plan) | 2100 | 170 | 65 | 210 | Inicial |

> Chequeo nutricionista: 170×4 + 65×9 + 210×4 = 680 + 585 + 840 = **2.105 kcal** → consistente con 2.100. Proteína = 2,0 g/kg del peso actual (2,2 g/kg del peso objetivo): adecuada para preservar músculo en déficit.

---

## 3. `PESO` — peso diario en ayunas (módulo 1)

| Columna | Tipo | Validación | Descripción |
|---------|------|------------|-------------|
| `fecha` | Fecha | Obligatoria, **única** | Si ya existe ese día, la Web App pregunta "¿reemplazar?" |
| `peso_kg` | Decimal (1) | 50,0–150,0 | |
| `condicion` | Lista | `Ayunas` (default), `No ayunas` | Los "No ayunas" se excluyen del promedio |
| `nota` | Texto | Opcional | Ej.: "cena salada", "viaje a faena" |
| `anulado` | Casilla | — | |
| `timestamp` | Fecha-hora | Auto | |

Formulario móvil: **un campo** (peso) + botón Guardar. La fecha va precargada.

Los cálculos (promedio 7 d y tendencia) **no** van en esta hoja: van a `CALC_DIARIO` (sección 13).

---

## 4. `MEDIDAS` — medidas corporales cada 2 semanas (módulo 2)

| Columna | Tipo | Validación | Descripción |
|---------|------|------------|-------------|
| `fecha` | Fecha | Obligatoria, única | |
| `cintura_cm` | Decimal (1) | 50–150 | A la altura del ombligo, relajado, al final de una espiración normal |
| `cadera_cm` | Decimal (1) | 60–160 | Parte más ancha de los glúteos |
| `pecho_cm` | Decimal (1) | 60–160 | A la altura de los pezones, brazos abajo |
| `brazo_cm` | Decimal (1) | 20–60 | **PENDIENTE**: ¿relajado o contraído? ¿qué brazo? |
| `muslo_cm` | Decimal (1) | 30–90 | **PENDIENTE**: ¿punto medio entre cadera y rodilla o bajo el glúteo? ¿qué pierna? |
| `cuello_cm` | Decimal (1) | 25–60 | Justo bajo la nuez, cinta levemente inclinada hacia abajo |
| `grasa_navy_pct` | Decimal (1) | Calc. | Fórmula US Navy (abajo) |
| `peso_ref_kg` | Decimal (2) | Calc. | Promedio 7 d del peso a esa fecha |
| `masa_grasa_kg` | Decimal (1) | Calc. | `peso_ref × grasa% / 100` |
| `masa_magra_kg` | Decimal (1) | Calc. | `peso_ref − masa_grasa` |
| `nota` | Texto | Opcional | |
| `anulado` | Casilla | — | |
| `timestamp` | Fecha-hora | Auto | |

**Fórmula US Navy (hombres, en cm):**

```
%grasa = 495 / (1,0324 − 0,19077 · log10(cintura − cuello) + 0,15456 · log10(altura)) − 450
```

- Para hombres **no usa cadera** (la cadera se registra igual para seguimiento).
- Validación: `cintura > cuello`; si no, error.
- Referencia con valores típicos: cintura 95, cuello 40, altura 177 → ≈ 22,4 %.

> Chequeo entrenador: la masa magra estimada es el mejor indicador de "mantener/ganar músculo". Si baja más de ~1 kg entre dos mediciones mientras el peso baja, es señal de revisar proteína y volumen de entrenamiento. (Lo usaremos solo como alerta informativa, no como regla de ajuste.)

---

## 5. `ALIMENTOS` — catálogo de alimentos frecuentes (módulo 3)

Valores **por 100 g** (o 100 ml en líquidos, tratando 1 ml ≈ 1 g). Opcionalmente una "porción" para registrar por unidades (ej. 2 huevos) sin pesar.

| Columna | Tipo | Validación | Descripción |
|---------|------|------------|-------------|
| `id_alimento` | Texto | Único | `A-001` |
| `nombre` | Texto | Único | Lo que ves en la lista |
| `categoria` | Lista | `Proteína`, `Carbohidrato`, `Grasa`, `Lácteo`, `Fruta`, `Suplemento`, `Otro` | Para ordenar la lista |
| `kcal_100` | Decimal | 0–900 | |
| `prot_100` | Decimal | 0–100 | |
| `grasa_100` | Decimal | 0–100 | |
| `carb_100` | Decimal | 0–100 | |
| `porcion_nombre` | Texto | Opcional | Ej.: "unidad", "scoop", "taza" |
| `porcion_g` | Decimal | Opcional, > 0 | Gramos de esa porción |
| `favorito` | Casilla | — | Aparece primero en el móvil |
| `fuente` | Texto | — | Etiqueta / tabla de referencia |
| `activo` | Casilla | — | Si FALSE no aparece en la lista |

Validación cruzada (alerta, no bloqueo): `kcal_100` debería ≈ `4·prot + 9·grasa + 4·carb` (±15 %). Detecta errores de tipeo.

Catálogo inicial (11 alimentos). **Todos los valores nutricionales quedan PENDIENTE hasta que confirmes la variante exacta** de cada producto, porque cambian mucho según el tipo:

| id | nombre | categoria | Variante a confirmar (**PENDIENTE**) | porción sugerida |
|----|--------|-----------|---------------------------------------|------------------|
| A-001 | Huevo | Proteína | Entero, ¿crudo/cocido? | unidad ≈ **PENDIENTE** g (¿tamaño?) |
| A-002 | Atún | Proteína | ¿En agua o en aceite? ¿Peso drenado? | lata drenada **PENDIENTE** g |
| A-003 | Arroz | Carbohidrato | ¿Pesas **crudo** o **cocido**? (≈ 3× diferencia en kcal/100 g) | — |
| A-004 | Pasta | Carbohidrato | ¿Cruda o cocida? | — |
| A-005 | Leche | Lácteo | ¿Entera, semi o descremada? | taza 200 ml |
| A-006 | Plátano | Fruta | Pulpa sin cáscara | unidad **PENDIENTE** g |
| A-007 | Palta | Grasa | Hass, pulpa | — |
| A-008 | Yogur | Lácteo | ¿Natural, batido, proteico, light? Marca | pote **PENDIENTE** g |
| A-009 | Queso | Lácteo | ¿Gauda, mantecoso, fresco, cottage? | lámina **PENDIENTE** g |
| A-010 | Naranja | Fruta | Pulpa | unidad **PENDIENTE** g |
| A-011 | Whey ON Gold Standard | Suplemento | **Sabor** (macros varían por sabor); valores de la etiqueta | scoop (según etiqueta) |

> Mi propuesta: tú me confirmas la variante (o me mandas foto de las etiquetas) y yo cargo los valores por 100 g en la etapa 2. Para genéricos (huevo, arroz, plátano, palta, naranja) puedo usar la tabla USDA como fuente y lo dejo indicado en `fuente`.

---

## 6. `COMIDAS` — registro por comida (módulo 3)

| Columna | Tipo | Validación | Descripción |
|---------|------|------------|-------------|
| `id` | Texto | Único | `C-yyyyMMdd-HHmmss-xx` (lo genera el cliente; evita duplicados al sincronizar sin señal) |
| `fecha` | Fecha | Obligatoria | |
| `comida` | Lista | `Desayuno`, `Almuerzo`, `Once`, `Cena`, `Snack` | La Web App sugiere según la hora |
| `id_alimento` | Texto | Debe existir en `ALIMENTOS` o vacío | Vacío = ingreso manual |
| `nombre` | Texto | Obligatorio | Copia del catálogo o texto libre |
| `cantidad` | Decimal | > 0 | |
| `unidad` | Lista | `g`, `porción` | |
| `gramos` | Decimal | 1–2000 | Calc.: si unidad = porción → `cantidad × porcion_g` |
| `kcal` | Decimal | 0–3000 | Snapshot: `gramos × kcal_100 / 100` |
| `prot_g` | Decimal | 0–300 | Snapshot |
| `grasa_g` | Decimal | 0–300 | Snapshot |
| `carb_g` | Decimal | 0–500 | Snapshot |
| `origen` | Lista | `Catálogo`, `Manual` | Manual = escribiste kcal/macros a mano (comida de casino en faena, por ejemplo) |
| `anulado` | Casilla | — | |
| `timestamp` | Fecha-hora | Auto | |

Flujo móvil (< 30 s): elegir comida → tocar alimento (favoritos arriba) → escribir gramos → Guardar. Botón "Repetir ayer" para copiar una comida completa del día anterior.

> Chequeo nutricionista: en faena probablemente comes en casino y no puedes pesar. Por eso existe el modo `Manual` y la idea de "platos frecuentes" (ver pregunta 9).

---

## 7. `EJERCICIOS` — catálogo (módulo 5)

| Columna | Tipo | Validación | Descripción |
|---------|------|------------|-------------|
| `ejercicio` | Texto | Único | Mismo nombre que en Gymbler, para poder importar |
| `tipo` | Lista | `Torso`, `Pierna`, `Full`, `Core`, `Cardio` | |
| `grupo` | Texto | — | Pecho, espalda, cuádriceps… |
| `principal` | Casilla | — | Se muestra primero en el formulario |
| `activo` | Casilla | — | |

Lista inicial: **PENDIENTE** — necesito tus ejercicios reales de cada rutina (turno y descanso).

---

## 8. `ENTRENOS` — cabecera de sesión (módulo 5)

| Columna | Tipo | Validación | Descripción |
|---------|------|------------|-------------|
| `id_sesion` | Texto | Único | `S-yyyyMMdd-xx` |
| `fecha` | Fecha | Obligatoria | |
| `tipo` | Lista | `Torso`, `Pierna`, `Full`, `Cardio`, `Otro` | |
| `rutina` | Lista | `Turno`, `Descanso` | Precargado según ciclo 7x7 |
| `duracion_min` | Entero | 5–240 | |
| `rpe_sesion` | Entero | 1–10, opcional | Esfuerzo percibido global |
| `origen` | Lista | `Manual`, `Gymbler` | |
| `nota` | Texto | Opcional | |
| `anulado` | Casilla | — | |
| `timestamp` | Fecha-hora | Auto | |

## 9. `ENTRENO_DET` — ejercicios de la sesión (módulo 5)

Una fila **por ejercicio** (no por serie), para que sea rápido: registras la **serie top** y cuántas series hiciste.

| Columna | Tipo | Validación | Descripción |
|---------|------|------------|-------------|
| `id_sesion` | Texto | Debe existir en `ENTRENOS` | |
| `fecha` | Fecha | Copia | Para filtrar rápido |
| `ejercicio` | Texto | Lista desde `EJERCICIOS` | |
| `series` | Entero | 1–15 | |
| `kg` | Decimal (1) | 0–400 | Peso de la serie top (0 = peso corporal) |
| `reps` | Entero | 1–50 | Reps de la serie top |
| `rir` | Entero | 0–5, opcional | Reps en reserva |
| `e1rm` | Decimal (1) | Calc. | Epley: `kg × (1 + reps/30)` |
| `volumen` | Decimal | Calc. | `series × kg × reps` (aprox.) |
| `progresion` | Lista | Calc.: `↑ Sube`, `= Igual`, `↓ Baja`, `Nuevo` | Compara con la última sesión del mismo ejercicio |
| `delta_e1rm` | Decimal | Calc. | Diferencia vs sesión anterior |

Regla de progresión (propuesta entrenador): primero se compara `kg`; a igual kg, se comparan `reps`; si sube cualquiera sin bajar el otro → `↑`. Para pesos distintos se usa `e1rm` con tolerancia ±1 %. Así un "mismo peso, +1 rep" cuenta como progreso, que es lo realista en déficit.

> Chequeo entrenador: en definición el objetivo es **mantener o subir** cargas. Si un ejercicio principal muestra `↓` en 2 sesiones seguidas, el dashboard lo marca como alerta (posible déficit excesivo, mal sueño o fatiga de turno).

**Importación Gymbler:** **PENDIENTE** — necesito saber qué exporta Gymbler (CSV, texto para compartir, nada). Si exporta texto/CSV, hago un "pegar e importar" en la Web App; si no, queda el registro manual.

---

## 10. `HABITOS` — hábitos diarios (módulo 6)

| Columna | Tipo | Validación | Descripción |
|---------|------|------------|-------------|
| `fecha` | Fecha | Obligatoria, única | |
| `pasos` | Entero | 0–60000 | |
| `sueno_h` | Decimal (1) | 0–14 | |
| `agua_l` | Decimal (1) | 0–8 | |
| `creatina` | Casilla (Sí/No) | — | |
| `jornada` | Lista | `Turno`, `Descanso` | Precargado según `ciclo_7x7_inicio`; editable |
| `horario_turno` | Lista | `Día`, `Noche`, `—` | **PENDIENTE**: ¿tienes turnos de noche? |
| `nota` | Texto | Opcional | |
| `timestamp` | Fecha-hora | Auto | |

Formulario: se puede guardar parcial (ej. creatina en la mañana, pasos en la noche); el script **actualiza la fila del día** en vez de crear otra.

---

## 11. `FOTOS` — fotos de progreso (módulo 7)

| Columna | Tipo | Validación | Descripción |
|---------|------|------------|-------------|
| `fecha` | Fecha | Obligatoria | |
| `link` | URL | Debe empezar con `https://` | Link a la subcarpeta o fotos en Drive |
| `peso_ref_kg` | Decimal | Calc. | Promedio 7 d ese día |
| `cintura_ref_cm` | Decimal | Calc. | Última cintura registrada |
| `nota` | Texto | Opcional | Luz, hora, ropa (para que sean comparables) |
| `timestamp` | Fecha-hora | Auto | |

Recordatorio: `proxima_foto = última fecha + 28 días`. La Web App muestra un aviso desde 2 días antes. Opcional: correo automático con trigger diario (gratis, `MailApp`).

---

## 12. `AJUSTES` — sugerencias de ajuste de calorías

Cada 14 días el script evalúa y escribe una fila. Tú la aceptas o rechazas desde la Web App.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id_ajuste` | Texto | `AJ-0001` |
| `fecha_eval` | Fecha | Día de la evaluación |
| `ventana_desde` / `ventana_hasta` | Fecha | 14 días evaluados |
| `prom7_inicio` | Decimal | Promedio 7 d al inicio de la ventana |
| `prom7_medio` | Decimal | Promedio 7 d a los 7 días |
| `prom7_fin` | Decimal | Promedio 7 d al final |
| `tend_sem1` | Decimal | kg/sem (negativo = baja) |
| `tend_sem2` | Decimal | kg/sem |
| `tend_prom` | Decimal | Promedio de ambas |
| `dias_con_peso` | Entero | Pesajes válidos en la ventana |
| `adherencia_kcal_pct` | Decimal | % de días en verde (para contexto) |
| `regla` | Lista | `MANTENER`, `BAJAR_150`, `SUBIR_150`, `SIN_DATOS`, `ZONA_INTERMEDIA` |
| `kcal_actual` | Entero | |
| `kcal_propuesta` | Entero | |
| `delta_grasa_g` / `delta_carb_g` | Entero | Cómo se reparte el cambio (proteína nunca cambia) |
| `bajo_piso` | Casilla | TRUE si `kcal_propuesta < 1800` |
| `estado` | Lista | `Pendiente`, `Aceptada`, `Rechazada`, `Informativa` |
| `fecha_respuesta` | Fecha-hora | |
| `comentario` | Texto | Tu motivo (opcional) |

**Lógica (borrador, convenciones: valores negativos = pérdida):**

```
tend_semN = prom7(fin de semana N) − prom7(fin de semana N−1)   [kg/sem]

si dias_con_peso < MIN_PESAJES          → SIN_DATOS (no sugiere nada)
si tend_prom < −1,0                     → SUBIR_150  (baja > 1 kg/sem)
si −0,7 ≤ tend_prom ≤ −0,5              → MANTENER
si tend_sem1 > −0,25 y tend_sem2 > −0,25 → BAJAR_150 (baja < 0,25 kg/sem 2 semanas seguidas, incluye subir de peso)
otro caso                                → ZONA_INTERMEDIA (ver pregunta 3)
```

Al aceptar: se crea fila nueva en `METAS_HIST` con `fecha_desde = mañana`, `origen = Ajuste aceptado` e `id_ajuste`. Si `bajo_piso = TRUE`, la Web App muestra advertencia y exige marcar "Entiendo y confirmo" (queda en `confirmo_bajo_piso`).

> Chequeo coach: una ventana de 14 días cubre **un ciclo 7x7 completo** (turno + descanso), lo que neutraliza las diferencias de retención de líquido entre semanas (comida de casino más salada, viajes). Es la ventana correcta para tu régimen.

---

## 13. `CALC_DIARIO` — hoja calculada (protegida)

Una fila por día calendario desde el inicio del plan (incluye días sin registro).

| Columna | Descripción |
|---------|-------------|
| `fecha` | |
| `jornada` | Turno / Descanso |
| `peso_kg` | Pesaje del día (vacío si no hubo) |
| `prom7_kg` | Promedio de los pesajes válidos de los últimos 7 días (mín. **PENDIENTE**, propuesta 4 pesajes) |
| `tend_kg_sem` | `prom7(hoy) − prom7(hoy−7)` |
| `meta_kcal` / `meta_prot` / `meta_grasa` / `meta_carb` | Meta vigente ese día |
| `kcal` / `prot_g` / `grasa_g` / `carb_g` | Suma de `COMIDAS` no anuladas |
| `falta_kcal` / `falta_prot` / `falta_grasa` / `falta_carb` | Meta − consumido (negativo = te pasaste) |
| `sem_kcal` / `sem_prot` / `sem_grasa` / `sem_carb` | `VERDE` / `AMBAR` / `ROJO` |
| `registro_completo` | Casilla: marcaste el día como cerrado (si no, no cuenta para adherencia) |
| `pasos`, `sueno_h`, `agua_l`, `creatina` | Copia de `HABITOS` |
| `sem_pasos` | Semáforo pasos |
| `entreno` | Tipo de sesión del día (si hubo) |

**Semáforo propuesto (PENDIENTE de tu OK):**

| Indicador | Verde | Ámbar | Rojo |
|-----------|-------|-------|------|
| kcal | ±5 % de la meta (1.995–2.205) | ±5–10 % | > ±10 % |
| Proteína | ≥ 95 % (≥ 162 g) | 85–95 % | < 85 % |
| Grasa | ±10 % | ±10–20 % | > ±20 % |
| Carbohidratos | ±10 % | ±10–20 % | > ±20 % |
| Pasos | ≥ 8.000 | 6.000–7.999 | < 6.000 |

> Nota: pasarse en proteína **no** es rojo (no penaliza). En kcal, quedarse muy corto también es rojo: comer 1.500 un día no es "mejor", afecta rendimiento y adherencia.

## 14. `CALC_SEMANAL` — hoja calculada (protegida)

| Columna | Descripción |
|---------|-------------|
| `semana_inicio` | Lunes (o según `inicio_semana`) |
| `jornada_predominante` | Turno / Descanso / Mixta |
| `peso_prom` | Promedio de pesajes de la semana |
| `cambio_kg` | vs semana anterior |
| `cintura_cm` | Última medición disponible |
| `dias_registrados` | Días con registro completo |
| `kcal_prom` / `prot_prom` | Promedios diarios |
| `adher_kcal_pct` | % de días registrados con kcal en verde |
| `adher_prot_pct` | % de días registrados con proteína en verde |
| `pasos_prom` | |
| `sueno_prom` | |
| `creatina_pct` | % de días con creatina |
| `sesiones` | N° de entrenamientos |
| `ejercicios_con_progreso` | N° de ejercicios con `↑` |

## 15. `DASHBOARD`

Gráficos nativos de Sheets (los crea el script), alimentados por `CALC_DIARIO` y `CALC_SEMANAL`. La Web App tiene su propia vista con los mismos gráficos (Google Charts).

| Elemento | Fuente |
|----------|--------|
| Peso diario (puntos) + promedio 7 d (línea) | `CALC_DIARIO` |
| Cintura en el tiempo | `MEDIDAS` |
| % grasa Navy y masa magra | `MEDIDAS` |
| Adherencia semanal kcal y proteína (barras) | `CALC_SEMANAL` |
| KPIs del período: peso inicial/actual/Δ, kg/sem actual, cintura Δ, % grasa Δ, adherencia kcal y proteína, pasos prom., sueño prom., sesiones, días a la próxima foto/medición, ajuste pendiente | Calculados |

Período seleccionable: últimos 14 d, 28 d, fase completa.

## 16. `LOG` — auditoría

`timestamp`, `accion` (crear/editar/anular/recalcular/ajuste), `hoja`, `id`, `detalle` (JSON corto). Sirve para depurar y para la cola offline.

---

## 17. Mala señal (offline)

Limitación real de Apps Script: la Web App necesita conexión **para abrirse**. Lo que sí se puede hacer gratis:

1. Si la página ya está abierta, los registros se guardan primero en el teléfono (`localStorage`) y se envían cuando vuelve la señal (cola con reintento). Los `id` generados en el cliente evitan duplicados.
2. Indicador visible: "3 registros pendientes de enviar".
3. Recomendación de uso: abrir la app con señal (ej. en el campamento) y dejar la pestaña abierta.

---

## Preguntas abiertas (PENDIENTE)

1. **Fecha de inicio del plan** (para `METAS_HIST` y la primera evaluación de 14 días). ¿Hoy, 2026-10-03, u otra?
2. **Ciclo 7x7:** dame una fecha de inicio de turno conocida (ej. "subo el 2026-10-08") para calcular Turno/Descanso solo. ¿Turnos de día, de noche o rotativos?
3. **Huecos en la regla de ajuste.** Tus reglas no cubren estas zonas. Propuesta para cada una:
   - Baja entre 0,25 y 0,5 kg/sem → **mantener** (es lento, pero aceptable en recomposición, sobre todo si la cintura baja). ¿OK?
   - Baja entre 0,7 y 1,0 kg/sem → **mantener** con aviso si la masa magra estimada cae. ¿OK?
   - Una semana < 0,25 y la otra > 0,25 → **mantener** y reevaluar en 14 días. ¿OK?
4. **¿De dónde sale el −150 / +150?** Propuesta: −150 = −25 g carbohidratos y −5 g grasa (≈ −145 kcal), manteniendo grasa ≥ 0,6 g/kg (≈ 50 g mín.). +150 = todo a carbohidratos (+38 g), para rendir mejor entrenando. ¿O prefieres elegir tú en cada propuesta?
5. **Mínimo de pesajes** para que el promedio sea válido: propongo 4 de 7 días. ¿Tienes balanza en faena? (si no, la semana de turno quedaría sin datos y hay que ajustar la lógica).
6. **Inicio de semana** para el dashboard: ¿lunes, o alineada al día que subes a turno?
7. **Metas de agua y sueño** (no las diste). Sugerencia de referencia: agua 3 L, sueño 7 h, pero lo decides tú.
8. **Variantes de alimentos** de la tabla de la sección 5 (crudo/cocido, tipo de leche, queso, yogur, sabor del whey). Si puedes, foto de las etiquetas.
9. **Comidas en faena:** ¿comes en casino? ¿Te sirve un catálogo de "platos frecuentes" con macros estimados (ej. "plato casino almuerzo")?
10. **Gymbler:** ¿qué permite exportar (CSV, compartir texto, nada)? Si puedes, pégame un ejemplo.
11. **Ejercicios principales** de tus rutinas de turno y de descanso (torso/pierna).
12. **Brazo y muslo:** ¿qué lado y en qué punto exacto los mides? (lo dejo fijo en la ayuda de la app para que siempre se mida igual).
13. **Carpeta de Drive** para fotos: ¿ya existe (pásame el link) o el script la crea?
14. **Semáforo** de la sección 13: ¿te sirven esos rangos?
15. **Metas distintas turno vs descanso:** por ahora es una sola meta diaria. ¿Quieres metas diferentes por jornada (ej. más carbohidratos en días de entrenamiento)? Esto cambia el diseño de `METAS_HIST`, mejor decidirlo ahora.
