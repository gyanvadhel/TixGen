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
    with 5 numbers per row and numbers filled according to rules.
    This uses a deterministic mask construction for speed and reliability,
    and then fills numbers randomly from their respective ranges.
    """
    # Initialize 3x9 ticket grid with None values
    current_ticket = [[None for _ in range(9)] for _ in range(3)]

    # A single, pre-verified valid mask pattern for one Tambola ticket.
    # This mask ensures 15 numbers total (5 per row, and 1 or 2 per column).
    # This is a standard valid pattern.
    ticket_mask = [
        [1, 0, 1, 1, 0, 1, 0, 1, 0], # Row 1: 5 numbers
        [0, 1, 0, 1, 1, 0, 1, 0, 1], # Row 2: 5 numbers
        [1, 0, 1, 0, 0, 1, 1, 1, 0]  # Row 3: 5 numbers
    ]

    # Fill numbers into the ticket based on the fixed ticket_mask
    for c_idx in range(9): # For each column (0 to 8)
        numbers_for_this_col_range = col_ranges[c_idx].copy()
        random.shuffle(numbers_for_this_col_range) # Shuffle numbers within their range

        slots_in_this_col_for_ticket = []
        for r_idx in range(3):
            if ticket_mask[r_idx][c_idx] == 1:
                slots_in_this_col_for_ticket.append(r_idx)
        
        # Take exactly as many numbers as there are slots in this column for this ticket
        # The slice will safely handle cases where numbers_for_this_col_range might be shorter
        # (though for Tambola, col_ranges are always large enough for 1 or 2 slots).
        numbers_to_assign_to_slots = numbers_for_this_col_range[:len(slots_in_this_col_for_ticket)]
        
        assigned_count = 0
        for r_idx in slots_in_this_col_for_ticket: # Iterate only over rows with slots
            # This check ensures we don't try to assign more numbers than we have
            if assigned_count < len(numbers_to_assign_to_slots): 
                current_ticket[r_idx][c_idx] = numbers_to_assign_to_slots[assigned_count]
                assigned_count += 1
            else:
                # This error indicates a problem with the fixed mask or col_ranges setup
                # if it were to occur (shouldn't with standard Tambola masks and rules).
                raise RuntimeError(f"Logic error in number assignment for column {c_idx}. Too many slots for available numbers.")
    
    # Final check: ensure the ticket has exactly 15 numbers (total from the mask)
    total_numbers_in_ticket = sum(1 for row in current_ticket for cell in row if cell is not None)
    if total_numbers_in_ticket != 15:
        raise RuntimeError("Generated ticket does not have exactly 15 numbers. Mask is likely incorrect.")

    return current_ticket


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
