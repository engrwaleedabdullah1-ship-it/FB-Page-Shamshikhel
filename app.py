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
        "urdu_font.ttf": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf"
    }
    
    for filename, url in fonts_to_download.items():
        if not os.path.exists(filename):
            try:
                response = requests.get(url)
                with open(filename, 'wb') as f:
                    f.write(response.content)
            except Exception as e:
                print(f"Failed to download {filename}: {e}")

download_required_fonts()

# --- PAGE SETUP ---
st.set_page_config(page_title="Discover Shamshikhel Post Studio", page_icon="📱", layout="wide")

st.title("📱 Discover Shamshikhel: Pro Post Studio")

raqm_installed = PIL.features.check("raqm")
if raqm_installed:
    st.success("✅ OS-Level Urdu Graphics Engine (Raqm) is Active! Nastaliq script will render perfectly.")
else:
    st.error("⚠️ Urdu Engine (Raqm) not found. Streamlit is still installing packages.txt. Please wait or reboot the app.")

# --- UI CONTROLS ---
with st.sidebar:
    st.header("1. Post Content")
    
    heading_text = st.text_input("Heading (e.g. BREAKING NEWS 🚨):", placeholder="e.g. BREAKING NEWS 🚨")
    heading_language = st.selectbox("Heading Translation:", ["Original Text", "English", "Urdu", "Roman Urdu"], key="h_lang")
    
    st.markdown("---")
    
    body_text = st.text_area("Main Body Text (Emojis supported! 🌴✨):", height=120)
    body_language = st.selectbox("Body Translation:", ["Original Text", "English", "Urdu", "Roman Urdu"], key="b_lang")
    
    st.header("2. Background & Layout")
    size_choice = st.selectbox("Post Size:", ["Square (1080x1080)", "Landscape (1200x630)", "Portrait (1080x1350)"])
    
    theme = st.selectbox("Background Theme:", [
        "Breaking News (Urgent Blue/Red Gradient)", 
        "Community Update (Calm Blue Gradient)", 
        "Serious Announcement (Solid Red)", 
        "Cultural Event (Warm Orange/Gold Gradient)", 
        "Nature/Environment (Distinct Green Gradient)", 
        "Victory/Achievement (Proud Gold Gradient)", 
        "Blank White", 
        "Upload Custom Image"
    ])
    
    if theme == "Upload Custom Image":
        bg_image_upload = st.file_uploader("Upload your photo here:", type=["jpg", "png", "jpeg"])
        overlay_style = st.selectbox("Text Readability Box:", ["Semi-Transparent Dark Box", "Semi-Transparent Light Box", "None (Direct on Image)"])
    else:
        bg_image_upload = None
        overlay_style = "None (Direct on Image)"
    
    st.header("3. Typography")
    text_color = st.selectbox("Text Color:", ["Auto", "White", "Black", "Gold", "Dark Green"])
    body_font_style = st.selectbox("Body Font Style (English/Roman):", ["Regular", "Bold", "Italic"])
    
    with st.expander("🛠️ Advanced Fine-Tuning (Manual Edit)"):
        st.markdown("**Size & Positioning**")
        head_font_size = st.slider("Heading Font Size:", 20, 150, 90)
        body_font_size = st.slider("Body Font Size:", 20, 150, 60)
        text_y_offset = st.slider("Move Entire Text Block Up/Down:", -300, 300, 0, help="0 means perfectly centered automatically.")
        
        st.markdown("**Text Spacing (De-Congestion)**")
        # NEW: Spacing Controls
        line_spacing = st.slider("Line Spacing (Breathing Room):", 1.0, 3.0, 1.7, 0.1, help="Higher numbers push lines further apart. 1.7 is ideal for Urdu.")
        para_spacing = st.slider("Gap Between Heading & Body:", 0, 200, 60)

        st.markdown("**Logo Adjustments**")
        logo_scale = st.slider("Logo Size:", 50, 300, 150)
        logo_x_offset = st.slider("Move Logo Left/Right:", -500, 50, 0)
        logo_y_offset = st.slider("Move Logo Up/Down:", -50, 500, 0)

    generate_btn = st.button("⚙️ Generate HD Post", use_container_width=True)

# --- GRAPHICS ENGINE ---
def create_gradient_bg(width, height, color_top, color_bottom):
    base = Image.new('RGB', (width, height), color_top)
    top = Image.new('RGB', (width, height), color_bottom)
    mask = Image.new('L', (width, height))
    mask_data = [int(255 * (y / height)) for y in range(height) for _ in range(width)]
    mask.putdata(mask_data)
    base.paste(top, (0,0), mask)
    return base

