from flask import Flask, render_template, request, send_file
from io import BytesIO
import random
import math
from fpdf import FPDF

app = Flask(__name__)

# --- Ticket Generation Logic ---

# Column ranges for numbers (e.g., 1-9, 10-19, etc.)
col_ranges = [list(range(1, 10))] + [list(range(i, i + 10)) for i in range(10, 80, 10)] + [list(range(80, 91))]

def generate_ticket_structure_and_numbers():
    """
    Generates a single, valid Tambola ticket (3 rows x 9 columns)
    with 5 numbers per row, numbers filled according to rules,
    and sorted in ascending order within columns.
    This uses a highly efficient, deterministic construction.
    """
    ticket_grid = [[None for _ in range(9)] for _ in range(3)] # The 3x9 ticket grid
    
    # Store column indices for each row, 5 per row.
    # This ensures 5 numbers per row.
    row_col_indices = [[] for _ in range(3)] 
    
    # Track which columns have already been assigned a number to ensure each column has at least one number
    # and to distribute 1-number and 2-number columns
    cols_with_numbers_count = [0] * 9 # How many numbers are in each column on this ticket (max 2)

    # 1. Distribute 15 numbers across 9 columns, 3 rows, ensuring 5 numbers per row.
    # This algorithm fills numbers directly into columns ensuring correct distribution.
    
    # Step 1: Place one number in each column to ensure all columns have at least one.
    # We'll pick a random row for each column for its first number.
    
    # Create a list of all (row_idx, col_idx) pairs that are valid for 15 numbers (5 per row)
    all_possible_positions = []
    for r in range(3):
        for c in range(9):
            all_possible_positions.append((r, c))
    random.shuffle(all_possible_positions)

    # Assign 15 unique positions for numbers. This is the core mask generation.
    num_positions = []
    
    # Ensure 5 numbers per row
    row_counts = [0] * 3
    # Ensure all columns have at least one number
    column_has_number = [False] * 9

    # Try to fill 15 positions adhering to rules
    for r, c in all_possible_positions:
        if row_counts[r] < 5 and cols_with_numbers_count[c] < 2: # Max 2 numbers per column in a single ticket
            if not column_has_number[c]: # If this column doesn't have a number yet, prioritize it
                num_positions.append((r, c))
                row_counts[r] += 1
                cols_with_numbers_count[c] += 1
                column_has_number[c] = True
            elif sum(row_counts) < 15 and cols_with_numbers_count[c] == 1: # If already has one, can add a second
                 num_positions.append((r,c))
                 row_counts[r] += 1
                 cols_with_numbers_count[c] += 1
        
        if sum(row_counts) == 15: # Stop once 15 numbers are placed
            break

    # If we didn't get 15 numbers, or didn't get all columns with at least one, retry the whole ticket
    if sum(row_counts) != 15 or not all(column_has_number):
        # This branch indicates a flaw in the selection strategy, should rarely happen if loop is large enough
        # For a truly deterministic setup, one would use a known valid mask or a more complex greedy algorithm.
        # For now, we'll re-shuffle and retry.
        return generate_ticket_structure_and_numbers() # Recursive retry

    # Sort `num_positions` by column index primarily, then by row index.
    # This helps in the next step when filling numbers.
    num_positions.sort(key=lambda x: (x[1], x[0]))

    # 2. Fill the numbers into the generated structure
    for c_idx in range(9): # For each column (0 to 8)
        # Collect the actual numbers for this column's range, then shuffle.
        numbers_in_range = col_ranges[c_idx].copy()
        random.shuffle(numbers_in_range)
        
        # Get all row indices for current column that will have a number
        rows_for_this_col = []
        for r_idx in range(3):
            if (r_idx, c_idx) in num_positions:
                rows_for_this_col.append(r_idx)
        
        # Take exactly as many numbers as there are slots in this column
        num_to_assign_count = len(rows_for_this_col)
        
        # Ensure numbers are taken from range and sorted before assigning
        # This is where the ascending order per column is guaranteed.
        assigned_numbers_for_this_col = sorted(random.sample(numbers_in_range, num_to_assign_count))

        for i, r_idx in enumerate(rows_for_this_col):
            ticket_grid[r_idx][c_idx] = assigned_numbers_for_this_col[i]
            
    return ticket_grid


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

@app.route('/')
def landing_page():
    return render_template("landing.html")

