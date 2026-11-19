# Laboratorio 2 · Ciencia de Datos — Predicción de demanda a 30 días (H&M)

Universidad Católica del Norte, Coquimbo — Paulo Araya, Gian Guzmán.

Regresión logística (KNIME) que predice si un artículo de H&M tendrá al menos una venta en los
30 días siguientes al 23-08-2020. Informe en `sample.pdf`.

## Requisitos

| Componente | Versión usada | Para qué |
| --- | --- | --- |
| Python 3 + `pandas` | Python ≥ 3.10 | `Etapa0.py` (construye la tabla de modelado) |
| KNIME Analytics Platform | 5.12 (sirve 5.x) | workflow `knime/Lab2CienciaDatos` |
| TeX Live con `latexmk`, `biber`, `biblatex-chicago`, `pgfplots`, `pdflscape` | TeX Live 2026 | compilar el informe |

Memoria: `Etapa0.py` carga ~31,8 M de transacciones (se recomiendan ≥16 GB de RAM). En KNIME se
recomienda subir el heap a 8 GB (`-Xmx8192m` en `knime.ini`).

## Datos (no incluidos en el repositorio)

Los datos pertenecen a la competencia de Kaggle
[H&M Personalized Fashion Recommendations](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations)
(3,8 GB; sus reglas no permiten redistribuirlos). Hay que aceptar las reglas de la competencia y
descargar `transactions_train.csv` y `articles.csv` en:

```
knime/Lab2CienciaDatos/data/
```

Con la CLI de Kaggle:

```bash
kaggle competitions download -c h-and-m-personalized-fashion-recommendations \
  -f transactions_train.csv -p knime/Lab2CienciaDatos/data
kaggle competitions download -c h-and-m-personalized-fashion-recommendations \
  -f articles.csv -p knime/Lab2CienciaDatos/data
cd knime/Lab2CienciaDatos/data && unzip -o '*.zip' && rm -f *.zip
```

## Pasos para reproducir

1. **Construir la tabla de modelado** (desde la raíz del repositorio):
   ```bash
   python3 Etapa0.py
   ```
   Genera `knime/Lab2CienciaDatos/data/tabla_modelado.csv`. Verificación: 88.584 filas,
   23.866 positivos (26,9 %).
2. **Ejecutar el workflow KNIME**: en KNIME, *File → Import KNIME Workflow…* (o abrir la carpeta
   `knime/` como workspace), abrir `Lab2CienciaDatos` y ejecutar todos los nodos (*Execute all*).
   Todas las rutas son relativas al workflow. Escribe en `knime/Lab2CienciaDatos/data/`:
   `metricas_modelos.csv`, `coeficientes.csv`, `calibracion.csv` y `lift.csv`.
3. **Regenerar los datos de las figuras** (solo biblioteca estándar):
   ```bash
   python3 scripts/datos_informe.py
   ```
   Escribe `fig/data/*.csv` (ya incluidos en el repositorio con los resultados de la versión final).
4. **Compilar el informe**:
   ```bash
   latexmk -pdf sample.tex
   ```

El paso 4 funciona sin los pasos 1–3, porque `fig/data/` ya está versionado.

## Estructura

| Ruta | Contenido |
| --- | --- |
| `Etapa0.py` | Agregación de transacciones por artículo, ventanas temporales y variable objetivo |
| `knime/Lab2CienciaDatos/` | Workflow KNIME (E1 Carga → E7 Salidas), con nodos etiquetados y anotaciones |
| `scripts/datos_informe.py` | Convierte las salidas del workflow en los datos de las figuras |
| `fig/data/` | Datos de tablas y figuras del informe |
| `fig/workflow.pdf` | Diagrama del workflow (exportado de KNIME) |
| `sample.tex`, `referencias.bib` | Fuente del informe y bibliografía |
| `cup-journal.cls`, `apj.bst`, `aas-macros.sty`, `fig/ucn-EIC.pdf` | Plantilla UCN |
| `sample.pdf` | Informe compilado |

## Parámetros fijos

Observación 2018-09-20 a 2020-08-23 · predicción 2020-08-24 a 2020-09-22 · artículos con ≥5 ventas ·
partición estratificada 70/30, semilla 42 · categorías <1 % → `OTROS` · `ln(1+x)` en conteos ·
filtro de correlación |r| > 0,8 · umbral 0,5 · regresión logística SAG, 1000 épocas, prior con varianza 1.
