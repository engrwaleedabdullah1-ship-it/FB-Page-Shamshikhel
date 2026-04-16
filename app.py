import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import PIL.features 
from deep_translator import GoogleTranslator
import arabic_reshaper
from bidi.algorithm import get_display
import io
import textwrap
import os
import re
import requests 
from pilmoji import Pilmoji

# --- CLOUD-SAFE FONT DOWNLOADER ---
@st.cache_resource
def download_required_fonts():
    fonts_to_download = {
        "font_bold.ttf": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
        "font_regular.ttf": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf",
        "font_italic.ttf": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Italic.ttf",
        "urdu_font.ttf": "https://github.com/googlefonts/noto-fonts/raw/main/unhinted/ttf/NotoNastaliqUrdu/NotoNastaliqUrdu-Regular.ttf"
    }
    for filename, url in fonts_to_download.items():
        if not os.path.exists(filename):
            try:
                response = requests.get(url)
                with open(filename, 'wb') as f: f.write(response.content)
            except Exception: pass

download_required_fonts()

# --- PAGE SETUP ---
st.set_page_config(page_title="Discover Shamshikhel Post Studio", page_icon="📱", layout="wide")
st.title("📱 Discover Shamshikhel: Pro Post Studio")

# --- UI CONTROLS ---
with st.sidebar:
    st.header("1. Post Content")
    heading_text = st.text_input("Heading:", placeholder="e.g. BREAKING NEWS 🚨")
    heading_language = st.selectbox("Heading Translation:", ["Original Text", "English", "Urdu", "Roman Urdu"], key="h_lang")
    
    st.markdown("---")
    body_text = st.text_area("Main Body Text (Respects Enter keys!):", height=150)
    body_language = st.selectbox("Body Translation:", ["Original Text", "English", "Urdu", "Roman Urdu"], key="b_lang")
    
    st.header("2. Background & Layout")
    size_choice = st.selectbox("Post Size:", ["Square (1080x1080)", "Landscape (1200x630)", "Portrait (1080x1350)"])
    theme = st.selectbox("Background Theme:", ["Breaking News (Urgent Blue/Red)", "Community Update (Calm Blue)", "Serious Announcement (Solid Red)", "Cultural Event (Orange/Gold)", "Nature/Environment (Green)", "Victory (Gold)", "Blank White", "Upload Custom Image"])
    
    if theme == "Upload Custom Image":
        bg_image_upload = st.file_uploader("Upload photo:", type=["jpg", "png", "jpeg"])
        overlay_style = st.selectbox("Text Box:", ["Semi-Transparent Dark Box", "Semi-Transparent Light Box", "None"])
    else:
        bg_image_upload, overlay_style = None, "None"
    
    with st.expander("🛠️ Advanced Fine-Tuning"):
        head_font_size = st.slider("Heading Size:", 20, 150, 90)
        body_font_size = st.slider("Body Size:", 20, 150, 60)
        text_y_offset = st.slider("Move Text Up/Down:", -300, 300, 0)
        line_spacing = st.slider("Line Spacing:", 1.0, 3.0, 1.7, 0.1)
        para_spacing = st.slider("Heading/Body Gap:", 0, 200, 60)
        logo_scale = st.slider("Logo Size:", 50, 300, 150)
        logo_x_offset = st.slider("Logo L/R:", -500, 50, 0)
        logo_y_offset = st.slider("Logo U/D:", -50, 500, 0)

    generate_btn = st.button("⚙️ Generate HD Post", use_container_width=True)

# --- UTILS ---
def create_gradient_bg(w, h, c1, c2):
    base, top = Image.new('RGB', (w, h), c1), Image.new('RGB', (w, h), c2)
    mask = Image.new('L', (w, h))
    mask.putdata([int(255 * (y / h)) for y in range(h) for _ in range(w)])
    base.paste(top, (0,0), mask)
    return base

def get_theme_background(choice, w, h):
    if "Breaking" in choice: return create_gradient_bg(w, h, (24, 119, 242), (10, 50, 120)), "White"
    elif "Community" in choice: return create_gradient_bg(w, h, (173, 216, 230), (100, 149, 237)), "Black"
    elif "Serious" in choice: return Image.new('RGB', (w, h), (139, 0, 0)), "White"
    elif "Cultural" in choice: return create_gradient_bg(w, h, (255, 140, 0), (255, 215, 0)), "White"
    elif "Nature" in choice: return create_gradient_bg(w, h, (34, 139, 34), (0, 128, 0)), "White"
    elif "Victory" in choice: return create_gradient_bg(w, h, (255, 215, 0), (218, 165, 32)), "White"
    else: return Image.new('RGB', (w, h), (255, 255, 255)), "Black"

def contains_urdu(text): return bool(re.search(r'[\u0600-\u06FF]', text))

def get_font_path(is_urdu, style="Bold"):
    if is_urdu and os.path.exists("urdu_font.ttf"): return "urdu_font.ttf"
    m = {"Regular": "font_regular.ttf", "Bold": "font_bold.ttf", "Italic": "font_italic.ttf"}
    t = m.get(style, "font_bold.ttf")
    return t if os.path.exists(t) else "font_bold.ttf"

