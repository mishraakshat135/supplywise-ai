
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

df = pd.read_csv("retail_sales.csv", parse_dates=["date"])
df = df.sort_values(["store_id", "item_id", "date"])

g = df.groupby(["store_id", "item_id"])["sales"]

df["lag_1"] = g.shift(1)
df["lag_7"] = g.shift(7)
df["lag_14"] = g.shift(14)
df["rolling_7"] = g.transform(lambda x: x.shift(1).rolling(7).mean())
df["rolling_14"] = g.transform(lambda x: x.shift(1).rolling(14).mean())

df.dropna(inplace=True)

df["store_id"] = df["store_id"].astype("category")
df["item_id"] = df["item_id"].astype("category")

features = [
    "store_id", "item_id", "weekday", "month",
    "lag_1", "lag_7", "lag_14", "rolling_7", "rolling_14"
]

last_date = df["date"].max()
cutoff = last_date - pd.Timedelta(days=14)

train = df[df["date"] <= cutoff]
sample = train.sample(min(800000, len(train)), random_state=42)

model = HistGradientBoostingRegressor(
    max_iter=100,
    max_leaf_nodes=31,
    learning_rate=0.1,
    categorical_features=["store_id", "item_id"],
    random_state=42
)

model.fit(sample[features], sample["sales"])

wide = df.pivot(
    index="date", columns=["store_id", "item_id"], values="sales"
).sort_index()

series = wide.columns

def predict_days(history, dates):
    hist = history.to_numpy(dtype=float)
    predictions = []

    for date in dates:
        X = pd.DataFrame({
            "store_id": [s for s, i in series],
            "item_id": [i for s, i in series],
            "weekday": date.weekday(),
            "month": date.month,
            "lag_1": hist[-1],
            "lag_7": hist[-7],
            "lag_14": hist[-14],
            "rolling_7": hist[-7:].mean(axis=0),
            "rolling_14": hist[-14:].mean(axis=0)
        })

        X["store_id"] = X["store_id"].astype("category")
        X["item_id"] = X["item_id"].astype("category")

        pred = np.maximum(0, model.predict(X[features]))
        predictions.append(pred)
        hist = np.vstack([hist, pred])

    return np.array(predictions)

test_dates = pd.date_range(cutoff + pd.Timedelta(days=1), last_date)
history = wide.loc[wide.index <= cutoff]
actual = wide.reindex(test_dates).to_numpy()
predicted = predict_days(history, test_dates)

def evaluate(actual, predicted):
    mae = mean_absolute_error(actual.ravel(), predicted.ravel())
    rmse = np.sqrt(mean_squared_error(actual.ravel(), predicted.ravel()))
    wape = np.sum(np.abs(actual - predicted)) / np.sum(actual) * 100

    print("MAE:", round(mae, 2))
    print("RMSE:", round(rmse, 2))
    print("WAPE:", round(wape, 2), "%")

print("MODEL RESULTS")
evaluate(actual, predicted)

baseline_hist = history.to_numpy()
baseline = []

for date in test_dates:
    pred = baseline_hist[-7]
    baseline.append(pred)
    baseline_hist = np.vstack([baseline_hist, pred])

baseline = np.array(baseline)

print("\nSEASONAL NAIVE BASELINE")
evaluate(actual, baseline)

sample = df.sample(min(800000, len(df)), random_state=42)
model.fit(sample[features], sample["sales"])

future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=14)
future_predictions = predict_days(wide, future_dates)

forecast = pd.DataFrame({
    "date": np.repeat(future_dates, len(series)),
    "store_id": np.tile([s for s, i in series], 14),
    "item_id": np.tile([i for s, i in series], 14),
    "predicted_sales": future_predictions.ravel()
})

forecast["predicted_sales"] = forecast["predicted_sales"].round(2)
forecast.to_csv("sku_forecast_14_days.csv", index=False)

actual_df = pd.DataFrame(actual, index=test_dates, columns=series)
pred_df = pd.DataFrame(predicted, index=test_dates, columns=series)

items = sorted(
    df["item_id"].astype(str).unique(),
    key=lambda x: int("".join(c for c in x if c.isdigit()) or 0)
)

for item in items:
    cols = [c for c in series if str(c[1]) == item]

    a = actual_df[cols].sum(axis=1)
    p = pred_df[cols].sum(axis=1)

    plt.figure(figsize=(10, 5))
    plt.plot(test_dates, a, marker="o", label="Actual")
    plt.plot(test_dates, p, marker="o", label="Predicted")

    plt.title(f"Item {item}")
    plt.xlabel("Date")
    plt.ylabel("Sales Across Stores")
    plt.xticks(test_dates, rotation=45)
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()
