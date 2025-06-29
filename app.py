from flask import Flask, render_template, request, send_file
from io import BytesIO
import random
import math
from fpdf import FPDF

app = Flask(__name__)

# --- Optimized Ticket Generation Logic ---

# Column ranges for numbers (e.g., 1-9, 10-19, etc.)
COL_RANGES = [list(range(1, 10))] + [list(range(i, i + 10)) for i in range(10, 80, 10)] + [list(range(80, 91))]

def generate_valid_ticket():
    """
    Generates a single, valid Tambola ticket using a fast, constructive algorithm.
    This avoids the performance issues of random trial-and-error.
    """
    ticket_grid = [[None for _ in range(9)] for _ in range(3)]

    # Step 1: Determine the column indices for each row. Each row must have 5 numbers.
    # We start by randomly selecting 5 columns for each row.
    row_patterns = [sorted(random.sample(range(9), 5)) for _ in range(3)]

    # Step 2: Validate and fix the column structure.
    # The rule: Every column must have at least one number.
    # The initial random selection might leave a column empty. This loop fixes that.
    
    # Get all column indices that have at least one number assigned.
    all_used_cols = set(row_patterns[0]) | set(row_patterns[1]) | set(row_patterns[2])

    # Loop while not all 9 columns are used. This loop is fast and runs only a few times, if at all.
    while len(all_used_cols) < 9:
        # Find a column that is currently empty.
        unoccupied_col = list(set(range(9)) - all_used_cols)[0]

        # Find columns that are "over-occupied" (i.e., used in 2 or 3 rows).
        # These are ideal candidates for replacement.
        col_counts = [0] * 9
        for r in range(3):
            for c in row_patterns[r]:
                col_counts[c] += 1
        
        # We want to replace a column in a row that is used more than once.
        # This prevents us from creating a new empty column.
        candidates_for_replacement = [c for c, count in enumerate(col_counts) if count > 1]
        
        # Pick a random row to modify. A row with more "over-occupied" columns is a good choice.
        # This simple random choice is sufficient and fast.
        row_to_modify_idx = random.randint(0, 2)
        
        # From the chosen row, find a column that can be replaced.
        # The best column to replace is one from our candidate list.
        replaceable_cols_in_row = list(set(row_patterns[row_to_modify_idx]) & set(candidates_for_replacement))
        
        if not replaceable_cols_in_row:
            # Fallback: if the chosen row has no over-occupied columns (rare),
            # just pick any of its columns that isn't the sole occupant of its column.
            # This is a safeguard; the primary logic almost always works.
            for col_in_row in row_patterns[row_to_modify_idx]:
                 if col_counts[col_in_row] > 1:
                    replaceable_cols_in_row.append(col_in_row)
        
        col_to_replace = random.choice(replaceable_cols_in_row)

        # Perform the swap: remove the old column and add the unoccupied one.
        row_patterns[row_to_modify_idx].remove(col_to_replace)
        row_patterns[row_to_modify_idx].append(unoccupied_col)
        row_patterns[row_to_modify_idx].sort()

        # Update the set of used columns and repeat the check.
        all_used_cols = set(row_patterns[0]) | set(row_patterns[1]) | set(row_patterns[2])

    # Step 3: Place numbers into the valid structure.
    # The structure is now guaranteed to be valid.
    
    # First, group rows by column. `col_placement[0]` will list rows that need a number in column 0.
    col_placements = [[] for _ in range(9)]
    for r_idx, row_cols in enumerate(row_patterns):
        for c_idx in row_cols:
            col_placements[c_idx].append(r_idx)

    # Now, fill the grid column by column.
    for c_idx, rows in enumerate(col_placements):
        num_of_entries = len(rows)
        if num_of_entries > 0:
            # Get the valid number range for the current column (e.g., 1-9 for col 0).
            numbers_from_range = random.sample(COL_RANGES[c_idx], num_of_entries)
            numbers_from_range.sort() # Numbers must be sorted vertically.

            for i, r_idx in enumerate(rows):
                ticket_grid[r_idx][c_idx] = numbers_from_range[i]
                
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
    pages = max(1, min(pages, 10)) # Capping at 10 pages is reasonable

    page_bg_color = hex_to_rgb(request.form.get("page_bg_color", "#6A92CD"))
    header_fill = hex_to_rgb(request.form.get("header_color", "#658950"))
    footer_fill = header_fill
    grid_color = hex_to_rgb(request.form.get("grid_color", "#8B4513"))
    ticket_bg_fill = header_fill
    font_color = hex_to_rgb(request.form.get("font_color", "#FFFFFF"))

    tickets = []
    total_tickets_needed = pages * 12
    
    # Generate all tickets. This will now be very fast.
    for _ in range(total_tickets_needed):
        tickets.append(generate_valid_ticket())

    pdf = FPDF('P', 'mm', 'A4')
    pdf.set_auto_page_break(False)

    W, H = 210, 297
    mx, my = 10, 10
    gx, gy = 4, 7
    cp = 2
    per = 12 # 12 tickets per A4 page
    rows_on_page = 6 # 6 tickets per column on the page layout
    aw = W - 2 * mx - (cp - 1) * gx
    tw = aw / cp # Ticket width
    hh = 6 # Header height
    fh = 5 # Footer height
    ch = 9 # Cell height
    cw = tw / 9 # Cell width
    gh = ch * 3 # Grid height
    th = hh + gh + fh # Total ticket height

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
            colp = 0 if i < rows_on_page else 1
            rowp = i % rows_on_page
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
            
            # Center text vertically in header
            header_text_height = pdf.font_size
            header_vertical_offset = (hh - header_text_height) / 2
            pdf.set_xy(x0, y0 + header_vertical_offset)
            pdf.cell(tw, hh - 2 * header_vertical_offset, header_text, border=0, align='C')

            # Grid
            pdf.set_font('helvetica', 'B', 16)
            pdf.set_text_color(*font_color)
            pdf.set_draw_color(0, 0, 0) # Black borders for cells

            for r_cell in range(3):
                for c_cell in range(9):
                    cx = x0 + c_cell * cw
                    cy = y0 + hh + r_cell * ch
                    
                    # Set fill color for grid background
                    pdf.set_fill_color(*grid_color)
                    pdf.rect(cx, cy, cw, ch, style='FD') # FD = Fill and Draw

                    num = data[r_cell][c_cell]
                    if num:
                        sw = pdf.get_string_width(str(num))
                        # Center number in cell
                        pdf.set_xy(cx + (cw - sw) / 2, cy + (ch - pdf.font_size) / 2 + 0.5)
                        pdf.cell(sw, pdf.font_size, str(num), border=0)

            # Footer
            footer_y_start = y0 + hh + gh
            pdf.set_fill_color(*footer_fill)
            pdf.rect(x0, footer_y_start, tw, fh, style='F')
            
            pdf.set_text_color(*font_color)
            pdf.set_font('helvetica', 'I', 9) # A smaller, italic font for the footer

            footer_text = host
            if phone:
                footer_text += f" • {phone}"
            if message:
                footer_text += f" • {message}"

            # Center text vertically in footer
            footer_text_height = pdf.font_size
            footer_vertical_offset = (fh - footer_text_height) / 2
            pdf.set_xy(x0, footer_y_start + footer_vertical_offset)
            pdf.cell(tw, fh - 2*footer_vertical_offset, footer_text, align='C')

    # Prepare the PDF for sending
    output_bytes = pdf.output(dest='S').encode('latin1')
    pdf_stream = BytesIO(output_bytes)
    pdf_stream.seek(0)
    return send_file(pdf_stream, download_name="tambola_tickets.pdf", as_attachment=True, mimetype='application/pdf')

if __name__ == '__main__':
    # Use debug=False when deploying to a service like Render
    app.run(debug=False, host='0.0.0.0', port=5000)
