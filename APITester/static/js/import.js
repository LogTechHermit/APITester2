const form = document.querySelector("#import-form");
const button = document.querySelector("#upload-button");
const panel = document.querySelector("#results-panel");
const summary = document.querySelector("#summary");
const resultRows = document.querySelector("#result-rows");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = document.querySelector("#csv-file").files[0];
  if (!file) return;

  button.disabled = true;
  button.textContent = "Importing…";
  panel.hidden = true;
  try {
    const data = new FormData();
    data.append("file", file);
    const response = await fetch("/api/customers/import", {
      method: "POST",
      body: data,
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.detail || `Import failed (${response.status})`);
    }

    summary.textContent =
      `${body.succeeded} succeeded · ${body.failed} failed · ${body.total_rows} data rows`;
    summary.className = body.failed ? "error" : "success";
    resultRows.replaceChildren();
    for (const item of body.results) {
      const tr = document.createElement("tr");
      for (const value of [
        item.row,
        item.action,
        item.customer_number || "—",
        item.status === "success" ? "Saved" : item.message,
      ]) {
        const td = document.createElement("td");
        td.textContent = value;
        if (item.status === "error") td.className = "error";
        tr.append(td);
      }
      resultRows.append(tr);
    }
    panel.hidden = false;
  } catch (error) {
    summary.textContent = error.message;
    summary.className = "error";
    resultRows.replaceChildren();
    panel.hidden = false;
  } finally {
    button.disabled = false;
    button.textContent = "Import CSV";
  }
});
