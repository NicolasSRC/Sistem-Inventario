# Lista de Requerimientos – Entrega 2 (Escenario 5)
## Trazabilidad: PDF oficial vs. Repositorio `Sistem-Inventario`

**Leyenda:**
- ✅ **Cumplido** – Implementado en el repositorio.
- ⚠️ **Parcial** – Existe algo, pero no cubre lo que exige el documento.
- ❌ **Faltante** – No existe en el repositorio.

---

## 1. Requerimientos Funcionales (RF)

| Código | Requerimiento (según PDF) | Estado | Evidencia / Observación en el repo | Qué falta según el documento |
|---|---|---|---|---|
| **RF01** | Registro y autenticación de cuenta (usuario/correo y contraseña) | ✅ | Login con contraseñas hasheadas (Flask-Login). | — |
| **RF02** | Gestión de roles y permisos (Administrador/Tendero y Empleado/Cajero) | ⚠️ | Roles "Administrador" y "Cliente". | El documento pide **Tendero y Empleado/Cajero**; el repo usa "Cliente". Ajustar nombres y permisos al modelo del PDF. |
| **RF03** | Creación y edición de productos (nombre, código de barras, categoría, precio compra, precio venta, stock inicial) | ✅ | CRUD de productos con nombre, SKU, categoría y precios. | Verificar que el formulario incluya **stock inicial** explícito al crear. |
| **RF04** | Gestión de categorías (lácteos, granos, aseo, bebidas, etc.) | ✅ | CRUD de categorías. | — |
| **RF05** | Gestión de proveedores (directorio con datos de contacto) | ❌ | No existe módulo de proveedores. | Crear modelo `Proveedor`, CRUD y asociación producto–proveedor para agilizar pedidos. |
| **RF06** | Registro rápido de salidas (ventas) con descuento en tiempo real | ✅ | Movimientos de salida con validación de stock. | Revisar que la interfaz sea de "pocos clics" para uso en caja. |
| **RF07** | Registro de entradas (compras/abastecimiento) actualizando cantidades y costos | ⚠️ | Existe registro de entradas. | El documento exige actualizar **costos**; verificar que la entrada actualice precio de compra/costo, no solo cantidad. |
| **RF08** | Ajustes de inventario y registro de mermas (pérdidas, dañados, vencidos, diferencias de conteo) | ❌ | No hay funcionalidad de ajustes ni mermas. | Agregar tipo de movimiento "Ajuste/Merma" con motivo (daño, vencimiento, diferencia) y cálculo de impacto. |
| **RF09** | Trazabilidad e historial de movimientos (usuario, fecha y hora) | ✅ | Historial filtrable de movimientos. | Confirmar que registre **qué usuario** hizo cada movimiento, no solo el movimiento. |
| **RF10** | Consulta rápida de existencias (buscador por nombre o código de barras) | ✅ | Búsqueda por nombre/SKU y filtro por categoría. | — |
| **RF11** | Configuración y alertas de stock mínimo (umbral parametrizable) | ✅ | Productos con cantidad ≤ stock mínimo resaltados. | Verificar que el umbral sea **configurable por producto**. |
| **RF12** | Control y alertas de fechas de vencimiento (lotes, aviso 15 días antes) | ❌ | No hay control de lotes ni fechas de caducidad. | Agregar campo de fecha de vencimiento/lote y alerta temprana configurable (ej. 15 días). |
| **RF13** | Panel de control (Dashboard) con indicadores del día | ⚠️ | Dashboard con totales, alertas y últimos movimientos. | El documento pide **productos próximos a vencer** (depende de RF12) y **más vendidos**; además, **gráficos dinámicos**. |
| **RF14** | Reportes de rotación y sugerencia automática de pedidos | ⚠️ | Exportación CSV de productos y movimientos. | Falta el **listado de mayor/menor rotación** y las **sugerencias automáticas de reposición** basadas en historial. |

---

## 2. Requerimientos No Funcionales (RNF)

