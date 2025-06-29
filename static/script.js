from flask import Flask, render_template, request, send_file
from io import BytesIO
import random
import logging
from fpdf import FPDF  # fpdf2

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def clean_text(text):
    return str(text).strip() if isinstance(text, str) else ""

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generate_perfect_block_of_6():
    number_pool = [list(range(1 + i * 10, 10 + i * 10)) for i in range(8)]
    number_pool.append(list(range(80, 91)))
    number_pool[0] = list(range(1, 10))

    for col in number_pool:
        random.shuffle(col)

    tickets = [[[None for _ in range(9)] for _ in range(3)] for _ in range(6)]

    for c_idx, col_nums in enumerate(number_pool):
        positions = [(t, r) for t in range(6) for r in range(3)]
        selected = random.sample(positions, len(col_nums))
        for i, num in enumerate(col_nums):
            t, r = selected[i]
            tickets[t][r][c_idx] = num

    while True:
        row_counts = [[sum(1 for cell in row if cell) for row in t] for t in tickets]
        over = [(t, r) for t in range(6) for r in range(3) if row_counts[t][r] > 5]
        under = [(t, r) for t in range(6) for r in range(3) if row_counts[t][r] < 5]
        if not over and not under:
            break
        if over and under:
            from_t, from_r = random.choice(over)
            to_t, to_r = random.choice(under)
            for c in range(9):
                if tickets[from_t][from_r][c] and not tickets[to_t][to_r][c]:
                    tickets[to_t][to_r][c] = tickets[from_t][from_r][c]
                    tickets[from_t][from_r][c] = None
                    break
        else:
            break  # fallback to prevent infinite loop or crash


    for ticket in tickets:
        for c in range(9):
            col = [ticket[r][c] for r in range(3) if ticket[r][c]]
            col.sort()
            i = 0
            for r in range(3):
                if ticket[r][c]:
                    ticket[r][c] = col[i]
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

        # Instructions Page
        pdf.add_page()
        pdf.set_fill_color(*page_bg_color)
        pdf.rect(0, 0, W, H, 'F')
        pdf.set_text_color(*font_color)
        pdf.set_font("helvetica", 'B', 20)
        pdf.set_xy(mx, my)
        pdf.cell(W - 2 * mx, 10, 'How to Play Tambola (Housie)', align='C')
        pdf.ln(15)
        pdf.set_font("helvetica", '', 12)
        rules = [
            "Tambola (Housie) is a game of chance.",
            "Objective: Mark off numbers to form specific winning patterns.",
            "Gameplay:",
            "1. Listen to the caller. If a called number is on your ticket, mark it.",
            "2. When you complete a winning pattern, announce it immediately.",
            "Common Patterns:",
            "- Early Five: First 5 numbers marked.",
            "- Top/Middle/Bottom Line.",
            "- Full House: All 15 numbers on your ticket."
        ]
        for line in rules:
            pdf.set_x(mx)
            pdf.multi_cell(W - 2 * mx, 6, line)

        # Ticket Pages
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
                            pdf.set_xy(cx + (cw - sw) / 2.7, cy + (ch - pdf.font_size) / 2 + 1)
                            pdf.cell(sw, pdf.font_size, txt, 0)

                # Footer
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
                pdf.set_font("helvetica", 'B', 11)
                pdf.cell(tw, fh, footer_text, 0, align='C')

        output = pdf.output(dest='S') # only safe for ASCII/latin1
        return send_file(BytesIO(output), download_name="tixgen.pdf", as_attachment=True, mimetype='application/pdf')

    except Exception as e:
        logging.exception("Error during PDF generation:")
        return f"<h1>Internal Server Error</h1><p>{e}</p>", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