def get_theme_background(theme_choice, width, height):
    if "Breaking News" in theme_choice:
        return create_gradient_bg(width, height, (24, 119, 242), (10, 50, 120)), "White"
    elif "Community Update" in theme_choice:
        return create_gradient_bg(width, height, (173, 216, 230), (100, 149, 237)), "Black"
    elif "Serious Announcement" in theme_choice:
        return Image.new('RGB', (width, height), (139, 0, 0)), "White"
    elif "Cultural Event" in theme_choice:
        return create_gradient_bg(width, height, (255, 140, 0), (255, 215, 0)), "White"
    elif "Nature/Environment" in theme_choice:
        return create_gradient_bg(width, height, (34, 139, 34), (0, 128, 0)), "White"
    elif "Victory/Achievement" in theme_choice:
        return create_gradient_bg(width, height, (255, 215, 0), (218, 165, 32)), "White"
    else: 
        return Image.new('RGB', (width, height), (255, 255, 255)), "Black"

def contains_urdu(text): return bool(re.search(r'[\u0600-\u06FF]', text))

def get_font_path(is_urdu, style_choice="Bold"):
    if is_urdu and os.path.exists("urdu_font.ttf"): return "urdu_font.ttf"
    style_map = {"Regular": "font_regular.ttf", "Bold": "font_bold.ttf", "Italic": "font_italic.ttf"}
    target = style_map.get(style_choice, "font_bold.ttf")
    if os.path.exists(target): return target
    elif os.path.exists("font_bold.ttf"): return "font_bold.ttf"
    elif os.path.exists("font_regular.ttf"): return "font_regular.ttf"
    return None

# --- UPGRADED DUAL-TEXT ENGINE (With Dynamic Spacing) ---
def process_and_draw_text(img_rgba, heading, body, max_width, canvas_h, y_offset, head_urdu, body_urdu, base_color, h_size, b_size, b_style, overlay, line_spacing_mult, gap_size):
    
    h_font_path = get_font_path(head_urdu, "Bold") 
    b_font_path = get_font_path(body_urdu, b_style)
    
    try: h_font = ImageFont.truetype(h_font_path, h_size) if h_font_path else ImageFont.load_default()
    except OSError: h_font = ImageFont.load_default()
        
    try: b_font = ImageFont.truetype(b_font_path, b_size) if b_font_path else ImageFont.load_default()
    except OSError: b_font = ImageFont.load_default()

    head_lines = []
    # Use the new Line Spacing Multiplier
    h_line_height = 0
    if heading:
        h_char_width = h_size * 0.55
        h_wrap_width = max(1, int(max_width / h_char_width))
        head_lines = textwrap.wrap(heading, width=h_wrap_width)
        h_line_height = h_size * line_spacing_mult

    body_lines = []
    b_line_height = 0
    if body:
        b_char_width = b_size * 0.55
        b_wrap_width = max(1, int(max_width / b_char_width))
        body_lines = textwrap.wrap(body, width=b_wrap_width)
        b_line_height = b_size * line_spacing_mult

    # Use the new Paragraph Gap variable
    gap = gap_size if (heading and body) else 0 
    total_h_height = len(head_lines) * h_line_height
    total_b_height = len(body_lines) * b_line_height
    total_text_height = total_h_height + gap + total_b_height
    
    start_y = ((canvas_h - total_text_height) / 2) + y_offset

    draw_color = base_color
    if overlay != "None (Direct on Image)" and (heading or body):
        padding = 50 # Increased padding slightly to accommodate wider line spacing
        box_y1 = start_y - padding
        box_y2 = start_y + total_text_height + padding
        box_x1 = (img_rgba.width - max_width) / 2 - padding
        box_x2 = box_x1 + max_width + (padding * 2)
        
        fill_color = (0, 0, 0, 180) if "Dark" in overlay else (255, 255, 255, 210)
        draw_color = (255, 255, 255) if "Dark" in overlay else (0, 0, 0)
            
        box_layer = Image.new('RGBA', img_rgba.size, (0,0,0,0))
        box_draw = ImageDraw.Draw(box_layer)
        try: box_draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=25, fill=fill_color)
        except AttributeError: box_draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill=fill_color)
        img_rgba = Image.alpha_composite(img_rgba, box_layer)

    draw = ImageDraw.Draw(img_rgba)
    current_y = start_y
    
    def render_line(line, y_pos, font, is_urdu_text):
        if is_urdu_text and not raqm_installed:
            reshaped = arabic_reshaper.reshape(line)
            display_line = get_display(reshaped)
        else:
            display_line = line

        bbox = draw.textbbox((0, 0), display_line, font=font)
        line_width = bbox[2] - bbox[0]
        x_text = (img_rgba.width - line_width) / 2
        
        with Pilmoji(img_rgba) as pilmoji:
            if is_urdu_text and raqm_installed:
                pilmoji.text((x_text, y_pos), line, font=font, fill=draw_color, direction='rtl', language='ur')
            else:
                pilmoji.text((x_text, y_pos), display_line, font=font, fill=draw_color)

    for line in head_lines:
        render_line(line, current_y, h_font, head_urdu)
        current_y += h_line_height
        
    current_y += gap 

    for line in body_lines:
        render_line(line, current_y, b_font, body_urdu)
        current_y += b_line_height
        
    return img_rgba

