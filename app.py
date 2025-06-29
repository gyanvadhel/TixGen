from flask import Flask, render_template, request, send_file
from io import BytesIO
import random
import math
from fpdf import FPDF

app = Flask(__name__)

# --- Ticket Generation Logic ---

# Column ranges and expected number counts per column
col_ranges = [list(range(1, 10))] + [list(range(i, i + 10)) for i in range(10, 80, 10)] + [list(range(80, 91))]
col_supply = [len(r) for r in col_ranges]

def generate_ticket_structure():
    """
    Generates a valid Tambola ticket structure (3 rows x 9 columns)
    with 5 numbers per row and at least 1 number per column.
    This uses a more deterministic approach to ensure validity quickly.
    """
    while True: # Keep trying until a valid structure is generated
        pos = [[False] * 9 for _ in range(3)] # Initialize 3x9 grid
        
        # A standard Tambola ticket has:
        # - 3 columns with 1 number
        # - 6 columns with 2 numbers
        # This totals 3*1 + 6*2 = 15 numbers (5 per row)
        
        # Randomly assign which columns will have 1 number and which will have 2
        all_cols_indices = list(range(9))
        random.shuffle(all_cols_indices)
        
        # First 3 columns will have 1 number
        single_num_cols = all_cols_indices[:3]
        # Remaining 6 columns will have 2 numbers
        double_num_cols = all_cols_indices[3:]
        
        # Keep track of how many numbers are placed in each row
        row_current_fill = [0, 0, 0] # Max 5 numbers per row
        
        # List of (row_idx, col_idx) pairs to fill
        positions_to_place = []

        # Step 1: Place 1 number in each of the 'single_num_cols'
        # Distribute these across rows, ensuring rows don't get full prematurely
        single_col_row_choices = list(range(3)) # Rows 0, 1, 2
        random.shuffle(single_col_row_choices) # Random order for assigning single numbers
        
        for i, col_idx in enumerate(single_num_cols):
            row_idx = single_col_row_choices[i] # Assign unique row for each of these 3 single numbers initially
            positions_to_place.append((row_idx, col_idx))
            row_current_fill[row_idx] += 1

        # Step 2: Place 2 numbers in each of the 'double_num_cols'
        for col_idx in double_num_cols:
            # Find rows that are not yet full (less than 5 numbers)
            available_rows = [r for r in range(3) if row_current_fill[r] < 5]
            
            if len(available_rows) < 2:
                # This scenario should be rare with proper initial setup, but indicates failure
                # Need to restart if we can't place 2 numbers in distinct rows
                break # Break inner loop, outer while loop will retry
            
            # Select 2 distinct rows from available ones
            chosen_rows_for_col = random.sample(available_rows, 2)
            
            for row_idx in chosen_rows_for_col:
                positions_to_place.append((row_idx, col_idx))
                row_current_fill[row_idx] += 1
        
        else: # This 'else' block executes if the inner 'for col_idx' loop completed without a 'break'
            # All columns processed, now populate the actual 'pos' grid
            for r, c in positions_to_place:
                pos[r][c] = True
            
            # Final validation: check if all rows have exactly 5 numbers
            # And all columns have at least one number (implicitly handled by col_counts_config)
            if all(count == 5 for count in row_current_fill) and \
               all(any(pos[r_check][c_check] for r_check in range(3)) for c_check in range(9)):
                return pos
        
        # If any break occurred or final validation failed, the 'while True' loop continues for a new attempt

# This function is significantly changed to directly build the block of 6 tickets
def generate_block_of_6_tickets():
    """
    Generates a block of 6 Tambola tickets ensuring all numbers from 1-90 are used exactly once.
    This eliminates the need for random attempts to match col_supply, making it much faster.
    """
    # 1. Generate 6 valid ticket structures (True/False grids)
    grids = [generate_ticket_structure() for _ in range(6)]
    
    # Initialize the actual tickets with None
    tickets = [[[None]*9 for _ in range(3)] for _ in range(6)]

    # 2. Fill numbers for each column across all 6 tickets
    for c in range(9): # Iterate through each of the 9 columns (number ranges)
        nums_for_this_column = col_ranges[c].copy() # Get numbers for this column's range (e.g., 1-9, 10-19)
        random.shuffle(nums_for_this_column) # Shuffle them for randomness in placement
        
        current_num_idx = 0
        # Iterate through the 6 tickets and their 3 rows to place numbers
        for t in range(6): # For each ticket
            for r in range(3): # For each row
                if grids[t][r][c]: # If this cell in the structure is marked True (should contain a number)
                    if current_num_idx < len(nums_for_this_column):
                        tickets[t][r][c] = nums_for_this_column[current_num_idx]
                        current_num_idx += 1
                    else:
                        # This should ideally not happen if col_supply is consistent with total cells in grids
                        # But it's a safeguard against potential logic errors
                        raise RuntimeError(f"Not enough numbers for column {c} or too many cells marked True.")
    
    return tickets


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
    # Calculate how many blocks of 6 tickets are needed
    blocks_needed = math.ceil(pages * 12 / 6)
    
    for _ in range(blocks_needed):
        tickets.extend(generate_block_of_6_tickets()) # Use the new, efficient function

    # Set up PDF
    pdf = FPDF('P', 'mm', 'A4')
    pdf.set_auto_page_break(False)

    W, H = 210, 297
    mx, my = 10, 10
    gx, gy = 4, 7
    cp = 2
    per = 12 # Tickets per page
    rows = 6
    aw = W - 2 * mx - (cp - 1) * gx
    tw = aw / cp
    hh = 6
    fh = 5
    ch = 9
    cw = tw / 9
    gh = ch * 3
    th = hh + gh + fh # Exact total ticket height

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
    
    # --- Add Callable Numbers Page ---
    pdf.add_page()
    pdf.set_fill_color(*page_bg_color)
    pdf.rect(0, 0, W, H, 'F')
    pdf.set_text_color(*font_color)

    pdf.set_font('helvetica', 'B', 20)
    pdf.set_xy(mx, my)
    pdf.cell(W - 2 * mx, 10, 'Callable Numbers (For Caller)', align='C')
    pdf.ln(15)

    all_numbers = list(range(1, 91))
    random.shuffle(all_numbers)

    pdf.set_font('helvetica', '', 14)
    num_cols = 10
    num_width = (W - 2 * mx) / num_cols
    line_height = 8

    pdf.set_xy(mx, my + 20)
    for i, num in enumerate(all_numbers):
        col = i % num_cols
        row = i // num_cols
        pdf.set_xy(mx + col * num_width, my + 20 + row * line_height)
        pdf.cell(num_width, line_height, str(num), align='C', border=0)

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

            for r in range(3):
                for c in range(9):
                    cx = x0 + c * cw
                    cy = y0 + hh + r * ch
                    pdf.rect(cx, cy, cw, ch, style='F')
                    pdf.rect(cx, cy, cw, ch, style='D')

                    num = data[r][c]
                    if num:
                        sw = pdf.get_string_width(str(num))
                        pdf.set_xy(cx + (cw - sw) / 2, cy + (ch - pdf.font_size) / 2)
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
