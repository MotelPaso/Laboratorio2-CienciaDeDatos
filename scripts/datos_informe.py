"""Prepara los datos de tablas y figuras del informe a partir de las salidas del workflow KNIME.

Lee (desde knime/Lab2CienciaDatos/data/):
    tabla_modelado.csv, metricas_modelos.csv, lift.csv, calibracion.csv, coeficientes.csv
Escribe CSV limpios (separador ';', sin comillas) en fig/data/, que sample.tex grafica con pgfplots.

Uso (desde la raíz del repositorio):  python3 scripts/datos_informe.py
Solo usa la biblioteca estándar.
"""
import csv
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRADA = os.path.join(RAIZ, 'knime', 'Lab2CienciaDatos', 'data')
SALIDA = os.path.join(RAIZ, 'fig', 'data')
MODELOS = ['M1_L2', 'M2_L1', 'M3_L2_sin_alta_card']
CORTO = {'M1_L2': 'M1', 'M2_L1': 'M2', 'M3_L2_sin_alta_card': 'M3'}
ESTABLES = ['unidades_ult_30d', 'dias_desde_ultima_venta', 'dias_desde_primera_venta',
            'unidades_por_cliente', 'unidades_90d_previos', 'sin_hist_previo', 'cambio_precio_30d']


def leer(nombre):
    with open(os.path.join(ENTRADA, nombre), newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def escribir(nombre, cabecera, filas):
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, nombre), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';', quoting=csv.QUOTE_NONE, escapechar='\\')
        w.writerow(cabecera)
        w.writerows(filas)
    print(f'{nombre}: {len(filas)} filas')


def r(x, d=4):
    return f'{float(x):.{d}f}'


# ---------- EDA sobre tabla_modelado ----------
tabla = leer('tabla_modelado.csv')
y = [int(f['y_demanda_30d']) for f in tabla]


def tasa(clave, orden=None):
    g = {}
    for f, yy in zip(tabla, y):
        k = clave(f)
        n, p = g.get(k, (0, 0))
        g[k] = (n + 1, p + yy)
    claves = orden or sorted(g)
    return [(k, g[k][0], g[k][1] / g[k][0]) for k in claves if k in g]


def tramo(d):
    d = float(d)
    return '0-7' if d <= 7 else '8-30' if d <= 30 else '31-90' if d <= 90 else '91-365' if d <= 365 else '>365'


TRAMOS = ['0-7', '8-30', '31-90', '91-365', '>365']
escribir('recencia.csv', ['tramo', 'n', 'tasa'],
         [(k, n, r(t)) for k, n, t in tasa(lambda f: tramo(f['dias_desde_ultima_venta']), TRAMOS)])

seg = []
for k, n, t in tasa(lambda f: 'Ventas en ult. 30 d' if float(f['unidades_ult_30d']) > 0 else 'Sin ventas en ult. 30 d'):
    seg.append(('Actividad reciente', k, n, r(t)))
for k, n, t in tasa(lambda f: ('Al alza' if float(f['tendencia_90d']) > 0 else
                               'A la baja' if float(f['tendencia_90d']) < 0 else 'Sin cambio o sin historial')):
    seg.append(('Tendencia 90 d', k, n, r(t)))
for k, n, t in tasa(lambda f: 'Con ventas' if float(f['ventas_mismo_calendario']) > 0 else 'Sin ventas'):
    seg.append(('Mismo periodo 2019', k, n, r(t)))
for k, n, t in tasa(lambda f: f['index_group_name']):
    seg.append(('index_group_name', k.replace('/', '-'), n, r(t)))
escribir('segmentos.csv', ['grupo', 'segmento', 'n', 'tasa'], seg)
print(f'poblacion: {len(tabla)} articulos, {sum(y)} positivos, tasa {sum(y) / len(tabla):.4f}')

# ---------- Métricas finales ----------
met = {f['Modelo']: f for f in leer('metricas_modelos.csv')}
CAMPOS = ['accuracy', 'precision', 'recall', 'especificidad', 'f1', 'roc_auc', 'brier', 'logloss']
escribir('metricas.csv', ['modelo'] + CAMPOS + ['tp', 'fp', 'fn', 'tn'],
         [[CORTO[m]] + [r(met[m][c]) for c in CAMPOS] + [met[m][c] for c in ('tp', 'fp', 'fn', 'tn')]
          for m in MODELOS])

# ---------- Lift y ganancia acumulada ----------
lift = leer('lift.csv')
filas_lift, filas_gan = [], []
for m in MODELOS:
    dec = sorted((f for f in lift if f['Modelo'] == m), key=lambda f: int(f['decil']))
    pos = [float(f['y_num']) * float(f['uno']) for f in dec]
    total = sum(pos)
    acum = 0.0
    filas_gan.append((CORTO[m], 0, '0.0000'))
    for f, p in zip(dec, pos):
        acum += p
        filas_lift.append((CORTO[m], f['decil'], r(f['y_num']), r(f['lift'], 3)))
        filas_gan.append((CORTO[m], int(f['decil']) * 10, r(acum / total)))
escribir('lift.csv', ['modelo', 'decil', 'tasa', 'lift'], filas_lift)
for m in MODELOS:  # un archivo por modelo para pgfplots
    escribir(f'ganancia_{CORTO[m]}.csv', ['pct_articulos', 'pct_positivos'],
             [(p, g) for mm, p, g in filas_gan if mm == CORTO[m]])

# ---------- Calibración ----------
cal = leer('calibracion.csv')
for m in MODELOS:
    filas = sorted((f for f in cal if f['Modelo'] == m), key=lambda f: int(f['bin_calibracion']))
    def intervalo(b):
        b = int(b)
        return f'{b / 10:.1f}--{(b + 1) / 10:.1f}'.replace('.', ',')
    escribir(f'calibracion_{CORTO[m]}.csv', ['bin', 'intervalo', 'p_media', 'tasa_obs', 'n'],
             [(f['bin_calibracion'], intervalo(f['bin_calibracion']), r(f['p']), r(f['y_num']), f['uno'])
              for f in filas])

# ---------- Coeficientes estables (M1 y M3) ----------
coef = leer('coeficientes.csv')
idx = {(f['Modelo'], f['Variable']): f for f in coef}
filas = []
for v in ESTABLES:
    a, b = idx[('M1_L2', v)], idx[('M3_L2_sin_alta_card', v)]
    filas.append((v, r(a['Coeff.'], 3), r(a['odds_ratio'], 3), r(a['ic95_inf'], 3),
                  r(a['ic95_sup'], 3), r(b['Coeff.'], 3), r(b['odds_ratio'], 3), r(b['ic95_inf'], 3),
                  r(b['ic95_sup'], 3)))
escribir('coef_estables.csv', ['variable', 'b_m1', 'or_m1', 'li_m1', 'ls_m1', 'b_m3', 'or_m3', 'li_m3', 'ls_m3'],
         filas)