# --- MAIN GENERATOR ENGINE ---
if generate_btn:
    if not heading_text.strip() and not body_text.strip():
        st.warning("⚠️ Please enter either a Heading or Main Body text!")
    else:
        with st.spinner("Processing Professional Layout..."):
            
            final_heading = heading_text
            try:
                if heading_language == "English": final_heading = GoogleTranslator(source='auto', target='en').translate(heading_text)
                elif heading_language == "Urdu": final_heading = GoogleTranslator(source='auto', target='ur').translate(heading_text)
            except Exception: pass

            final_body = body_text
            try:
                if body_language == "English": final_body = GoogleTranslator(source='auto', target='en').translate(body_text)
                elif body_language == "Urdu": final_body = GoogleTranslator(source='auto', target='ur').translate(body_text)
            except Exception: pass

            head_is_urdu = contains_urdu(final_heading)
            body_is_urdu = contains_urdu(final_body)

            if "Square" in size_choice: canvas_w, canvas_h = 1080, 1080
            elif "Landscape" in size_choice: canvas_w, canvas_h = 1200, 630
            else: canvas_w, canvas_h = 1080, 1350

            if theme == "Upload Custom Image" and bg_image_upload is not None:
                user_img = Image.open(bg_image_upload).convert("RGBA")
                img = ImageOps.fit(user_img, (canvas_w, canvas_h), Image.LANCZOS)
                suggested_text_color = "White" 
            else:
                img_rgb, suggested_text_color = get_theme_background(theme, canvas_w, canvas_h)
                img = img_rgb.convert("RGBA")
                
            final_text_color = suggested_text_color if text_color == "Auto" else text_color
            color_map = {"White": (255,255,255), "Black": (0,0,0), "Gold": (255, 215, 0), "Dark Green": (0, 100, 0)}
            rgb_text_color = color_map.get(final_text_color, (255,255,255))

            text_box_width = canvas_w - 200
            
            # Pass the new spacing parameters to the rendering engine
            img = process_and_draw_text(
                img, final_heading, final_body, text_box_width, canvas_h, text_y_offset, 
                head_is_urdu, body_is_urdu, rgb_text_color, head_font_size, body_font_size, body_font_style, overlay_style, line_spacing, para_spacing
            )

            try: raw_logo = Image.open("logo.jpg").convert("RGBA")
            except FileNotFoundError:
                try: raw_logo = Image.open("logo.png").convert("RGBA")
                except FileNotFoundError: raw_logo = None

            if raw_logo:
                mask = Image.new('L', raw_logo.size, 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0) + raw_logo.size, fill=255)
                circular_logo = raw_logo.copy()
                circular_logo.putalpha(mask)
                
                circular_logo = circular_logo.resize((logo_scale, logo_scale), Image.LANCZOS)
                final_logo_x = (canvas_w - logo_scale - 40) + logo_x_offset
                final_logo_y = 40 + logo_y_offset
                
                logo_layer = Image.new('RGBA', img.size, (0,0,0,0))
                logo_layer.paste(circular_logo, (final_logo_x, final_logo_y))
                img = Image.alpha_composite(img, logo_layer)
            
            final_output = img.convert("RGB")
            buf = io.BytesIO()
            final_output.save(buf, format="JPEG", quality=95)
            byte_im = buf.getvalue()

            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                st.image(img, caption="HD Preview", use_container_width=True)
                st.download_button(
                    label="⬇️ Download HD Post",
                    data=byte_im,
                    file_name="Discover_Shamshikhel_Perfect.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