| Código | Requerimiento (según PDF) | Estado | Evidencia / Observación en el repo | Qué falta según el documento |
|---|---|---|---|---|
| **RNF01** | Acceso multicanal y diseño responsivo (PC, tablet, móvil) | ✅ | Bootstrap 5 (vía CDN). | Verificar que Bootstrap cargue también sin conexión o documentar la dependencia del CDN. |
| **RNF02** | Usabilidad e interfaz intuitiva (botones grandes, lenguaje cotidiano, flujos de 2–3 pasos) | ⚠️ | Interfaz Bootstrap funcional. | El documento exige **alto contraste**, botones grandes y flujos cortos; revisar y documentar cumplimiento. |
| **RNF03** | Rendimiento: consultas y ventas en < 2 segundos | ⚠️ | No hay medición documentada. | Incluir pruebas de tiempo de respuesta (búsqueda y registro de venta). |
| **RNF04** | Disponibilidad y copias de seguridad en la nube (respaldos automáticos) | ❌ | SQLite local (`instance/inventario.db`), sin respaldos automáticos. | Migrar a BD en la nube (o al menos respaldo automático) y documentar la estrategia. |
| **RNF05** | Seguridad e integridad (cifrado de credenciales, acceso restringido) | ⚠️ | Contraseñas hasheadas y permisos por rol. | Falta documentar/implementar **cifrado de datos sensibles** y privacidad por tienda. |
| **RNF06** | Escalabilidad multi-sede | ❌ | Modelo de una sola tienda. | Agregar modelo de sucursales (multi-sede) o al menos dejar la arquitectura preparada. |

---

## 3. Dimensiones del Prototipo (Tabla 1 del PDF)

| Dimensión | Exigencia del documento | Estado | Observación |
|---|---|---|---|
| **Representación** | Aplicativo web responsivo ejecutado en navegador (móvil y escritorio) | ✅ | Flask + Bootstrap, ejecutable en navegador. |
| **Precisión** | Interfaz web completa, identidad visual, gráficos y datos reales | ⚠️ | Hay datos simulados (`seed_datos.py`), pero **faltan gráficos** en el dashboard y validar identidad visual/contraste. |
| **Interactividad** | Formularios activos, filtros, actualización dinámica de stock y alertas | ✅ | Funcional: CRUD, filtros, movimientos y alertas de stock. |
| **Evolución** | Código base reutilizable para mejoras y escalamiento a MVP | ✅ | Arquitectura Flask modular y reutilizable. |

---

## 4. Resumen de faltantes (priorizados)

**Críticos (impactan directamente los dolores del documento):**
1. **RF12 – Vencimientos**: no hay lotes ni alertas de caducidad. Es un dolor central de las tiendas de barrio según la introducción del PDF.
2. **RF08 – Mermas y ajustes**: no existe registro de pérdidas, dañados o diferencias de conteo.
3. **RF05 – Proveedores**: falta el directorio de proveedores para agilizar pedidos.
4. **RF14 – Rotación y sugerencia de pedidos**: solo hay exportación CSV, sin análisis ni sugerencias automáticas.

**Importantes:**
5. **Dashboard con gráficos dinámicos** (RF13 / Dimensión Precisión).
6. **Despliegue web público** (URL accesible), ya que el documento exige un aplicativo "desplegado en entorno web". El README explica cómo hacerlo en PythonAnywhere, pero no confirma que esté publicado.
7. **RNF04 – Respaldos en la nube**: SQLite local sin respaldo automático.
8. **RNF06 – Multi-sede**: no existe modelo de sucursales.

**Menores / de forma:**
9. **RF02**: renombrar rol "Cliente" a "Empleado/Cajero" y ajustar permisos según el PDF.
10. **RF07**: confirmar que las entradas actualicen costos, no solo cantidades.
11. **RF09**: confirmar que el historial registre el usuario que hizo cada movimiento.
12. **RNF03**: documentar pruebas de rendimiento (< 2 s).
13. **Numeración de RF**: el README usa RF-01 a RF-10 con una numeración distinta a la oficial (RF01–RF14). **Remapear** para que coincida con el PDF.

---

## 5. Indicaciones generales para completar lo faltante

1. **Modelo de datos**: agregar entidades `Proveedor`, `Lote/Vencimiento` y `Ajuste/Merma`; añadir `sucursal_id` para preparar multi-sede.
2. **Módulos nuevos**: CRUD de proveedores, registro de mermas/ajustes con motivo, control de lotes con fecha de caducidad y alertas a 15 días.
3. **Dashboard**: incorporar gráficos dinámicos (ej. Chart.js) para productos más vendidos, evolución de stock y próximos a vencer.
4. **Reportes**: agregar listado de rotación (mayor/menor movimiento) y sugerencia automática de reposición basada en historial de salidas.
5. **Despliegue**: publicar en PythonAnywhere (o similar) y compartir la URL en la entrega; documentar el enlace en el README.
6. **Respaldos**: implementar respaldo automático de la BD (script programado o servicio en la nube).
7. **Seguridad**: definir `SECRET_KEY` en producción y documentar cifrado/privacidad por tienda.
8. **Trazabilidad**: incluir en el README una tabla RF del PDF ↔ módulo del repo, con la numeración oficial.
9. **Pruebas**: documentar tiempos de respuesta y flujos de 2–3 pasos para RNF02 y RNF03.