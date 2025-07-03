from flask import Flask, render_template, request, send_file
from io import BytesIO
import random
import logging
from fpdf import FPDF

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def clean_text(text):
    return str(text).strip() if isinstance(text, str) else ""

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generate_perfect_block_of_6():
    """
    Generates a block of 6 valid Tambola tickets without recursion,
    ensuring each ticket has exactly 15 numbers (5 per row).
    """
    # 1. Prepare and shuffle the numbers for each column
    number_pool = [list(range(1, 10))] + [list(range(i, i + 10)) for i in range(10, 80, 10)] + [list(range(80, 91))]
    for col in number_pool:
        random.shuffle(col)

    # 2. Create ticket skeletons and perform initial random distribution
    tickets = [[[None for _ in range(9)] for _ in range(3)] for _ in range(6)]
    for c_idx, col_nums in enumerate(number_pool):
        positions = [(t, r) for t in range(6) for r in range(3)]
        selected = random.sample(positions, len(col_nums))
        for i, num in enumerate(col_nums):
            t, r = selected[i]
            tickets[t][r][c_idx] = num

    # 3. Balance all tickets until every row has exactly 5 numbers
    while True:
        row_counts = [[sum(1 for cell in row if cell) for row in t] for t in tickets]
        over_filled = [(t, r) for t in range(6) for r in range(3) if row_counts[t][r] > 5]
        under_filled = [(t, r) for t in range(6) for r in range(3) if row_counts[t][r] < 5]

        # If both lists are empty, balance is perfect. We are done.
        if not over_filled and not under_filled:
            break

        # A more stable and efficient way to find and perform a swap
        swap_made = False
        # Iterate through each over-filled row to find a number to move
        for from_t, from_r in over_filled:
            # Find a column in this row that actually has a number
            possible_cols = [c for c, cell in enumerate(tickets[from_t][from_r]) if cell is not None]
            random.shuffle(possible_cols)

            for c_idx in possible_cols:
                # Find an under-filled row that is empty in this specific column
                for to_t, to_r in under_filled:
                    if tickets[to_t][to_r][c_idx] is None:
                        # Found a valid swap, perform it
                        tickets[to_t][to_r][c_idx] = tickets[from_t][from_r][c_idx]
                        tickets[from_t][from_r][c_idx] = None
                        swap_made = True
                        break  # Exit inner 'under_filled' loop
                if swap_made:
                    break  # Exit 'possible_cols' loop
            if swap_made:
                break # Exit 'over_filled' loop to restart the while loop

    # 4. Sort the numbers within each column of each ticket
    for ticket in tickets:
        for c in range(9):
            col_values = [ticket[r][c] for r in range(3) if ticket[r][c]]
            col_values.sort()
            i = 0
            for r in range(3):
                if ticket[r][c]:
                    ticket[r][c] = col_values[i]
                    i += 1
    return tickets


@app.route('/')
def landing_page():
    return render_template("landing.html")

@app.route('/generator')
def ticket_generator_page():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate():
    try:
        host = clean_text(request.form.get('name', 'Host'))
        phone = clean_text(request.form.get('phone', ''))
        message = clean_text(request.form.get('custom_message', ''))
        hide_ticket_number = 'hide_ticket_number' in request.form

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
        for _ in range(pages * 2):
            all_tickets.extend(generate_perfect_block_of_6())

        pdf = FPDF('P', 'mm', 'A4')
        pdf.set_auto_page_break(False)
        pdf.set_font("helvetica", size=12)

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

        # --- Instructions Page ---
        pdf.add_page()
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(0, 0, W, H, 'F')
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", 'B', 22)
        pdf.set_xy(mx, my)
        pdf.cell(W - 2 * mx, 12, 'How to Play Tambola (Housie)', align='C')
        pdf.ln(18)
        pdf.set_font("helvetica", '', 14)
        instructions = [
            "Tambola (also called Housie) is a game of luck and numbers.", "",
            "Objective:", "Mark off numbers on your ticket to complete winning patterns.", "",
            "How to Play:", "1. A number will be called out (between 1 to 90).",
            "2. If it appears on your ticket, mark it.",
            "3. Be the first to complete and claim a winning pattern.", "",
            "Common Winning Patterns:", "- Early Five: First 5 numbers marked on a ticket.",
            "- Top Line: All 5 numbers in the top row.",
            "- Middle Line: All 5 numbers in the middle row.",
            "- Bottom Line: All 5 numbers in the bottom row.",
            "- Full House: All 15 numbers on your ticket.", "",
            "Note: Call out your win immediately. Late claims are invalid!"
        ]
        for line in instructions:
            pdf.set_x(mx)
            pdf.multi_cell(W - 2 * mx, 8, line)

        # --- Ticket Pages ---
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
                pdf.rect(x0, y0, tw, th, 'F')

                # Header
                pdf.set_fill_color(*header_fill)
                pdf.rect(x0, y0, tw, hh, 'F')
                pdf.set_text_color(*font_color)
                pdf.set_font("helvetica", 'B', 10)
                header_text = host
                if not hide_ticket_number:
                    header_text += f" | Ticket {idx + 1}"
                while pdf.get_string_width(header_text) > (tw - 4) and len(header_text) > 0:
                    header_text = header_text[:-1]
                pdf.set_xy(x0, y0)
                pdf.cell(tw, hh, header_text, 0, align='C')

                # Grid
                pdf.set_font("helvetica", 'B', 16)
                for r in range(3):
                    for c in range(9):
                        cx, cy = x0 + c * cw, y0 + hh + r * ch
                        pdf.set_fill_color(*grid_color)
                        pdf.rect(cx, cy, cw, ch, 'FD')
                        num = data[r][c]
                        if num:
                            txt = str(num)
                            sw = pdf.get_string_width(txt)
                            pdf.set_text_color(*font_color)
                            pdf.set_xy(cx + (cw - sw) / 2.8, cy + (ch - pdf.font_size) / 1.8 + 1)
                            pdf.cell(sw, pdf.font_size, txt, 0)

                # Footer
                pdf.set_font("helvetica", 'B', 10)
                pdf.set_text_color(*font_color)
                footer_parts = []
                if phone: footer_parts.append(phone)
                if message: footer_parts.append(message)
                footer_text = " | ".join(footer_parts)
                while pdf.get_string_width(footer_text) > (tw - 4) and len(footer_text) > 0:
                    footer_text = footer_text[:-1]
                footer_y = y0 + hh + gh
                pdf.set_fill_color(*footer_fill)
                pdf.rect(x0, footer_y, tw, fh, 'F')
                pdf.set_xy(x0, footer_y)
                pdf.cell(tw, fh, footer_text, 0, align='C')

        # Use fpdf2's recommended byte output
        pdf_bytes = pdf.output()
        return send_file(BytesIO(pdf_bytes), download_name="tixgen.pdf", as_attachment=True, mimetype='application/pdf')

    except Exception as e:
        logging.exception("Error during PDF generation:")
        return f"<h1>Internal Server Error</h1><p>An error occurred: {e}</p>", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
