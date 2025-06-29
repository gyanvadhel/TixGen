from flask import Flask, render_template, request, send_file
from io import BytesIO
import random
import math
from fpdf import FPDF
import qrcode # Import the qrcode library
from PIL import Image # Pillow is needed by qrcode to generate image objects

app = Flask(__name__)

# --- Ticket Generation Logic ---

# Column ranges and expected number counts per column
col_ranges = [list(range(1, 10))] + [list(range(i, i + 10)) for i in range(10, 80, 10)] + [list(range(80, 91))]
col_supply = [len(r) for r in col_ranges]

def generate_ticket_structure():
    for _ in range(10**6):
        pos = [[False] * 9 for _ in range(3)]
        cols2 = sorted(random.sample(range(9), 6))
        cols1 = [c for c in range(9) if c not in cols2]
        counts = [0, 0, 0]
        rows1 = random.sample([0, 1, 2], 3)
        valid = True
        for i, c in enumerate(cols1):
            r = rows1[i]
            if counts[r] < 5:
                pos[r][c] = True
                counts[r] += 1
            else:
                valid = False
                break
        if not valid:
            continue
        for c in cols2:
            avail = [r for r in range(3) if counts[r] < 5]
            if len(avail) < 2:
                valid = False
                break
            r0, r1 = random.sample(avail, 2)
            pos[r0][c] = pos[r1][c] = True
            counts[r0] += 1
            counts[r1] += 1
        if valid and all(cnt == 5 for cnt in counts) and all(any(pos[r][c] for r in range(3)) for c in range(9)):
            return pos
    raise RuntimeError("Ticket structure generation failed")

def generate_perfect_block_of_6():
    for _ in range(10**6):
        grids = [generate_ticket_structure() for _ in range(6)]
        demand = [sum(grids[t][r][c] for t in range(6) for r in range(3)) for c in range(9)]
        if demand == col_supply:
            tickets = [[[None]*9 for _ in range(3)] for _ in range(6)]
            for c in range(9):
                nums = col_ranges[c].copy()
                random.shuffle(nums)
                idx = 0
                for t in range(6):
                    for r in range(3):
                        if grids[t][r][c]:
                            tickets[t][r][c] = nums[idx]
                            idx += 1
            return tickets
    raise RuntimeError("Block generation failed")

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

@app.route('/')
def landing_page():
    # This is the new landing page route
    return render_template("landing.html")

@app.route('/generator')
def ticket_generator_page():
    # The main ticket generator form is now at /generator
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate():
    host = request.form.get('name', 'Host')
    phone = request.form.get('phone', '').strip()
    message = request.form.get('custom_message', '').strip()
    hide_ticket_number = 'hide_ticket_number' in request.form # Checkbox value

    try:
        pages = int(request.form.get('pages', 1))
    except ValueError:
        pages = 1
    pages = max(1, min(pages, 10))

    # Get colors from form
    page_bg_color = hex_to_rgb(request.form.get("page_bg_color", "#6A92CD"))
    header_fill = hex_to_rgb(request.form.get("header_color", "#658950"))
    footer_fill = header_fill # Footer color matches header
    grid_color = hex_to_rgb(request.form.get("grid_color", "#8B4513"))
    # ticket_bg_fill is now derived from header_fill as per request
    ticket_bg_fill = header_fill 
    font_color = hex_to_rgb(request.form.get("font_color", "#FFFFFF")) # New font color

    tickets = []
    blocks = math.ceil(pages * 12 / 6)
    for _ in range(blocks):
        tickets += generate_perfect_block_of_6()

    # Set up PDF
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
    th = hh + gh + fh # Exact total ticket height

    # --- Add Instructions Page ---
    pdf.add_page()
    pdf.set_fill_color(*page_bg_color)
    pdf.rect(0, 0, W, H, 'F')
    pdf.set_text_color(*font_color)

    pdf.set_font('helvetica', 'B', 20)
    pdf.set_xy(mx, my)
    pdf.cell(W - 2 * mx, 10, 'How to Play Tambola (Housie)', align='C')

    pdf.ln(15) # New line
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

            # Draw the entire ticket background first with the header/footer color
            pdf.set_fill_color(*ticket_bg_fill)
            pdf.rect(x0, y0, tw, th, style='F')

            # Header
            pdf.set_fill_color(*header_fill)
            pdf.rect(x0, y0, tw, hh, style='F')
            pdf.set_text_color(*font_color) # Use selected font color
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
            pdf.set_text_color(*font_color) # Use selected font color
            pdf.set_fill_color(*grid_color) # Cell foreground color
            pdf.set_draw_color(0, 0, 0) # Black borders for cells

            for r in range(3):
                for c in range(9):
                    cx = x0 + c * cw
                    cy = y0 + hh + r * ch
                    pdf.rect(cx, cy, cw, ch, style='F') # Fill cell background with grid_color
                    pdf.rect(cx, cy, cw, ch, style='D') # Draw cell border

                    num = data[r][c]
                    if num:
                        sw = pdf.get_string_width(str(num))
                        pdf.set_xy(cx + (cw - sw) / 2.7, cy + (ch - pdf.font_size) / 2) # Centering numbers
                        pdf.cell(sw, pdf.font_size, str(num), border=0)


            # Footer
            footer_y_start = y0 + hh + gh
            pdf.set_fill_color(*footer_fill)
            pdf.rect(x0, footer_y_start, tw, fh, style='F')
            
            pdf.set_text_color(*font_color) # Use selected font color
            pdf.set_font('helvetica', 'B', 11)

            footer_text_height = pdf.font_size
            footer_vertical_offset = (fh - footer_text_height) / 2
            
            pdf.set_xy(x0, footer_y_start + footer_vertical_offset)

            footer_text = host # As per latest image, only host in footer

            pdf.cell(tw, fh, footer_text, align='C')


    pdf_output = pdf.output(dest='S')
    pdf_bytes = pdf_output.encode('latin1') if isinstance(pdf.output(dest='S'), str) else pdf.output(dest='S')
    pdf_stream = BytesIO(pdf_bytes)
    pdf_stream.seek(0)
    return send_file(pdf_stream, download_name="tickets.pdf", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=False)
