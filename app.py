import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
from deep_translator import GoogleTranslator
import arabic_reshaper
from bidi.algorithm import get_display
import io
import textwrap
import os

# --- PAGE SETUP ---
st.set_page_config(page_title="Discover Shamshikhel Post Studio", page_icon="📱", layout="wide")

st.title("📱 Discover Shamshikhel: Pro Post Studio")
st.markdown("Create stunning, perfectly branded updates with smart text scaling, rich gradients, and custom image backgrounds.")

# --- UI CONTROLS ---
with st.sidebar:
    st.header("1. Post Content")
    user_text = st.text_area("Paste your news or update here:", height=150)
    language = st.selectbox("Language Translation:", ["Original Text", "English", "Urdu", "Roman Urdu"])
    
    st.header("2. Background & Layout")
    size_choice = st.selectbox("Post Size:", ["Square (1080x1080)", "Landscape (1200x630)", "Portrait (1080x1350)"])
    
    # NEW UI FLOW: Upload is now inside the Theme dropdown!
    theme = st.selectbox("Background Theme:", [
        "Facebook Blue", 
        "Emerald News", 
        "Sunrise (Gold/Orange)", 
        "Midnight Alert", 
        "Blank (White)", 
        "Upload Custom Image" # Your requested option!
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
    max_font_size = st.slider("Maximum Font Size:", min_value=30, max_value=120, value=90)

    generate_btn = st.button("⚙️ Generate HD Post", use_container_width=True)

# --- GRAPHICS ENGINE: GRADIENTS & THEMES ---
def create_gradient_bg(width, height, color_top, color_bottom):
    base = Image.new('RGB', (width, height), color_top)
    top = Image.new('RGB', (width, height), color_bottom)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0,0), mask)
    return base

def get_theme_background(theme_choice, width, height):
    if theme_choice == "Facebook Blue":
        return create_gradient_bg(width, height, (24, 119, 242), (10, 50, 120)), "White"
    elif theme_choice == "Emerald News":
        return create_gradient_bg(width, height, (25, 135, 84), (10, 60, 35)), "White"
    elif theme_choice == "Sunrise (Gold/Orange)":
        return create_gradient_bg(width, height, (255, 165, 0), (220, 20, 60)), "White"
    elif theme_choice == "Midnight Alert":
        return create_gradient_bg(width, height, (139, 0, 0), (50, 0, 0)), "White"
    else: # Blank White
        return Image.new('RGB', (width, height), (255, 255, 255)), "Black"

# --- FONT & TEXT ENGINE ---
def get_font_path(is_urdu, style_choice):
    if is_urdu and os.path.exists("urdu_font.ttf"):
        return "urdu_font.ttf"
    style_map = {"Regular": "font_regular.ttf", "Bold": "font_bold.ttf", "Italic": "font_italic.ttf"}
    target_font = style_map.get(style_choice, "font_bold.ttf")
    if os.path.exists(target_font): return target_font
    elif os.path.exists("font_bold.ttf"): return "font_bold.ttf"
    elif os.path.exists("font_regular.ttf"): return "font_regular.ttf"
    return None

def process_and_draw_text(img_rgba, text, max_width, max_height, start_y, is_urdu, color, max_font, selected_style, overlay):
    font_path = get_font_path(is_urdu, selected_style)
    current_size = max_font
    wrapped_lines = []
    
    # 1. Auto-Scaling Logic
    while current_size > 20:
        font = ImageFont.truetype(font_path, current_size) if font_path else ImageFont.load_default()
        char_width = current_size * 0.55
        wrap_width = int(max_width / char_width)
        wrapped_lines = textwrap.wrap(text, width=wrap_width)
        
        total_text_height = len(wrapped_lines) * (current_size * 1.5)
        if total_text_height <= max_height:
            break
        current_size -= 5
        
    # 2. Draw Semi-Transparent Box Overlay (If requested)
    if overlay != "None (Direct on Image)":
        padding = 50
        box_y1 = start_y - padding
        box_y2 = start_y + total_text_height + padding
        box_x1 = (img_rgba.width - max_width) / 2 - padding
        box_x2 = box_x1 + max_width + (padding * 2)
        
        # Determine box color and force text color for contrast
        if "Dark" in overlay:
            fill_color = (0, 0, 0, 180) # 180 is transparency level
            color = (255, 255, 255) # Force white text
        else:
            fill_color = (255, 255, 255, 200)
            color = (0, 0, 0) # Force black text
            
        box_layer = Image.new('RGBA', img_rgba.size, (0,0,0,0))
        box_draw = ImageDraw.Draw(box_layer)
        
        try:
            box_draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=30, fill=fill_color)
        except AttributeError:
            box_draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill=fill_color)
            
        img_rgba = Image.alpha_composite(img_rgba, box_layer)

    # 3. Draw Text
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
        draw.text((x_text, y_text), line, font=font, fill=color)
        y_text += (current_size * 1.5)
        
    return img_rgba