@app.route('/generator')
def ticket_generator_page():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate():
    host = request.form.get('name', 'Host')
    phone = request.form.get('phone', '').strip()
    message = request.form.get('custom_message', '').strip()
    hide_ticket_number = 'hide_ticket_number' in request.form

    try:
        pages = int(request.form.get('pages', 1))
    except ValueError:
        pages = 1
    pages = max(1, min(pages, 10))

    page_bg_color = hex_to_rgb(request.form.get("page_bg_color", "#6A92CD"))
    header_fill = hex_to_rgb(request.form.get("header_color", "#658950"))
    footer_fill = header_fill
    grid_color = hex_to_rgb(request.form.get("grid_color", "#8B4513"))
    ticket_bg_fill = header_fill
    font_color = hex_to_rgb(request.form.get("font_color", "#FFFFFF"))

    tickets = []
    total_tickets_needed = pages * 12
    
    try:
        for _ in range(total_tickets_needed):
            tickets.append(generate_ticket_structure_and_numbers())
    except RuntimeError as e:
        return render_template("error.html", message=str(e)), 500


    pdf = FPDF('P', 'mm', 'A4')
    pdf.set_auto_page_break(False)

    W, H = 210, 297
    mx, my = 10, 10
    gx, gy = 4, 7
    cp = 2
    per = 12 # 12 tickets per A4 page
    rows = 6 # 6 tickets per column on the page layout (2 columns total)
    aw = W - 2 * mx - (cp - 1) * gx # Available width for tickets
    tw = aw / cp # Ticket width
    hh = 6 # Header height
    fh = 5 # Footer height
    ch = 9 # Cell height
    cw = tw / 9 # Cell width (ticket width / 9 columns)
    gh = ch * 3 # Grid height (3 rows * cell height)
    th = hh + gh + fh # Total ticket height (header + grid + footer)

    # --- Add Instructions Page ---
    pdf.add_page()
    pdf.set_fill_color(*page_bg_color)
    pdf.rect(0, 0, W, H, 'F')
    pdf.set_text_color(*font_color)

    pdf.set_font('helvetica', 'B', 20)
    pdf.set_xy(mx, my)
    pdf.cell(W - 2 * mx, 10, 'How to Play Tambola (Housie)', align='C')

    pdf.ln(15)
    pdf.set_font('helvetica', '', 12)
    rules_text = [
        "Tambola, also known as Housie, is a popular game of chance.",
        "",
        "Objective: To be the first to mark off numbers on your ticket in specific patterns.",
        "",
        "Setup:",
        "- Each player receives one or more unique Tambola tickets.",
        "- The Caller announces random numbers (1-90).",
        "",
        "Gameplay:",
        "1.  As the Caller announces a number, if it's on your ticket, mark it off.",
        "2.  Announce your claim for a winning pattern immediately after marking the last number for that pattern.",
        "3.  The Caller verifies the claim. If correct, you win the prize for that pattern!",
        "",
        "Common Patterns:",
        "- Early Five: First 5 numbers marked on a ticket.",
        "- Top Line: All numbers marked in the top row.",
        "- Middle Line: All numbers marked in the middle row.",
        "- Bottom Line: All numbers marked in the bottom row.",
        "- Full House: All 15 numbers marked on your ticket."
    ]
    for line in rules_text:
        pdf.set_x(mx)
        pdf.multi_cell(W - 2 * mx, 6, line)
    
    # --- Callable Numbers Page (Removed as requested) ---
    # The section for callable numbers page has been removed.

    # --- Add Tickets Pages ---
    for p in range(math.ceil(len(tickets) / per)):
        pdf.add_page()
        pdf.set_fill_color(*page_bg_color)
        pdf.rect(0, 0, W, H, 'F')

        for i in range(per):
            idx = p * per + i
            if idx >= len(tickets):
                break
            data = tickets[idx]
            colp = 0 if i < rows else 1
            rowp = i % rows
            x0 = mx + colp * (tw + gx)
            y0 = my + rowp * (th + gy)

            pdf.set_fill_color(*ticket_bg_fill)
            pdf.rect(x0, y0, tw, th, style='F')

            # Header
            pdf.set_fill_color(*header_fill)
            pdf.rect(x0, y0, tw, hh, style='F')
            pdf.set_text_color(*font_color)
            pdf.set_font('helvetica', 'B', 10)
            
            header_text = host
            if not hide_ticket_number:
                header_text += f" | Ticket {idx + 1}"
            
            header_text_height = pdf.font_size
            header_vertical_offset = (hh - header_text_height) / 2
            
            pdf.set_xy(x0, y0 + header_vertical_offset) 
            pdf.cell(tw, hh - 2 * header_vertical_offset, header_text, border=0, align='C')

            # Grid (cells with their background and black borders)
            pdf.set_font('helvetica', 'B', 16)
            pdf.set_text_color(*font_color)
            pdf.set_fill_color(*grid_color)
            pdf.set_draw_color(0, 0, 0)

            for r_cell in range(3):
                for c_cell in range(9):
                    cx = x0 + c_cell * cw
                    cy = y0 + hh + r_cell * ch
                    pdf.rect(cx, cy, cw, ch, style='F')
                    pdf.rect(cx, cy, cw, ch, style='D')

                    num = data[r_cell][c_cell]
                    if num:
                        sw = pdf.get_string_width(str(num))
                        pdf.set_xy(cx + (cw - sw) / 2.8, cy + (ch - pdf.font_size) / 2)
                        pdf.cell(sw, pdf.font_size, str(num), border=0)

            # Footer
            footer_y_start = y0 + hh + gh
            pdf.set_fill_color(*footer_fill)
            pdf.rect(x0, footer_y_start, tw, fh, style='F')
            
            pdf.set_text_color(*font_color)
            pdf.set_font('helvetica', 'B', 11)

            footer_text_height = pdf.font_size
            footer_vertical_offset = (fh - footer_text_height) / 2
            
            pdf.set_xy(x0, footer_y_start + footer_vertical_offset)

            footer_text = host
            if phone:
                footer_text += f" - {phone}"
            if message:
                footer_text += f" - {message}"

            pdf.cell(tw, fh, footer_text, align='C')

    output_bytes = pdf.output(dest='S').encode('latin1') if isinstance(pdf.output(dest='S'), str) else pdf.output(dest='S')
    pdf_stream = BytesIO(output_bytes)
    pdf_stream.seek(0)
    return send_file(pdf_stream, download_name="tickets.pdf", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=False)
