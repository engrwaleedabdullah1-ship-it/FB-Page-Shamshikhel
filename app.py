import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from deep_translator import GoogleTranslator
import arabic_reshaper
from bidi.algorithm import get_display
import io
import textwrap
import os

# --- PAGE SETUP ---
st.set_page_config(page_title="Discover Shamshikhel Post Generator", page_icon="📱", layout="wide")

st.title("📱 Discover Shamshikhel: Post Studio")
st.markdown("Generate HD, perfectly branded Facebook posts. Select 'Auto' to let the tool decide the best layout.")

# --- UI CONTROLS ---
with st.sidebar:
    st.header("1. Post Content")
    user_text = st.text_area("Paste your news or update here:", height=150)
    language = st.selectbox("Language Translation:", ["Original Text", "English", "Urdu", "Roman Urdu"])
    
    st.header("2. Layout Options")
    size_choice = st.selectbox("Post Size:", ["Square (1080x1080)", "Landscape (1200x630)", "Portrait (1080x1350)"])
    theme = st.selectbox("Background Theme:", ["Auto (Smart Pick)", "Professional News", "Urgent Update", "Celebration", "Blank (White)"])
    
    st.header("3. Typography")
    text_color = st.selectbox("Text Color:", ["Auto", "White", "Black", "Gold", "Dark Green"])
    # The tool will auto-scale text by default
    max_font_size = st.slider("Maximum Font Size:", min_value=30, max_value=120, value=80, help="The tool will automatically shrink text to fit, but won't go larger than this.")

    generate_btn = st.button("⚙️ Generate HD Post", use_container_width=True)

# --- SMART THEME LOGIC ---
def get_theme_colors(theme_choice):
    # Returns (Background Color, Auto Text Color)
    if theme_choice == "Professional News" or theme_choice == "Auto (Smart Pick)":
        return ((10, 40, 70), "White") # Dark Blue
    elif theme_choice == "Urgent Update":
        return ((139, 0, 0), "White") # Dark Red
    elif theme_choice == "Celebration":
        return ((25, 100, 50), "Gold") # Village Green
    else: # Blank
        return ((255, 255, 255), "Black") # White

# --- TEXT WRAPPING & SCALING ENGINE ---
def draw_auto_scaled_text(draw, text, max_width, max_height, start_y, is_urdu, color, max_font):
    # Fallback to default font if the user didn't upload a .ttf file
    font_path = "urdu_font.ttf" if (is_urdu and os.path.exists("urdu_font.ttf")) else ("font.ttf" if os.path.exists("font.ttf") else None)
    
    current_size = max_font
    wrapped_lines = []
    
    # Auto-scaling loop: Shrink font until it fits the width and height
    while current_size > 20:
        if font_path:
            font = ImageFont.truetype(font_path, current_size)
        else:
            font = ImageFont.load_default()
            
        # Wrap text based on character count (rough estimation for dynamic width)
        char_width = current_size * 0.6
        wrap_width = int(max_width / char_width)
        wrapped_lines = textwrap.wrap(text, width=wrap_width)
        
        # Check height
        total_height = len(wrapped_lines) * (current_size * 1.5)
        if total_height <= max_height:
            break # It fits!
        current_size -= 5 # Shrink and try again
        
    # Draw the text
    y_text = start_y
    for line in wrapped_lines:
        # Proper Urdu right-to-left processing
        if is_urdu:
            reshaped_text = arabic_reshaper.reshape(line)
            line = get_display(reshaped_text)
            
        # Get width to center the text
        if font_path:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
        else:
            line_width = draw.textlength(line, font=font)
            
        x_text = (max_width - line_width) / 2
        
        draw.text((x_text, y_text), line, font=font, fill=color)
        y_text += (current_size * 1.5)

# --- GENERATOR ENGINE ---
if generate_btn:
    if not user_text.strip():
        st.warning("⚠️ Please enter some text first!")
    else:
        with st.spinner("Translating and designing your post..."):
            
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
                    # Translates to English first to grab context, then romanizes (Simplified for this app)
                    st.info("Note: True Roman Urdu AI translation requires advanced APIs; using standard formatting.")
                    final_text = user_text 
            except Exception as e:
                st.error(f"Translation error: {e}")

            # 2. Setup Canvas Dimensions
            if "Square" in size_choice:
                canvas_w, canvas_h = 1080, 1080
            elif "Landscape" in size_choice:
                canvas_w, canvas_h = 1200, 630
            else:
                canvas_w, canvas_h = 1080, 1350

            # 3. Setup Colors (The 'Auto' Logic)
            bg_color, suggested_text_color = get_theme_colors(theme)
            final_text_color = suggested_text_color if text_color == "Auto" else text_color
            
            # Convert color names to RGB for Pillow
            color_map = {"White": (255,255,255), "Black": (0,0,0), "Gold": (255, 215, 0), "Dark Green": (0, 100, 0)}
            rgb_text_color = color_map.get(final_text_color, (255,255,255))

            # 4. Create the Image
            img = Image.new('RGB', (canvas_w, canvas_h), color=bg_color)
            draw = ImageDraw.Draw(img)

            # 5. Place the Logo (Top Right)
            try:
                # Looks for your exact uploaded logo!
                logo = Image.open("logo.jpg").convert("RGBA") 
                
                # Resize logo perfectly based on canvas size
                logo_size = int(canvas_w * 0.15) 
                logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
                
                # Paste in top right corner with padding
                padding = 40
                img.paste(logo, (canvas_w - logo_size - padding, padding), logo)
            except FileNotFoundError:
                st.warning("⚠️ 'logo.jpg' not found in repository. Upload it to GitHub to see the watermark!")

            # 6. Draw Auto-Scaled Text
            # We constrain the text to an invisible box in the middle of the screen
            text_box_width = canvas_w - 200
            text_box_height = canvas_h - 300
            start_y = 200
            
            draw_auto_scaled_text(draw, final_text, canvas_w, text_box_height, start_y, is_urdu, rgb_text_color, max_font_size)

            # 7. Render to Screen
            st.success("✅ Post generated successfully!")
            
            # Convert image to bytes for download
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()

            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                st.image(img, caption="HD Preview", use_container_width=True)
                st.download_button(
                    label="⬇️ Download HD Post",
                    data=byte_im,
                    file_name="Shamshikhel_Post.png",
                    mime="image/png",
                    use_container_width=True
                )
