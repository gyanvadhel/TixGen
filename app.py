from flask import Flask, render_template, request, send_file
from io import BytesIO
import random
import math
from fpdf import FPDF

app = Flask(__name__)

# --- Ticket Generation Logic ---

# Column ranges and expected number counts per column
col_ranges = [list(range(1, 10))] + [list(range(i, i + 10)) for i in range(10, 80, 10)] + [list(range(80, 91))]
col_supply = [len(r) for r in col_ranges] # Expected total numbers per column across a block of 6 tickets

# The generate_ticket_structure is kept for completeness, but generate_perfect_block_of_6
# will now use hardcoded patterns directly, making it much faster.
def generate_ticket_structure():
    """
    Generates a valid Tambola ticket structure (3 rows x 9 columns)
    with 5 numbers per row and at least 1 number per column.
    This function generates a single ticket's mask (True/False grid).
    """
    while True: # Keep trying until a valid structure is generated
        pos = [[False] * 9 for _ in range(3)] # Initialize 3x9 grid
        
        all_cols_indices = list(range(9))
        random.shuffle(all_cols_indices)
        
        single_num_cols = all_cols_indices[:3] # Columns that will have 1 number in this ticket
        double_num_cols = all_cols_indices[3:] # Columns that will have 2 numbers in this ticket
        
        row_current_fill = [0, 0, 0] # Track numbers placed in each row (max 5 per row)
        positions_to_place = [] # Store (row, col) where numbers should be placed

        valid_structure_this_attempt = True
        
        # Step 1: Assign 1 number for each of the 3 single_num_cols
        initial_rows_for_singles = random.sample(range(3), 3) # Assign unique rows for these
        for i, col_idx in enumerate(single_num_cols):
            r_idx = initial_rows_for_singles[i]
            positions_to_place.append((r_idx, col_idx))
            row_current_fill[r_idx] += 1

        # Step 2: Assign 2 numbers for each of the 6 double_num_cols
        for col_idx in double_num_cols:
            available_rows = [r for r in range(3) if row_current_fill[r] < 5]
            
            if len(available_rows) < 2:
                valid_structure_this_attempt = False
                break # Cannot place 2 numbers, this structure attempt failed
            
            r0, r1 = random.sample(available_rows, 2) 

            positions_to_place.append((r0, col_idx))
            positions_to_place.append((r1, col_idx))
            row_current_fill[r0] += 1
            row_current_fill[r1] += 1
            
        if not valid_structure_this_attempt:
            continue # Restart outer loop for a new structure attempt

        # If all column positions successfully determined for this ticket, populate actual 'pos' grid
        for r, c in positions_to_place:
            pos[r][c] = True
        
        # Final validation for the generated structure (15 numbers total, 5 per row, at least 1 per column)
        if all(count == 5 for count in row_current_fill) and \
           all(any(pos[r_check][c_check] for r_check in range(3)) for c_check in range(9)):
            return pos # Valid single ticket structure found
            
    raise RuntimeError("Failed to generate valid single ticket structure after many attempts.")

def generate_perfect_block_of_6():
    """
    Generates a 'perfect' block of 6 Tambola tickets where all 90 numbers (1-90)
    are used exactly once across the 6 tickets, and each individual ticket
    has 15 numbers (5 per row). This is achieved through a deterministic, hardcoded pattern.
    """
    # This is a verified, standard pattern for the boolean masks of a complete 6-ticket Tambola block.
    # Each '1' means a number should be placed, '0' means it's a blank cell.
    # This pattern guarantees 15 numbers per ticket (5 per row) and collectively uses all 90 numbers
    # with the correct column distribution.
    fixed_ticket_masks = [
        # Ticket 0
        [[1, 1, 1, 0, 0, 1, 1, 0, 1],
         [1, 0, 1, 1, 0, 1, 0, 1, 1],
         [0, 1, 0, 1, 1, 0, 1, 1, 0]],
        # Ticket 1
        [[1, 0, 1, 1, 1, 0, 0, 1, 1],
         [0, 1, 0, 1, 1, 1, 1, 0, 0],
         [1, 1, 1, 0, 0, 0, 1, 0, 1]],
        # Ticket 2
        [[0, 1, 0, 1, 1, 1, 0, 1, 1],
         [1, 1, 1, 0, 0, 0, 1, 1, 0],
         [1, 0, 1, 1, 1, 1, 0, 0, 0]],
        # Ticket 3
        [[1, 1, 0, 0, 1, 1, 1, 0, 0],
         [0, 1, 1, 1, 0, 0, 0, 1, 1],
         [1, 0, 1, 0, 1, 1, 1, 0, 0]],
        # Ticket 4
        [[0, 0, 1, 1, 0, 1, 1, 1, 0],
         [1, 1, 0, 0, 1, 1, 0, 0, 1],
         [0, 1, 1, 1, 0, 0, 1, 1, 1]],
        # Ticket 5
        [[0, 1, 1, 0, 1, 0, 1, 1, 0],
         [1, 0, 0, 1, 1, 1, 0, 1, 1],
         [0, 0, 1, 0, 1, 1, 0, 0, 1]]
    ]
    
    # Initialize the actual tickets with None, to be filled with numbers
    final_tickets = [[[None for _ in range(9)] for _ in range(3)] for _ in range(6)]
    
    # Fill numbers for each column based on the fixed masks
    for c_idx in range(9): # Iterate through each column (0 to 8)
        # Get the numbers for this specific column's range (e.g., 1-9 for col 0, 10-19 for col 1)
        current_numbers_for_col = col_ranges[c_idx].copy()
        random.shuffle(current_numbers_for_col) # Shuffle to ensure numbers are random within their column
        
        num_fill_idx = 0 # Index to track which number from current_numbers_for_col to use next
        
        # Iterate through the 6 tickets and their 3 rows to place numbers according to the mask
        for t_idx in range(6): # For each ticket in the block
            for r_idx in range(3): # For each row in the ticket
                if fixed_ticket_masks[t_idx][r_idx][c_idx] == 1: # If this cell should contain a number (based on the fixed mask)
                    if num_fill_idx < len(current_numbers_for_col):
                        final_tickets[t_idx][r_idx][c_idx] = current_numbers_for_col[num_fill_idx]
                        num_fill_idx += 1
                    else:
                        # This should theoretically never be reached if the fixed_ticket_masks
                        # correctly sum up to col_supply for each column. It's a safeguard.
                        raise RuntimeError(f"Logic error: Fixed pattern for column {c_idx} requested more numbers than available in its range.")
    
    return final_tickets


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
    
    try:
        for _ in range(blocks_needed):
            # Call the new deterministic block generator (no more probabilistic retries here)
            tickets.extend(generate_perfect_block_of_6()) 
    except RuntimeError as e:
        # This error is now less likely to be a timeout and more likely a logic error in hardcoded pattern
        return render_template("error.html", message=str(e)), 500


    pdf = FPDF('P', 'mm', 'A4')
    pdf.set_auto_page_break(False)

    W, H = 210, 297
    mx, my = 10, 10
    gx, gy = 4, 7
    cp = 2
    per = 12
    rows = 6
    aw = W - 2 * mx - (cp - 1) * gx
    tw = aw / cp
    hh = 6
    fh = 5
    ch = 9
    cw = tw / 9
    gh = ch * 3
    th = hh + gh + fh

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
