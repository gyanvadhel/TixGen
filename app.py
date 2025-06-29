from flask import Flask, render_template, request, send_file
from io import BytesIO
import random
import math
from fpdf import FPDF

app = Flask(__name__)

# --- Ticket Generation Logic ---

# Column ranges for numbers (e.g., 1-9, 10-19, etc.)
# col_supply is no longer directly used to validate block sums, only for number ranges
col_ranges = [list(range(1, 10))] + [list(range(i, i + 10)) for i in range(10, 80, 10)] + [list(range(80, 91))]

def generate_ticket_structure_and_numbers():
    """
    Generates a single, valid Tambola ticket (3 rows x 9 columns)
    with 5 numbers per row and at least 1 number per column.
    This function also fills the numbers directly into the ticket,
    without needing a 'perfect block' check against col_supply globally.
    """
    # Max attempts for generating a single valid ticket structure. This should be very fast.
    for _ in range(5000): 
        ticket = [[[None] * 9 for _ in range(3)] for _ in range(3)] # Initialize 3x9 ticket grid
        
        # --- Step 1: Create the True/False mask for this single ticket ---
        pos_mask = [[False] * 9 for _ in range(3)] 
        
        all_cols_indices = list(range(9))
        random.shuffle(all_cols_indices)
        
        single_num_cols = all_cols_indices[:3] # Columns that will have 1 number in this ticket
        double_num_cols = all_cols_indices[3:] # Columns that will have 2 numbers in this ticket
        
        row_current_fill = [0, 0, 0] # Track numbers placed in each row (max 5 per row)
        positions_to_place_in_mask = [] # Store (row, col) where numbers should be placed in mask

        valid_structure_this_attempt = True
        
        # Assign 1 number for each of the 3 single_num_cols
        initial_rows_for_singles = random.sample(range(3), 3) 
        for i, col_idx in enumerate(single_num_cols):
            r_idx = initial_rows_for_singles[i]
            positions_to_place_in_mask.append((r_idx, col_idx))
            row_current_fill[r_idx] += 1

        # Assign 2 numbers for each of the 6 double_num_cols
        for col_idx in double_num_cols:
            available_rows = [r for r in range(3) if row_current_fill[r] < 5]
            
            if len(available_rows) < 2:
                valid_structure_this_attempt = False
                break # Cannot place 2 numbers, this structure attempt failed
            
            r0, r1 = random.sample(available_rows, 2) 

            positions_to_place_in_mask.append((r0, col_idx))
            positions_to_place_in_mask.append((r1, col_idx))
            row_current_fill[r0] += 1
            row_current_fill[r1] += 1
            
        if not valid_structure_this_attempt:
            continue # Restart outer loop for a new mask structure attempt

        # If mask structure is valid, populate actual 'pos_mask' grid
        for r, c in positions_to_place_in_mask:
            pos_mask[r][c] = True
        
        # Final validation for the generated mask structure: 15 numbers total, 5 per row, at least 1 per column
        if not all(count == 5 for count in row_current_fill) or \
           not all(any(pos_mask[r_check][c_check] for r_check in range(3)) for c_check in range(9)):
            continue # Mask invalid, restart attempt
        
        # --- Step 2: Fill numbers into the validated mask for this ticket ---
        for c_idx in range(9): # For each column
            # Collect slots for numbers in this column for this ticket
            slots_in_this_col = []
            for r_idx in range(3):
                if pos_mask[r_idx][c_idx]:
                    slots_in_this_col.append(r_idx)
            
            if slots_in_this_col: # If this column has slots
                numbers_for_this_col_range = col_ranges[c_idx].copy()
                random.shuffle(numbers_for_this_col_range) # Shuffle numbers within their range

                # Take as many numbers as there are slots in this column for this ticket
                numbers_to_assign = numbers_for_this_col_range[:len(slots_in_this_col)]
                
                # Assign numbers to the slots
                for i, r_idx in enumerate(slots_in_this_col):
                    ticket[r_idx][c_idx] = numbers_to_assign[i]
        
        return ticket # Return the fully generated ticket with numbers
            
    # This theoretical error means the single ticket generation itself failed many times, highly unlikely
    raise RuntimeError("Failed to generate a valid individual ticket after many attempts.")


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
    # Generate 12 tickets for each requested page
    total_tickets_needed = pages * 12
    
    try:
        for _ in range(total_tickets_needed):
            # Call the function that generates a single, valid ticket with numbers
            tickets.append(generate_ticket_structure_and_numbers()) 
    except RuntimeError as e:
        # If any single ticket generation fails, return an error page
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
    

    # --- Add Tickets Pages ---
    # Loop through tickets, placing 12 tickets per page
    for p in range(math.ceil(len(tickets) / per)):
        pdf.add_page()
        pdf.set_fill_color(*page_bg_color)
        pdf.rect(0, 0, W, H, 'F')

        for i in range(per): # Iterate for 12 tickets per page
            idx = p * per + i # Global ticket index
            if idx >= len(tickets):
                break # Stop if we've placed all generated tickets

            data = tickets[idx] # Get the ticket data (numbers grid)
            
            # Determine position on the A4 page (2 columns, 6 rows of tickets)
            colp = 0 if i < rows else 1 # Column on page (left/right)
            rowp = i % rows # Row on page (0 to 5)

            x0 = mx + colp * (tw + gx) # X start for current ticket
            y0 = my + rowp * (th + gy) # Y start for current ticket

            # Draw the overall ticket background
            pdf.set_fill_color(*ticket_bg_fill)
            pdf.rect(x0, y0, tw, th, style='F')

            # Header
            pdf.set_fill_color(*header_fill)
            pdf.rect(x0, y0, tw, hh, style='F')
            pdf.set_text_color(*font_color)
            pdf.set_font('helvetica', 'B', 10)
            
            header_text = host
            if not hide_ticket_number:
                header_text += f" | Ticket {idx + 1}" # Display actual ticket number
            
            header_text_height = pdf.font_size
            header_vertical_offset = (hh - header_text_height) / 2
            
            pdf.set_xy(x0, y0 + header_vertical_offset) 
            pdf.cell(tw, hh - 2 * header_vertical_offset, header_text, border=0, align='C')

            # Grid (cells with their background and black borders)
            pdf.set_font('helvetica', 'B', 16)
            pdf.set_text_color(*font_color)
            pdf.set_fill_color(*grid_color)
            pdf.set_draw_color(0, 0, 0)

            for r_cell in range(3): # Iterate through 3 rows of the ticket grid
                for c_cell in range(9): # Iterate through 9 columns of the ticket grid
                    cx = x0 + c_cell * cw
                    cy = y0 + hh + r_cell * ch
                    pdf.rect(cx, cy, cw, ch, style='F') # Fill cell background with grid_color
                    pdf.rect(cx, cy, cw, ch, style='D') # Draw cell border

                    num = data[r_cell][c_cell] # Get the number for this cell
                    if num: # If there's a number to display
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

    # Output the PDF as a downloadable file
    output_bytes = pdf.output(dest='S').encode('latin1') if isinstance(pdf.output(dest='S'), str) else pdf.output(dest='S')
    pdf_stream = BytesIO(output_bytes)
    pdf_stream.seek(0)
    return send_file(pdf_stream, download_name="tickets.pdf", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=False)
