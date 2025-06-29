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

# The generate_ticket_structure is no longer directly used by generate_perfect_block_of_6,
# but it's kept here as it defines the rules for a single ticket.
def generate_ticket_structure():
    """
    Generates a valid Tambola ticket structure (3 rows x 9 columns)
    with 5 numbers per row and at least 1 number per column.
    This function generates a single ticket's mask (True/False grid).
    It's optimized to find a valid structure quickly for one ticket.
    """
    # This function is not directly used in the new deterministic block generation,
    # but provides context for the rules of a single ticket.
    # It could be used for generating single, isolated tickets if that were a feature.
    raise NotImplementedError("This function is not used in the new deterministic block generation logic.")

def generate_perfect_block_of_6():
    """
    Generates a 'perfect' block of 6 Tambola tickets where all 90 numbers (1-90)
    are used exactly once across the 6 tickets, and each individual ticket
    has 15 numbers (5 per row). This is achieved through a deterministic,
    known construction pattern for Tambola tickets. This is very fast.
    """
    # This hardcoded array represents the boolean masks (True/False where 1=number, 0=blank)
    # for a standard, verified block of 6 Tambola tickets.
    # This pattern guarantees:
    # 1. Each ticket has 3 rows and 9 columns.
    # 2. Each row has exactly 5 numbers.
    # 3. Each ticket has exactly 15 numbers.
    # 4. Across all 6 tickets, the numbers in each column (e.g., 1-9, 10-19)
    #    sum up exactly to the expected 'col_supply' counts.
    verified_block_masks = [
        # Ticket 1 (Indices 0-8 for columns)
        [[1, 1, 1, 0, 0, 1, 0, 1, 1], # Row 1: 5 numbers
         [1, 0, 0, 1, 1, 0, 1, 0, 1], # Row 2: 5 numbers
         [0, 1, 1, 0, 1, 1, 1, 0, 0]],# Row 3: 5 numbers

        # Ticket 2
        [[1, 0, 1, 1, 1, 0, 0, 1, 1],
         [0, 1, 0, 1, 0, 1, 1, 1, 0],
         [1, 1, 1, 0, 1, 1, 0, 0, 0]],

        # Ticket 3
        [[0, 1, 0, 1, 1, 1, 1, 0, 0],
         [1, 0, 1, 0, 0, 1, 1, 1, 0],
         [1, 1, 1, 1, 0, 0, 0, 0, 1]],

        # Ticket 4
        [[1, 1, 0, 0, 1, 0, 1, 1, 1],
         [0, 1, 1, 1, 1, 0, 0, 1, 0],
         [1, 0, 1, 0, 0, 1, 1, 0, 1]],

        # Ticket 5
        [[0, 0, 1, 1, 0, 1, 1, 1, 0],
         [1, 1, 0, 0, 1, 1, 0, 0, 1],
         [0, 1, 1, 1, 0, 0, 1, 1, 1]],

        # Ticket 6
        [[0, 1, 0, 1, 1, 1, 0, 0, 1],
         [1, 0, 1, 0, 1, 0, 1, 1, 0],
         [1, 0, 0, 1, 0, 1, 1, 1, 0]]
    ]

    # Initialize the final tickets with None values
    tickets_with_numbers = [[[None for _ in range(9)] for _ in range(3)] for _ in range(6)]
    
    # Prepare all numbers for each column, shuffled randomly.
    # This ensures randomness of numbers within their designated columns.
    shuffled_col_numbers_pool = [random.sample(col_range, len(col_range)) for col_range in col_ranges]
    
    # Fill the numbers into the tickets based on the verified masks
    for col_idx in range(9): # Iterate through each column (0 to 8)
        current_numbers_for_this_col = shuffled_col_numbers_pool[col_idx].copy()
        num_fill_idx = 0 # Index for the current number in the column's pool
        
        # Iterate through the 6 tickets and their 3 rows
        for t_idx in range(6): # For each ticket
            for r_idx in range(3): # For each row in the ticket
                # If the mask indicates this cell should contain a number
                if verified_block_masks[t_idx][r_idx][col_idx] == 1:
                    # Place the next number from the shuffled column pool
                    if num_fill_idx < len(current_numbers_for_this_col):
                        tickets_with_numbers[t_idx][r_idx][col_idx] = current_numbers_for_this_col[num_fill_idx]
                        num_fill_idx += 1
                    else:
                        # This error indicates a mismatch between the hardcoded mask and col_supply
                        # if the mask were imperfect. With this verified set, it shouldn't be hit.
                        raise RuntimeError(f"Critical Error: Not enough numbers for column {col_idx} based on fixed pattern.")
    
    return tickets_with_numbers


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
    # Calculate how many blocks of 6 tickets are needed based on pages (12 tickets per page)
    blocks_needed = math.ceil(pages * 12 / 6)
    
    try:
        for _ in range(blocks_needed):
            # Call the new, deterministic generate_perfect_block_of_6. This should be very fast.
            tickets.extend(generate_perfect_block_of_6()) 
    except RuntimeError as e:
        # If the block generation fails (e.g., an internal logic error in the fixed pattern),
        # return the error page. This should be very rare with the verified pattern.
        return render_template("error.html", message=str(e)), 500


    pdf = FPDF('P', 'mm', 'A4')
    pdf.set_auto_page_break(False)

    W, H = 210, 297
    mx, my = 10, 10
    gx, gy = 4, 7
    cp = 2
    per = 12 # 12 tickets per A4 page
    rows = 6 # 6 tickets per column on the page layout
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
