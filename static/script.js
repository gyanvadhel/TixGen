// Global state
let isInitialized = false;

// Initialize the application
function initializeApp() {
  if (isInitialized) return;
  
  createPreviewGrid();
  setupEventListeners();
  initializeDarkMode();
  updatePreview();
  
  isInitialized = true;
}

// Create the preview grid with sample numbers
function createPreviewGrid() {
  const grid = document.getElementById("preview-grid");
  if (!grid) return;
  
  grid.innerHTML = "";
  
  // Sample ticket data for preview
  const sampleNumbers = [
    [null, 12, null, 34, null, 56, null, 78, null],
    [5, null, 23, null, 45, null, 67, null, 89],
    [null, 18, null, 39, null, 52, null, 71, null]
  ];
  
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 9; col++) {
      const cell = document.createElement("div");
      cell.className = "ticket-cell";
      
      const number = sampleNumbers[row][col];
      if (number) {
        cell.textContent = number;
      }
      
      grid.appendChild(cell);
    }
  }
}

// Update the live preview
function updatePreview() {
  const elements = {
    name: document.querySelector('input[name="name"]'),
    phone: document.querySelector('input[name="phone"]'),
    message: document.querySelector('input[name="custom_message"]'),
    hideTicketNumber: document.getElementById("hide_ticket_number"),
    headerColor: document.querySelector('input[name="header_color"]'),
    gridColor: document.querySelector('input[name="grid_color"]'),
    fontColor: document.querySelector('input[name="font_color"]'),
    pageBgColor: document.querySelector('input[name="page_bg_color"]'),
    previewHeader: document.getElementById("preview-header"),
    previewFooter: document.getElementById("preview-footer"),
    pdfBg: document.getElementById("pdf-bg"),
    ticketPreview: document.querySelector('.ticket-preview'),
    previewGrid: document.getElementById("preview-grid")
  };

  // Check if all required elements exist
  if (!elements.name || !elements.previewHeader) return;

  // Get values
  const name = elements.name.value || "Host";
  const phone = elements.phone?.value.trim() || "";
  const message = elements.message?.value.trim() || "";
  const hideTicketNumber = elements.hideTicketNumber?.checked || false;
  const headerColor = elements.headerColor?.value || "#667eea";
  const gridColor = elements.gridColor?.value || "#f8fafc";
  const fontColor = elements.fontColor?.value || "#1e293b";
  const pageBgColor = elements.pageBgColor?.value || "#ffffff";

  // Update page background
  if (elements.pdfBg) {
    elements.pdfBg.style.backgroundColor = pageBgColor;
  }

  // Update header
  if (elements.previewHeader) {
    elements.previewHeader.style.backgroundColor = headerColor;
    elements.previewHeader.style.color = fontColor;
    elements.previewHeader.textContent = hideTicketNumber ? name : `${name} | Ticket #`;
  }

  // Update footer
  if (elements.previewFooter) {
    elements.previewFooter.style.backgroundColor = headerColor;
    elements.previewFooter.style.color = fontColor;
    
    let footerText = "";
    if (phone) footerText += phone;
    if (message) {
      if (footerText) footerText += " - ";
      footerText += message;
    }
    elements.previewFooter.textContent = footerText || "Optional info";
  }

  // Update ticket background
  if (elements.ticketPreview) {
    elements.ticketPreview.style.backgroundColor = headerColor;
  }

  // Update grid cells
  if (elements.previewGrid) {
    elements.previewGrid.style.borderColor = '#e2e8f0';
    const cells = elements.previewGrid.querySelectorAll(".ticket-cell");
    cells.forEach(cell => {
      cell.style.backgroundColor = gridColor;
      cell.style.borderColor = '#e2e8f0';
      cell.style.color = fontColor;
    });
  }
}

// Setup all event listeners
function setupEventListeners() {
  // Input event listeners for real-time updates
  const inputSelectors = [
    'input[name="name"]',
    'input[name="phone"]',
    'input[name="custom_message"]',
    'input[name="header_color"]',
    'input[name="grid_color"]',
    'input[name="font_color"]',
    'input[name="page_bg_color"]'
  ];

  inputSelectors.forEach(selector => {
    const element = document.querySelector(selector);
    if (element) {
      element.addEventListener('input', debounce(updatePreview, 100));
    }
  });

  // Checkbox event listener
  const hideTicketCheckbox = document.getElementById('hide_ticket_number');
  if (hideTicketCheckbox) {
    hideTicketCheckbox.addEventListener('change', updatePreview);
  }

  // Form submission enhancement
  const form = document.querySelector('.ticket-form');
  if (form) {
    form.addEventListener('submit', handleFormSubmission);
  }
}

// Handle form submission with loading state
function handleFormSubmission(event) {
  const submitButton = event.target.querySelector('.generate-btn');
  if (submitButton) {
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    submitButton.disabled = true;
    
    // Reset button after 10 seconds (fallback)
    setTimeout(() => {
      submitButton.innerHTML = originalText;
      submitButton.disabled = false;
    }, 10000);
  }
}

// Dark mode functionality
function initializeDarkMode() {
  const darkToggle = document.getElementById("darkModeToggle");
  if (!darkToggle) return;

  // Load saved preference
  const prefersDark = localStorage.getItem("darkMode") === "true";
  document.body.classList.toggle("dark", prefersDark);
  darkToggle.checked = prefersDark;

  // Add event listener
  darkToggle.addEventListener("change", () => {
    const isDark = darkToggle.checked;
    document.body.classList.toggle("dark", isDark);
    localStorage.setItem("darkMode", isDark);
    
    // Add smooth transition
    document.body.style.transition = "all 0.3s ease";
    setTimeout(() => {
      document.body.style.transition = "";
    }, 300);
  });
}

// Utility function for debouncing
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Smooth animations for form interactions
function addFormAnimations() {
  const formInputs = document.querySelectorAll('.form-input, .color-input');
  
  formInputs.forEach(input => {
    input.addEventListener('focus', function() {
      this.parentElement.style.transform = 'scale(1.02)';
      this.parentElement.style.transition = 'transform 0.2s ease';
    });
    
    input.addEventListener('blur', function() {
      this.parentElement.style.transform = 'scale(1)';
    });
  });
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  initializeApp();
  addFormAnimations();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && isInitialized) {
    updatePreview();
  }
});

// Export functions for potential external use
window.TixGenApp = {
  updatePreview,
  initializeApp,
  createPreviewGrid
};