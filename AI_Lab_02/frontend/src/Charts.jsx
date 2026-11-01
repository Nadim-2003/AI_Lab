import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
export function RuntimeChart({ rows }) {
  return (
    <div className="chart" aria-label="Measured solver runtime chart">
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} />
          <YAxis unit=" ms" tick={{ fontSize: 10 }} />
          <Tooltip />
          <Bar
            dataKey="runtime"
            name="Solver runtime (ms)"
            fill="#168c79"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
export function ExperimentChart({ rows, metric = "runtime_ms" }) {
  const methods = [...new Set(rows.map((r) => r.method))];
  const points = [...new Set(rows.map((r) => r.variant))].map((variant) => {
    const point = { variant };
    for (const method of methods) {
      const samples = rows.filter(
        (r) => r.variant === variant && r.method === method,
      );
      point[method] =
        samples.reduce(
          (sum, r) =>
            sum +
            (metric === "fully_served"
              ? r.summary.fully_served
              : r.metrics[metric]),
          0,
        ) / samples.length;
    }
    return point;
  });
  return (
    <div className="chart" aria-label={`Experiment ${metric} chart`}>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={points}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="variant" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 10 }} />
          {methods.map((method, n) => (
            <Line
              key={method}
              dataKey={method}
              stroke={
                [
                  "#168c79",
                  "#7455b4",
                  "#dd654e",
                  "#3983bb",
                  "#b28d28",
                  "#324e55",
                  "#a95080",
                ][n % 7]
              }
              dot
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
