export async function api(path, data) {
  const response = await fetch(
    `/api${path}`,
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
  );
  const result = await response.json();
  if (!response.ok)
    throw new Error(
      typeof result.detail === "string"
        ? result.detail
        : JSON.stringify(result.detail),
    );
  return result;
}
export const colors = {
  ambulance: "#168c79",
  fire: "#dd654e",
  rescue: "#7455b4",
};
export const algorithms = [
  ["backtracking", "Backtracking"],
  ["backjumping", "Conflict-directed backjumping"],
  ["forward_checking", "Forward checking"],
  ["arc_consistency", "AC-3 + backtracking"],
  ["local_search", "Min-conflicts local search"],
];
export const presets = [
  {
    label: "Plain BT",
    algorithm: "backtracking",
    mrv: false,
    degree: false,
    lcv: false,
    severity_order: false,
  },
  {
    label: "BT + MRV",
    algorithm: "backtracking",
    mrv: true,
    degree: false,
    lcv: false,
  },
  {
    label: "BT + MRV + LCV",
    algorithm: "backtracking",
    mrv: true,
    degree: true,
    lcv: true,
  },
  {
    label: "Forward checking",
    algorithm: "forward_checking",
    mrv: true,
    degree: true,
  },
  { label: "AC-3", algorithm: "arc_consistency", mrv: true, degree: true },
  { label: "Backjumping", algorithm: "backjumping", mrv: true, degree: true },
  { label: "Local search", algorithm: "local_search" },
  {
    label: "Plain CBJ",
    algorithm: "backjumping",
    mrv: false,
    degree: false,
    lcv: false,
    severity_order: false,
  },
];
export function download(name, value) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
export const labelOptions = (o) =>
  `${algorithms.find(([key]) => key === o.algorithm)?.[1] || o.algorithm}${o.algorithm === "local_search" ? "" : ` · ${o.mrv ? "MRV" : "fixed"}${o.degree ? "+degree" : ""}${o.lcv ? "+LCV" : ""}${o.mac ? "+MAC" : ""}`}`;
