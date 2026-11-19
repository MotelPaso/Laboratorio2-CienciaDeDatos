
import pandas as pd


DATA_DIR = "./knime/Lab2CienciaDatos/data"
TRANSACCIONES = f"{DATA_DIR}/transactions_train.csv"
ARTICULOS = f"{DATA_DIR}/articles.csv"
SALIDA = f"{DATA_DIR}/tabla_modelado.csv"

FECHA_CORTE = pd.Timestamp("2020-08-23")
PRED_INICIO = pd.Timestamp("2020-08-24")
PRED_FIN = pd.Timestamp("2020-09-22")

ULT_30_INICIO = pd.Timestamp("2020-07-25")
ULT_90_INICIO = pd.Timestamp("2020-05-26")
PREV_90_INICIO = pd.Timestamp("2020-02-26")
PREV_90_FIN = pd.Timestamp("2020-05-25")
CALENDARIO_INICIO = pd.Timestamp("2019-08-24")
CALENDARIO_FIN = pd.Timestamp("2019-09-22")


df = pd.read_csv(
    TRANSACCIONES,
    usecols=["t_dat", "customer_id", "article_id", "price"],
)
df["t_dat"] = pd.to_datetime(df["t_dat"], format="%Y-%m-%d")
df["unidades"] = 1

obs = df[df["t_dat"].le(FECHA_CORTE)].copy()
pred = df[df["t_dat"].between(PRED_INICIO, PRED_FIN, inclusive="both")].copy()

base = (
    obs.groupby("article_id", observed=True)
    .agg(
        unidades_obs=("unidades", "sum"),
        clientes_unicos=("customer_id", "nunique"),
        dias_con_venta=("t_dat", "nunique"),
        precio_medio=("price", "mean"),
        precio_min=("price", "min"),
        precio_max=("price", "max"),
        precio_sd=("price", "std"),
        primera_venta=("t_dat", "min"),
        ultima_venta=("t_dat", "max"),
    )
)


def contar_por_ventana(tabla, inicio, fin, nombre):
    ventana = tabla[
        tabla["t_dat"].between(inicio, fin, inclusive="both")
    ]
    return (
        ventana.groupby("article_id", observed=True)["unidades"]
        .sum()
        .rename(nombre)
    )


features = base.copy()

features = features.join(
    contar_por_ventana(obs, ULT_30_INICIO, FECHA_CORTE, "unidades_ult_30d")
)
features = features.join(
    contar_por_ventana(obs, ULT_90_INICIO, FECHA_CORTE, "unidades_ult_90d")
)
features = features.join(
    contar_por_ventana(obs, PREV_90_INICIO, PREV_90_FIN, "unidades_90d_previos")
)
features = features.join(
    contar_por_ventana(
        obs,
        CALENDARIO_INICIO,
        CALENDARIO_FIN,
        "ventas_mismo_calendario",
    )
)

features[
    [
        "unidades_ult_30d",
        "unidades_ult_90d",
        "unidades_90d_previos",
        "ventas_mismo_calendario",
    ]
] = features[
    [
        "unidades_ult_30d",
        "unidades_ult_90d",
        "unidades_90d_previos",
        "ventas_mismo_calendario",
    ]
].fillna(0)

ultimo_precio = (
    obs.sort_values("t_dat", kind="stable")
    .drop_duplicates("article_id", keep="last")
    .set_index("article_id")["price"]
    .rename("precio_ultimo")
)
features = features.join(ultimo_precio)

features["dias_desde_ultima_venta"] = (
    FECHA_CORTE - features["ultima_venta"]
).dt.days
features["dias_desde_primera_venta"] = (
    FECHA_CORTE - features["primera_venta"]
).dt.days

features["tendencia_90d"] = 0.0
con_historial_previo = features["unidades_90d_previos"] > 0
features.loc[con_historial_previo, "tendencia_90d"] = (
    features.loc[con_historial_previo, "unidades_ult_90d"]
    - features.loc[con_historial_previo, "unidades_90d_previos"]
) / features.loc[con_historial_previo, "unidades_90d_previos"]
features["sin_hist_previo"] = (features["unidades_90d_previos"] == 0).astype(int)

features["unidades_por_cliente"] = (
    features["unidades_obs"] / features["clientes_unicos"]
)
features["unidades_por_dia_activo"] = (
    features["unidades_obs"] / features["dias_con_venta"]
)

compra_por_cliente = (
    obs.groupby(["article_id", "customer_id"], observed=True)["unidades"]
    .sum()
)
clientes_recurrentes = compra_por_cliente[
    compra_por_cliente >= 2
].groupby(level="article_id").size()
features["clientes_recurrentes"] = (
    clientes_recurrentes.reindex(features.index).fillna(0).astype(int)
)
features["share_clientes_recurrentes"] = (
    features["clientes_recurrentes"] / features["clientes_unicos"]
).fillna(0)

features["cambio_precio_30d"] = (
    features["precio_ultimo"] - features["precio_medio"]
)

unidades_pred = (
    pred.groupby("article_id", observed=True)["unidades"]
    .sum()
    .rename("unidades_prox_30d")
)
features = features.join(unidades_pred)
features["unidades_prox_30d"] = features["unidades_prox_30d"].fillna(0).astype(int)
features["y_demanda_30d"] = (
    features["unidades_prox_30d"].ge(1).astype(int)
)

features = features.reset_index()
filtrado_1 = features[features["unidades_obs"].ge(1)].copy()
filtrado_5 = features[features["unidades_obs"].ge(5)].copy()
filtrado_10 = features[features["unidades_obs"].ge(10)].copy()

print("Resumen de población:")
print(f"Con al menos 1 venta en observación: {filtrado_1.shape[0]:,}")
print(f"Con al menos 5 ventas en observación: {filtrado_5.shape[0]:,}")
print(f"Con al menos 10 ventas en observación: {filtrado_10.shape[0]:,}")

features = features[
    features["unidades_obs"].ge(5)
].copy()

articulos = pd.read_csv(
    ARTICULOS,
    usecols=[
        "article_id",
        "product_type_name",
        "product_group_name",
        "index_group_name",
        "garment_group_name",
        "colour_group_name",
        "graphical_appearance_name",
        "section_name",
        "department_name",
    ],
)

modelado = features.merge(articulos, on="article_id", how="left", validate="one_to_one")
modelado = modelado.drop(
    columns=[
        "primera_venta",
        "ultima_venta",
        "clientes_recurrentes",
    ]
)

positivos = int(modelado["y_demanda_30d"].sum())
tasa = positivos / modelado.shape[0]

modelado.to_csv(SALIDA, index=False)

print(f"Archivo generado: {SALIDA}")
print(f"Filas: {modelado.shape[0]:,}")
print(f"Positivos: {positivos:,}")
print(f"Tasa positiva: {tasa:.1%}")