# --- LINE-BY-LINE TEXT ENGINE (THE FIX) ---
def process_and_draw_text(img, heading, body, max_width, canvas_h, y_off, h_ur, b_ur, color, h_sz, b_sz, b_st, overlay, l_spc, p_spc):
    h_font = ImageFont.truetype(get_font_path(h_ur, "Bold"), h_sz)
    b_font = ImageFont.truetype(get_font_path(b_ur, b_st), b_sz)

    # Function to preserve manual line breaks (The core fix)
    def wrap_preserve_breaks(text, font, max_w):
        lines = []
        for paragraph in text.split('\n'):
            if not paragraph.strip():
                lines.append("") # Keep empty lines
                continue
            char_w = font.size * 0.55
            wrap_w = max(1, int(max_w / char_w))
            lines.extend(textwrap.wrap(paragraph, width=wrap_w))
        return lines

    h_lines = wrap_preserve_breaks(heading, h_font, max_width) if heading else []
    b_lines = wrap_preserve_breaks(body, b_font, max_width) if body else []

    t_h_h = len(h_lines) * (h_sz * l_spc)
    t_b_h = len(b_lines) * (b_sz * l_spc)
    gap = p_spc if (heading and body) else 0
    total_h = t_h_h + gap + t_b_h
    
    start_y = ((canvas_h - total_h) / 2) + y_off

    # Draw Glass Box
    if overlay != "None" and (heading or body):
        pad = 50
        fill = (0, 0, 0, 180) if "Dark" in overlay else (255, 255, 255, 210)
        color = (255, 255, 255) if "Dark" in overlay else (0, 0, 0)
        box = Image.new('RGBA', img.size, (0,0,0,0))
        d_box = ImageDraw.Draw(box)
        d_box.rounded_rectangle([(img.width-max_width)/2-pad, start_y-pad, (img.width-max_width)/2+max_width+pad, start_y+total_h+pad], 25, fill)
        img = Image.alpha_composite(img, box)

    curr_y = start_y
    raqm = PIL.features.check("raqm")

    def draw_line(line, y, font, ur, clr):
        if not line: return
        disp = get_display(arabic_reshaper.reshape(line)) if (ur and not raqm) else line
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), disp, font=font)
        x = (img.width - (bbox[2] - bbox[0])) / 2
        with Pilmoji(img) as p:
            if ur and raqm: p.text((x, y), line, font=font, fill=clr, direction='rtl', language='ur')
            else: p.text((x, y), disp, font=font, fill=clr)

    for l in h_lines:
        draw_line(l, curr_y, h_font, h_ur, color)
        curr_y += (h_sz * l_spc)
    curr_y += gap
    for l in b_lines:
        draw_line(l, curr_y, b_font, b_ur, color)
        curr_y += (b_sz * l_spc)
    return img

# --- MAIN ENGINE ---
if generate_btn:
    if not heading_text.strip() and not body_text.strip():
        st.warning("Enter text!")
    else:
        with st.spinner("Generating..."):
            h_final, b_final = heading_text, body_text
            try:
                if heading_language == "Urdu": h_final = GoogleTranslator(source='auto', target='ur').translate(heading_text)
                if body_language == "Urdu": b_final = GoogleTranslator(source='auto', target='ur').translate(body_text)
                if heading_language == "English": h_final = GoogleTranslator(source='auto', target='en').translate(heading_text)
                if body_language == "English": b_final = GoogleTranslator(source='auto', target='en').translate(body_text)
            except: pass

            h_ur, b_ur = contains_urdu(h_final), contains_urdu(b_final)
            w, h = (1080, 1080) if "Square" in size_choice else (1200, 630) if "Landscape" in size_choice else (1080, 1350)
            
            if theme == "Upload Custom Image" and bg_image_upload:
                img = ImageOps.fit(Image.open(bg_image_upload).convert("RGBA"), (w, h), Image.LANCZOS)
                s_clr = "White"
            else:
                img_rgb, s_clr = get_theme_background(theme, w, h)
                img = img_rgb.convert("RGBA")

            c_map = {"White": (255,255,255), "Black": (0,0,0), "Gold": (255, 215, 0), "Dark Green": (0, 100, 0)}
            f_clr = c_map.get(s_clr if text_color=="Auto" else text_color, (255,255,255))

            img = process_and_draw_text(img, h_final, b_final, w-200, h, text_y_offset, h_ur, b_ur, f_clr, head_font_size, body_font_size, body_font_style, overlay_style, line_spacing, para_spacing)

            try:
                l_raw = Image.open("logo.jpg").convert("RGBA")
                mask = Image.new('L', l_raw.size, 0)
                ImageDraw.Draw(mask).ellipse((0, 0)+l_raw.size, 255)
                l_raw.putalpha(mask)
                l_res = l_raw.resize((logo_scale, logo_scale), Image.LANCZOS)
                l_lay = Image.new('RGBA', img.size, (0,0,0,0))
                l_lay.paste(l_res, (w-logo_scale-40+logo_x_offset, 40+logo_y_offset))
                img = Image.alpha_composite(img, l_lay)
            except: pass
            
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=95)
            st.image(img, use_container_width=True)
            st.download_button("⬇️ Download Post", buf.getvalue(), "post.jpg", "image/jpeg")
