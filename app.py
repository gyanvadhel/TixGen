from flask import Flask, render_template, request, send_file
from io import BytesIO
import random
import math
from fpdf import FPDF

app = Flask(__name__)

# --- Correct, Block-Based Ticket Generation Logic ---

def generate_perfect_block_of_6():
    """
    Generates a "perfect block" of 6 Tambola tickets where every number
    from 1 to 90 is used exactly once, and all ticket rules are followed.
    This is the standard method for creating non-repeating ticket books.
    """
    
    # 1. Prepare all 90 numbers, grouped by their columns.
    number_pool = [
        list(range(1, 10)),   # Col 0: 9 numbers
        list(range(10, 20)),  # Col 1: 10 numbers
        list(range(20, 30)),  # Col 2: 10 numbers
        list(range(30, 40)),  # Col 3: 10 numbers
        list(range(40, 50)),  # Col 4: 10 numbers
        list(range(50, 60)),  # Col 5: 10 numbers
        list(range(60, 70)),  # Col 6: 10 numbers
        list(range(70, 80)),  # Col 7: 10 numbers
        list(range(80, 91))   # Col 8: 11 numbers
    ]

    # Shuffle numbers within each column's pool.
    for col_nums in number_pool:
        random.shuffle(col_nums)

    # 2. Create 6 empty tickets (3 rows x 9 cols each).
    tickets = [[[None for _ in range(9)] for _ in range(3)] for _ in range(6)]

    # 3. Distribute the numbers into the columns of the 6 tickets.
    # There are 18 total rows available for each column across the 6 tickets.
    for c_idx, col_nums_to_place in enumerate(number_pool):
        # Get all 18 possible positions (ticket_idx, row_idx) in the current column.
        all_positions_in_col = [(t_idx, r_idx) for t_idx in range(6) for r_idx in range(3)]
        
        # Randomly choose positions for the numbers in this column.
        chosen_positions = random.sample(all_positions_in_col, len(col_nums_to_place))

        # Place the numbers.
        for i, num in enumerate(col_nums_to_place):
            ticket_idx, row_idx = chosen_positions[i]
            tickets[ticket_idx][row_idx][c_idx] = num

    # 4. Balance the tickets: Ensure each row has exactly 5 numbers.
    # This is the most critical step. We swap numbers *within the same column*
    # between over-filled and under-filled rows until every row is balanced.
    while True:
        row_counts = [[sum(1 for cell in row if cell is not None) for row in t] for t in tickets]
        
        over_filled_rows = []
        under_filled_rows = []
        
        # Identify which rows need balancing.
        for t_idx in range(6):
            for r_idx in range(3):
                if row_counts[t_idx][r_idx] > 5:
                    over_filled_rows.append((t_idx, r_idx))
                elif row_counts[t_idx][r_idx] < 5:
                    under_filled_rows.append((t_idx, r_idx))

        # If all rows have exactly 5 numbers, we are done!
        if not over_filled_rows and not under_filled_rows:
            break

        # Pick one over-filled and one under-filled row to try and swap between.
        from_ticket, from_row = random.choice(over_filled_rows)
        to_ticket, to_row = random.choice(under_filled_rows)

        # Find a column where the 'from' row has a number and the 'to' row is empty.
        # This makes for a valid swap.
        possible_swap_cols = []
        for c_idx in range(9):
            if tickets[from_ticket][from_row][c_idx] is not None and tickets[to_ticket][to_row][c_idx] is None:
                possible_swap_cols.append(c_idx)
        
        if possible_swap_cols:
            # Perform the swap.
            swap_col = random.choice(possible_swap_cols)
            tickets[to_ticket][to_row][swap_col] = tickets[from_ticket][from_row][swap_col]
            tickets[from_ticket][from_row][swap_col] = None

    # 5. Final step: Sort the numbers within each column of each ticket.
    for ticket in tickets:
        for c_idx in range(9):
            col_vals = [ticket[r][c_idx] for r in range(3) if ticket[r][c_idx] is not None]
            col_vals.sort()
            
            val_idx = 0
            for r_idx in range(3):
                if ticket[r_idx][c_idx] is not None:
                    ticket[r_idx][c_idx] = col_vals[val_idx]
                    val_idx += 1
    
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

    # Sanitize text to handle special characters (this is still good practice)
    safe_host = host.encode('latin-1', 'replace').decode('latin-1')
    safe_phone = phone.encode('latin-1', 'replace').decode('latin-1')
    safe_message = message.encode('latin-1', 'replace').decode('latin-1')

    try:
        pages = int(request.form.get('pages', 1))
    except ValueError:
        pages = 1
    pages = max(1, min(pages, 10))

    page_bg_color = hex_to_rgb(request.form.get("page_bg_color", "#6A92CD"))
    header_fill = hex_to_rgb(request.form.get("header_color", "#658950"))
    grid_color = hex_to_rgb(request.form.get("grid_color", "#8B4513"))
    font_color = hex_to_rgb(request.form.get("font_color", "#FFFFFF"))
    footer_fill = header_fill
    ticket_bg_fill = header_fill

    all_tickets = []
    num_blocks_needed = pages * 2
    for _ in range(num_blocks_needed):
        all_tickets.extend(generate_perfect_block_of_6())

    pdf = FPDF('P', 'mm', 'A4')
    pdf.set_auto_page_break(False)

    W, H = 210, 297
    mx, my = 10, 10
    gx, gy = 4, 7
    cp = 2
    per_page = 12
    rows_on_page = 6
    aw = W - 2 * mx - (cp - 1) * gx
    tw = aw / cp
    hh = 6
    fh = 5
    ch = 9
    cw = tw / 9
    gh = ch * 3
    th = hh + gh + fh

    # --- Add Instructions Page ---
    # This part is unchanged and fine
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
        "", "Objective: To be the first to mark off numbers on your ticket in specific patterns.",
        "", "Gameplay:", "1.  As the Caller announces a number, if it's on your ticket, mark it off.",
        "2.  Announce your claim for a winning pattern immediately after marking the last number for that pattern.",
        "", "Common Patterns:", "- Early Five: First 5 numbers marked on a ticket.",
        "- Top Line, Middle Line, Bottom Line", "- Full House: All 15 numbers marked on your ticket."
    ]
    for line in rules_text:
        pdf.set_x(mx)
        pdf.multi_cell(W - 2 * mx, 6, line)

    # --- Add Tickets Pages ---
    for p in range(pages):
        pdf.add_page()
        pdf.set_fill_color(*page_bg_color)
        pdf.rect(0, 0, W, H, 'F')

        for i in range(per_page):
            idx = p * per_page + i
            if idx >= len(all_tickets): break
            
            data = all_tickets[idx]
            colp = 0 if i < rows_on_page else 1
            rowp = i % rows_on_page
            x0 = mx + colp * (tw + gx)
            y0 = my + rowp * (th + gy)

            pdf.set_fill_color(*ticket_bg_fill)
            pdf.rect(x0, y0, tw, th, style='F')

            # --- HEADER SECTION WITH FIX ---
            pdf.set_fill_color(*header_fill)
            pdf.rect(x0, y0, tw, hh, style='F')
            pdf.set_text_color(*font_color)
            pdf.set_font('helvetica', 'B', 10)
            
            header_text = safe_host
            if not hide_ticket_number:
                header_text += f" | Ticket {idx + 1}"

            # NEW: Truncate header text if it's too wide for the ticket
            padding = 4  # Give 4mm of padding
            while pdf.get_string_width(header_text) > (tw - padding):
                header_text = header_text[:-1]

            pdf.set_xy(x0, y0)
            pdf.cell(tw, hh, header_text, border=0, align='C')

            # --- GRID SECTION (Unchanged) ---
            pdf.set_font('helvetica', 'B', 16)
            pdf.set_draw_color(0, 0, 0)
            for r_cell in range(3):
                for c_cell in range(9):
                    cx, cy = x0 + c_cell * cw, y0 + hh + r_cell * ch
                    pdf.set_fill_color(*grid_color)
                    pdf.rect(cx, cy, cw, ch, style='FD')
                    num = data[r_cell][c_cell]
                    if num:
                        pdf.set_text_color(*font_color)
                        sw = pdf.get_string_width(str(num))
                        pdf.set_xy(cx + (cw - sw) / 2, cy + (ch - pdf.font_size) / 2 + 1)
                        pdf.cell(sw, pdf.font_size, str(num), border=0)

            # --- FOOTER SECTION WITH FIX ---
            footer_y_start = y0 + hh + gh
            pdf.set_fill_color(*footer_fill)
            pdf.rect(x0, footer_y_start, tw, fh, style='F')
            pdf.set_text_color(*font_color)
            pdf.set_font('helvetica', 'I', 9)

            footer_text = safe_host
            if safe_phone: footer_text += f" • {safe_phone}"
            if safe_message: footer_text += f" • {safe_message}"

            # NEW: Truncate footer text if it's too wide for the ticket
            while pdf.get_string_width(footer_text) > (tw - padding):
                footer_text = footer_text[:-1]

            pdf.set_xy(x0, footer_y_start)
            pdf.cell(tw, fh, footer_text, align='C')

    output_bytes = pdf.output(dest='S').encode('latin1')
    pdf_stream = BytesIO(output_bytes)
    pdf_stream.seek(0)
    return send_file(pdf_stream, download_name="tixgen.pdf", as_attachment=True, mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
