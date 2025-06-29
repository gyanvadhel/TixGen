function createPreviewGrid() {
  const grid = document.getElementById("preview-grid");
  grid.innerHTML = ""; // Clear existing cells
  for (let i = 0; i < 27; i++) {
    const cell = document.createElement("div");
    cell.className = "ticket-cell";
    cell.innerText = "12"; // Placeholder number
    grid.appendChild(cell);
  }
}

function updatePreview() {
  const name = document.querySelector('input[name="name"]').value || "Host";
  const phone = document.querySelector('input[name="phone"]').value.trim();
  const message = document.querySelector('input[name="custom_message"]').value.trim();
  const hideTicketNumber = document.getElementById("hide_ticket_number").checked;

  const headerColor = document.querySelector('input[name="header_color"]').value;
  const gridColor = document.querySelector('input[name="grid_color"]').value;
  const fontColor = document.querySelector('input[name="font_color"]').value; // Get the new font color
  
  // Overall ticket background will be same as header/footer
  const ticketBgColor = headerColor; 
  const pageBgColor = document.querySelector('input[name="page_bg_color"]').value;

  // Update page background in preview
  document.getElementById("pdf-bg").style.backgroundColor = pageBgColor;

  // Set ticket header
  const header = document.getElementById("preview-header");
  header.style.backgroundColor = headerColor;
  header.style.color = fontColor; // Use selected font color
  header.innerText = hideTicketNumber ? name : `${name} | Ticket #`; // Update based on checkbox

  // Set ticket footer
  const footer = document.getElementById("preview-footer");
  footer.style.backgroundColor = headerColor; // Footer background is header color
  footer.style.color = fontColor; // Use selected font color

    // DARK MODE TOGGLE
  const darkToggle = document.getElementById("darkModeToggle");
  const prefersDark = localStorage.getItem("darkMode") === "true";
  document.body.classList.toggle("dark", prefersDark);
  darkToggle.checked = prefersDark;

  darkToggle.addEventListener("change", () => {
    const isDark = darkToggle.checked;
    document.body.classList.toggle("dark", isDark);
    localStorage.setItem("darkMode", isDark);
  });

  
  // Construct footer text: only phone and message
  let footerText = "";
  if (phone) {
    footerText += phone;
  }
  if (message) {
    if (footerText) { // Add a separator if phone number exists
      footerText += " - ";
    }
    footerText += message;
  }
  footer.innerText = footerText || "(Optional info)"; // Display placeholder if both are empty

  // Update the entire ticket-preview background to ticketBgColor (which is now headerColor)
  // This covers the space behind the grid cells, header and footer are drawn on top.
  document.querySelector('.ticket-preview').style.backgroundColor = ticketBgColor;

  // Update ticket grid border and cell colors
  document.getElementById("preview-grid").style.borderColor = '#000000'; // Black border for grid container
  const cells = document.querySelectorAll(".ticket-cell");
  cells.forEach(cell => {
    cell.style.backgroundColor = gridColor; // Cell background is grid color
    cell.style.borderColor = '#000000'; // Cell borders are black
    cell.style.color = fontColor; // Use selected font color for numbers
  });
}

// Ensure the grid is created and preview is updated when the DOM is fully loaded
document.addEventListener("DOMContentLoaded", () => {
  createPreviewGrid();
  updatePreview(); // Initial update
  // DARK MODE TOGGLE
  const darkToggle = document.getElementById("darkModeToggle");
  const prefersDark = localStorage.getItem("darkMode") === "true";
  document.body.classList.toggle("dark", prefersDark);
  darkToggle.checked = prefersDark;

  darkToggle.addEventListener("change", () => {
    const isDark = darkToggle.checked;
    document.body.classList.toggle("dark", isDark);
    localStorage.setItem("darkMode", isDark);
  });

  // Add event listeners to all relevant input fields for continuous updates
  document.querySelectorAll('input[type="color"], input[type="text"], input[type="tel"], input[type="number"]').forEach(input => {
    input.addEventListener('input', updatePreview); // 'input' event for continuous updates
  });

  // Special handling for checkbox as it uses 'change' event
  document.getElementById('hide_ticket_number').addEventListener('change', updatePreview);
});
