const form = document.querySelector("#customer-form");
const rows = document.querySelector("#customer-rows");
const message = document.querySelector("#message");
const status = document.querySelector("#feed-status");
const numberInput = form.elements.customer_number;
let editingNumber = null;
let refreshInProgress = false;

async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

async function loadCustomers() {
  if (refreshInProgress) return;
  refreshInProgress = true;
  try {
    const customers = await request("/api/customers");
    rows.replaceChildren();
    for (const customer of customers) {
      const row = document.createElement("tr");
      for (const key of ["customer_number", "customer_name", "customer_type", "customer_category"]) {
        const cell = document.createElement("td");
        cell.textContent = customer[key];
        row.append(cell);
      }
      const actions = document.createElement("td");
      actions.className = "actions";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "secondary";
      edit.textContent = "Edit";
      edit.addEventListener("click", () => beginEdit(customer));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "danger";
      remove.textContent = "Delete";
      remove.addEventListener("click", () => deleteCustomer(customer.customer_number));
      actions.append(edit, remove);
      row.append(actions);
      rows.append(row);
    }
    status.textContent = `Updated ${new Date().toLocaleTimeString()} · refreshes every 5 seconds`;
  } catch (error) {
    status.textContent = `Could not refresh: ${error.message}`;
  } finally {
    refreshInProgress = false;
  }
}

function beginEdit(customer) {
  editingNumber = customer.customer_number;
  form.elements.customer_number.value = customer.customer_number;
  form.elements.customer_name.value = customer.customer_name;
  form.elements.customer_type.value = customer.customer_type;
  form.elements.customer_category.value = customer.customer_category;
  numberInput.disabled = true;
  document.querySelector("#form-title").textContent = "Edit customer";
  document.querySelector("#save-button").textContent = "Save changes";
  document.querySelector("#cancel-button").hidden = false;
  message.textContent = "";
}

function resetForm() {
  editingNumber = null;
  form.reset();
  numberInput.disabled = false;
  document.querySelector("#form-title").textContent = "Add customer";
  document.querySelector("#save-button").textContent = "Add customer";
  document.querySelector("#cancel-button").hidden = true;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(form).entries());
  if (editingNumber) delete data.customer_number;
  try {
    await request(
      editingNumber
        ? `/api/customers/${encodeURIComponent(editingNumber)}`
        : "/api/customers",
      {
        method: editingNumber ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      },
    );
    resetForm();
    message.textContent = "Customer saved.";
    await loadCustomers();
  } catch (error) {
    message.textContent = error.message;
  }
});

async function deleteCustomer(customerNumber) {
  if (!window.confirm(`Delete customer ${customerNumber}?`)) return;
  try {
    await request(`/api/customers/${encodeURIComponent(customerNumber)}`, { method: "DELETE" });
    if (editingNumber === customerNumber) resetForm();
    message.textContent = "Customer deleted.";
    await loadCustomers();
  } catch (error) {
    message.textContent = error.message;
  }
}

document.querySelector("#cancel-button").addEventListener("click", resetForm);
loadCustomers();
window.setInterval(loadCustomers, 5000);