# --- MAIN GENERATOR ENGINE ---
if generate_btn:
    if not user_text.strip():
        st.warning("⚠️ Please enter some text first!")
    else:
        with st.spinner("Designing your HD Post..."):
            
            # 1. Handle Translation
            final_text = user_text
            is_urdu = False
            try:
                if language == "English":
                    final_text = GoogleTranslator(source='auto', target='en').translate(user_text)
                elif language == "Urdu":
                    final_text = GoogleTranslator(source='auto', target='ur').translate(user_text)
                    is_urdu = True
                elif language == "Roman Urdu":
                    final_text = user_text 
            except Exception:
                pass

            # 2. Dimensions
            if "Square" in size_choice: canvas_w, canvas_h = 1080, 1080
            elif "Landscape" in size_choice: canvas_w, canvas_h = 1200, 630
            else: canvas_w, canvas_h = 1080, 1350

            # 3. Setup Background Canvas
            if theme == "Upload Custom Image" and bg_image_upload is not None:
                # User uploaded an image - scale it to fit the canvas perfectly
                user_img = Image.open(bg_image_upload).convert("RGBA")
                img = ImageOps.fit(user_img, (canvas_w, canvas_h), Image.LANCZOS)
                suggested_text_color = "White"
            else:
                # Use gradient themes
                img_rgb, suggested_text_color = get_theme_background(theme, canvas_w, canvas_h)
                img = img_rgb.convert("RGBA")
                
            final_text_color = suggested_text_color if text_color == "Auto" else text_color
            color_map = {"White": (255,255,255), "Black": (0,0,0), "Gold": (255, 215, 0), "Dark Green": (0, 100, 0)}
            rgb_text_color = color_map.get(final_text_color, (255,255,255))

            # 4. Draw Text and Overlay Box
            text_box_width = canvas_w - 200
            text_box_height = canvas_h - 300
            start_y = int(canvas_h * 0.25)
            
            img = process_and_draw_text(img, final_text, text_box_width, text_box_height, start_y, is_urdu, rgb_text_color, max_font_size, font_style, overlay_style)

            # 5. Place the Logo with AUTO-CIRCULAR CROPPING
            try:
                raw_logo = Image.open("logo.jpg").convert("RGBA")
            except FileNotFoundError:
                try:
                    raw_logo = Image.open("logo.png").convert("RGBA")
                except FileNotFoundError:
                    raw_logo = None
                    st.warning("⚠️ Logo file not found in GitHub. Please upload it as 'logo.jpg' or 'logo.png'.")

            if raw_logo:
                # Step A: Make it a perfect circle (Deletes white corners)
                mask = Image.new('L', raw_logo.size, 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0) + raw_logo.size, fill=255)
                circular_logo = raw_logo.copy()
                circular_logo.putalpha(mask)
                
                # Step B: Resize and Place
                logo_size = int(canvas_w * 0.15) 
                circular_logo = circular_logo.resize((logo_size, logo_size), Image.LANCZOS)
                padding = 40
                
                # Create a blank layer, paste logo, then merge so transparency works perfectly
                logo_layer = Image.new('RGBA', img.size, (0,0,0,0))
                logo_layer.paste(circular_logo, (canvas_w - logo_size - padding, padding))
                img = Image.alpha_composite(img, logo_layer)

            # 6. Render
            st.success("✅ Masterpiece generated successfully!")
            
            # Convert to pure RGB to save as JPG
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
