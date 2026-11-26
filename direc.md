# Directriz final de ajustes — CrediCalc

Realizar exclusivamente los siguientes ajustes y revisiones sobre la versión actual del proyecto. No reconstruir la aplicación, no agregar nuevas funcionalidades ajenas a estas solicitudes ni modificar innecesariamente lo que ya funciona.

## 1. Ajuste del tamaño de la tipografía

- Reducir ligeramente el tamaño de la tipografía actual, regresando a un tamaño más cercano al que se tenía anteriormente.
- Corregir los botones cuyos textos actualmente no se muestran completos debido al tamaño de la fuente.
- Verificar que los textos, botones, campos y demás controles se visualicen correctamente sin recortes.

## 2. Información del proyecto visible desde el inicio

La información de los integrantes y del proyecto sigue sin estar suficientemente visible.

Integrar directamente en la pantalla inicial, preferiblemente dentro del módulo de caracterización del usuario, la información institucional y los integrantes del equipo.

Debe ser visible desde que se abre la aplicación, sin tener que ingresar a otro apartado para consultarla.

Mostrar:

**Universidad Distrital Francisco José de Caldas**  
Proyecto académico — 2026

- Harold Mateus — 202626780XX
- Santiago Castiblanco — 202626780XX
- Erick Lemus — 20262678012
- Camilo Ocampo — 20262678061

Integrarlo de forma estética, compacta y coherente con el diseño existente, sin quitar espacio innecesario al formulario de caracterización.

## 3. Revisión de las clasificaciones de pago

Realizar una nueva revisión de las modalidades de pago y las clasificaciones del crédito actualmente implementadas.

Verificar que:

- Las opciones no sean redundantes entre sí.
- La selección de una modalidad no altere accidentalmente el comportamiento de otra.
- Las opciones que representan conceptos diferentes mantengan su independencia.
- Las combinaciones permitidas sean matemáticamente coherentes.
- Las selecciones y configuraciones desactivadas no sigan influyendo en la simulación.
- Los cálculos correspondientes a cada modalidad sean consistentes con su definición.

No agregar nuevas modalidades ni ampliar las clasificaciones existentes. Corregir únicamente inconsistencias, redundancias o problemas de implementación que se encuentren.

## 4. Auditoría del panel de Recomendaciones

Revisar a profundidad el funcionamiento del panel de recomendaciones, utilizando como referencia el comportamiento observado en la captura proporcionada.

En el ejemplo, las recomendaciones **Menor costo** y **Menor tiempo** presentan exactamente la misma configuración, total pagado, intereses, duración y cuota inicial.

Determinar si este resultado es realmente correcto o si existe algún problema en la evaluación, selección, clasificación o comparación de las alternativas.

Revisar especialmente:

- Que se evalúen correctamente las alternativas de configuración disponibles.
- Que la recomendación de menor costo realmente corresponda al menor valor total pagado.
- Que la recomendación de menor tiempo realmente corresponda a la menor duración real del crédito.
- Que la recomendación equilibrada represente efectivamente un balance entre costo y tiempo, y no sea una selección arbitraria.
- Que las configuraciones recomendadas sean válidas y compatibles entre sí.
- Que los pagos anticipados y vencidos reflejen correctamente la duración real del crédito.
- Que las conversiones de tasas y las fórmulas de interés compuesto sean correctas para las periodicidades utilizadas.
- Que las modalidades crecientes y decrecientes apliquen correctamente sus variaciones y no generen resultados incoherentes.
- Que los diferimientos, periodos de gracia y demás ajustes avanzados se consideren correctamente cuando estén habilitados.
- Que las métricas mostradas en las recomendaciones coincidan con los resultados reales de las simulaciones utilizadas para evaluarlas.

No asumir que la coincidencia entre dos recomendaciones es necesariamente un error. Si una misma configuración realmente es la mejor en costo y tiempo, puede aparecer en ambas; sin embargo, validar que la evaluación se esté realizando correctamente y que no existan fallos que estén provocando coincidencias artificiales.

Si se encuentran errores matemáticos o lógicos, corregirlos y agregar las pruebas correspondientes.

## 5. Verificación final

- Ejecutar las pruebas existentes y las nuevas que sean necesarias.
- Verificar visualmente el tamaño de fuente y la visualización completa de los botones.
- Comprobar que la información institucional y los integrantes sean visibles desde el inicio.
- Probar las clasificaciones y sus combinaciones.
- Validar el funcionamiento del panel de recomendaciones con diferentes montos, plazos, tasas y configuraciones.
- Verificar que las recomendaciones tengan sentido matemático y financiero.
- Generar nuevamente el ejecutable y comprobar su funcionamiento.

## Restricciones

- No reconstruir el proyecto.
- No realizar refactorizaciones generales.
- No agregar nuevas clasificaciones de crédito.
- No modificar funcionalidades que ya funcionan correctamente.
- No cambiar fórmulas sin verificar primero su validez.
- Limitar los cambios exclusivamente a los puntos descritos.

Al finalizar, entregar un resumen de los cambios realizados, los hallazgos de la auditoría matemática y lógica del panel de recomendaciones, las pruebas ejecutadas y el ejecutable actualizado.