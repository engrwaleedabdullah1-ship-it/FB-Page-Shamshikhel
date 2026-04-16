import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
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
        # Changed to a highly stable, cloud-friendly Urdu font (Noto Sans Arabic)
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
st.markdown("Create stunning updates. Use the **Advanced Fine-Tuning** menu to manually position your text and logo!")

# --- UI CONTROLS ---
with st.sidebar:
    st.header("1. Post Content")
    user_text = st.text_area("Paste your news or update here (Emojis supported! 🌴✨):", height=150)
    language = st.selectbox("Language Translation:", ["Original Text", "English", "Urdu", "Roman Urdu"])
    
    st.header("2. Background & Layout")
    size_choice = st.selectbox("Post Size:", ["Square (1080x1080)", "Landscape (1200x630)", "Portrait (1080x1350)"])
    
    theme = st.selectbox("Background Theme:", [
        "Facebook Blue", "Emerald News", "Sunrise (Gold/Orange)", 
        "Midnight Alert", "Blank (White)", "Upload Custom Image"
    ])
    
    if theme == "Upload Custom Image":
        bg_image_upload = st.file_uploader("Upload your photo here:", type=["jpg", "png", "jpeg"])
        overlay_style = st.selectbox("Text Readability Box:", ["Semi-Transparent Dark Box", "Semi-Transparent Light Box", "None (Direct on Image)"])
    else:
        bg_image_upload = None
        overlay_style = "None (Direct on Image)"
    
    st.header("3. Typography")
    text_color = st.selectbox("Text Color:", ["Auto", "White", "Black", "Gold", "Dark Green"])
    font_style = st.selectbox("Font Style (English/Roman):", ["Bold", "Regular", "Italic"])
    
    # NEW: ADVANCED MANUAL CONTROLS
    with st.expander("🛠️ Advanced Fine-Tuning (Manual Edit)"):
        st.markdown("**Text Adjustments**")
        manual_font_size = st.slider("Force Font Size:", 20, 150, 70)
        text_y_offset = st.slider("Move Text Up/Down:", -300, 300, 0, help="Negative moves up, positive moves down.")
        
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
    if theme_choice == "Facebook Blue": return create_gradient_bg(width, height, (24, 119, 242), (10, 50, 120)), "White"
    elif theme_choice == "Emerald News": return create_gradient_bg(width, height, (25, 135, 84), (10, 60, 35)), "White"
    elif theme_choice == "Sunrise (Gold/Orange)": return create_gradient_bg(width, height, (255, 165, 0), (220, 20, 60)), "White"
    elif theme_choice == "Midnight Alert": return create_gradient_bg(width, height, (139, 0, 0), (50, 0, 0)), "White"
    else: return Image.new('RGB', (width, height), (255, 255, 255)), "Black"

def contains_urdu(text): return bool(re.search(r'[\u0600-\u06FF]', text))

def get_font_path(is_urdu, style_choice):
    if is_urdu and os.path.exists("urdu_font.ttf"): return "urdu_font.ttf"
    style_map = {"Regular": "font_regular.ttf", "Bold": "font_bold.ttf", "Italic": "font_italic.ttf"}
    target = style_map.get(style_choice, "font_bold.ttf")
    return target if os.path.exists(target) else ("font_bold.ttf" if os.path.exists("font_bold.ttf") else None)

# --- TEXT ENGINE ---
def process_and_draw_text(img_rgba, text, max_width, start_y, is_urdu, color, manual_size, selected_style, overlay):
    font_path = get_font_path(is_urdu, selected_style)
    
    try:
        font = ImageFont.truetype(font_path, manual_size) if font_path else ImageFont.load_default()
    except OSError:
        font = ImageFont.load_default()
        font_path = None
        
    char_width = manual_size * 0.55
    wrap_width = int(max_width / char_width)
    if wrap_width < 1: wrap_width = 1 # Prevent crash on massive fonts
    wrapped_lines = textwrap.wrap(text, width=wrap_width)
    total_text_height = len(wrapped_lines) * (manual_size * 1.5)
        
    if overlay != "None (Direct on Image)":
        padding = 40
        box_y1 = start_y - padding
        box_y2 = start_y + total_text_height + padding
        box_x1 = (img_rgba.width - max_width) / 2 - padding
        box_x2 = box_x1 + max_width + (padding * 2)
        
        fill_color = (0, 0, 0, 180) if "Dark" in overlay else (255, 255, 255, 210)
        color = (255, 255, 255) if "Dark" in overlay else (0, 0, 0)
            
        box_layer = Image.new('RGBA', img_rgba.size, (0,0,0,0))
        box_draw = ImageDraw.Draw(box_layer)
        try: box_draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=25, fill=fill_color)
        except AttributeError: box_draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill=fill_color)
        img_rgba = Image.alpha_composite(img_rgba, box_layer)

    draw = ImageDraw.Draw(img_rgba)
    y_text = start_y
    for line in wrapped_lines:
        if is_urdu:
            reshaped_text = arabic_reshaper.reshape(line)
            line = get_display(reshaped_text)
            
        if font_path:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
        else:
            line_width = draw.textlength(line, font=font)
            
        x_text = (img_rgba.width - line_width) / 2
        
        with Pilmoji(img_rgba) as pilmoji:
            pilmoji.text((x_text, y_text), line, font=font, fill=color)
            
        y_text += (manual_size * 1.5)
        
    return img_rgba

# --- MAIN GENERATOR ENGINE ---
if generate_btn:
    if not user_text.strip():
        st.warning("⚠️ Please enter some text first!")
    else:
        with st.spinner("Downloading assets and designing your HD Post..."):
            
            final_text = user_text
            try:
                if language == "English": final_text = GoogleTranslator(source='auto', target='en').translate(user_text)
                elif language == "Urdu": final_text = GoogleTranslator(source='auto', target='ur').translate(user_text)
                elif language == "Roman Urdu": final_text = user_text 
            except Exception: pass

            is_urdu = contains_urdu(final_text)

            if "Square" in size_choice: 
                canvas_w, canvas_h = 1080, 1080
                base_start_y = 350
            elif "Landscape" in size_choice: 
                canvas_w, canvas_h = 1200, 630
                base_start_y = 200
            else: 
                canvas_w, canvas_h = 1080, 1350
                base_start_y = 400

            # Apply Manual Y Offset
            final_start_y = base_start_y + text_y_offset

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
            
            # Pass the manual_font_size to the text drawing engine
            img = process_and_draw_text(img, final_text, text_box_width, final_start_y, is_urdu, rgb_text_color, manual_font_size, font_style, overlay_style)

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
                
                # Apply Manual Logo Scaling and Positioning
                circular_logo = circular_logo.resize((logo_scale, logo_scale), Image.LANCZOS)
                
                base_padding_x = canvas_w - logo_scale - 40
                base_padding_y = 40
                
                final_logo_x = base_padding_x + logo_x_offset
                final_logo_y = base_padding_y + logo_y_offset
                
                logo_layer = Image.new('RGBA', img.size, (0,0,0,0))
                logo_layer.paste(circular_logo, (final_logo_x, final_logo_y))
                img = Image.alpha_composite(img, logo_layer)

            st.success("✅ Masterpiece generated successfully!")
            
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
                    file_name="Discover_Shamshikhel_Pro.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
