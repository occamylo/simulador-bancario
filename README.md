# CrediCalc — Simulador bancario de créditos

Aplicación de escritorio académica para explorar créditos con interés compuesto,
distintas modalidades de amortización, periodos de gracia, tasas escalonadas
programadas y abonos extraordinarios. Los cálculos financieros están separados
de la interfaz y se pueden probar de forma independiente.

## Requisitos

- Python 3.10 o posterior para ejecutar desde el código fuente.
- Tkinter (incluido en la distribución estándar de Python para Windows).
- Para empaquetar el ejecutable: instalar `requirements-build.txt`.

La aplicación no necesita conexión, servicios externos ni guarda perfiles o
simulaciones. La exportación CSV solo ocurre cuando el usuario la solicita.
Al cerrar «Ajustes avanzados», sus parámetros se restablecen; el panel de
resultados incluye alternativas de menor costo, menor tiempo y equilibrada,
calculadas con el motor financiero. Se conservan los cambios de tasa, la gracia
y los abonos extraordinarios configurados; las tasas se convierten a una tasa
efectiva anual equivalente al comparar periodicidades, y cada cambio permanece
en el mismo número de periodo. Las cuotas crecientes o decrecientes usan el
porcentaje configurado cuando se seleccionó una de esas modalidades; en los demás
casos se comparan con una variación del 2% por periodo. Las opciones de tasa
escalonada requieren cambios explícitos por periodo.

## Ejecutar

```powershell
python main.py
```

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

## Crear el ejecutable de Windows

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name CrediCalc main.py
```

El ejecutable se genera en `dist\CrediCalc.exe`. PyInstaller debe ejecutarse en
Windows para producir un ejecutable de Windows. Antes de distribuirlo, pruébalo
en una cuenta/equipo sin Python y desde una carpeta independiente.
